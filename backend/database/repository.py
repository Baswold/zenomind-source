"""
Database repository layer
Provides high-level database operations for tasks, agents, and metrics
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import uuid

from .models import Task, Agent, Metric, Memory, Plugin, TaskStatus, TaskPriority


class TaskRepository:
    """Repository for task operations"""

    @staticmethod
    async def create(db: AsyncSession, task_data: Dict[str, Any]) -> Task:
        """Create a new task"""
        # Generate task_id if not provided
        if "task_id" not in task_data:
            task_data["task_id"] = str(uuid.uuid4())

        # Convert enum strings
        if isinstance(task_data.get("priority"), str):
            task_data["priority"] = TaskPriority(task_data["priority"])
        if isinstance(task_data.get("status"), str):
            task_data["status"] = TaskStatus(task_data["status"])

        task = Task(**task_data)
        db.add(task)
        await db.flush()
        await db.refresh(task)

        logger.info(f"📝 Created task in database: {task.task_id}")
        return task

    @staticmethod
    async def get_by_id(db: AsyncSession, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        result = await db.execute(
            select(Task).where(Task.task_id == task_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        db: AsyncSession,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Task]:
        """Get all tasks with optional filtering"""
        query = select(Task)

        if status:
            query = query.where(Task.status == status)

        query = query.order_by(desc(Task.created_at)).limit(limit).offset(offset)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_status(
        db: AsyncSession,
        task_id: str,
        status: TaskStatus,
        **kwargs
    ) -> Optional[Task]:
        """Update task status"""
        task = await TaskRepository.get_by_id(db, task_id)
        if not task:
            return None

        task.status = status
        task.updated_at = datetime.utcnow()

        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)

        await db.flush()
        await db.refresh(task)

        logger.info(f"📊 Updated task {task_id} status to {status.value}")
        return task

    @staticmethod
    async def update_progress(
        db: AsyncSession,
        task_id: str,
        progress: float,
        current_step: Optional[str] = None
    ) -> Optional[Task]:
        """Update task progress"""
        task = await TaskRepository.get_by_id(db, task_id)
        if not task:
            return None

        task.progress = progress
        if current_step:
            task.current_step = current_step
        task.updated_at = datetime.utcnow()

        await db.flush()
        await db.refresh(task)

        return task

    @staticmethod
    async def complete_task(
        db: AsyncSession,
        task_id: str,
        result: str,
        success: bool = True
    ) -> Optional[Task]:
        """Mark task as completed"""
        status = TaskStatus.COMPLETED if success else TaskStatus.FAILED

        return await TaskRepository.update_status(
            db,
            task_id,
            status,
            result=result if success else None,
            error=result if not success else None,
            completed_at=datetime.utcnow(),
            progress=1.0
        )

    @staticmethod
    async def get_statistics(db: AsyncSession, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get task statistics"""
        query = select(
            Task.status,
            func.count(Task.id).label("count")
        )

        if agent_id:
            query = query.where(Task.agent_id == agent_id)

        query = query.group_by(Task.status)

        result = await db.execute(query)
        stats = {row.status.value: row.count for row in result}

        return {
            "total": sum(stats.values()),
            "by_status": stats
        }

    @staticmethod
    async def cleanup_old_tasks(
        db: AsyncSession,
        days: int = 30,
        keep_failed: bool = True
    ) -> int:
        """Clean up old completed tasks"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = delete(Task).where(
            and_(
                Task.completed_at < cutoff_date,
                Task.status == TaskStatus.COMPLETED
            )
        )

        result = await db.execute(query)
        deleted = result.rowcount

        logger.info(f"🧹 Cleaned up {deleted} old tasks")
        return deleted


class AgentRepository:
    """Repository for agent operations"""

    @staticmethod
    async def create(db: AsyncSession, agent_id: str, **kwargs) -> Agent:
        """Create a new agent"""
        agent = Agent(agent_id=agent_id, **kwargs)
        db.add(agent)
        await db.flush()
        await db.refresh(agent)

        logger.info(f"🤖 Created agent in database: {agent_id}")
        return agent

    @staticmethod
    async def get_by_id(db: AsyncSession, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        result = await db.execute(
            select(Agent).where(Agent.agent_id == agent_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_or_create(db: AsyncSession, agent_id: str, **kwargs) -> Agent:
        """Get existing agent or create new one"""
        agent = await AgentRepository.get_by_id(db, agent_id)
        if agent:
            # Update last_active_at
            agent.last_active_at = datetime.utcnow()
            await db.flush()
            await db.refresh(agent)
            return agent

        return await AgentRepository.create(db, agent_id, **kwargs)

    @staticmethod
    async def update_metrics(
        db: AsyncSession,
        agent_id: str,
        **metrics
    ) -> Optional[Agent]:
        """Update agent metrics"""
        agent = await AgentRepository.get_by_id(db, agent_id)
        if not agent:
            return None

        for key, value in metrics.items():
            if hasattr(agent, key):
                setattr(agent, key, value)

        agent.last_active_at = datetime.utcnow()

        # Recalculate success rate
        total_tasks = agent.tasks_completed + agent.tasks_failed
        if total_tasks > 0:
            agent.success_rate = agent.tasks_completed / total_tasks

        await db.flush()
        await db.refresh(agent)

        return agent

    @staticmethod
    async def increment_task_count(
        db: AsyncSession,
        agent_id: str,
        success: bool,
        duration: float
    ) -> Optional[Agent]:
        """Increment task completion count"""
        agent = await AgentRepository.get_by_id(db, agent_id)
        if not agent:
            return None

        if success:
            agent.tasks_completed += 1
        else:
            agent.tasks_failed += 1

        agent.total_execution_time += duration

        total_tasks = agent.tasks_completed + agent.tasks_failed
        if total_tasks > 0:
            agent.success_rate = agent.tasks_completed / total_tasks
            agent.average_task_duration = agent.total_execution_time / total_tasks

        agent.last_active_at = datetime.utcnow()

        await db.flush()
        await db.refresh(agent)

        return agent

    @staticmethod
    async def get_all(db: AsyncSession) -> List[Agent]:
        """Get all agents"""
        result = await db.execute(select(Agent))
        return list(result.scalars().all())


class MetricRepository:
    """Repository for metrics operations"""

    @staticmethod
    async def record(
        db: AsyncSession,
        metric_name: str,
        metric_value: float,
        metric_type: str = "gauge",
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        labels: Optional[Dict[str, Any]] = None
    ) -> Metric:
        """Record a metric"""
        metric = Metric(
            metric_name=metric_name,
            metric_value=metric_value,
            metric_type=metric_type,
            agent_id=agent_id,
            task_id=task_id,
            labels=labels or {}
        )

        db.add(metric)
        await db.flush()
        await db.refresh(metric)

        return metric

    @staticmethod
    async def get_time_series(
        db: AsyncSession,
        metric_name: str,
        agent_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Metric]:
        """Get time series data for a metric"""
        query = select(Metric).where(Metric.metric_name == metric_name)

        if agent_id:
            query = query.where(Metric.agent_id == agent_id)
        if start_time:
            query = query.where(Metric.timestamp >= start_time)
        if end_time:
            query = query.where(Metric.timestamp <= end_time)

        query = query.order_by(Metric.timestamp).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_aggregated(
        db: AsyncSession,
        metric_name: str,
        aggregation: str = "avg",  # avg, sum, min, max, count
        agent_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> float:
        """Get aggregated metric value"""
        # Map aggregation to SQL function
        agg_func = {
            "avg": func.avg,
            "sum": func.sum,
            "min": func.min,
            "max": func.max,
            "count": func.count
        }.get(aggregation, func.avg)

        query = select(agg_func(Metric.metric_value)).where(
            Metric.metric_name == metric_name
        )

        if agent_id:
            query = query.where(Metric.agent_id == agent_id)
        if start_time:
            query = query.where(Metric.timestamp >= start_time)
        if end_time:
            query = query.where(Metric.timestamp <= end_time)

        result = await db.execute(query)
        return result.scalar() or 0.0

    @staticmethod
    async def cleanup_old_metrics(
        db: AsyncSession,
        days: int = 7
    ) -> int:
        """Clean up old metrics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            delete(Metric).where(Metric.timestamp < cutoff_date)
        )

        deleted = result.rowcount
        logger.info(f"🧹 Cleaned up {deleted} old metrics")
        return deleted


class MemoryRepository:
    """Repository for memory operations"""

    @staticmethod
    async def create(
        db: AsyncSession,
        content: str,
        memory_id: Optional[str] = None,
        **kwargs
    ) -> Memory:
        """Create a new memory"""
        import hashlib

        if not memory_id:
            memory_id = f"mem_{uuid.uuid4().hex[:16]}"

        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        memory = Memory(
            memory_id=memory_id,
            content=content,
            content_hash=content_hash,
            **kwargs
        )

        db.add(memory)
        await db.flush()
        await db.refresh(memory)

        return memory

    @staticmethod
    async def get_by_id(db: AsyncSession, memory_id: str) -> Optional[Memory]:
        """Get memory by ID"""
        result = await db.execute(
            select(Memory).where(Memory.memory_id == memory_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_recent(
        db: AsyncSession,
        limit: int = 20,
        memory_type: Optional[str] = None
    ) -> List[Memory]:
        """Get recent memories"""
        query = select(Memory).order_by(desc(Memory.created_at)).limit(limit)

        if memory_type:
            query = query.where(Memory.memory_type == memory_type)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def increment_access(db: AsyncSession, memory_id: str) -> Optional[Memory]:
        """Increment access count for a memory"""
        memory = await MemoryRepository.get_by_id(db, memory_id)
        if not memory:
            return None

        memory.access_count += 1
        memory.accessed_at = datetime.utcnow()

        await db.flush()
        await db.refresh(memory)

        return memory


class PluginRepository:
    """Repository for plugin operations"""

    @staticmethod
    async def create(db: AsyncSession, plugin_data: Dict[str, Any]) -> Plugin:
        """Create a new plugin"""
        plugin = Plugin(**plugin_data)
        db.add(plugin)
        await db.flush()
        await db.refresh(plugin)

        logger.info(f"🔌 Installed plugin: {plugin.plugin_id}")
        return plugin

    @staticmethod
    async def get_by_id(db: AsyncSession, plugin_id: str) -> Optional[Plugin]:
        """Get plugin by ID"""
        result = await db.execute(
            select(Plugin).where(Plugin.plugin_id == plugin_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_enabled(db: AsyncSession) -> List[Plugin]:
        """Get all enabled plugins"""
        result = await db.execute(
            select(Plugin).where(Plugin.enabled == True)
        )
        return list(result.scalars().all())

    @staticmethod
    async def toggle_enabled(
        db: AsyncSession,
        plugin_id: str,
        enabled: bool
    ) -> Optional[Plugin]:
        """Enable or disable a plugin"""
        plugin = await PluginRepository.get_by_id(db, plugin_id)
        if not plugin:
            return None

        plugin.enabled = enabled
        await db.flush()
        await db.refresh(plugin)

        logger.info(f"🔌 Plugin {plugin_id} {'enabled' if enabled else 'disabled'}")
        return plugin

    @staticmethod
    async def record_usage(
        db: AsyncSession,
        plugin_id: str,
        success: bool
    ) -> Optional[Plugin]:
        """Record plugin usage"""
        plugin = await PluginRepository.get_by_id(db, plugin_id)
        if not plugin:
            return None

        plugin.usage_count += 1
        if success:
            plugin.success_count += 1
        else:
            plugin.failure_count += 1

        plugin.last_used_at = datetime.utcnow()

        await db.flush()
        await db.refresh(plugin)

        return plugin
