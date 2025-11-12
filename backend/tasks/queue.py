"""
Task Queue - Long-running task execution with Dramatiq
Enables hours-long autonomous operation
"""

from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger
import asyncio

# Simplified task queue without Redis dependency for now
# In production, use Dramatiq + Redis for distributed task queue


class TaskQueue:
    """
    Simple async task queue for long-running operations

    In production, replace with:
    - Dramatiq for task execution
    - Redis for queue backend
    - Celery as alternative
    """

    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}

    async def enqueue(
        self,
        task_id: str,
        coroutine,
        priority: str = "medium",
        max_duration: int = 1800
    ):
        """
        Enqueue a task for execution

        Args:
            task_id: Unique task identifier
            coroutine: Async coroutine to execute
            priority: Task priority (low, medium, high, critical)
            max_duration: Maximum execution time in seconds
        """
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": "queued",
            "priority": priority,
            "max_duration": max_duration,
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }

        # Execute task
        task = asyncio.create_task(self._execute_task(task_id, coroutine, max_duration))
        self.running_tasks[task_id] = task

        logger.info(f"📋 Task queued: {task_id} (priority: {priority})")

    async def _execute_task(self, task_id: str, coroutine, max_duration: int):
        """Execute a task with timeout"""
        task_info = self.tasks[task_id]
        task_info["status"] = "running"
        task_info["started_at"] = datetime.now()

        try:
            result = await asyncio.wait_for(coroutine, timeout=max_duration)
            task_info["status"] = "completed"
            task_info["result"] = result
            task_info["completed_at"] = datetime.now()

            logger.info(f"✅ Task completed: {task_id}")

        except asyncio.TimeoutError:
            task_info["status"] = "timeout"
            task_info["error"] = "Task exceeded maximum duration"
            task_info["completed_at"] = datetime.now()

            logger.warning(f"⏱️ Task timeout: {task_id}")

        except Exception as e:
            task_info["status"] = "failed"
            task_info["error"] = str(e)
            task_info["completed_at"] = datetime.now()

            logger.error(f"❌ Task failed: {task_id} - {str(e)}")

        finally:
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all tasks"""
        return self.tasks

    async def cancel_task(self, task_id: str):
        """Cancel a running task"""
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            self.tasks[task_id]["status"] = "cancelled"
            self.tasks[task_id]["completed_at"] = datetime.now()

            logger.info(f"🛑 Task cancelled: {task_id}")


# Global task queue instance
task_queue = TaskQueue()
