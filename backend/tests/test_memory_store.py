"""
Test suite for intelligent memory store
Tests importance scoring, consolidation, clustering, and more
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from memory.vector_store import MemoryStore


class TestMemoryStore:
    """Test the memory store functionality"""

    @pytest.fixture
    async def memory_store(self, tmp_path):
        """Create a fresh memory store for each test"""
        store = MemoryStore(persist_directory=str(tmp_path / "test_memory"))
        await store.initialize()
        yield store
        await store.close()

    @pytest.mark.asyncio
    async def test_add_memory_with_importance(self, memory_store):
        """Test adding memories with importance scoring"""
        memory_id = await memory_store.add_memory(
            content="Test memory content",
            metadata={"task_id": "test_1", "success": True}
        )

        assert memory_id is not None

        # Verify memory was added
        memories = await memory_store.search("Test memory", limit=1)
        assert len(memories) > 0
        assert memories[0]["content"] == "Test memory content"

        # Check importance score was calculated
        assert "importance" in memories[0]["metadata"]
        assert 0.0 <= memories[0]["metadata"]["importance"] <= 1.0

    @pytest.mark.asyncio
    async def test_importance_scoring_factors(self, memory_store):
        """Test that importance scoring considers multiple factors"""
        # Recent successful task with rich content
        mem1_id = await memory_store.add_memory(
            content="This is a very detailed and comprehensive memory with lots of useful information that should score highly due to its length and richness. " * 5,
            metadata={"task_id": "task1", "success": True, "timestamp": datetime.now().isoformat()}
        )

        # Older failed task with minimal content
        old_time = (datetime.now() - timedelta(days=30)).isoformat()
        mem2_id = await memory_store.add_memory(
            content="Short",
            metadata={"task_id": "task2", "success": False, "timestamp": old_time}
        )

        # Get both memories
        mem1 = next(m for m in memory_store.memories if m["id"] == mem1_id)
        mem2 = next(m for m in memory_store.memories if m["id"] == mem2_id)

        # Recent successful rich content should score higher
        assert mem1["metadata"]["importance"] > mem2["metadata"]["importance"]

    @pytest.mark.asyncio
    async def test_search_with_access_tracking(self, memory_store):
        """Test that searches track access counts"""
        # Add memory
        memory_id = await memory_store.add_memory(
            content="Searchable content here",
            metadata={"task_id": "test"}
        )

        # Search multiple times
        for _ in range(3):
            await memory_store.search("Searchable", limit=5)

        # Access count should increase
        assert memory_store.memory_access_count[memory_id] >= 3

    @pytest.mark.asyncio
    async def test_memory_consolidation(self, memory_store):
        """Test intelligent memory consolidation"""
        # Set low threshold for testing
        memory_store.consolidation_threshold = 20

        # Add many memories with varying importance
        for i in range(25):
            importance = 0.9 if i < 5 else (0.5 if i < 15 else 0.2)
            await memory_store.add_memory(
                content=f"Memory {i}",
                metadata={"task_id": f"task_{i}", "importance": importance}
            )

        # Manually trigger consolidation
        await memory_store.consolidate_memories()

        # Should have pruned low-importance memories
        assert len(memory_store.memories) < 25

        # High importance memories should be retained
        high_importance_count = sum(
            1 for m in memory_store.memories
            if m["metadata"]["importance"] >= 0.7
        )
        assert high_importance_count >= 5

    @pytest.mark.asyncio
    async def test_memory_clustering(self, memory_store):
        """Test memory clustering by similarity"""
        # Add memories with different task IDs
        for i in range(10):
            await memory_store.add_memory(
                content=f"Content for cluster {i % 3}",
                metadata={"task_id": f"task_{i % 3}"}
            )

        clusters = await memory_store.cluster_memories(num_clusters=3)

        # Should create clusters
        assert len(clusters) > 0
        assert sum(len(cluster) for cluster in clusters.values()) == 10

    @pytest.mark.asyncio
    async def test_memory_reinforcement(self, memory_store):
        """Test memory reinforcement"""
        memory_id = await memory_store.add_memory(
            content="Important memory",
            metadata={"importance": 0.5}
        )

        # Reinforce the memory
        await memory_store.reinforce_memory(memory_id, boost=0.2)

        # Find memory and check importance increased
        memory = next(m for m in memory_store.memories if m["id"] == memory_id)
        assert memory["metadata"]["importance"] >= 0.7

    @pytest.mark.asyncio
    async def test_get_memory_by_importance(self, memory_store):
        """Test retrieving memories by importance threshold"""
        # Add memories with different importance
        await memory_store.add_memory("Low", metadata={"importance": 0.3})
        await memory_store.add_memory("High", metadata={"importance": 0.8})
        await memory_store.add_memory("Medium", metadata={"importance": 0.5})

        high_memories = await memory_store.get_memory_by_importance(
            min_importance=0.7,
            limit=10
        )

        # Should only get high importance memories
        assert len(high_memories) >= 1
        assert all(m["metadata"]["importance"] >= 0.7 for m in high_memories)

    @pytest.mark.asyncio
    async def test_recent_memories(self, memory_store):
        """Test getting recent memories"""
        # Add memories with time delays
        for i in range(5):
            await memory_store.add_memory(
                f"Memory {i}",
                metadata={"timestamp": datetime.now().isoformat()}
            )
            await asyncio.sleep(0.1)

        recent = await memory_store.get_recent(limit=3)

        # Should get most recent 3
        assert len(recent) <= 3

        # Should be sorted by recency
        if len(recent) > 1:
            timestamps = [
                datetime.fromisoformat(m["metadata"]["timestamp"])
                for m in recent
            ]
            assert timestamps == sorted(timestamps, reverse=True)

    @pytest.mark.asyncio
    async def test_memory_stats(self, memory_store):
        """Test comprehensive memory statistics"""
        # Add various memories
        for i in range(10):
            importance = 0.8 if i < 3 else (0.5 if i < 7 else 0.2)
            await memory_store.add_memory(
                f"Memory {i}",
                metadata={"importance": importance}
            )

            # Access some memories
            if i < 5:
                memory_store.memory_access_count[f"mem_{i}"] = i + 1

        stats = await memory_store.get_memory_stats()

        assert "total_memories" in stats
        assert "importance_distribution" in stats
        assert "access_statistics" in stats

        dist = stats["importance_distribution"]
        assert dist["high"] >= 3  # Should have high importance memories
        assert dist["low"] >= 3   # Should have low importance memories

    @pytest.mark.asyncio
    async def test_search_with_importance_filter(self, memory_store):
        """Test searching with importance filtering"""
        # Add memories with different importance
        await memory_store.add_memory(
            "Important searchable content",
            metadata={"importance": 0.9, "task_id": "high"}
        )

        await memory_store.add_memory(
            "Searchable but unimportant",
            metadata={"importance": 0.2, "task_id": "low"}
        )

        # Search with importance filter
        results = await memory_store.search(
            "searchable",
            limit=10,
            min_importance=0.7
        )

        # Should only get high importance results
        for result in results:
            assert result["metadata"]["importance"] >= 0.7


@pytest.mark.asyncio
async def test_memory_persistence(tmp_path):
    """Test that memories are persisted to disk"""
    persist_dir = str(tmp_path / "persist_test")

    # Create store and add memories
    store1 = MemoryStore(persist_directory=persist_dir)
    await store1.initialize()

    await store1.add_memory("Persistent memory", metadata={"test": True})

    await store1.close()

    # Verify backup file was created
    import json
    from pathlib import Path

    backup_file = Path(persist_dir) / "backup.json"
    assert backup_file.exists()

    with open(backup_file) as f:
        data = json.load(f)
        assert len(data) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
