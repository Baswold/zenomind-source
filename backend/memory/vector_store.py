"""
Memory Store - Advanced long-term memory with intelligent consolidation
Signature Features:
- Memory Palace for visualizing agent knowledge
- Importance scoring for memory prioritization
- Intelligent consolidation and clustering
- Memory decay and reinforcement
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import asyncio
import json
from pathlib import Path
from loguru import logger
import math
from collections import defaultdict

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
    Advanced long-term memory storage with intelligent management

    Features:
    - Vector similarity search for relevant memories
    - Importance scoring and prioritization
    - Intelligent consolidation and clustering
    - Memory decay and reinforcement
    - Persistent storage
    - Metadata filtering
    - Temporal queries
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

        # Memory importance tracking
        self.memory_access_count: Dict[str, int] = defaultdict(int)
        self.memory_last_access: Dict[str, datetime] = {}

        # Consolidation settings
        self.consolidation_threshold = 1000  # Start consolidating after this many memories
        self.importance_threshold = 0.3  # Memories below this importance may be pruned

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

    def _calculate_importance_score(
        self,
        content: str,
        metadata: Dict[str, Any],
        access_count: int = 0
    ) -> float:
        """
        Calculate importance score for a memory

        Factors:
        - Recency (newer memories score higher)
        - Access frequency (frequently accessed memories score higher)
        - Content richness (longer, more detailed content scores higher)
        - Task success (memories from successful tasks score higher)
        - Emotional valence (error/failure memories score differently)

        Returns:
            Importance score between 0.0 and 1.0
        """
        score = 0.0

        # Recency factor (0.3 weight)
        timestamp = metadata.get("timestamp")
        if timestamp:
            try:
                memory_time = datetime.fromisoformat(timestamp)
                age_hours = (datetime.now() - memory_time).total_seconds() / 3600
                # Exponential decay: e^(-age/168) where 168 hours = 1 week
                recency_score = math.exp(-age_hours / 168)
                score += 0.3 * recency_score
            except:
                score += 0.15  # Default middle score if timestamp invalid

        # Access frequency factor (0.25 weight)
        if access_count > 0:
            # Logarithmic scaling: log(count + 1) / log(11) caps at ~10 accesses = 1.0
            frequency_score = min(math.log(access_count + 1) / math.log(11), 1.0)
            score += 0.25 * frequency_score

        # Content richness factor (0.2 weight)
        content_length = len(content)
        # 500 chars = 1.0, linearly scale
        richness_score = min(content_length / 500, 1.0)
        score += 0.2 * richness_score

        # Task success factor (0.15 weight)
        if metadata.get("success", False):
            score += 0.15
        elif metadata.get("success") is False:
            score += 0.05  # Failed tasks still have some value

        # Emotional/Error factor (0.1 weight)
        if "error" in metadata:
            score += 0.1  # Errors are important to remember
        elif metadata.get("task_id"):
            score += 0.05  # Task-related memories get small boost

        return min(score, 1.0)

    async def add_memory(
        self,
        content: str,
        metadata: Dict[str, Any] = None,
        importance: Optional[float] = None
    ) -> str:
        """
        Add a memory to the store with importance scoring

        Args:
            content: Memory content
            metadata: Additional metadata
            importance: Manual importance override (0.0-1.0)

        Returns:
            Memory ID
        """
        memory_id = f"mem_{self.memory_counter}"
        self.memory_counter += 1

        metadata = metadata or {}
        metadata["timestamp"] = datetime.now().isoformat()
        metadata["memory_id"] = memory_id

        # Calculate importance score
        if importance is not None:
            metadata["importance"] = importance
        else:
            metadata["importance"] = self._calculate_importance_score(content, metadata)

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

        # Initialize tracking
        self.memory_access_count[memory_id] = 0
        self.memory_last_access[memory_id] = datetime.now()

        logger.debug(f"💭 Memory stored: {memory_id} (importance: {metadata['importance']:.2f})")

        # Check if consolidation needed
        if len(self.memories) > self.consolidation_threshold:
            asyncio.create_task(self.consolidate_memories())

        return memory_id

    async def search(
        self,
        query: str,
        limit: int = 10,
        filter_metadata: Dict[str, Any] = None,
        min_importance: Optional[float] = None
    ) -> List[Dict]:
        """
        Search for relevant memories with importance filtering

        Args:
            query: Search query
            limit: Maximum results
            filter_metadata: Metadata filter
            min_importance: Minimum importance score (0.0-1.0)

        Returns:
            List of relevant memories, sorted by relevance and importance
        """
        if CHROMADB_AVAILABLE and self.collection:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=limit * 2,  # Get more results for importance filtering
                    where=filter_metadata
                )

                memories = []
                for i in range(len(results["ids"][0])):
                    memory_id = results["ids"][0][i]
                    metadata = results["metadatas"][0][i]

                    # Filter by importance if specified
                    if min_importance and metadata.get("importance", 0) < min_importance:
                        continue

                    # Track access
                    self.memory_access_count[memory_id] += 1
                    self.memory_last_access[memory_id] = datetime.now()

                    # Update importance based on access
                    access_count = self.memory_access_count[memory_id]
                    metadata["importance"] = self._calculate_importance_score(
                        results["documents"][0][i],
                        metadata,
                        access_count
                    )

                    memories.append({
                        "id": memory_id,
                        "content": results["documents"][0][i],
                        "metadata": metadata,
                        "distance": results["distances"][0][i] if "distances" in results else None,
                        "relevance_score": 1.0 - (results["distances"][0][i] if "distances" in results else 0)
                    })

                # Sort by combined relevance and importance
                memories.sort(
                    key=lambda m: m["relevance_score"] * 0.7 + m["metadata"]["importance"] * 0.3,
                    reverse=True
                )

                return memories[:limit]

            except Exception as e:
                logger.error(f"Search failed: {e}")

        # Fallback: simple keyword search with importance
        query_lower = query.lower()
        results = []

        for memory in self.memories:
            if query_lower in memory["content"].lower():
                memory_id = memory["id"]

                # Filter by importance
                importance = memory["metadata"].get("importance", 0)
                if min_importance and importance < min_importance:
                    continue

                # Track access
                self.memory_access_count[memory_id] += 1
                self.memory_last_access[memory_id] = datetime.now()

                results.append({
                    "id": memory_id,
                    "content": memory["content"],
                    "metadata": memory["metadata"],
                    "importance": importance
                })

        # Sort by importance
        results.sort(key=lambda m: m["importance"], reverse=True)

        return results[:limit]

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
        Intelligent memory consolidation based on importance scoring

        Strategies:
        - Prune low-importance old memories
        - Cluster similar memories
        - Reinforce frequently accessed memories
        - Keep diverse, high-value memories
        """
        if len(self.memories) < self.consolidation_threshold:
            return

        logger.info(f"🗜️ Starting intelligent memory consolidation ({len(self.memories)} memories)...")

        # Step 1: Recalculate importance for all memories
        for memory in self.memories:
            memory_id = memory["id"]
            access_count = self.memory_access_count.get(memory_id, 0)

            memory["metadata"]["importance"] = self._calculate_importance_score(
                memory["content"],
                memory["metadata"],
                access_count
            )

        # Step 2: Sort by importance
        self.memories.sort(key=lambda m: m["metadata"]["importance"], reverse=True)

        # Step 3: Identify memories to keep vs prune
        target_size = int(self.consolidation_threshold * 0.8)  # Keep 80% of threshold

        # Always keep high-importance memories
        high_importance = [m for m in self.memories if m["metadata"]["importance"] >= 0.7]

        # Keep medium-importance recent memories
        medium_importance = [
            m for m in self.memories
            if 0.3 <= m["metadata"]["importance"] < 0.7
        ][:int(target_size * 0.3)]

        # Keep some low-importance very recent memories (might become important)
        recent_cutoff = datetime.now() - timedelta(hours=24)
        low_importance_recent = [
            m for m in self.memories
            if m["metadata"]["importance"] < 0.3 and
            datetime.fromisoformat(m["metadata"]["timestamp"]) > recent_cutoff
        ][:int(target_size * 0.1)]

        # Combine kept memories
        kept_memories = high_importance + medium_importance + low_importance_recent

        # Ensure we don't exceed target
        kept_memories = kept_memories[:target_size]

        pruned_count = len(self.memories) - len(kept_memories)

        # Step 4: Update memory list
        pruned_ids = set(m["id"] for m in self.memories) - set(m["id"] for m in kept_memories)

        self.memories = kept_memories

        # Step 5: Clean up tracking data
        for memory_id in pruned_ids:
            self.memory_access_count.pop(memory_id, None)
            self.memory_last_access.pop(memory_id, None)

        logger.info(
            f"✅ Memory consolidation complete: "
            f"kept {len(kept_memories)}, pruned {pruned_count} "
            f"(high: {len(high_importance)}, medium: {len(medium_importance)}, recent: {len(low_importance_recent)})"
        )

    async def cluster_memories(self, num_clusters: int = 10) -> Dict[int, List[Dict]]:
        """
        Cluster memories by semantic similarity

        Args:
            num_clusters: Number of clusters to create

        Returns:
            Dictionary mapping cluster_id to list of memories
        """
        if len(self.memories) < num_clusters:
            return {0: self.memories}

        # Simple clustering based on metadata tags
        # In a production system, use embeddings and K-means
        clusters = defaultdict(list)

        for memory in self.memories:
            # Hash task_id or agent_id to create clusters
            task_id = memory["metadata"].get("task_id", "default")
            cluster_id = hash(task_id) % num_clusters

            clusters[cluster_id].append(memory)

        logger.info(f"📊 Clustered {len(self.memories)} memories into {len(clusters)} clusters")

        return dict(clusters)

    async def get_memory_by_importance(
        self,
        min_importance: float = 0.5,
        limit: int = 20
    ) -> List[Dict]:
        """Get memories above a certain importance threshold"""
        high_importance = [
            m for m in self.memories
            if m["metadata"].get("importance", 0) >= min_importance
        ]

        # Sort by importance descending
        high_importance.sort(
            key=lambda m: m["metadata"]["importance"],
            reverse=True
        )

        return high_importance[:limit]

    async def reinforce_memory(self, memory_id: str, boost: float = 0.1):
        """
        Reinforce a memory's importance

        Args:
            memory_id: Memory to reinforce
            boost: How much to boost importance (added to current)
        """
        for memory in self.memories:
            if memory["id"] == memory_id:
                current = memory["metadata"].get("importance", 0.5)
                memory["metadata"]["importance"] = min(current + boost, 1.0)

                logger.debug(f"💪 Reinforced memory {memory_id}: importance now {memory['metadata']['importance']:.2f}")
                break

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the memory store"""
        if CHROMADB_AVAILABLE and self.collection:
            count = self.collection.count()
        else:
            count = len(self.memories)

        # Calculate importance distribution
        importance_high = sum(1 for m in self.memories if m["metadata"].get("importance", 0) >= 0.7)
        importance_medium = sum(1 for m in self.memories if 0.3 <= m["metadata"].get("importance", 0) < 0.7)
        importance_low = sum(1 for m in self.memories if m["metadata"].get("importance", 0) < 0.3)

        # Calculate access statistics
        total_accesses = sum(self.memory_access_count.values())
        avg_accesses = total_accesses / max(len(self.memory_access_count), 1)

        # Get most accessed memories
        most_accessed = sorted(
            self.memory_access_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            "total_memories": count,
            "storage_type": "chromadb" if CHROMADB_AVAILABLE else "in-memory",
            "collection_name": self.collection_name,
            "importance_distribution": {
                "high": importance_high,
                "medium": importance_medium,
                "low": importance_low
            },
            "access_statistics": {
                "total_accesses": total_accesses,
                "average_accesses_per_memory": round(avg_accesses, 2),
                "most_accessed": [{"memory_id": mid, "access_count": count} for mid, count in most_accessed]
            },
            "consolidation_threshold": self.consolidation_threshold,
            "importance_threshold": self.importance_threshold
        }

    async def close(self):
        """Close the memory store"""
        logger.info("🔒 Closing memory store...")

        # Save in-memory memories to disk as backup
        backup_file = self.persist_directory / "backup.json"
        with open(backup_file, "w") as f:
            json.dump(self.memories, f, indent=2)

        logger.info("✅ Memory store closed")
