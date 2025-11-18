"""
Task Queue - Advanced priority-based task queue with intelligent scheduling
Enables hours-long autonomous operation with dependency management
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from loguru import logger
import asyncio
import heapq
from enum import Enum
from dataclasses import dataclass, field


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 0  # Highest priority
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4  # Lowest priority


class TaskStatus(Enum):
    """Task execution status"""
    QUEUED = "queued"
    WAITING_DEPENDENCIES = "waiting_dependencies"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


@dataclass(order=True)
class PrioritizedTask:
    """Task with priority for heap queue"""
    priority: int
    created_at: datetime = field(compare=False)
    task_id: str = field(compare=False)

    def __lt__(self, other):
        # First compare by priority
        if self.priority != other.priority:
            return self.priority < other.priority
        # If same priority, older tasks first (FIFO within priority)
        return self.created_at < other.created_at


class AdvancedTaskQueue:
    """
    Advanced async task queue with:
    - Priority-based scheduling
    - Task dependencies
    - Automatic retry logic
    - Resource limits and throttling
    - Deadline scheduling
    - Task cancellation and cleanup
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 3,
        default_timeout: int = 1800,
        max_retries: int = 3,
        retry_delay: int = 5
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Task storage
        self.tasks: Dict[str, Dict[str, Any]] = {}

        # Priority queue (min heap)
        self.task_queue: List[PrioritizedTask] = []

        # Running tasks
        self.running_tasks: Dict[str, asyncio.Task] = {}

        # Task dependencies
        self.task_dependencies: Dict[str, List[str]] = {}  # task_id -> [dependent_task_ids]
        self.task_dependents: Dict[str, List[str]] = {}    # task_id -> [tasks waiting on this]

        # Scheduler control
        self.scheduler_running = False
        self.scheduler_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats = {
            "total_enqueued": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_cancelled": 0,
            "total_timeout": 0,
            "total_retries": 0,
        }

    async def enqueue(
        self,
        task_id: str,
        coroutine: Callable,
        priority: str = "medium",
        max_duration: Optional[int] = None,
        dependencies: Optional[List[str]] = None,
        deadline: Optional[datetime] = None,
        retry_on_failure: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Enqueue a task for execution

        Args:
            task_id: Unique task identifier
            coroutine: Async coroutine or callable to execute
            priority: Task priority (critical, high, medium, low, background)
            max_duration: Maximum execution time in seconds (None = use default)
            dependencies: List of task IDs this task depends on
            deadline: Absolute deadline for task completion
            retry_on_failure: Whether to retry on failure
            metadata: Additional metadata
        """
        # Convert string priority to enum
        priority_map = {
            "critical": TaskPriority.CRITICAL,
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW,
            "background": TaskPriority.BACKGROUND
        }
        priority_enum = priority_map.get(priority.lower(), TaskPriority.MEDIUM)

        # Create task info
        created_at = datetime.now()
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": TaskStatus.QUEUED.value,
            "priority": priority,
            "priority_value": priority_enum.value,
            "max_duration": max_duration or self.default_timeout,
            "created_at": created_at,
            "started_at": None,
            "completed_at": None,
            "deadline": deadline,
            "result": None,
            "error": None,
            "retry_count": 0,
            "retry_on_failure": retry_on_failure,
            "coroutine": coroutine,
            "metadata": metadata or {},
            "execution_history": []
        }

        # Handle dependencies
        if dependencies:
            self.task_dependencies[task_id] = dependencies
            for dep_id in dependencies:
                if dep_id not in self.task_dependents:
                    self.task_dependents[dep_id] = []
                self.task_dependents[dep_id].append(task_id)

            # Check if dependencies are met
            if not await self._check_dependencies(task_id):
                self.tasks[task_id]["status"] = TaskStatus.WAITING_DEPENDENCIES.value
                logger.info(f"📋 Task queued (waiting on dependencies): {task_id}")
                self.stats["total_enqueued"] += 1
                return

        # Add to priority queue
        prioritized = PrioritizedTask(
            priority=priority_enum.value,
            created_at=created_at,
            task_id=task_id
        )
        heapq.heappush(self.task_queue, prioritized)

        logger.info(f"📋 Task queued: {task_id} (priority: {priority})")
        self.stats["total_enqueued"] += 1

        # Start scheduler if not running
        if not self.scheduler_running:
            await self.start_scheduler()

    async def _check_dependencies(self, task_id: str) -> bool:
        """Check if all dependencies for a task are completed"""
        dependencies = self.task_dependencies.get(task_id, [])

        for dep_id in dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task["status"] != TaskStatus.COMPLETED.value:
                return False

        return True

    async def start_scheduler(self):
        """Start the task scheduler"""
        if self.scheduler_running:
            return

        self.scheduler_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("🚀 Task scheduler started")

    async def stop_scheduler(self):
        """Stop the task scheduler"""
        self.scheduler_running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Task scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop - processes tasks from priority queue"""
        while self.scheduler_running:
            try:
                # Check if we can run more tasks
                if len(self.running_tasks) < self.max_concurrent_tasks and self.task_queue:
                    # Get highest priority task
                    prioritized = heapq.heappop(self.task_queue)
                    task_id = prioritized.task_id

                    # Verify task still exists and is queued
                    task_info = self.tasks.get(task_id)
                    if task_info and task_info["status"] == TaskStatus.QUEUED.value:
                        # Start task execution
                        asyncio.create_task(self._execute_task_with_retry(task_id))

                # Small sleep to prevent busy waiting
                await asyncio.sleep(0.1)

            except IndexError:
                # Queue is empty
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(1)

    async def _execute_task_with_retry(self, task_id: str):
        """Execute a task with automatic retry logic"""
        task_info = self.tasks.get(task_id)
        if not task_info:
            return

        max_retries = self.max_retries if task_info["retry_on_failure"] else 0

        for attempt in range(max_retries + 1):
            if attempt > 0:
                task_info["status"] = TaskStatus.RETRYING.value
                task_info["retry_count"] = attempt
                self.stats["total_retries"] += 1
                logger.info(f"🔄 Retrying task {task_id} (attempt {attempt + 1}/{max_retries + 1})")
                await asyncio.sleep(self.retry_delay * attempt)  # Exponential backoff

            success = await self._execute_task(task_id)

            if success:
                break

            if attempt < max_retries:
                task_info["execution_history"].append({
                    "attempt": attempt + 1,
                    "status": "failed",
                    "error": task_info.get("error"),
                    "timestamp": datetime.now().isoformat()
                })

    async def _execute_task(self, task_id: str) -> bool:
        """
        Execute a single task

        Returns:
            True if successful, False if failed
        """
        task_info = self.tasks.get(task_id)
        if not task_info:
            return False

        task_info["status"] = TaskStatus.RUNNING.value
        task_info["started_at"] = datetime.now()

        # Create asyncio task
        coroutine = task_info["coroutine"]
        if callable(coroutine):
            coroutine = coroutine()

        task = asyncio.create_task(coroutine)
        self.running_tasks[task_id] = task

        try:
            # Check for deadline
            timeout = task_info["max_duration"]
            if task_info["deadline"]:
                remaining = (task_info["deadline"] - datetime.now()).total_seconds()
                timeout = min(timeout, max(remaining, 1))

            result = await asyncio.wait_for(task, timeout=timeout)

            task_info["status"] = TaskStatus.COMPLETED.value
            task_info["result"] = result
            task_info["completed_at"] = datetime.now()

            logger.info(f"✅ Task completed: {task_id}")
            self.stats["total_completed"] += 1

            # Process dependent tasks
            await self._process_dependents(task_id)

            return True

        except asyncio.TimeoutError:
            task_info["status"] = TaskStatus.TIMEOUT.value
            task_info["error"] = "Task exceeded maximum duration"
            task_info["completed_at"] = datetime.now()

            logger.warning(f"⏱️ Task timeout: {task_id}")
            self.stats["total_timeout"] += 1

            return False

        except asyncio.CancelledError:
            task_info["status"] = TaskStatus.CANCELLED.value
            task_info["completed_at"] = datetime.now()

            logger.info(f"🛑 Task cancelled: {task_id}")
            self.stats["total_cancelled"] += 1

            return False

        except Exception as e:
            task_info["status"] = TaskStatus.FAILED.value
            task_info["error"] = str(e)
            task_info["completed_at"] = datetime.now()

            logger.error(f"❌ Task failed: {task_id} - {str(e)}")
            self.stats["total_failed"] += 1

            return False

        finally:
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

    async def _process_dependents(self, completed_task_id: str):
        """Process tasks that were waiting on this task"""
        dependents = self.task_dependents.get(completed_task_id, [])

        for dependent_id in dependents:
            task_info = self.tasks.get(dependent_id)
            if not task_info:
                continue

            if task_info["status"] == TaskStatus.WAITING_DEPENDENCIES.value:
                # Check if all dependencies are now met
                if await self._check_dependencies(dependent_id):
                    # Add to queue
                    task_info["status"] = TaskStatus.QUEUED.value
                    prioritized = PrioritizedTask(
                        priority=task_info["priority_value"],
                        created_at=task_info["created_at"],
                        task_id=dependent_id
                    )
                    heapq.heappush(self.task_queue, prioritized)
                    logger.info(f"📋 Task dependencies met, queued: {dependent_id}")

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task

        Returns:
            True if cancelled, False if task not found or already completed
        """
        task_info = self.tasks.get(task_id)
        if not task_info:
            return False

        status = task_info["status"]

        # Can't cancel completed/failed/cancelled tasks
        if status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value,
                      TaskStatus.CANCELLED.value, TaskStatus.TIMEOUT.value]:
            return False

        # Cancel running task
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()

        # Remove from queue if queued
        if status == TaskStatus.QUEUED.value:
            # Rebuild heap without this task (inefficient but simple)
            self.task_queue = [pt for pt in self.task_queue if pt.task_id != task_id]
            heapq.heapify(self.task_queue)

        task_info["status"] = TaskStatus.CANCELLED.value
        task_info["completed_at"] = datetime.now()

        logger.info(f"🛑 Task cancelled: {task_id}")
        self.stats["total_cancelled"] += 1

        return True

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        task = self.tasks.get(task_id)
        if not task:
            return None

        # Return clean copy without coroutine
        task_copy = task.copy()
        task_copy.pop("coroutine", None)
        return task_copy

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks (without coroutines)"""
        tasks = []
        for task in self.tasks.values():
            task_copy = task.copy()
            task_copy.pop("coroutine", None)
            tasks.append(task_copy)
        return tasks

    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue statistics and status"""
        return {
            "scheduler_running": self.scheduler_running,
            "queued_tasks": len(self.task_queue),
            "running_tasks": len(self.running_tasks),
            "max_concurrent": self.max_concurrent_tasks,
            "total_tasks": len(self.tasks),
            "statistics": self.stats.copy()
        }

    def get_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all tasks with a specific status"""
        matching = []
        for task in self.tasks.values():
            if task["status"] == status:
                task_copy = task.copy()
                task_copy.pop("coroutine", None)
                matching.append(task_copy)
        return matching

    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Optional[Any]:
        """
        Wait for a task to complete

        Returns:
            Task result if successful, None if failed/timeout
        """
        start_time = datetime.now()

        while True:
            task_info = self.tasks.get(task_id)
            if not task_info:
                return None

            status = task_info["status"]

            if status == TaskStatus.COMPLETED.value:
                return task_info["result"]

            if status in [TaskStatus.FAILED.value, TaskStatus.CANCELLED.value, TaskStatus.TIMEOUT.value]:
                return None

            if timeout:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout:
                    raise asyncio.TimeoutError(f"Timeout waiting for task {task_id}")

            await asyncio.sleep(0.1)

    async def clear_completed_tasks(self, older_than_hours: int = 24):
        """Clear completed tasks older than specified hours"""
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        to_remove = []

        for task_id, task_info in self.tasks.items():
            if task_info["status"] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value,
                                       TaskStatus.CANCELLED.value, TaskStatus.TIMEOUT.value]:
                if task_info.get("completed_at") and task_info["completed_at"] < cutoff:
                    to_remove.append(task_id)

        for task_id in to_remove:
            del self.tasks[task_id]
            # Clean up dependencies
            self.task_dependencies.pop(task_id, None)
            self.task_dependents.pop(task_id, None)

        if to_remove:
            logger.info(f"🧹 Cleared {len(to_remove)} old completed tasks")

        return len(to_remove)


# Global task queue instance with advanced features
task_queue = AdvancedTaskQueue(
    max_concurrent_tasks=3,
    default_timeout=1800,
    max_retries=3,
    retry_delay=5
)
