"""
Strategy optimization system
Optimizes task execution strategies based on historical performance
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import numpy as np
from loguru import logger


@dataclass
class Strategy:
    """Represents an execution strategy"""
    strategy_id: str
    name: str
    description: str
    applicable_patterns: List[str] = field(default_factory=list)
    tools_sequence: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Performance metrics
    total_uses: int = 0
    successful_uses: int = 0
    failed_uses: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    success_rate: float = 0.0

    # Learning metrics
    exploration_rate: float = 0.2  # Chance to try this strategy
    exploitation_value: float = 0.5  # How good we think this strategy is

    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "applicable_patterns": self.applicable_patterns,
            "tools_sequence": self.tools_sequence,
            "parameters": self.parameters,
            "total_uses": self.total_uses,
            "successful_uses": self.successful_uses,
            "failed_uses": self.failed_uses,
            "avg_duration": self.avg_duration,
            "success_rate": self.success_rate,
            "exploration_rate": self.exploration_rate,
            "exploitation_value": self.exploitation_value,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None
        }


class StrategyOptimizer:
    """
    Strategy optimization using multi-armed bandit approach

    Features:
    - Epsilon-greedy exploration
    - Upper confidence bound (UCB)
    - Success rate tracking
    - Adaptive strategy selection
    """

    def __init__(self, epsilon: float = 0.1):
        """
        Initialize strategy optimizer

        Args:
            epsilon: Exploration rate (0-1), higher = more exploration
        """
        self.strategies: Dict[str, Strategy] = {}
        self.epsilon = epsilon  # For epsilon-greedy
        self.total_selections = 0

        # Initialize default strategies
        self._initialize_default_strategies()

    def _initialize_default_strategies(self):
        """Initialize default execution strategies"""
        default_strategies = [
            Strategy(
                strategy_id="direct_execution",
                name="Direct Execution",
                description="Execute task directly without decomposition",
                applicable_patterns=["simple", "single_step"],
                tools_sequence=["execute"]
            ),
            Strategy(
                strategy_id="decompose_and_execute",
                name="Decompose and Execute",
                description="Break down task into steps, then execute sequentially",
                applicable_patterns=["multi_step", "complex"],
                tools_sequence=["decompose", "execute_steps", "combine"]
            ),
            Strategy(
                strategy_id="research_first",
                name="Research First",
                description="Research the topic before executing",
                applicable_patterns=["search", "research", "analyze"],
                tools_sequence=["search", "analyze", "execute"]
            ),
            Strategy(
                strategy_id="iterative_refinement",
                name="Iterative Refinement",
                description="Execute, evaluate, and refine iteratively",
                applicable_patterns=["create", "generate"],
                tools_sequence=["draft", "evaluate", "refine", "finalize"]
            )
        ]

        for strategy in default_strategies:
            self.strategies[strategy.strategy_id] = strategy

        logger.info(f"📚 Initialized {len(default_strategies)} default strategies")

    async def select_strategy(
        self,
        patterns: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Strategy:
        """
        Select optimal strategy using UCB (Upper Confidence Bound)

        Args:
            patterns: List of applicable pattern IDs
            context: Additional context for selection

        Returns:
            Selected strategy
        """
        self.total_selections += 1

        # Find applicable strategies
        applicable = [
            s for s in self.strategies.values()
            if any(p in s.applicable_patterns for p in patterns) or not s.applicable_patterns
        ]

        if not applicable:
            # Fall back to first strategy
            applicable = list(self.strategies.values())

        # Epsilon-greedy: sometimes explore random strategy
        if np.random.random() < self.epsilon:
            # Exploration: random selection
            strategy = np.random.choice(applicable)
            logger.debug(f"🎲 Exploring with strategy: {strategy.name}")
        else:
            # Exploitation: select best strategy using UCB
            strategy = self._select_ucb(applicable)
            logger.debug(f"🎯 Exploiting with strategy: {strategy.name}")

        return strategy

    def _select_ucb(self, strategies: List[Strategy]) -> Strategy:
        """
        Select strategy using Upper Confidence Bound algorithm

        UCB = exploitation_value + sqrt(2 * ln(total_selections) / strategy_uses)

        Args:
            strategies: List of strategies to choose from

        Returns:
            Strategy with highest UCB score
        """
        best_strategy = None
        best_score = -float('inf')

        for strategy in strategies:
            if strategy.total_uses == 0:
                # Prioritize untried strategies
                return strategy

            # Calculate UCB score
            exploitation = strategy.exploitation_value
            exploration = np.sqrt(
                2 * np.log(self.total_selections) / strategy.total_uses
            )

            ucb_score = exploitation + exploration

            if ucb_score > best_score:
                best_score = ucb_score
                best_strategy = strategy

        return best_strategy or strategies[0]

    async def update_strategy_performance(
        self,
        strategy_id: str,
        success: bool,
        duration: float,
        reward: Optional[float] = None
    ):
        """
        Update strategy performance metrics

        Args:
            strategy_id: Strategy ID
            success: Whether execution succeeded
            duration: Execution duration
            reward: Optional reward signal (0-1)
        """
        if strategy_id not in self.strategies:
            logger.warning(f"Strategy {strategy_id} not found")
            return

        strategy = self.strategies[strategy_id]

        # Update usage counts
        strategy.total_uses += 1
        if success:
            strategy.successful_uses += 1
        else:
            strategy.failed_uses += 1

        # Update duration statistics
        strategy.total_duration += duration
        strategy.avg_duration = strategy.total_duration / strategy.total_uses

        # Update success rate
        strategy.success_rate = strategy.successful_uses / strategy.total_uses

        # Update exploitation value (reward-based)
        if reward is not None:
            # Use exponential moving average
            alpha = 0.1  # Learning rate
            strategy.exploitation_value = (
                (1 - alpha) * strategy.exploitation_value + alpha * reward
            )
        else:
            # Use success rate as proxy for value
            strategy.exploitation_value = strategy.success_rate

        # Update timestamp
        strategy.last_used = datetime.now()

        logger.info(
            f"📊 Updated strategy '{strategy.name}': "
            f"success_rate={strategy.success_rate:.2%}, "
            f"avg_duration={strategy.avg_duration:.1f}s, "
            f"value={strategy.exploitation_value:.2f}"
        )

    async def create_strategy(
        self,
        name: str,
        description: str,
        applicable_patterns: List[str],
        tools_sequence: List[str],
        parameters: Optional[Dict[str, Any]] = None
    ) -> Strategy:
        """
        Create a new strategy

        Args:
            name: Strategy name
            description: Strategy description
            applicable_patterns: Applicable pattern IDs
            tools_sequence: Sequence of tools to use
            parameters: Optional parameters

        Returns:
            Created strategy
        """
        strategy_id = f"strategy_{len(self.strategies)}"

        strategy = Strategy(
            strategy_id=strategy_id,
            name=name,
            description=description,
            applicable_patterns=applicable_patterns,
            tools_sequence=tools_sequence,
            parameters=parameters or {}
        )

        self.strategies[strategy_id] = strategy

        logger.info(f"✨ Created new strategy: {name}")

        return strategy

    def get_strategy_rankings(self) -> List[Dict[str, Any]]:
        """
        Get strategies ranked by performance

        Returns:
            List of strategies sorted by exploitation value
        """
        ranked = sorted(
            self.strategies.values(),
            key=lambda s: s.exploitation_value,
            reverse=True
        )

        return [s.to_dict() for s in ranked]

    def get_strategy_stats(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        total_strategies = len(self.strategies)
        total_uses = sum(s.total_uses for s in self.strategies.values())
        avg_success_rate = (
            sum(s.success_rate for s in self.strategies.values()) / total_strategies
            if total_strategies > 0 else 0.0
        )

        # Find best strategy
        best_strategy = max(
            self.strategies.values(),
            key=lambda s: s.exploitation_value
        ) if self.strategies else None

        return {
            "total_strategies": total_strategies,
            "total_uses": total_uses,
            "avg_success_rate": avg_success_rate,
            "epsilon": self.epsilon,
            "best_strategy": best_strategy.to_dict() if best_strategy else None,
            "rankings": self.get_strategy_rankings()[:5]  # Top 5
        }
