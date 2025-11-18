"""
Test suite for advanced task queue system
Tests priority scheduling, dependencies, retry logic, and more
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from tasks.queue import AdvancedTaskQueue, TaskPriority, TaskStatus


class TestAdvancedTaskQueue:
    """Test the advanced task queue functionality"""

    @pytest.fixture
    async def queue(self):
        """Create a fresh task queue for each test"""
        q = AdvancedTaskQueue(
            max_concurrent_tasks=2,
            default_timeout=10,
            max_retries=2,
            retry_delay=1
        )
        yield q
        await q.stop_scheduler()

    @pytest.mark.asyncio
    async def test_basic_enqueue_and_execution(self, queue):
        """Test basic task enqueueing and execution"""
        result_container = []

        async def simple_task():
            await asyncio.sleep(0.1)
            result_container.append("completed")
            return "success"

        task_id = "test_task_1"
        await queue.enqueue(
            task_id=task_id,
            coroutine=simple_task,
            priority="high"
        )

        # Wait for task to complete
        result = await queue.wait_for_task(task_id, timeout=5)

        assert result == "success"
        assert result_container == ["completed"]

        task_status = queue.get_task_status(task_id)
        assert task_status["status"] == TaskStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_priority_scheduling(self, queue):
        """Test that tasks are executed in priority order"""
        execution_order = []

        async def task_with_id(task_id):
            execution_order.append(task_id)
            await asyncio.sleep(0.1)

        # Enqueue tasks with different priorities
        # Lower priority value = higher priority
        await queue.enqueue("low", lambda: task_with_id("low"), priority="low")
        await queue.enqueue("critical", lambda: task_with_id("critical"), priority="critical")
        await queue.enqueue("medium", lambda: task_with_id("medium"), priority="medium")
        await queue.enqueue("high", lambda: task_with_id("high"), priority="high")

        # Wait for all tasks to complete
        await asyncio.sleep(2)

        # Critical and high should execute before medium and low
        assert execution_order.index("critical") < execution_order.index("low")
        assert execution_order.index("high") < execution_order.index("low")

    @pytest.mark.asyncio
    async def test_task_dependencies(self, queue):
        """Test task dependency resolution"""
        execution_order = []

        async def dependent_task(task_id):
            execution_order.append(task_id)
            await asyncio.sleep(0.1)

        # Create tasks with dependencies
        await queue.enqueue("task_1", lambda: dependent_task("task_1"), priority="medium")
        await queue.enqueue(
            "task_2",
            lambda: dependent_task("task_2"),
            priority="medium",
            dependencies=["task_1"]
        )
        await queue.enqueue(
            "task_3",
            lambda: dependent_task("task_3"),
            priority="medium",
            dependencies=["task_2"]
        )

        # Wait for completion
        await asyncio.sleep(3)

        # Tasks should execute in dependency order
        assert execution_order == ["task_1", "task_2", "task_3"]

    @pytest.mark.asyncio
    async def test_retry_logic(self, queue):
        """Test automatic retry on failure"""
        attempt_counter = {"count": 0}

        async def failing_task():
            attempt_counter["count"] += 1
            if attempt_counter["count"] < 3:
                raise Exception("Temporary failure")
            return "success after retries"

        task_id = "retry_test"
        await queue.enqueue(
            task_id=task_id,
            coroutine=failing_task,
            priority="medium",
            retry_on_failure=True
        )

        result = await queue.wait_for_task(task_id, timeout=10)

        assert result == "success after retries"
        assert attempt_counter["count"] == 3

        task_status = queue.get_task_status(task_id)
        assert task_status["retry_count"] > 0

    @pytest.mark.asyncio
    async def test_task_timeout(self, queue):
        """Test task timeout handling"""
        async def long_running_task():
            await asyncio.sleep(20)  # Longer than queue timeout
            return "should not complete"

        task_id = "timeout_test"
        await queue.enqueue(
            task_id=task_id,
            coroutine=long_running_task,
            priority="medium",
            max_duration=1  # 1 second timeout
        )

        await asyncio.sleep(3)

        task_status = queue.get_task_status(task_id)
        assert task_status["status"] == TaskStatus.TIMEOUT.value

    @pytest.mark.asyncio
    async def test_task_cancellation(self, queue):
        """Test task cancellation"""
        async def cancellable_task():
            await asyncio.sleep(10)
            return "should be cancelled"

        task_id = "cancel_test"
        await queue.enqueue(
            task_id=task_id,
            coroutine=cancellable_task,
            priority="medium"
        )

        await asyncio.sleep(0.5)  # Let task start

        cancelled = await queue.cancel_task(task_id)
        assert cancelled is True

        task_status = queue.get_task_status(task_id)
        assert task_status["status"] == TaskStatus.CANCELLED.value

    @pytest.mark.asyncio
    async def test_concurrent_execution_limit(self, queue):
        """Test that concurrent task limit is respected"""
        active_tasks = {"count": 0, "max_concurrent": 0}

        async def tracking_task():
            active_tasks["count"] += 1
            active_tasks["max_concurrent"] = max(
                active_tasks["max_concurrent"],
                active_tasks["count"]
            )
            await asyncio.sleep(0.5)
            active_tasks["count"] -= 1

        # Enqueue more tasks than the concurrent limit
        for i in range(5):
            await queue.enqueue(
                f"task_{i}",
                tracking_task,
                priority="medium"
            )

        await asyncio.sleep(3)

        # Should never exceed max_concurrent_tasks (set to 2 in fixture)
        assert active_tasks["max_concurrent"] <= 2

    @pytest.mark.asyncio
    async def test_deadline_scheduling(self, queue):
        """Test deadline-based task execution"""
        async def deadline_task():
            await asyncio.sleep(0.1)
            return "completed"

        near_deadline = datetime.now() + timedelta(seconds=2)
        far_deadline = datetime.now() + timedelta(seconds=10)

        task_id_1 = "deadline_soon"
        task_id_2 = "deadline_later"

        await queue.enqueue(
            task_id_1,
            deadline_task,
            priority="low",
            deadline=near_deadline
        )

        await queue.enqueue(
            task_id_2,
            deadline_task,
            priority="low",
            deadline=far_deadline
        )

        await asyncio.sleep(3)

        # Both should complete, but near deadline should complete first
        status_1 = queue.get_task_status(task_id_1)
        status_2 = queue.get_task_status(task_id_2)

        assert status_1["status"] == TaskStatus.COMPLETED.value
        # Deadline affects timeout calculation

    @pytest.mark.asyncio
    async def test_queue_statistics(self, queue):
        """Test queue statistics tracking"""
        async def simple_task():
            await asyncio.sleep(0.1)

        # Create various task outcomes
        await queue.enqueue("success_1", simple_task, priority="medium")

        async def failing_task():
            raise Exception("Test failure")

        await queue.enqueue("fail_1", failing_task, priority="medium", retry_on_failure=False)

        await asyncio.sleep(2)

        stats = queue.get_queue_status()

        assert stats["statistics"]["total_enqueued"] >= 2
        assert stats["statistics"]["total_completed"] >= 1
        assert stats["statistics"]["total_failed"] >= 1

    @pytest.mark.asyncio
    async def test_task_history(self, queue):
        """Test execution history tracking for retries"""
        attempt_count = {"count": 0}

        async def flaky_task():
            attempt_count["count"] += 1
            if attempt_count["count"] < 2:
                raise Exception("Flaky failure")
            return "eventually succeeds"

        task_id = "history_test"
        await queue.enqueue(
            task_id,
            flaky_task,
            priority="medium",
            retry_on_failure=True
        )

        await queue.wait_for_task(task_id, timeout=10)

        task_status = queue.get_task_status(task_id)
        assert "execution_history" in task_status
        assert len(task_status["execution_history"]) > 0


@pytest.mark.asyncio
async def test_clear_completed_tasks():
    """Test clearing old completed tasks"""
    queue = AdvancedTaskQueue()

    async def quick_task():
        return "done"

    # Add some tasks
    for i in range(5):
        await queue.enqueue(f"task_{i}", quick_task, priority="medium")

    await asyncio.sleep(2)

    initial_count = len(queue.get_all_tasks())

    # Clear very old tasks (won't clear anything recent)
    cleared = await queue.clear_completed_tasks(older_than_hours=1)

    # Should not clear anything since tasks are brand new
    assert cleared == 0

    await queue.stop_scheduler()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
