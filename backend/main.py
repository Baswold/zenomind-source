"""
ZenoMind Backend Server
Ambient AI Agent with OpenManus Integration
"""

import sys
import os
from pathlib import Path

# Add openmanus to path
sys.path.insert(0, str(Path(__file__).parent.parent / "openmanus-source"))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from loguru import logger

from pydantic import BaseModel, Field
from agents.ambient import AmbientAgent
from tasks.queue import task_queue
from memory.vector_store import MemoryStore
from websocket.consciousness import ConsciousnessStreamer
from database import init_db, close_db, get_db
from database.repository import TaskRepository, AgentRepository, MetricRepository
from database.models import TaskStatus as DBTaskStatus, TaskPriority

# Configure logger
logger.add("logs/zenomind.log", rotation="100 MB", retention="10 days", level="INFO")


class TaskRequest(BaseModel):
    """Task creation request"""
    prompt: str = Field(..., description="Task description in natural language")
    priority: str = Field(default="medium", description="Priority: low, medium, high, critical")
    max_duration: int = Field(default=1800, description="Max execution time in seconds")
    enable_browser: bool = Field(default=True, description="Enable browser automation")
    enable_learning: bool = Field(default=True, description="Learn from this task")


class TaskResponse(BaseModel):
    """Task response"""
    task_id: str
    status: str
    created_at: datetime
    message: str


class TaskStatus(BaseModel):
    """Task status information"""
    task_id: str
    status: str
    progress: float
    current_step: Optional[str]
    result: Optional[str]
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    thoughts: List[Dict]
    actions: List[Dict]


# Global state
class AppState:
    """Application state"""
    def __init__(self):
        self.agents: Dict[str, AmbientAgent] = {}
        self.tasks: Dict[str, Dict] = {}  # In-memory cache for quick access
        self.memory_store: Optional[MemoryStore] = None
        self.consciousness_streamer: Optional[ConsciousnessStreamer] = None
        self.websocket_connections: List[WebSocket] = []

app_state = AppState()


# Database dependency
async def get_session() -> AsyncSession:
    """Alias for get_db for convenience"""
    async for session in get_db():
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    logger.info("🚀 Starting ZenoMind Ambient Agent...")

    # Initialize database
    await init_db()

    # Initialize memory store
    app_state.memory_store = MemoryStore()
    await app_state.memory_store.initialize()
    logger.info("💾 Memory store initialized")

    # Initialize consciousness streamer
    app_state.consciousness_streamer = ConsciousnessStreamer()
    logger.info("🧠 Consciousness streamer initialized")

    # Create default ambient agent
    default_agent = AmbientAgent(
        agent_id="default",
        memory_store=app_state.memory_store,
        consciousness_streamer=app_state.consciousness_streamer
    )
    await default_agent.initialize()
    app_state.agents["default"] = default_agent
    logger.info("🤖 Default ambient agent created")

    # Register agent in database
    async for db in get_db():
        await AgentRepository.get_or_create(
            db,
            "default",
            name="Default Ambient Agent",
            description="Primary autonomous agent"
        )
        await db.commit()
        break

    # Load pending/running tasks from database and resume them
    async for db in get_db():
        pending_tasks = await TaskRepository.get_all(
            db,
            status=DBTaskStatus.RUNNING,
            limit=100
        )
        logger.info(f"📋 Found {len(pending_tasks)} running tasks to resume")

        for task_db in pending_tasks:
            # Mark as queued for retry
            await TaskRepository.update_status(
                db,
                task_db.task_id,
                DBTaskStatus.QUEUED,
                error="Server restarted, task will be retried"
            )

            # Cache in memory
            app_state.tasks[task_db.task_id] = task_db.to_dict()

            # Re-queue the task
            asyncio.create_task(execute_task(task_db.task_id))

        await db.commit()
        break

    yield

    # Cleanup
    logger.info("🛑 Shutting down ZenoMind...")
    for agent in app_state.agents.values():
        await agent.cleanup()
    if app_state.memory_store:
        await app_state.memory_store.close()
    await close_db()
    logger.info("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="ZenoMind API",
    description="Ambient AI Agent with OpenManus",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "ZenoMind",
        "status": "operational",
        "version": "1.0.0",
        "agents": len(app_state.agents),
        "active_tasks": len([t for t in app_state.tasks.values() if t["status"] == "running"]),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(request: TaskRequest, db: AsyncSession = Depends(get_db)):
    """Create a new task with database persistence"""
    task_id = str(uuid.uuid4())

    # Create task in database
    task_db = await TaskRepository.create(
        db,
        {
            "task_id": task_id,
            "prompt": request.prompt,
            "priority": request.priority,
            "max_duration": request.max_duration,
            "enable_browser": request.enable_browser,
            "enable_learning": request.enable_learning,
            "status": DBTaskStatus.QUEUED,
            "agent_id": "default"
        }
    )
    await db.commit()

    # Cache in memory for quick access
    app_state.tasks[task_id] = task_db.to_dict()

    # Queue the task for execution
    asyncio.create_task(execute_task(task_id))

    logger.info(f"📝 Task created: {task_id} - {request.prompt[:50]}...")

    return TaskResponse(
        task_id=task_id,
        status="queued",
        created_at=task_db.created_at,
        message="Task queued successfully"
    )


async def execute_task(task_id: str):
    """Execute a task asynchronously with database persistence"""
    task = app_state.tasks.get(task_id)
    if not task:
        logger.error(f"Task {task_id} not found")
        return

    start_time = datetime.now()

    try:
        # Update status to running in database and cache
        async for db in get_db():
            await TaskRepository.update_status(
                db,
                task_id,
                DBTaskStatus.RUNNING,
                started_at=start_time
            )
            await db.commit()
            break

        task["status"] = "running"
        task["started_at"] = start_time

        # Get agent
        agent = app_state.agents.get("default")
        if not agent:
            raise Exception("No agent available")

        # Execute task
        result = await agent.execute_task(
            prompt=task["prompt"],
            task_id=task_id,
            max_duration=task["max_duration"],
            enable_browser=task["enable_browser"]
        )

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()

        # Update task as completed in database
        async for db in get_db():
            await TaskRepository.complete_task(db, task_id, result, success=True)

            # Update agent metrics
            await AgentRepository.increment_task_count(
                db,
                "default",
                success=True,
                duration=duration
            )

            # Record metrics
            await MetricRepository.record(
                db,
                "task_duration",
                duration,
                metric_type="histogram",
                agent_id="default",
                task_id=task_id,
                labels={"status": "completed"}
            )

            await db.commit()
            break

        task["status"] = "completed"
        task["result"] = result
        task["progress"] = 1.0
        task["completed_at"] = datetime.now()

        logger.info(f"✅ Task completed: {task_id} (duration: {duration:.2f}s)")

        # Broadcast completion
        await broadcast_task_update(task_id)

    except Exception as e:
        logger.error(f"❌ Task failed: {task_id} - {str(e)}")

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()

        # Update task as failed in database
        async for db in get_db():
            await TaskRepository.complete_task(db, task_id, str(e), success=False)

            # Update agent metrics
            await AgentRepository.increment_task_count(
                db,
                "default",
                success=False,
                duration=duration
            )

            # Record metrics
            await MetricRepository.record(
                db,
                "task_duration",
                duration,
                metric_type="histogram",
                agent_id="default",
                task_id=task_id,
                labels={"status": "failed"}
            )

            await db.commit()
            break

        task["status"] = "failed"
        task["error"] = str(e)
        task["completed_at"] = datetime.now()

        await broadcast_task_update(task_id)


@app.get("/api/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    """Get task status from database"""
    # Try cache first
    task = app_state.tasks.get(task_id)
    if task:
        return TaskStatus(**task)

    # Fallback to database
    task_db = await TaskRepository.get_by_id(db, task_id)
    if not task_db:
        raise HTTPException(status_code=404, detail="Task not found")

    task_dict = task_db.to_dict()
    app_state.tasks[task_id] = task_dict  # Cache it

    return TaskStatus(**task_dict)


@app.get("/api/tasks")
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List tasks from database"""
    # Convert status string to enum if provided
    status_enum = DBTaskStatus(status) if status else None

    # Get tasks from database
    tasks_db = await TaskRepository.get_all(db, status=status_enum, limit=limit)

    # Convert to dicts and update cache
    tasks = []
    for task_db in tasks_db:
        task_dict = task_db.to_dict()
        app_state.tasks[task_db.task_id] = task_dict
        tasks.append(task_dict)

    return {"tasks": tasks, "total": len(tasks)}


@app.delete("/api/tasks/{task_id}")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel a task"""
    task_db = await TaskRepository.get_by_id(db, task_id)
    if not task_db:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_db.status == DBTaskStatus.RUNNING or task_db.status == DBTaskStatus.QUEUED:
        await TaskRepository.update_status(
            db,
            task_id,
            DBTaskStatus.CANCELLED,
            completed_at=datetime.now()
        )
        await db.commit()

        # Update cache
        if task_id in app_state.tasks:
            app_state.tasks[task_id]["status"] = "cancelled"
            app_state.tasks[task_id]["completed_at"] = datetime.now()

        logger.info(f"🛑 Task cancelled: {task_id}")

    return {"message": "Task cancelled", "task_id": task_id}


@app.get("/api/memory/search")
async def search_memory(query: str, limit: int = 10):
    """Search agent memory"""
    if not app_state.memory_store:
        raise HTTPException(status_code=503, detail="Memory store not available")

    results = await app_state.memory_store.search(query, limit=limit)
    return {"results": results, "query": query}


@app.get("/api/memory/recent")
async def get_recent_memories(limit: int = 20):
    """Get recent memories"""
    if not app_state.memory_store:
        raise HTTPException(status_code=503, detail="Memory store not available")

    memories = await app_state.memory_store.get_recent(limit=limit)
    return {"memories": memories}


@app.get("/api/agents")
async def list_agents(db: AsyncSession = Depends(get_db)):
    """List all agents with metrics from database"""
    agents_db = await AgentRepository.get_all(db)

    agents = [agent.to_dict() for agent in agents_db]

    return {"agents": agents}


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed agent information"""
    agent_db = await AgentRepository.get_by_id(db, agent_id)
    if not agent_db:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent_db.to_dict()


@app.get("/api/metrics/tasks")
async def get_task_metrics(
    agent_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get task statistics"""
    stats = await TaskRepository.get_statistics(db, agent_id=agent_id)
    return stats


@app.get("/api/metrics/time-series/{metric_name}")
async def get_metric_time_series(
    metric_name: str,
    agent_id: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get time series data for a metric"""
    metrics = await MetricRepository.get_time_series(
        db,
        metric_name=metric_name,
        agent_id=agent_id,
        limit=limit
    )

    return {
        "metric_name": metric_name,
        "data": [m.to_dict() for m in metrics]
    }


@app.get("/api/metrics/aggregate/{metric_name}")
async def get_metric_aggregate(
    metric_name: str,
    aggregation: str = "avg",
    agent_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get aggregated metric value"""
    value = await MetricRepository.get_aggregated(
        db,
        metric_name=metric_name,
        aggregation=aggregation,
        agent_id=agent_id
    )

    return {
        "metric_name": metric_name,
        "aggregation": aggregation,
        "value": value
    }


@app.websocket("/ws/consciousness")
async def consciousness_websocket(websocket: WebSocket):
    """WebSocket for consciousness stream"""
    await websocket.accept()
    app_state.websocket_connections.append(websocket)
    logger.info(f"🔌 WebSocket connected. Total connections: {len(app_state.websocket_connections)}")

    try:
        # Subscribe to consciousness stream
        if app_state.consciousness_streamer:
            async for event in app_state.consciousness_streamer.subscribe():
                await websocket.send_json(event)

    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected")
    finally:
        if websocket in app_state.websocket_connections:
            app_state.websocket_connections.remove(websocket)


async def broadcast_task_update(task_id: str):
    """Broadcast task update to all connected clients"""
    task = app_state.tasks.get(task_id)
    if not task:
        return

    message = {
        "type": "task_update",
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "current_step": task["current_step"]
    }

    # Remove disconnected clients
    disconnected = []
    for ws in app_state.websocket_connections:
        try:
            await ws.send_json(message)
        except:
            disconnected.append(ws)

    for ws in disconnected:
        if ws in app_state.websocket_connections:
            app_state.websocket_connections.remove(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
