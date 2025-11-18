"""
System Analytics and Metrics API
Comprehensive monitoring and performance tracking endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import psutil
import platform
from loguru import logger

from tasks.queue import task_queue
from memory.vector_store import MemoryStore
from agents.orchestrator import AgentOrchestrator


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class SystemMetrics(BaseModel):
    """System resource metrics"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_usage_percent: float
    disk_used_gb: float
    disk_total_gb: float
    platform: str
    python_version: str
    uptime_seconds: float


class TaskMetrics(BaseModel):
    """Task execution metrics"""
    total_tasks: int
    queued_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    timeout_tasks: int
    retry_count: int
    success_rate: float
    average_execution_time: Optional[float]
    tasks_per_hour: float


class MemoryMetrics(BaseModel):
    """Memory system metrics"""
    total_memories: int
    high_importance: int
    medium_importance: int
    low_importance: int
    total_accesses: int
    average_accesses: float
    storage_type: str
    consolidation_threshold: int


class AgentMetrics(BaseModel):
    """Agent orchestration metrics"""
    total_orchestrations: int
    successful_orchestrations: int
    failed_orchestrations: int
    success_rate: float
    average_agents_used: float
    total_agents_created: int
    active_agents: int


class PerformanceSnapshot(BaseModel):
    """Complete system performance snapshot"""
    timestamp: datetime
    system: SystemMetrics
    tasks: TaskMetrics
    memory: MemoryMetrics
    agents: Optional[AgentMetrics]


# Track system start time
system_start_time = datetime.now()

# Performance history (keep last 100 snapshots)
performance_history: List[Dict[str, Any]] = []


async def get_system_metrics() -> SystemMetrics:
    """Get current system resource metrics"""
    # CPU and Memory
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()

    # Disk
    disk = psutil.disk_usage('/')

    # Uptime
    uptime = (datetime.now() - system_start_time).total_seconds()

    return SystemMetrics(
        cpu_percent=round(cpu_percent, 2),
        memory_percent=round(memory.percent, 2),
        memory_used_mb=round(memory.used / 1024 / 1024, 2),
        memory_total_mb=round(memory.total / 1024 / 1024, 2),
        disk_usage_percent=round(disk.percent, 2),
        disk_used_gb=round(disk.used / 1024 / 1024 / 1024, 2),
        disk_total_gb=round(disk.total / 1024 / 1024 / 1024, 2),
        platform=platform.platform(),
        python_version=platform.python_version(),
        uptime_seconds=round(uptime, 2)
    )


async def get_task_metrics() -> TaskMetrics:
    """Get task execution metrics"""
    queue_status = task_queue.get_queue_status()
    stats = queue_status["statistics"]

    total = queue_status["total_tasks"]
    completed = stats["total_completed"]

    # Calculate success rate
    attempted = completed + stats["total_failed"] + stats["total_timeout"]
    success_rate = (completed / attempted * 100) if attempted > 0 else 0.0

    # Calculate tasks per hour
    uptime_hours = (datetime.now() - system_start_time).total_seconds() / 3600
    tasks_per_hour = stats["total_enqueued"] / uptime_hours if uptime_hours > 0 else 0.0

    # Calculate average execution time
    all_tasks = task_queue.get_all_tasks()
    execution_times = []
    for task in all_tasks:
        if task.get("started_at") and task.get("completed_at"):
            started = datetime.fromisoformat(task["started_at"])
            completed_at = datetime.fromisoformat(task["completed_at"])
            execution_times.append((completed_at - started).total_seconds())

    avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else None

    return TaskMetrics(
        total_tasks=total,
        queued_tasks=queue_status["queued_tasks"],
        running_tasks=queue_status["running_tasks"],
        completed_tasks=stats["total_completed"],
        failed_tasks=stats["total_failed"],
        cancelled_tasks=stats["total_cancelled"],
        timeout_tasks=stats["total_timeout"],
        retry_count=stats["total_retries"],
        success_rate=round(success_rate, 2),
        average_execution_time=round(avg_execution_time, 2) if avg_execution_time else None,
        tasks_per_hour=round(tasks_per_hour, 2)
    )


@router.get("/system", response_model=SystemMetrics)
async def get_system_analytics():
    """Get current system resource metrics"""
    return await get_system_metrics()


@router.get("/tasks", response_model=TaskMetrics)
async def get_task_analytics():
    """Get task execution metrics"""
    return await get_task_metrics()


@router.get("/memory")
async def get_memory_analytics(memory_store: MemoryStore):
    """Get memory system metrics"""
    stats = await memory_store.get_memory_stats()

    return MemoryMetrics(
        total_memories=stats["total_memories"],
        high_importance=stats["importance_distribution"]["high"],
        medium_importance=stats["importance_distribution"]["medium"],
        low_importance=stats["importance_distribution"]["low"],
        total_accesses=stats["access_statistics"]["total_accesses"],
        average_accesses=stats["access_statistics"]["average_accesses_per_memory"],
        storage_type=stats["storage_type"],
        consolidation_threshold=stats["consolidation_threshold"]
    )


@router.get("/snapshot", response_model=PerformanceSnapshot)
async def get_performance_snapshot():
    """Get complete system performance snapshot"""
    system_metrics = await get_system_metrics()
    task_metrics = await get_task_metrics()

    # Mock memory metrics (would need to pass memory_store from app state)
    memory_metrics = MemoryMetrics(
        total_memories=0,
        high_importance=0,
        medium_importance=0,
        low_importance=0,
        total_accesses=0,
        average_accesses=0.0,
        storage_type="in-memory",
        consolidation_threshold=1000
    )

    snapshot = PerformanceSnapshot(
        timestamp=datetime.now(),
        system=system_metrics,
        tasks=task_metrics,
        memory=memory_metrics,
        agents=None
    )

    # Store in history
    performance_history.append(snapshot.dict())
    if len(performance_history) > 100:
        performance_history.pop(0)

    return snapshot


@router.get("/history")
async def get_performance_history(
    limit: int = Query(20, ge=1, le=100),
    metric: Optional[str] = Query(None, description="Specific metric to retrieve")
):
    """
    Get performance history

    Args:
        limit: Number of snapshots to return
        metric: Specific metric path (e.g., "system.cpu_percent", "tasks.success_rate")
    """
    history = performance_history[-limit:]

    if metric:
        # Extract specific metric from history
        metric_parts = metric.split('.')

        result = []
        for snapshot in history:
            value = snapshot
            try:
                for part in metric_parts:
                    value = value[part]
                result.append({
                    "timestamp": snapshot["timestamp"],
                    "value": value
                })
            except (KeyError, TypeError):
                pass

        return {"metric": metric, "data": result}

    return {"history": history}


@router.get("/task-distribution")
async def get_task_distribution():
    """Get distribution of tasks by status and priority"""
    all_tasks = task_queue.get_all_tasks()

    # Group by status
    by_status = {}
    for task in all_tasks:
        status = task["status"]
        by_status[status] = by_status.get(status, 0) + 1

    # Group by priority
    by_priority = {}
    for task in all_tasks:
        priority = task.get("priority", "unknown")
        by_priority[priority] = by_priority.get(priority, 0) + 1

    # Calculate average execution time by priority
    avg_time_by_priority = {}
    for priority in by_priority.keys():
        priority_tasks = [t for t in all_tasks if t.get("priority") == priority]
        times = []

        for task in priority_tasks:
            if task.get("started_at") and task.get("completed_at"):
                started = datetime.fromisoformat(task["started_at"])
                completed = datetime.fromisoformat(task["completed_at"])
                times.append((completed - started).total_seconds())

        if times:
            avg_time_by_priority[priority] = round(sum(times) / len(times), 2)

    return {
        "by_status": by_status,
        "by_priority": by_priority,
        "average_execution_time_by_priority": avg_time_by_priority
    }


@router.get("/task-timeline")
async def get_task_timeline(hours: int = Query(24, ge=1, le=168)):
    """
    Get task execution timeline for the past N hours

    Args:
        hours: Number of hours to include
    """
    all_tasks = task_queue.get_all_tasks()

    cutoff = datetime.now() - timedelta(hours=hours)

    # Filter tasks within timeframe
    recent_tasks = [
        t for t in all_tasks
        if t.get("created_at") and datetime.fromisoformat(t["created_at"]) > cutoff
    ]

    # Group by hour
    timeline = {}
    for task in recent_tasks:
        created = datetime.fromisoformat(task["created_at"])
        hour_key = created.strftime("%Y-%m-%d %H:00")

        if hour_key not in timeline:
            timeline[hour_key] = {
                "created": 0,
                "completed": 0,
                "failed": 0
            }

        timeline[hour_key]["created"] += 1

        if task["status"] == "completed":
            timeline[hour_key]["completed"] += 1
        elif task["status"] in ["failed", "timeout"]:
            timeline[hour_key]["failed"] += 1

    # Convert to list sorted by time
    timeline_list = [
        {"hour": hour, **stats}
        for hour, stats in sorted(timeline.items())
    ]

    return {
        "hours": hours,
        "timeline": timeline_list,
        "total_tasks": len(recent_tasks)
    }


@router.get("/resource-usage-trend")
async def get_resource_usage_trend():
    """Get trend of resource usage over time from history"""
    if not performance_history:
        return {"message": "No history available yet"}

    cpu_trend = [
        {
            "timestamp": snapshot["timestamp"],
            "cpu_percent": snapshot["system"]["cpu_percent"]
        }
        for snapshot in performance_history
    ]

    memory_trend = [
        {
            "timestamp": snapshot["timestamp"],
            "memory_percent": snapshot["system"]["memory_percent"]
        }
        for snapshot in performance_history
    ]

    return {
        "cpu_trend": cpu_trend,
        "memory_trend": memory_trend
    }


@router.get("/health")
async def health_check():
    """Comprehensive health check"""
    system_metrics = await get_system_metrics()
    task_metrics = await get_task_metrics()

    # Determine health status
    health_issues = []

    if system_metrics.cpu_percent > 90:
        health_issues.append("High CPU usage")

    if system_metrics.memory_percent > 90:
        health_issues.append("High memory usage")

    if system_metrics.disk_usage_percent > 90:
        health_issues.append("High disk usage")

    if task_metrics.success_rate < 50 and task_metrics.completed_tasks > 10:
        health_issues.append("Low task success rate")

    if task_metrics.running_tasks == 0 and task_metrics.queued_tasks > 0:
        health_issues.append("Tasks queued but not executing")

    status = "healthy" if not health_issues else "degraded"

    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "issues": health_issues,
        "uptime_seconds": system_metrics.uptime_seconds,
        "metrics_summary": {
            "cpu": f"{system_metrics.cpu_percent}%",
            "memory": f"{system_metrics.memory_percent}%",
            "tasks_success_rate": f"{task_metrics.success_rate}%",
            "active_tasks": task_metrics.running_tasks
        }
    }


@router.post("/record-snapshot")
async def record_performance_snapshot():
    """Manually trigger recording of a performance snapshot"""
    snapshot = await get_performance_snapshot()
    return {
        "message": "Snapshot recorded",
        "snapshot": snapshot
    }
