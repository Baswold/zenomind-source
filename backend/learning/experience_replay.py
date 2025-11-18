"""
Experience replay system
Stores and replays agent experiences for continuous learning
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import random
from loguru import logger


@dataclass
class Experience:
    """Represents a single agent experience"""
    experience_id: str
    task_prompt: str
    task_result: Optional[str]
    success: bool
    duration: float
    patterns: List[str] = field(default_factory=list)
    strategy_used: Optional[str] = None
    tools_used: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    reward: float = 0.0  # Computed reward signal
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "experience_id": self.experience_id,
            "task_prompt": self.task_prompt,
            "task_result": self.task_result,
            "success": self.success,
            "duration": self.duration,
            "patterns": self.patterns,
            "strategy_used": self.strategy_used,
            "tools_used": self.tools_used,
            "errors": self.errors,
            "reward": self.reward,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class ExperienceReplay:
    """
    Experience replay buffer

    Features:
    - Stores agent experiences
    - Prioritized sampling
    - Experience deduplication
    - Batch retrieval for learning
    """

    def __init__(self, max_size: int = 10000):
        """
        Initialize experience replay buffer

        Args:
            max_size: Maximum number of experiences to store
        """
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.experience_counter = 0

        # Priority tracking for sampling
        self.priorities: Dict[str, float] = {}

    async def add_experience(
        self,
        task_prompt: str,
        task_result: Optional[str],
        success: bool,
        duration: float,
        patterns: List[str] = None,
        strategy_used: Optional[str] = None,
        tools_used: List[str] = None,
        errors: List[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Experience:
        """
        Add an experience to the buffer

        Args:
            task_prompt: Task description
            task_result: Task result
            success: Whether task succeeded
            duration: Task duration
            patterns: Identified patterns
            strategy_used: Strategy ID used
            tools_used: Tools used
            errors: Errors encountered
            metadata: Additional metadata

        Returns:
            Created experience
        """
        experience_id = f"exp_{self.experience_counter}"
        self.experience_counter += 1

        # Calculate reward signal
        reward = self._calculate_reward(success, duration, errors or [])

        experience = Experience(
            experience_id=experience_id,
            task_prompt=task_prompt,
            task_result=task_result,
            success=success,
            duration=duration,
            patterns=patterns or [],
            strategy_used=strategy_used,
            tools_used=tools_used or [],
            errors=errors or [],
            reward=reward,
            metadata=metadata or {}
        )

        # Add to buffer
        self.buffer.append(experience)

        # Set priority (higher for failures and extreme cases)
        priority = self._calculate_priority(experience)
        self.priorities[experience_id] = priority

        logger.debug(f"💾 Stored experience: {experience_id} (reward: {reward:.2f})")

        return experience

    def _calculate_reward(
        self,
        success: bool,
        duration: float,
        errors: List[str]
    ) -> float:
        """
        Calculate reward signal for an experience

        Reward factors:
        - Success: +1.0
        - Failure: -0.5
        - Speed bonus: +0.3 if < 10s, +0.1 if < 60s
        - Error penalty: -0.1 per error

        Args:
            success: Whether task succeeded
            duration: Task duration
            errors: List of errors

        Returns:
            Reward value (typically -1.0 to 1.5)
        """
        reward = 1.0 if success else -0.5

        # Speed bonus
        if duration < 10:
            reward += 0.3
        elif duration < 60:
            reward += 0.1

        # Error penalty
        reward -= len(errors) * 0.1

        # Clamp between -1 and 2
        return max(-1.0, min(2.0, reward))

    def _calculate_priority(self, experience: Experience) -> float:
        """
        Calculate sampling priority for an experience

        Higher priority for:
        - Failures (to learn from mistakes)
        - Unusual/rare patterns
        - Recent experiences

        Args:
            experience: Experience to prioritize

        Returns:
            Priority value (0-1)
        """
        priority = 0.5  # Base priority

        # Failures get higher priority
        if not experience.success:
            priority += 0.3

        # Recent experiences get slight boost
        age_hours = (datetime.now() - experience.timestamp).total_seconds() / 3600
        if age_hours < 1:
            priority += 0.2
        elif age_hours < 24:
            priority += 0.1

        # Normalize to 0-1
        return min(1.0, priority)

    async def sample_batch(
        self,
        batch_size: int = 32,
        prioritized: bool = True
    ) -> List[Experience]:
        """
        Sample a batch of experiences for learning

        Args:
            batch_size: Number of experiences to sample
            prioritized: Whether to use prioritized sampling

        Returns:
            List of sampled experiences
        """
        if not self.buffer:
            return []

        batch_size = min(batch_size, len(self.buffer))

        if prioritized and self.priorities:
            # Prioritized sampling
            experiences = list(self.buffer)
            weights = [
                self.priorities.get(exp.experience_id, 0.5)
                for exp in experiences
            ]

            # Normalize weights
            total_weight = sum(weights)
            if total_weight > 0:
                weights = [w / total_weight for w in weights]
            else:
                weights = [1.0 / len(weights)] * len(weights)

            # Sample with weights
            sampled = random.choices(
                experiences,
                weights=weights,
                k=batch_size
            )
        else:
            # Uniform random sampling
            sampled = random.sample(list(self.buffer), batch_size)

        logger.debug(f"📊 Sampled {len(sampled)} experiences for learning")

        return sampled

    async def get_successful_experiences(
        self,
        patterns: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Experience]:
        """
        Get successful experiences, optionally filtered by patterns

        Args:
            patterns: Optional pattern filter
            limit: Maximum number to return

        Returns:
            List of successful experiences
        """
        successful = [
            exp for exp in self.buffer
            if exp.success and (
                not patterns or
                any(p in exp.patterns for p in patterns)
            )
        ]

        # Sort by reward
        successful.sort(key=lambda x: x.reward, reverse=True)

        return successful[:limit]

    async def get_failure_experiences(
        self,
        patterns: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Experience]:
        """
        Get failed experiences for learning from mistakes

        Args:
            patterns: Optional pattern filter
            limit: Maximum number to return

        Returns:
            List of failed experiences
        """
        failures = [
            exp for exp in self.buffer
            if not exp.success and (
                not patterns or
                any(p in exp.patterns for p in patterns)
            )
        ]

        # Sort by recency
        failures.sort(key=lambda x: x.timestamp, reverse=True)

        return failures[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get experience buffer statistics"""
        total = len(self.buffer)
        if total == 0:
            return {
                "total_experiences": 0,
                "success_count": 0,
                "failure_count": 0,
                "avg_reward": 0.0,
                "avg_duration": 0.0
            }

        successful = sum(1 for exp in self.buffer if exp.success)
        failed = total - successful

        avg_reward = sum(exp.reward for exp in self.buffer) / total
        avg_duration = sum(exp.duration for exp in self.buffer) / total

        return {
            "total_experiences": total,
            "success_count": successful,
            "failure_count": failed,
            "success_rate": successful / total,
            "avg_reward": avg_reward,
            "avg_duration": avg_duration,
            "buffer_utilization": total / self.max_size
        }

    def clear_old_experiences(self, hours: int = 168):  # 1 week default
        """
        Clear experiences older than specified hours

        Args:
            hours: Age threshold in hours
        """
        cutoff = datetime.now().timestamp() - (hours * 3600)

        before_count = len(self.buffer)

        # Filter buffer
        self.buffer = deque(
            (exp for exp in self.buffer if exp.timestamp.timestamp() > cutoff),
            maxlen=self.max_size
        )

        # Clean priorities
        valid_ids = {exp.experience_id for exp in self.buffer}
        self.priorities = {
            k: v for k, v in self.priorities.items()
            if k in valid_ids
        }

        removed = before_count - len(self.buffer)

        if removed > 0:
            logger.info(f"🧹 Cleared {removed} old experiences")
