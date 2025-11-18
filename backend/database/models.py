"""
Database models for ZenoMind
Defines SQLAlchemy models for tasks, agents, metrics, and memories
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, Text,
    ForeignKey, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
import uuid

Base = declarative_base()


class TaskStatus(enum.Enum):
    """Task status enumeration"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(enum.Enum):
    """Task priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Task(Base):
    """
    Task model - Represents a single task for the agent

    Provides persistence for task state across restarts
    """
    __tablename__ = "tasks"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(String(36), unique=True, index=True, nullable=False)

    # Task details
    prompt = Column(Text, nullable=False)
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.QUEUED, nullable=False, index=True)

    # Configuration
    max_duration = Column(Integer, default=1800)  # seconds
    enable_browser = Column(Boolean, default=True)
    enable_learning = Column(Boolean, default=True)

    # Execution state
    progress = Column(Float, default=0.0)
    current_step = Column(String(500), nullable=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Relationships
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True)
    agent = relationship("Agent", back_populates="tasks")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_agent_status', 'agent_id', 'status'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "task_id": self.task_id,
            "prompt": self.prompt,
            "priority": self.priority.value,
            "status": self.status.value,
            "max_duration": self.max_duration,
            "enable_browser": self.enable_browser,
            "enable_learning": self.enable_learning,
            "progress": self.progress,
            "current_step": self.current_step,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
            "agent_id": self.agent_id,
            "thoughts": [],
            "actions": []
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create task from dictionary"""
        # Convert enum strings to enums
        if isinstance(data.get("priority"), str):
            data["priority"] = TaskPriority(data["priority"])
        if isinstance(data.get("status"), str):
            data["status"] = TaskStatus(data["status"])

        # Convert datetime strings to datetime objects
        for field in ["created_at", "started_at", "completed_at", "updated_at"]:
            if isinstance(data.get(field), str):
                data[field] = datetime.fromisoformat(data[field])

        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


class Agent(Base):
    """
    Agent model - Represents an ambient agent instance

    Tracks agent state, performance, and learning progress
    """
    __tablename__ = "agents"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agent_id = Column(String(50), unique=True, index=True, nullable=False)

    # Agent details
    name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="idle", index=True)

    # Performance metrics
    tasks_completed = Column(Integer, default=0)
    tasks_failed = Column(Integer, default=0)
    total_execution_time = Column(Float, default=0.0)  # seconds
    average_task_duration = Column(Float, default=0.0)  # seconds
    success_rate = Column(Float, default=0.0)  # 0.0 to 1.0

    # Learning metrics
    patterns_learned = Column(Integer, default=0)
    strategies_optimized = Column(Integer, default=0)
    experience_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Configuration
    config = Column(JSON, default=dict)

    # Relationships
    tasks = relationship("Task", back_populates="agent", cascade="all, delete-orphan")
    metrics = relationship("Metric", back_populates="agent", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "total_execution_time": self.total_execution_time,
            "average_task_duration": self.average_task_duration,
            "success_rate": self.success_rate,
            "patterns_learned": self.patterns_learned,
            "strategies_optimized": self.strategies_optimized,
            "experience_count": self.experience_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "config": self.config
        }


class Metric(Base):
    """
    Metric model - Time-series metrics for agent performance

    Tracks detailed performance metrics over time for analytics
    """
    __tablename__ = "metrics"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Metric details
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_type = Column(String(50), nullable=False)  # counter, gauge, histogram

    # Context
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True, index=True)
    task_id = Column(String(36), nullable=True, index=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Additional data
    labels = Column(JSON, default=dict)

    # Relationships
    agent = relationship("Agent", back_populates="metrics")

    # Indexes for time-series queries
    __table_args__ = (
        Index('idx_metric_timestamp', 'metric_name', 'timestamp'),
        Index('idx_agent_metric_timestamp', 'agent_id', 'metric_name', 'timestamp'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary"""
        return {
            "id": self.id,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metric_type": self.metric_type,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "labels": self.labels
        }


class Memory(Base):
    """
    Memory model - Persistent storage for agent memories

    Complements vector store with structured metadata
    """
    __tablename__ = "memories"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    memory_id = Column(String(50), unique=True, index=True, nullable=False)

    # Memory content
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), index=True)  # For deduplication

    # Context
    agent_id = Column(String(50), nullable=True, index=True)
    task_id = Column(String(36), nullable=True, index=True)

    # Classification
    memory_type = Column(String(50), default="experience", index=True)
    importance = Column(Float, default=0.5)  # 0.0 to 1.0
    success = Column(Boolean, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    accessed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    access_count = Column(Integer, default=0)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Indexes
    __table_args__ = (
        Index('idx_type_importance', 'memory_type', 'importance'),
        Index('idx_created_importance', 'created_at', 'importance'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary"""
        return {
            "id": self.memory_id,
            "content": self.content,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "success": self.success,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "accessed_at": self.accessed_at.isoformat() if self.accessed_at else None,
            "access_count": self.access_count,
            "metadata": self.metadata
        }


# Add more models as needed for plugins, configurations, etc.
class Plugin(Base):
    """
    Plugin model - Represents installed plugins

    Enables dynamic tool and capability extension
    """
    __tablename__ = "plugins"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    plugin_id = Column(String(100), unique=True, index=True, nullable=False)

    # Plugin details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(20), nullable=False)

    # Status
    enabled = Column(Boolean, default=True, index=True)
    installed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Configuration
    config = Column(JSON, default=dict)
    capabilities = Column(JSON, default=list)  # List of capabilities provided

    # Usage statistics
    usage_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert plugin to dictionary"""
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "installed_at": self.installed_at.isoformat() if self.installed_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "config": self.config,
            "capabilities": self.capabilities,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count
        }
