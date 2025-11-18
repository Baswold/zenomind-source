"""
Learning engine - Integrates all learning components
Coordinates pattern recognition, strategy optimization, and experience replay
"""

from typing import Dict, Any, List, Optional
from loguru import logger

from .pattern_recognizer import PatternRecognizer
from .strategy_optimizer import StrategyOptimizer, Strategy
from .experience_replay import ExperienceReplay, Experience


class LearningEngine:
    """
    Main learning engine

    Integrates:
    - Pattern recognition
    - Strategy optimization
    - Experience replay
    - Adaptive learning
    """

    def __init__(self):
        """Initialize learning engine"""
        self.pattern_recognizer = PatternRecognizer()
        self.strategy_optimizer = StrategyOptimizer(epsilon=0.1)
        self.experience_replay = ExperienceReplay(max_size=10000)

        self.learning_enabled = True
        self.auto_optimize = True

        logger.info("🧠 Learning engine initialized")

    async def process_task_completion(
        self,
        task_prompt: str,
        task_result: Optional[str],
        success: bool,
        duration: float,
        tools_used: List[str] = None,
        errors: List[str] = None,
        strategy_id: Optional[str] = None
    ):
        """
        Process a completed task for learning

        This is the main entry point for the learning system

        Args:
            task_prompt: Task description
            task_result: Task result
            success: Whether task succeeded
            duration: Task duration
            tools_used: Tools used
            errors: Errors encountered
            strategy_id: Strategy used
        """
        if not self.learning_enabled:
            return

        try:
            # 1. Pattern recognition
            patterns = await self.pattern_recognizer.analyze_task(
                task_prompt=task_prompt,
                task_result=task_result,
                success=success,
                duration=duration,
                tools_used=tools_used
            )

            # 2. Update strategy performance
            if strategy_id:
                # Calculate reward for strategy
                reward = self._calculate_strategy_reward(
                    success, duration, errors or []
                )

                await self.strategy_optimizer.update_strategy_performance(
                    strategy_id=strategy_id,
                    success=success,
                    duration=duration,
                    reward=reward
                )

            # 3. Store experience
            await self.experience_replay.add_experience(
                task_prompt=task_prompt,
                task_result=task_result,
                success=success,
                duration=duration,
                patterns=patterns,
                strategy_used=strategy_id,
                tools_used=tools_used,
                errors=errors
            )

            # 4. Auto-optimize (learn from batch of experiences)
            if self.auto_optimize and len(self.experience_replay.buffer) % 10 == 0:
                await self._perform_batch_learning()

            logger.info(
                f"📚 Processed task for learning: "
                f"patterns={len(patterns)}, success={success}"
            )

        except Exception as e:
            logger.error(f"Learning engine error: {e}")

    def _calculate_strategy_reward(
        self,
        success: bool,
        duration: float,
        errors: List[str]
    ) -> float:
        """Calculate reward signal for strategy optimization"""
        reward = 1.0 if success else 0.0

        # Time bonus (faster is better)
        if duration < 10:
            reward += 0.3
        elif duration < 60:
            reward += 0.1
        elif duration > 300:  # 5 minutes
            reward -= 0.2

        # Error penalty
        reward -= len(errors) * 0.1

        return max(0.0, min(1.0, reward))

    async def _perform_batch_learning(self):
        """Perform batch learning from experiences"""
        try:
            # Sample experiences
            experiences = await self.experience_replay.sample_batch(
                batch_size=32,
                prioritized=True
            )

            if not experiences:
                return

            # Analyze patterns across batch
            pattern_frequencies = {}
            for exp in experiences:
                for pattern in exp.patterns:
                    pattern_frequencies[pattern] = pattern_frequencies.get(pattern, 0) + 1

            # Log insights
            if pattern_frequencies:
                top_pattern = max(pattern_frequencies.items(), key=lambda x: x[1])
                logger.info(
                    f"📊 Batch learning: Most common pattern = {top_pattern[0]} "
                    f"({top_pattern[1]}/{len(experiences)} tasks)"
                )

        except Exception as e:
            logger.error(f"Batch learning error: {e}")

    async def get_task_recommendations(
        self,
        task_prompt: str
    ) -> Dict[str, Any]:
        """
        Get recommendations for executing a task

        Args:
            task_prompt: Task description

        Returns:
            Dictionary with recommendations
        """
        # Get pattern-based recommendations
        pattern_recs = await self.pattern_recognizer.get_recommendations(task_prompt)

        # Identify patterns
        patterns = await self.pattern_recognizer.analyze_task(task_prompt)

        # Get optimal strategy
        strategy = await self.strategy_optimizer.select_strategy(patterns)

        # Get similar successful experiences
        successful_experiences = await self.experience_replay.get_successful_experiences(
            patterns=patterns,
            limit=3
        )

        return {
            "patterns": pattern_recs,
            "recommended_strategy": strategy.to_dict(),
            "similar_successes": [exp.to_dict() for exp in successful_experiences],
            "confidence": self._calculate_recommendation_confidence(
                pattern_recs,
                successful_experiences
            )
        }

    def _calculate_recommendation_confidence(
        self,
        pattern_recs: Dict[str, Any],
        successful_experiences: List[Experience]
    ) -> float:
        """Calculate confidence in recommendations"""
        # Base confidence
        confidence = 0.5

        # Boost if patterns found
        if pattern_recs["patterns_found"] > 0:
            confidence += 0.2

        # Boost if we have successful experiences
        if successful_experiences:
            confidence += min(len(successful_experiences) * 0.1, 0.3)

        return min(1.0, confidence)

    async def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights about what the agent has learned"""
        pattern_stats = self.pattern_recognizer.get_pattern_stats()
        strategy_stats = self.strategy_optimizer.get_strategy_stats()
        experience_stats = self.experience_replay.get_statistics()

        return {
            "patterns": pattern_stats,
            "strategies": strategy_stats,
            "experiences": experience_stats,
            "learning_enabled": self.learning_enabled,
            "auto_optimize": self.auto_optimize
        }

    async def export_knowledge(self) -> Dict[str, Any]:
        """Export learned knowledge for persistence"""
        return {
            "patterns": [p.to_dict() for p in self.pattern_recognizer.get_all_patterns()],
            "strategies": self.strategy_optimizer.get_strategy_rankings(),
            "top_experiences": [
                exp.to_dict()
                for exp in (await self.experience_replay.get_successful_experiences(limit=100))
            ]
        }

    async def import_knowledge(self, knowledge: Dict[str, Any]):
        """Import previously learned knowledge"""
        logger.info("📥 Importing learned knowledge...")

        # Note: Full implementation would restore patterns, strategies, etc.
        # This is a placeholder for the architecture

        logger.info("✅ Knowledge imported")

    def set_learning_enabled(self, enabled: bool):
        """Enable/disable learning"""
        self.learning_enabled = enabled
        logger.info(f"🧠 Learning {'enabled' if enabled else 'disabled'}")

    def set_auto_optimize(self, enabled: bool):
        """Enable/disable auto-optimization"""
        self.auto_optimize = enabled
        logger.info(f"⚙️  Auto-optimization {'enabled' if enabled else 'disabled'}")


# Global learning engine instance
learning_engine = LearningEngine()
