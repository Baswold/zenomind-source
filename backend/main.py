"""
ZenoMind Backend Server
Ambient AI Agent with OpenManus Integration
"""

import sys
import os
from pathlib import Path

# Add openmanus to path
sys.path.insert(0, str(Path(__file__).parent.parent / "openmanus-source"))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
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
        self.tasks: Dict[str, Dict] = {}
        self.memory_store: Optional[MemoryStore] = None
        self.consciousness_streamer: Optional[ConsciousnessStreamer] = None
        self.websocket_connections: List[WebSocket] = []

app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    logger.info("🚀 Starting ZenoMind Ambient Agent...")

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

    yield

    # Cleanup
    logger.info("🛑 Shutting down ZenoMind...")
    for agent in app_state.agents.values():
        await agent.cleanup()
    if app_state.memory_store:
        await app_state.memory_store.close()
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
async def create_task(request: TaskRequest):
    """Create a new task"""
    task_id = str(uuid.uuid4())

    task_data = {
        "task_id": task_id,
        "prompt": request.prompt,
        "priority": request.priority,
        "max_duration": request.max_duration,
        "enable_browser": request.enable_browser,
        "enable_learning": request.enable_learning,
        "status": "queued",
        "progress": 0.0,
        "created_at": datetime.now(),
        "started_at": None,
        "completed_at": None,
        "current_step": None,
        "result": None,
        "error": None,
        "thoughts": [],
        "actions": []
    }

    app_state.tasks[task_id] = task_data

    # Queue the task
    asyncio.create_task(execute_task(task_id))

    logger.info(f"📝 Task created: {task_id} - {request.prompt[:50]}...")

    return TaskResponse(
        task_id=task_id,
        status="queued",
        created_at=task_data["created_at"],
        message="Task queued successfully"
    )


async def execute_task(task_id: str):
    """Execute a task asynchronously"""
    task = app_state.tasks.get(task_id)
    if not task:
        logger.error(f"Task {task_id} not found")
        return

    try:
        task["status"] = "running"
        task["started_at"] = datetime.now()

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

        task["status"] = "completed"
        task["result"] = result
        task["progress"] = 1.0
        task["completed_at"] = datetime.now()

        logger.info(f"✅ Task completed: {task_id}")

        # Broadcast completion
        await broadcast_task_update(task_id)

    except Exception as e:
        logger.error(f"❌ Task failed: {task_id} - {str(e)}")
        task["status"] = "failed"
        task["error"] = str(e)
        task["completed_at"] = datetime.now()

        await broadcast_task_update(task_id)


@app.get("/api/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get task status"""
    task = app_state.tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatus(**task)


@app.get("/api/tasks")
async def list_tasks(status: Optional[str] = None, limit: int = 50):
    """List tasks"""
    tasks = list(app_state.tasks.values())

    if status:
        tasks = [t for t in tasks if t["status"] == status]

    # Sort by created_at descending
    tasks.sort(key=lambda x: x["created_at"], reverse=True)

    return {"tasks": tasks[:limit], "total": len(tasks)}


@app.delete("/api/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a task"""
    task = app_state.tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] == "running":
        task["status"] = "cancelled"
        task["completed_at"] = datetime.now()
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
async def list_agents():
    """List all agents"""
    agents = []
    for agent_id, agent in app_state.agents.items():
        agents.append({
            "agent_id": agent_id,
            "status": agent.status,
            "tasks_completed": agent.tasks_completed,
            "created_at": agent.created_at.isoformat()
        })

    return {"agents": agents}


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
