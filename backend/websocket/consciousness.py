"""
Consciousness Streamer - Real-time thought streaming
Signature Feature: Watch the agent think in real-time
"""

import asyncio
from typing import Dict, List, AsyncGenerator, Any
from datetime import datetime
from loguru import logger
import json


class ConsciousnessEvent:
    """Represents a single consciousness event"""

    def __init__(
        self,
        event_type: str,
        agent_id: str,
        task_id: str,
        content: str,
        metadata: Dict[str, Any] = None
    ):
        self.event_type = event_type
        self.agent_id = agent_id
        self.task_id = task_id
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "event_type": self.event_type,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class ConsciousnessStreamer:
    """
    Consciousness Streamer - Broadcasts agent thoughts in real-time

    This is a signature feature that gives visibility into the agent's reasoning process.
    Users can watch the agent think, plan, and execute tasks step by step.

    Event Types:
    - thought: Agent reasoning and planning
    - action: Tool calls and executions
    - observation: Results and feedback
    - reflection: Self-assessment and meta-cognition
    - emotion: Agent state changes (curious, focused, stuck, satisfied)
    """

    def __init__(self, buffer_size: int = 100):
        self.buffer_size = buffer_size
        self.event_buffer: List[ConsciousnessEvent] = []
        self.subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def emit_thought(
        self,
        agent_id: str,
        task_id: str,
        thought: str,
        thought_type: str = "reasoning",
        metadata: Dict[str, Any] = None
    ):
        """
        Emit a thought event

        Args:
            agent_id: Agent identifier
            task_id: Task identifier
            thought: Thought content
            thought_type: Type of thought (reasoning, planning, reflection, etc.)
            metadata: Additional context
        """
        event = ConsciousnessEvent(
            event_type="thought",
            agent_id=agent_id,
            task_id=task_id,
            content=thought,
            metadata={"thought_type": thought_type, **(metadata or {})}
        )

        await self._broadcast_event(event)

    async def emit_action(
        self,
        agent_id: str,
        task_id: str,
        action: str,
        tool: str,
        parameters: Dict[str, Any] = None
    ):
        """
        Emit an action event

        Args:
            agent_id: Agent identifier
            task_id: Task identifier
            action: Action description
            tool: Tool being used
            parameters: Tool parameters
        """
        event = ConsciousnessEvent(
            event_type="action",
            agent_id=agent_id,
            task_id=task_id,
            content=action,
            metadata={"tool": tool, "parameters": parameters or {}}
        )

        await self._broadcast_event(event)

    async def emit_observation(
        self,
        agent_id: str,
        task_id: str,
        observation: str,
        success: bool = True
    ):
        """
        Emit an observation event (result of an action)

        Args:
            agent_id: Agent identifier
            task_id: Task identifier
            observation: Observation content
            success: Whether the action succeeded
        """
        event = ConsciousnessEvent(
            event_type="observation",
            agent_id=agent_id,
            task_id=task_id,
            content=observation,
            metadata={"success": success}
        )

        await self._broadcast_event(event)

    async def emit_reflection(
        self,
        agent_id: str,
        task_id: str,
        reflection: str
    ):
        """
        Emit a reflection event (meta-cognition, self-assessment)

        Args:
            agent_id: Agent identifier
            task_id: Task identifier
            reflection: Reflection content
        """
        event = ConsciousnessEvent(
            event_type="reflection",
            agent_id=agent_id,
            task_id=task_id,
            content=reflection,
            metadata={}
        )

        await self._broadcast_event(event)

    async def emit_emotion(
        self,
        agent_id: str,
        task_id: str,
        emotion: str,
        intensity: float = 0.5
    ):
        """
        Emit an emotion event (agent state)

        Args:
            agent_id: Agent identifier
            task_id: Task identifier
            emotion: Emotion name (curious, focused, stuck, satisfied, etc.)
            intensity: Emotion intensity (0.0 to 1.0)
        """
        event = ConsciousnessEvent(
            event_type="emotion",
            agent_id=agent_id,
            task_id=task_id,
            content=emotion,
            metadata={"intensity": intensity}
        )

        await self._broadcast_event(event)

    async def _broadcast_event(self, event: ConsciousnessEvent):
        """Broadcast event to all subscribers"""
        async with self._lock:
            # Add to buffer
            self.event_buffer.append(event)
            if len(self.event_buffer) > self.buffer_size:
                self.event_buffer.pop(0)

            # Send to all subscribers
            event_dict = event.to_dict()
            for queue in self.subscribers:
                try:
                    await queue.put(event_dict)
                except asyncio.QueueFull:
                    # Skip if queue is full
                    logger.warning("Subscriber queue full, skipping event")

            logger.debug(f"🧠 Consciousness: {event.event_type} - {event.content[:50]}...")

    async def subscribe(self) -> AsyncGenerator[Dict, None]:
        """
        Subscribe to consciousness stream

        Yields:
            Consciousness events as dictionaries
        """
        queue = asyncio.Queue(maxsize=50)

        async with self._lock:
            self.subscribers.append(queue)

        try:
            # Send recent events from buffer
            for event in self.event_buffer[-10:]:
                yield event.to_dict()

            # Stream new events
            while True:
                event = await queue.get()
                yield event

        finally:
            async with self._lock:
                if queue in self.subscribers:
                    self.subscribers.remove(queue)

    def get_recent_events(self, limit: int = 20) -> List[Dict]:
        """Get recent consciousness events"""
        return [event.to_dict() for event in self.event_buffer[-limit:]]

    def get_events_for_task(self, task_id: str) -> List[Dict]:
        """Get all events for a specific task"""
        return [
            event.to_dict()
            for event in self.event_buffer
            if event.task_id == task_id
        ]

    def clear_buffer(self):
        """Clear the event buffer"""
        self.event_buffer.clear()
        logger.info("🧹 Consciousness buffer cleared")
