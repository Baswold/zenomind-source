"""
Emotional state tracking for consciousness streaming
Provides richer, more expressive agent state information
"""

from enum import Enum
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


class EmotionType(Enum):
    """Types of agent emotions"""
    # Positive states
    CURIOUS = "curious"  # Exploring new information
    FOCUSED = "focused"  # Deep in work
    CONFIDENT = "confident"  # High certainty
    SATISFIED = "satisfied"  # Task completed well
    EXCITED = "excited"  # Discovered something interesting
    DETERMINED = "determined"  # Pushing through challenges

    # Neutral states
    ANALYZING = "analyzing"  # Processing information
    PLANNING = "planning"  # Strategizing approach
    SEARCHING = "searching"  # Looking for information
    REFLECTING = "reflecting"  # Thinking about approach

    # Challenging states
    UNCERTAIN = "uncertain"  # Low confidence
    STUCK = "stuck"  # Can't make progress
    CONFUSED = "confused"  # Don't understand
    FRUSTRATED = "frustrated"  # Hitting obstacles
    TIRED = "tired"  # Resource constrained

    # Meta states
    LEARNING = "learning"  # Acquiring new knowledge
    ADAPTING = "adapting"  # Changing approach


@dataclass
class EmotionalState:
    """Represents the agent's emotional state"""
    primary_emotion: EmotionType
    intensity: float  # 0.0 to 1.0
    reason: Optional[str] = None
    confidence: float = 0.5  # How confident about this emotion
    duration: float = 0.0  # How long in this state (seconds)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "emotion": self.primary_emotion.value,
            "intensity": self.intensity,
            "reason": self.reason,
            "confidence": self.confidence,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat()
        }


class EmotionalStateTracker:
    """
    Tracks and manages agent's emotional states

    Features:
    - State transitions
    - Emotion intensity tracking
    - Contextual emotion selection
    - State history
    """

    def __init__(self):
        self.current_state: Optional[EmotionalState] = None
        self.state_history: List[EmotionalState] = []
        self.max_history = 100

        # Emotion transition rules
        self.transition_rules = self._initialize_transition_rules()

    def _initialize_transition_rules(self) -> Dict:
        """Initialize emotion transition probabilities"""
        return {
            # From CURIOUS
            EmotionType.CURIOUS: {
                EmotionType.EXCITED: 0.3,  # Found something!
                EmotionType.FOCUSED: 0.3,  # Deep diving
                EmotionType.ANALYZING: 0.2,
                EmotionType.UNCERTAIN: 0.2  # Didn't find what expected
            },
            # From FOCUSED
            EmotionType.FOCUSED: {
                EmotionType.SATISFIED: 0.3,  # Made progress
                EmotionType.STUCK: 0.2,  # Hit obstacle
                EmotionType.ANALYZING: 0.3,
                EmotionType.TIRED: 0.2  # Long session
            },
            # From STUCK
            EmotionType.STUCK: {
                EmotionType.FRUSTRATED: 0.3,  # Still stuck
                EmotionType.ADAPTING: 0.4,  # Trying new approach
                EmotionType.REFLECTING: 0.3  # Rethinking
            },
            # From UNCERTAIN
            EmotionType.UNCERTAIN: {
                EmotionType.SEARCHING: 0.4,  # Looking for info
                EmotionType.CONFUSED: 0.3,  # Still unclear
                EmotionType.LEARNING: 0.3  # Researching
            }
        }

    def infer_emotion(
        self,
        context: Dict[str, any]
    ) -> EmotionType:
        """
        Infer appropriate emotion based on context

        Args:
            context: Dictionary with context info like:
                - progress: float
                - errors: List[str]
                - success: bool
                - complexity: str
                - new_information: bool

        Returns:
            Appropriate emotion
        """
        progress = context.get("progress", 0.0)
        errors = context.get("errors", [])
        success = context.get("success")
        new_information = context.get("new_information", False)
        complexity = context.get("complexity", "medium")

        # Just started
        if progress < 0.1:
            return EmotionType.CURIOUS

        # Making good progress, no errors
        if progress > 0.7 and not errors:
            return EmotionType.CONFIDENT

        # Completed successfully
        if success is True:
            return EmotionType.SATISFIED

        # Failed
        if success is False:
            if errors:
                return EmotionType.FRUSTRATED
            return EmotionType.UNCERTAIN

        # Stuck in middle with errors
        if 0.3 < progress < 0.7 and errors:
            return EmotionType.STUCK

        # Discovered something new
        if new_information:
            return EmotionType.EXCITED

        # High complexity
        if complexity == "high":
            return EmotionType.FOCUSED

        # Default to analyzing
        return EmotionType.ANALYZING

    def update_state(
        self,
        emotion: EmotionType,
        intensity: float,
        reason: Optional[str] = None
    ):
        """
        Update the current emotional state

        Args:
            emotion: New emotion
            intensity: Emotion intensity (0-1)
            reason: Optional reason for the emotion
        """
        # Calculate duration of previous state
        if self.current_state:
            duration = (datetime.now() - self.current_state.timestamp).total_seconds()
            self.current_state.duration = duration

            # Add to history
            self.state_history.append(self.current_state)

            # Limit history size
            if len(self.state_history) > self.max_history:
                self.state_history.pop(0)

        # Create new state
        self.current_state = EmotionalState(
            primary_emotion=emotion,
            intensity=intensity,
            reason=reason
        )

        logger.debug(
            f"💭 Emotional state: {emotion.value} "
            f"(intensity: {intensity:.2f})"
        )

    def get_state_summary(self) -> Dict:
        """Get summary of emotional states"""
        if not self.current_state:
            return {
                "current": None,
                "history_count": 0,
                "dominant_emotion": None
            }

        # Find most common emotion in recent history
        recent_history = self.state_history[-10:]
        if recent_history:
            emotion_counts = {}
            for state in recent_history:
                emotion = state.primary_emotion.value
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

            dominant = max(emotion_counts.items(), key=lambda x: x[1])
            dominant_emotion = dominant[0]
        else:
            dominant_emotion = None

        return {
            "current": self.current_state.to_dict() if self.current_state else None,
            "history_count": len(self.state_history),
            "dominant_emotion": dominant_emotion
        }

    def get_emotion_insights(self) -> Dict:
        """Get insights about emotional patterns"""
        if not self.state_history:
            return {
                "total_states": 0,
                "avg_intensity": 0.0,
                "most_common": None
            }

        # Calculate statistics
        total_states = len(self.state_history)
        avg_intensity = sum(s.intensity for s in self.state_history) / total_states

        # Count emotions
        emotion_counts = {}
        for state in self.state_history:
            emotion = state.primary_emotion.value
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        most_common = max(emotion_counts.items(), key=lambda x: x[1])[0]

        return {
            "total_states": total_states,
            "avg_intensity": avg_intensity,
            "most_common": most_common,
            "emotion_distribution": emotion_counts
        }


# Global emotional state tracker
emotional_state_tracker = EmotionalStateTracker()
