"""
Memory Store - Long-term memory with vector similarity search
Signature Feature: Memory Palace for visualizing agent knowledge
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
import json
from pathlib import Path
from loguru import logger

try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not available, using in-memory fallback")


class MemoryStore:
    """
    Long-term memory storage with semantic search

    Features:
    - Vector similarity search for relevant memories
    - Persistent storage
    - Metadata filtering
    - Temporal queries
    - Memory consolidation
    """

    def __init__(self, persist_directory: str = "./data/memory"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.collection_name = "agent_memories"
        self.client = None
        self.collection = None
        self.embedder = None

        # Fallback in-memory storage
        self.memories: List[Dict] = []
        self.memory_counter = 0

    async def initialize(self):
        """Initialize the memory store"""
        logger.info("💾 Initializing memory store...")

        if CHROMADB_AVAILABLE:
            try:
                # Initialize ChromaDB
                self.client = chromadb.PersistentClient(
                    path=str(self.persist_directory),
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )

                # Get or create collection
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": "Agent long-term memories"}
                )

                # Initialize embedder
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

                logger.info("✅ ChromaDB memory store initialized")

            except Exception as e:
                logger.warning(f"Failed to initialize ChromaDB: {e}. Using fallback.")
                CHROMADB_AVAILABLE = False

        if not CHROMADB_AVAILABLE:
            logger.info("✅ Fallback in-memory store initialized")

    async def add_memory(
        self,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Add a memory to the store

        Args:
            content: Memory content
            metadata: Additional metadata

        Returns:
            Memory ID
        """
        memory_id = f"mem_{self.memory_counter}"
        self.memory_counter += 1

        metadata = metadata or {}
        metadata["timestamp"] = datetime.now().isoformat()
        metadata["memory_id"] = memory_id

        if CHROMADB_AVAILABLE and self.collection:
            try:
                # Add to ChromaDB
                self.collection.add(
                    ids=[memory_id],
                    documents=[content],
                    metadatas=[metadata]
                )
            except Exception as e:
                logger.error(f"Failed to add to ChromaDB: {e}")

        # Always add to fallback
        self.memories.append({
            "id": memory_id,
            "content": content,
            "metadata": metadata
        })

        logger.debug(f"💭 Memory stored: {memory_id}")

        return memory_id

    async def search(
        self,
        query: str,
        limit: int = 10,
        filter_metadata: Dict[str, Any] = None
    ) -> List[Dict]:
        """
        Search for relevant memories

        Args:
            query: Search query
            limit: Maximum results
            filter_metadata: Metadata filter

        Returns:
            List of relevant memories
        """
        if CHROMADB_AVAILABLE and self.collection:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=limit,
                    where=filter_metadata
                )

                memories = []
                for i in range(len(results["ids"][0])):
                    memories.append({
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else None
                    })

                return memories

            except Exception as e:
                logger.error(f"Search failed: {e}")

        # Fallback: simple keyword search
        query_lower = query.lower()
        results = []

        for memory in self.memories:
            if query_lower in memory["content"].lower():
                results.append({
                    "id": memory["id"],
                    "content": memory["content"],
                    "metadata": memory["metadata"]
                })

                if len(results) >= limit:
                    break

        return results

    async def get_recent(self, limit: int = 20) -> List[Dict]:
        """Get recent memories"""
        # Sort by timestamp
        sorted_memories = sorted(
            self.memories,
            key=lambda m: m["metadata"].get("timestamp", ""),
            reverse=True
        )

        return sorted_memories[:limit]

    async def get_by_task(self, task_id: str) -> List[Dict]:
        """Get memories for a specific task"""
        return await self.search(
            query="",
            limit=100,
            filter_metadata={"task_id": task_id}
        )

    async def consolidate_memories(self):
        """
        Consolidate and compress old memories
        This prevents the memory from growing unbounded
        """
        # Simple strategy: keep recent 1000 memories
        if len(self.memories) > 1000:
            self.memories = self.memories[-1000:]
            logger.info("🗜️ Consolidated memories")

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory store"""
        if CHROMADB_AVAILABLE and self.collection:
            count = self.collection.count()
        else:
            count = len(self.memories)

        return {
            "total_memories": count,
            "storage_type": "chromadb" if CHROMADB_AVAILABLE else "in-memory",
            "collection_name": self.collection_name
        }

    async def close(self):
        """Close the memory store"""
        logger.info("🔒 Closing memory store...")

        # Save in-memory memories to disk as backup
        backup_file = self.persist_directory / "backup.json"
        with open(backup_file, "w") as f:
            json.dump(self.memories, f, indent=2)

        logger.info("✅ Memory store closed")
