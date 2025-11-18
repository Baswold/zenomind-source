"""
Retry utilities with exponential backoff
Provides robust retry mechanisms for handling transient failures
"""

import asyncio
import functools
import random
from typing import Callable, Any, TypeVar, Optional, Type, Tuple
from dataclasses import dataclass
from loguru import logger
import traceback


T = TypeVar('T')


class RetryableError(Exception):
    """Base class for retryable errors"""
    pass


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 5
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomization to prevent thundering herd
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        RetryableError,
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError
    )

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the given attempt number

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: delay = initial_delay * (base ^ attempt)
        delay = self.initial_delay * (self.exponential_base ** attempt)

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter (randomness) to prevent thundering herd
        if self.jitter:
            delay = delay * (0.5 + random.random())  # Random between 50% and 150%

        return delay


def retry_async(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator for async functions with exponential backoff retry logic

    Args:
        config: RetryConfig instance for customization
        on_retry: Optional callback called on each retry with (exception, attempt)

    Example:
        @retry_async(RetryConfig(max_attempts=3))
        async def fetch_data():
            # This will retry up to 3 times with exponential backoff
            return await api_call()
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    # Try to execute the function
                    result = await func(*args, **kwargs)

                    # Success! Log if we had previous failures
                    if attempt > 0:
                        logger.info(
                            f"✅ {func.__name__} succeeded on attempt {attempt + 1}"
                        )

                    return result

                except config.retryable_exceptions as e:
                    last_exception = e

                    # Check if we should retry
                    if attempt < config.max_attempts - 1:
                        delay = config.calculate_delay(attempt)

                        logger.warning(
                            f"⚠️  {func.__name__} failed (attempt {attempt + 1}/{config.max_attempts}): {str(e)}"
                            f"\n    Retrying in {delay:.2f}s..."
                        )

                        # Call on_retry callback if provided
                        if on_retry:
                            on_retry(e, attempt)

                        # Wait before retrying
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"❌ {func.__name__} failed after {config.max_attempts} attempts: {str(e)}"
                        )

                except Exception as e:
                    # Non-retryable exception, raise immediately
                    logger.error(
                        f"❌ {func.__name__} failed with non-retryable error: {str(e)}"
                    )
                    raise

            # All retries exhausted
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


async def retry_with_exponential_backoff(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> T:
    """
    Execute an async function with exponential backoff retry

    Args:
        func: Async function to execute
        *args: Arguments to pass to func
        config: RetryConfig instance
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result from func

    Example:
        result = await retry_with_exponential_backoff(
            fetch_data,
            url="https://api.example.com",
            config=RetryConfig(max_attempts=3)
        )
    """
    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)

            if attempt > 0:
                logger.info(
                    f"✅ {func.__name__} succeeded on attempt {attempt + 1}"
                )

            return result

        except config.retryable_exceptions as e:
            last_exception = e

            if attempt < config.max_attempts - 1:
                delay = config.calculate_delay(attempt)

                logger.warning(
                    f"⚠️  {func.__name__} failed (attempt {attempt + 1}/{config.max_attempts}): {str(e)}"
                    f"\n    Retrying in {delay:.2f}s..."
                )

                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"❌ {func.__name__} failed after {config.max_attempts} attempts"
                )

        except Exception as e:
            logger.error(
                f"❌ {func.__name__} failed with non-retryable error: {str(e)}"
            )
            raise

    if last_exception:
        raise last_exception


class CircuitBreaker:
    """
    Circuit breaker pattern implementation

    Prevents cascading failures by stopping calls to a failing service
    after a threshold is reached, then gradually allowing retries.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, all requests immediately fail
    - HALF_OPEN: Testing if service recovered, limited requests pass through
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function through circuit breaker

        Args:
            func: Async function to execute
            *args: Arguments to pass to func
            **kwargs: Keyword arguments to pass to func

        Returns:
            Result from func

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "OPEN":
            # Check if recovery timeout has passed
            if (asyncio.get_event_loop().time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("🔄 Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)

            # Success! Reset if we were in HALF_OPEN
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("✅ Circuit breaker CLOSED (service recovered)")

            return result

        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = asyncio.get_event_loop().time()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(
                    f"⚠️  Circuit breaker OPEN (threshold: {self.failure_threshold} failures)"
                )

            raise


# Predefined retry configurations for common scenarios
NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True
)

DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True
)

API_RETRY_CONFIG = RetryConfig(
    max_attempts=4,
    initial_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True
)

QUICK_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=0.1,
    max_delay=1.0,
    exponential_base=2.0,
    jitter=False
)
