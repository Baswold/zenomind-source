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

        # Advanced learning system
        self.experience_buffer: List[Dict] = []
        self.success_patterns: List[Dict] = []
        self.failure_patterns: List[Dict] = []
        self.task_type_performance: Dict[str, Dict[str, Any]] = {}
        self.learning_enabled = True

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

    async def learn_from_task(self, prompt: str, result: str, success: bool = True):
        """
        Advanced auto-learning: Extract patterns and predict future performance
        This is a signature feature - the agent learns and improves over time!

        Features:
        - Task type classification
        - Success/failure pattern recognition
        - Performance prediction
        - Strategy optimization
        - Continuous improvement
        """
        if not self.learning_enabled:
            return

        task_type = self._classify_task(prompt)

        # Update task type performance tracking
        if task_type not in self.task_type_performance:
            self.task_type_performance[task_type] = {
                "total_attempts": 0,
                "successes": 0,
                "failures": 0,
                "average_complexity": 0.0,
                "common_keywords": [],
                "success_strategies": [],
                "failure_causes": []
            }

        perf = self.task_type_performance[task_type]
        perf["total_attempts"] += 1

        if success:
            perf["successes"] += 1
        else:
            perf["failures"] += 1

        # Extract keywords from prompt
        keywords = self._extract_keywords(prompt)

        # Update common keywords
        for keyword in keywords:
            if keyword not in perf["common_keywords"]:
                perf["common_keywords"].append(keyword)

        # Analyze patterns periodically
        if len(self.experience_buffer) >= 10:
            await self._analyze_patterns()

        # Make predictions for similar future tasks
        prediction = self._predict_success_probability(prompt)

        logger.info(
            f"🎓 Learning update: {task_type} "
            f"(success rate: {perf['successes']}/{perf['total_attempts']}, "
            f"predicted: {prediction:.1%})"
        )

    async def _analyze_patterns(self):
        """Analyze recent experiences to extract patterns"""
        recent_experiences = self.experience_buffer[-50:]  # Last 50 tasks

        # Group by success/failure
        successes = [exp for exp in recent_experiences if exp["success"]]
        failures = [exp for exp in recent_experiences if not exp["success"]]

        # Analyze successful patterns
        if len(successes) >= 5:
            success_pattern = self._extract_common_features(successes)

            self.success_patterns.append({
                **success_pattern,
                "timestamp": datetime.now().isoformat(),
                "sample_size": len(successes)
            })

            # Keep only recent patterns
            if len(self.success_patterns) > 20:
                self.success_patterns = self.success_patterns[-20:]

            logger.info(f"✨ Extracted success pattern with {len(successes)} examples")

        # Analyze failure patterns
        if len(failures) >= 3:
            failure_pattern = self._extract_common_features(failures)

            self.failure_patterns.append({
                **failure_pattern,
                "timestamp": datetime.now().isoformat(),
                "sample_size": len(failures)
            })

            # Keep only recent patterns
            if len(self.failure_patterns) > 10:
                self.failure_patterns = self.failure_patterns[-10:]

            logger.warning(f"⚠️ Extracted failure pattern with {len(failures)} examples")

    def _extract_common_features(self, experiences: List[Dict]) -> Dict[str, Any]:
        """Extract common features from a set of experiences"""
        # Extract task types
        task_types = [self._classify_task(exp["prompt"]) for exp in experiences]

        # Find most common task type
        task_type_counts = {}
        for tt in task_types:
            task_type_counts[tt] = task_type_counts.get(tt, 0) + 1

        most_common_type = max(task_type_counts.items(), key=lambda x: x[1])[0]

        # Extract common keywords
        all_keywords = []
        for exp in experiences:
            all_keywords.extend(self._extract_keywords(exp["prompt"]))

        # Count keyword frequency
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

        # Get top keywords
        top_keywords = sorted(
            keyword_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "dominant_task_type": most_common_type,
            "task_type_distribution": task_type_counts,
            "common_keywords": [kw for kw, _ in top_keywords],
            "keyword_frequencies": dict(top_keywords)
        }

    def _extract_keywords(self, prompt: str) -> List[str]:
        """Extract meaningful keywords from prompt"""
        # Simple keyword extraction (in production, use NLP)
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "as", "is", "was",
            "are", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "will", "would", "should", "could",
            "may", "might", "must", "can", "this", "that", "these", "those"
        }

        words = prompt.lower().split()
        keywords = [
            word.strip('.,!?;:')
            for word in words
            if len(word) > 3 and word.lower() not in stop_words
        ]

        return keywords

    def _predict_success_probability(self, prompt: str) -> float:
        """
        Predict probability of success for a given task

        Based on:
        - Historical performance for similar task types
        - Keyword similarity to past successes
        - Recent success rate trends
        """
        task_type = self._classify_task(prompt)

        # Base probability from task type performance
        if task_type in self.task_type_performance:
            perf = self.task_type_performance[task_type]
            attempts = perf["total_attempts"]

            if attempts > 0:
                base_prob = perf["successes"] / attempts
            else:
                base_prob = 0.5  # Default
        else:
            base_prob = 0.5  # Default for unknown task types

        # Adjust based on keyword similarity to success patterns
        prompt_keywords = set(self._extract_keywords(prompt))

        if self.success_patterns:
            # Find most similar success pattern
            max_similarity = 0.0

            for pattern in self.success_patterns:
                pattern_keywords = set(pattern.get("common_keywords", []))

                if pattern_keywords:
                    # Jaccard similarity
                    intersection = len(prompt_keywords & pattern_keywords)
                    union = len(prompt_keywords | pattern_keywords)
                    similarity = intersection / union if union > 0 else 0

                    max_similarity = max(max_similarity, similarity)

            # Boost probability based on similarity to successful patterns
            base_prob = base_prob * 0.7 + max_similarity * 0.3

        # Adjust based on recent trend
        if len(self.experience_buffer) >= 10:
            recent_successes = sum(
                1 for exp in self.experience_buffer[-10:]
                if exp["success"]
            )
            recent_rate = recent_successes / 10

            # Slight adjustment based on recent performance
            base_prob = base_prob * 0.9 + recent_rate * 0.1

        return min(max(base_prob, 0.0), 1.0)

    async def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights from the learning system"""
        insights = {
            "total_experiences": len(self.experience_buffer),
            "success_patterns": len(self.success_patterns),
            "failure_patterns": len(self.failure_patterns),
            "task_type_performance": {}
        }

        # Add task type performance
        for task_type, perf in self.task_type_performance.items():
            total = perf["total_attempts"]
            success_rate = (perf["successes"] / total * 100) if total > 0 else 0

            insights["task_type_performance"][task_type] = {
                "attempts": total,
                "success_rate": round(success_rate, 2),
                "top_keywords": perf["common_keywords"][:5]
            }

        # Overall success rate
        if self.experience_buffer:
            overall_successes = sum(1 for exp in self.experience_buffer if exp["success"])
            insights["overall_success_rate"] = round(
                overall_successes / len(self.experience_buffer) * 100, 2
            )
        else:
            insights["overall_success_rate"] = 0.0

        # Recent performance (last 20 tasks)
        if len(self.experience_buffer) >= 20:
            recent_successes = sum(
                1 for exp in self.experience_buffer[-20:]
                if exp["success"]
            )
            insights["recent_success_rate"] = round(recent_successes / 20 * 100, 2)

        return insights

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
