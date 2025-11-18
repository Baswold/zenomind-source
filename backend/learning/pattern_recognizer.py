"""
Pattern recognition system
Identifies common patterns in tasks and successful approaches
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from loguru import logger
import re
import json


@dataclass
class TaskPattern:
    """Represents a recognized task pattern"""
    pattern_id: str
    pattern_type: str  # keyword, structure, semantic, temporal
    description: str
    keywords: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    occurrence_count: int = 0
    avg_duration: float = 0.0  # seconds
    optimal_tools: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "keywords": self.keywords,
            "success_rate": self.success_rate,
            "occurrence_count": self.occurrence_count,
            "avg_duration": self.avg_duration,
            "optimal_tools": self.optimal_tools,
            "metadata": self.metadata,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat()
        }


class PatternRecognizer:
    """
    Advanced pattern recognition system

    Features:
    - Keyword-based pattern matching
    - Structural pattern detection
    - Temporal pattern analysis
    - Success correlation tracking
    """

    def __init__(self):
        self.patterns: Dict[str, TaskPattern] = {}
        self.pattern_counter = 0

        # Predefined pattern templates
        self.keyword_patterns = {
            "search": ["search", "find", "lookup", "query", "research"],
            "create": ["create", "make", "generate", "build", "write", "compose"],
            "analyze": ["analyze", "examine", "review", "compare", "evaluate"],
            "transform": ["convert", "transform", "translate", "format", "process"],
            "summarize": ["summarize", "condense", "brief", "overview", "recap"],
            "code": ["code", "program", "script", "function", "implement"],
            "data": ["data", "dataset", "csv", "json", "database"]
        }

    async def analyze_task(
        self,
        task_prompt: str,
        task_result: Optional[str] = None,
        success: bool = True,
        duration: float = 0.0,
        tools_used: List[str] = None
    ) -> List[str]:
        """
        Analyze a task and identify matching patterns

        Args:
            task_prompt: Task description
            task_result: Task result
            success: Whether task succeeded
            duration: Task duration in seconds
            tools_used: List of tools used

        Returns:
            List of matched pattern IDs
        """
        matched_patterns = []

        # Keyword pattern matching
        prompt_lower = task_prompt.lower()

        for pattern_type, keywords in self.keyword_patterns.items():
            if any(keyword in prompt_lower for keyword in keywords):
                pattern_id = await self._get_or_create_pattern(
                    pattern_type,
                    keywords
                )

                # Update pattern statistics
                await self._update_pattern_stats(
                    pattern_id,
                    success,
                    duration,
                    tools_used or []
                )

                matched_patterns.append(pattern_id)

        # Structural pattern detection
        structural_patterns = await self._detect_structural_patterns(task_prompt)
        matched_patterns.extend(structural_patterns)

        logger.info(f"🔍 Identified {len(matched_patterns)} patterns in task")

        return matched_patterns

    async def _get_or_create_pattern(
        self,
        pattern_type: str,
        keywords: List[str]
    ) -> str:
        """Get existing pattern or create new one"""
        # Generate pattern ID
        pattern_id = f"pattern_{pattern_type}"

        if pattern_id not in self.patterns:
            # Create new pattern
            self.patterns[pattern_id] = TaskPattern(
                pattern_id=pattern_id,
                pattern_type="keyword",
                description=f"{pattern_type.capitalize()} tasks",
                keywords=keywords
            )

            logger.info(f"📝 Created new pattern: {pattern_type}")

        return pattern_id

    async def _update_pattern_stats(
        self,
        pattern_id: str,
        success: bool,
        duration: float,
        tools_used: List[str]
    ):
        """Update pattern statistics"""
        if pattern_id not in self.patterns:
            return

        pattern = self.patterns[pattern_id]

        # Update occurrence count
        pattern.occurrence_count += 1

        # Update success rate (running average)
        if pattern.occurrence_count == 1:
            pattern.success_rate = 1.0 if success else 0.0
        else:
            old_rate = pattern.success_rate
            pattern.success_rate = (
                (old_rate * (pattern.occurrence_count - 1) + (1.0 if success else 0.0))
                / pattern.occurrence_count
            )

        # Update average duration
        if duration > 0:
            if pattern.avg_duration == 0:
                pattern.avg_duration = duration
            else:
                pattern.avg_duration = (
                    (pattern.avg_duration * (pattern.occurrence_count - 1) + duration)
                    / pattern.occurrence_count
                )

        # Track optimal tools
        if success and tools_used:
            for tool in tools_used:
                if tool not in pattern.optimal_tools:
                    pattern.optimal_tools.append(tool)

        # Update timestamp
        pattern.last_seen = datetime.now()

    async def _detect_structural_patterns(
        self,
        task_prompt: str
    ) -> List[str]:
        """
        Detect structural patterns in task

        Examples:
        - Lists: "Create a list of..."
        - Comparisons: "Compare X and Y"
        - Multi-step: "First... then... finally..."
        """
        patterns = []

        # List pattern
        if re.search(r'\blist of\b|\blists?\b|\bitems?\b', task_prompt, re.IGNORECASE):
            patterns.append(await self._create_structural_pattern("list"))

        # Comparison pattern
        if re.search(r'\bcompare\b|\bvs\.?\b|\bversus\b', task_prompt, re.IGNORECASE):
            patterns.append(await self._create_structural_pattern("comparison"))

        # Multi-step pattern
        if re.search(r'\b(first|then|next|finally|after|before)\b', task_prompt, re.IGNORECASE):
            patterns.append(await self._create_structural_pattern("multi_step"))

        # Question pattern
        if task_prompt.strip().endswith('?'):
            patterns.append(await self._create_structural_pattern("question"))

        return patterns

    async def _create_structural_pattern(self, structure_type: str) -> str:
        """Create or get structural pattern"""
        pattern_id = f"struct_{structure_type}"

        if pattern_id not in self.patterns:
            self.patterns[pattern_id] = TaskPattern(
                pattern_id=pattern_id,
                pattern_type="structure",
                description=f"{structure_type.replace('_', ' ').title()} structure",
                metadata={"structure_type": structure_type}
            )

        return pattern_id

    async def get_recommendations(
        self,
        task_prompt: str
    ) -> Dict[str, Any]:
        """
        Get recommendations based on recognized patterns

        Args:
            task_prompt: Task description

        Returns:
            Recommendations dictionary
        """
        # Analyze task
        matched_patterns = await self.analyze_task(task_prompt)

        if not matched_patterns:
            return {
                "patterns_found": 0,
                "recommendations": []
            }

        # Get patterns
        patterns = [
            self.patterns[pid] for pid in matched_patterns
            if pid in self.patterns
        ]

        # Sort by success rate
        patterns.sort(key=lambda p: p.success_rate, reverse=True)

        recommendations = []

        for pattern in patterns:
            if pattern.occurrence_count >= 3:  # Only recommend if seen enough times
                recommendations.append({
                    "pattern": pattern.description,
                    "success_rate": f"{pattern.success_rate * 100:.1f}%",
                    "avg_duration": f"{pattern.avg_duration:.1f}s",
                    "optimal_tools": pattern.optimal_tools[:3],  # Top 3 tools
                    "confidence": min(pattern.occurrence_count / 10, 1.0)  # Max at 10 occurrences
                })

        return {
            "patterns_found": len(patterns),
            "recommendations": recommendations
        }

    def get_all_patterns(self) -> List[TaskPattern]:
        """Get all recognized patterns"""
        return list(self.patterns.values())

    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get pattern statistics"""
        total_patterns = len(self.patterns)
        total_occurrences = sum(p.occurrence_count for p in self.patterns.values())
        avg_success_rate = (
            sum(p.success_rate for p in self.patterns.values()) / total_patterns
            if total_patterns > 0 else 0.0
        )

        # Group by type
        by_type = defaultdict(int)
        for pattern in self.patterns.values():
            by_type[pattern.pattern_type] += 1

        return {
            "total_patterns": total_patterns,
            "total_occurrences": total_occurrences,
            "avg_success_rate": avg_success_rate,
            "by_type": dict(by_type),
            "top_patterns": sorted(
                [p.to_dict() for p in self.patterns.values()],
                key=lambda x: x["occurrence_count"],
                reverse=True
            )[:10]
        }
