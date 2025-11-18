"""
Comprehensive error handling system
Provides categorization, logging, and recovery strategies for errors
"""

import traceback
import sys
from typing import Optional, Callable, Any, Dict
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from loguru import logger
import asyncio


class ErrorCategory(Enum):
    """Error category classification"""
    NETWORK = "network"  # Network-related errors
    DATABASE = "database"  # Database errors
    VALIDATION = "validation"  # Input validation errors
    AUTHENTICATION = "authentication"  # Auth errors
    AUTHORIZATION = "authorization"  # Permission errors
    RESOURCE = "resource"  # Resource not found errors
    RATE_LIMIT = "rate_limit"  # Rate limiting errors
    TIMEOUT = "timeout"  # Timeout errors
    INTERNAL = "internal"  # Internal server errors
    EXTERNAL_API = "external_api"  # Third-party API errors
    UNKNOWN = "unknown"  # Uncategorized errors


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"  # Minor issues, no immediate action needed
    MEDIUM = "medium"  # Issues that need attention but not critical
    HIGH = "high"  # Critical issues requiring immediate attention
    CRITICAL = "critical"  # System-breaking issues


@dataclass
class ErrorContext:
    """Context information for an error"""
    category: ErrorCategory
    severity: ErrorSeverity
    error: Exception
    timestamp: datetime = field(default_factory=datetime.now)
    function_name: Optional[str] = None
    traceback_str: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    recovery_attempted: bool = False
    recovery_successful: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "error_type": type(self.error).__name__,
            "error_message": str(self.error),
            "timestamp": self.timestamp.isoformat(),
            "function_name": self.function_name,
            "traceback": self.traceback_str,
            "metadata": self.metadata,
            "recovery_attempted": self.recovery_attempted,
            "recovery_successful": self.recovery_successful
        }


class ErrorHandler:
    """
    Centralized error handling system

    Features:
    - Error categorization
    - Severity classification
    - Structured logging
    - Recovery strategies
    - Error metrics tracking
    """

    def __init__(self):
        self.error_history: list[ErrorContext] = []
        self.error_counts: Dict[ErrorCategory, int] = {cat: 0 for cat in ErrorCategory}
        self.recovery_strategies: Dict[ErrorCategory, Callable] = {}

    def categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Categorize an error based on its type

        Args:
            error: Exception to categorize

        Returns:
            ErrorCategory
        """
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()

        # Network errors
        if any(term in error_type for term in ['connection', 'network', 'socket', 'timeout']):
            return ErrorCategory.NETWORK

        if 'timeout' in error_message:
            return ErrorCategory.TIMEOUT

        # Database errors
        if any(term in error_type for term in ['database', 'sql', 'db', 'integrity']):
            return ErrorCategory.DATABASE

        # Validation errors
        if any(term in error_type for term in ['validation', 'invalid', 'value']):
            return ErrorCategory.VALIDATION

        # Authentication/Authorization
        if any(term in error_message for term in ['unauthorized', 'authentication', 'auth']):
            return ErrorCategory.AUTHENTICATION

        if any(term in error_message for term in ['forbidden', 'permission', 'access denied']):
            return ErrorCategory.AUTHORIZATION

        # Resource errors
        if any(term in error_message for term in ['not found', 'does not exist']):
            return ErrorCategory.RESOURCE

        # Rate limiting
        if any(term in error_message for term in ['rate limit', 'too many requests', '429']):
            return ErrorCategory.RATE_LIMIT

        # API errors
        if any(term in error_type for term in ['api', 'http', 'request']):
            return ErrorCategory.EXTERNAL_API

        return ErrorCategory.UNKNOWN

    def determine_severity(
        self,
        error: Exception,
        category: ErrorCategory
    ) -> ErrorSeverity:
        """
        Determine error severity

        Args:
            error: Exception
            category: Error category

        Returns:
            ErrorSeverity
        """
        # Critical categories
        if category in [ErrorCategory.DATABASE, ErrorCategory.INTERNAL]:
            return ErrorSeverity.CRITICAL

        # High severity
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.NETWORK]:
            return ErrorSeverity.HIGH

        # Medium severity
        if category in [ErrorCategory.TIMEOUT, ErrorCategory.EXTERNAL_API, ErrorCategory.RATE_LIMIT]:
            return ErrorSeverity.MEDIUM

        # Low severity
        if category in [ErrorCategory.VALIDATION, ErrorCategory.RESOURCE]:
            return ErrorSeverity.LOW

        return ErrorSeverity.MEDIUM

    def register_recovery_strategy(
        self,
        category: ErrorCategory,
        strategy: Callable[[ErrorContext], Any]
    ):
        """
        Register a recovery strategy for an error category

        Args:
            category: Error category
            strategy: Callable that attempts to recover from the error
        """
        self.recovery_strategies[category] = strategy
        logger.info(f"🔧 Registered recovery strategy for {category.value}")

    async def handle_error(
        self,
        error: Exception,
        function_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        attempt_recovery: bool = True
    ) -> ErrorContext:
        """
        Handle an error with categorization, logging, and optional recovery

        Args:
            error: Exception to handle
            function_name: Name of the function where error occurred
            metadata: Additional context
            attempt_recovery: Whether to attempt recovery

        Returns:
            ErrorContext with details about handling
        """
        # Categorize and create context
        category = self.categorize_error(error)
        severity = self.determine_severity(error, category)

        context = ErrorContext(
            category=category,
            severity=severity,
            error=error,
            function_name=function_name,
            traceback_str=traceback.format_exc(),
            metadata=metadata or {}
        )

        # Track error
        self.error_history.append(context)
        self.error_counts[category] += 1

        # Log error based on severity
        log_message = (
            f"[{category.value.upper()}] {type(error).__name__}: {str(error)}"
            f"\n    Function: {function_name or 'unknown'}"
            f"\n    Severity: {severity.value}"
        )

        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # Attempt recovery if enabled and strategy exists
        if attempt_recovery and category in self.recovery_strategies:
            try:
                context.recovery_attempted = True
                logger.info(f"🔧 Attempting recovery for {category.value} error...")

                recovery_strategy = self.recovery_strategies[category]

                # Handle both sync and async recovery strategies
                if asyncio.iscoroutinefunction(recovery_strategy):
                    await recovery_strategy(context)
                else:
                    recovery_strategy(context)

                context.recovery_successful = True
                logger.info(f"✅ Recovery successful for {category.value} error")

            except Exception as recovery_error:
                context.recovery_successful = False
                logger.error(
                    f"❌ Recovery failed for {category.value} error: {str(recovery_error)}"
                )

        return context

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        total_errors = len(self.error_history)

        return {
            "total_errors": total_errors,
            "by_category": {cat.value: count for cat, count in self.error_counts.items()},
            "recent_errors": [ctx.to_dict() for ctx in self.error_history[-10:]],
            "recovery_rate": (
                sum(1 for ctx in self.error_history if ctx.recovery_successful) / total_errors
                if total_errors > 0 else 0.0
            )
        }

    def clear_old_errors(self, max_age_hours: int = 24):
        """Clear old errors from history"""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)

        self.error_history = [
            ctx for ctx in self.error_history
            if ctx.timestamp.timestamp() > cutoff
        ]

        logger.info(f"🧹 Cleared old errors (keeping last {max_age_hours}h)")


# Global error handler instance
error_handler = ErrorHandler()


def handle_errors(
    category: Optional[ErrorCategory] = None,
    severity: Optional[ErrorSeverity] = None,
    reraise: bool = True,
    attempt_recovery: bool = True
):
    """
    Decorator for automatic error handling

    Args:
        category: Optional forced category (otherwise auto-detected)
        severity: Optional forced severity (otherwise auto-determined)
        reraise: Whether to re-raise the error after handling
        attempt_recovery: Whether to attempt recovery

    Example:
        @handle_errors(category=ErrorCategory.NETWORK, reraise=True)
        async def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Handle the error
                context = await error_handler.handle_error(
                    e,
                    function_name=func.__name__,
                    metadata={"args": str(args)[:100], "kwargs": str(kwargs)[:100]},
                    attempt_recovery=attempt_recovery
                )

                # Override category/severity if specified
                if category:
                    context.category = category
                if severity:
                    context.severity = severity

                # Re-raise if requested
                if reraise:
                    raise

        return wrapper
    return decorator


# Register default recovery strategies
async def network_recovery(context: ErrorContext):
    """Default recovery strategy for network errors"""
    logger.info("🔄 Network recovery: Waiting before retry...")
    await asyncio.sleep(2)


async def rate_limit_recovery(context: ErrorContext):
    """Default recovery strategy for rate limit errors"""
    logger.info("🔄 Rate limit recovery: Waiting 60 seconds...")
    await asyncio.sleep(60)


error_handler.register_recovery_strategy(
    ErrorCategory.NETWORK,
    network_recovery
)
error_handler.register_recovery_strategy(
    ErrorCategory.RATE_LIMIT,
    rate_limit_recovery
)
