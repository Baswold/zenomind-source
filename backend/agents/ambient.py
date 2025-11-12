"""
Ambient Agent - Enhanced OpenManus Wrapper
Provides ambient operation with consciousness streaming and memory
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "openmanus-source"))

import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any
from loguru import logger

from app.agent.manus import Manus
from app.schema import Message, AgentState
from memory.vector_store import MemoryStore
from websocket.consciousness import ConsciousnessStreamer
from agents.browser import EnhancedBrowserAgent


class AmbientAgent:
    """
    Ambient AI Agent - Continuously operational agent with:
    - Real-time consciousness streaming
    - Long-term memory with vector storage
    - Enhanced browser capabilities
    - Auto-learning from experiences
    """

    def __init__(
        self,
        agent_id: str,
        memory_store: MemoryStore,
        consciousness_streamer: ConsciousnessStreamer
    ):
        self.agent_id = agent_id
        self.memory_store = memory_store
        self.consciousness_streamer = consciousness_streamer

        self.manus_agent: Optional[Manus] = None
        self.browser_agent: Optional[EnhancedBrowserAgent] = None

        self.status = "idle"
        self.tasks_completed = 0
        self.created_at = datetime.now()
        self.current_task_id: Optional[str] = None

        # Learning system
        self.experience_buffer: List[Dict] = []
        self.success_patterns: List[Dict] = []

    async def initialize(self):
        """Initialize the ambient agent"""
        logger.info(f"🚀 Initializing ambient agent: {self.agent_id}")

        # Create Manus agent
        self.manus_agent = await Manus.create()
        logger.info("✅ Manus agent created")

        # Create enhanced browser agent
        self.browser_agent = EnhancedBrowserAgent()
        await self.browser_agent.initialize()
        logger.info("✅ Enhanced browser agent initialized")

        self.status = "ready"
        logger.info(f"✨ Ambient agent {self.agent_id} ready")

    async def execute_task(
        self,
        prompt: str,
        task_id: str,
        max_duration: int = 1800,
        enable_browser: bool = True
    ) -> str:
        """
        Execute a task with consciousness streaming and memory storage

        Args:
            prompt: Task description
            task_id: Unique task identifier
            max_duration: Maximum execution time in seconds
            enable_browser: Enable browser capabilities

        Returns:
            Task result
        """
        self.status = "working"
        self.current_task_id = task_id

        try:
            # Stream initial thought
            await self.consciousness_streamer.emit_thought(
                agent_id=self.agent_id,
                task_id=task_id,
                thought=f"Beginning task: {prompt}",
                thought_type="initiation"
            )

            # Search memory for relevant context
            relevant_memories = await self.memory_store.search(prompt, limit=5)
            if relevant_memories:
                context = "\n".join([m["content"] for m in relevant_memories])
                enhanced_prompt = f"{prompt}\n\nRelevant past experience:\n{context}"

                await self.consciousness_streamer.emit_thought(
                    agent_id=self.agent_id,
                    task_id=task_id,
                    thought=f"Found {len(relevant_memories)} relevant memories from past experiences",
                    thought_type="reflection"
                )
            else:
                enhanced_prompt = prompt

            # Hook into agent's thinking process
            original_think = self.manus_agent.think

            async def streaming_think():
                """Wrapper that streams thoughts"""
                result = await original_think()

                # Get last assistant message
                last_message = self.manus_agent.memory.messages[-1]
                if last_message.role == "assistant":
                    await self.consciousness_streamer.emit_thought(
                        agent_id=self.agent_id,
                        task_id=task_id,
                        thought=last_message.content or "",
                        thought_type="reasoning"
                    )

                return result

            # Temporarily replace think method
            self.manus_agent.think = streaming_think

            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    self.manus_agent.run(enhanced_prompt),
                    timeout=max_duration
                )
            except asyncio.TimeoutError:
                result = "Task exceeded maximum duration and was terminated"
                await self.consciousness_streamer.emit_thought(
                    agent_id=self.agent_id,
                    task_id=task_id,
                    thought="Task timeout reached",
                    thought_type="termination"
                )

            # Restore original think method
            self.manus_agent.think = original_think

            # Store experience in memory
            await self.store_experience(
                prompt=prompt,
                result=result,
                task_id=task_id,
                success=True
            )

            # Learn from experience
            await self.learn_from_task(prompt, result)

            # Stream completion
            await self.consciousness_streamer.emit_thought(
                agent_id=self.agent_id,
                task_id=task_id,
                thought=f"Task completed successfully",
                thought_type="completion"
            )

            self.tasks_completed += 1
            self.status = "ready"
            self.current_task_id = None

            return result

        except Exception as e:
            logger.error(f"Error executing task: {str(e)}")

            await self.consciousness_streamer.emit_thought(
                agent_id=self.agent_id,
                task_id=task_id,
                thought=f"Error encountered: {str(e)}",
                thought_type="error"
            )

            # Store failed experience
            await self.store_experience(
                prompt=prompt,
                result=str(e),
                task_id=task_id,
                success=False
            )

            self.status = "ready"
            self.current_task_id = None

            raise

    async def store_experience(
        self,
        prompt: str,
        result: str,
        task_id: str,
        success: bool
    ):
        """Store task experience in long-term memory"""
        experience = {
            "task_id": task_id,
            "prompt": prompt,
            "result": result,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id
        }

        # Store in vector database
        await self.memory_store.add_memory(
            content=f"Task: {prompt}\nResult: {result}",
            metadata=experience
        )

        # Add to experience buffer for learning
        self.experience_buffer.append(experience)

        logger.info(f"📚 Stored experience for task {task_id}")

    async def learn_from_task(self, prompt: str, result: str):
        """
        Auto-learning: Extract patterns from successful tasks
        This is a signature feature - the agent learns over time!
        """
        # Simple pattern extraction: identify successful strategies
        if len(self.experience_buffer) > 10:
            # Analyze recent successful tasks
            recent_successes = [
                exp for exp in self.experience_buffer[-20:]
                if exp["success"]
            ]

            if len(recent_successes) >= 5:
                # Find common patterns (simplified for now)
                pattern = {
                    "task_type": self._classify_task(prompt),
                    "success_rate": len(recent_successes) / 20,
                    "timestamp": datetime.now().isoformat()
                }

                self.success_patterns.append(pattern)
                logger.info(f"🎓 Learned new pattern: {pattern['task_type']}")

    def _classify_task(self, prompt: str) -> str:
        """Simple task classification"""
        prompt_lower = prompt.lower()

        if any(word in prompt_lower for word in ["search", "find", "lookup", "research"]):
            return "research"
        elif any(word in prompt_lower for word in ["create", "write", "generate", "build"]):
            return "creation"
        elif any(word in prompt_lower for word in ["analyze", "examine", "review", "compare"]):
            return "analysis"
        elif any(word in prompt_lower for word in ["browse", "navigate", "click", "website"]):
            return "browsing"
        else:
            return "general"

    async def cleanup(self):
        """Cleanup resources"""
        logger.info(f"🧹 Cleaning up ambient agent: {self.agent_id}")

        if self.manus_agent:
            await self.manus_agent.cleanup()

        if self.browser_agent:
            await self.browser_agent.cleanup()

        self.status = "stopped"
        logger.info(f"✅ Ambient agent {self.agent_id} cleaned up")
