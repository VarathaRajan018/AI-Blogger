"""Retry utilities using tenacity.

Provides configurable retry decorators with exponential backoff
and structured logging of retry attempts.

Usage:
    from app.utils.retry import retry_with_backoff

    @retry_with_backoff(max_retries=3)
    async def call_external_api():
        ...
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Sequence, Type

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.utils.logging import get_logger

logger = get_logger(__name__)


# Default retryable exceptions (network/API errors)
DEFAULT_RETRYABLE_EXCEPTIONS: tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def retry_with_backoff(
    max_retries: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
    retryable_exceptions: Sequence[Type[Exception]] | None = None,
) -> Callable[..., Any]:
    """Decorator factory for async functions with exponential backoff retry.

    Args:
        max_retries: Maximum number of retry attempts.
        min_wait: Minimum seconds to wait between retries.
        max_wait: Maximum seconds to wait between retries.
        retryable_exceptions: Exception types that trigger a retry.
            Defaults to ConnectionError, TimeoutError, OSError.

    Returns:
        Decorator that wraps async functions with retry logic.

    Example:
        @retry_with_backoff(max_retries=3)
        async def fetch_data():
            async with httpx.AsyncClient() as client:
                return await client.get("https://api.example.com")
    """
    exceptions = tuple(retryable_exceptions or DEFAULT_RETRYABLE_EXCEPTIONS)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @retry(
            stop=stop_after_attempt(max_retries + 1),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            reraise=True,
        )
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        # Store retry config on the wrapper for introspection
        wrapper.max_retries = max_retries  # type: ignore[attr-defined]
        wrapper.retryable_exceptions = exceptions  # type: ignore[attr-defined]

        return wrapper

    return decorator


async def execute_with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
    retryable_exceptions: Sequence[Type[Exception]] | None = None,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Any:
    """Execute an async function with retry logic (imperative style).

    Use this when you cannot use the decorator pattern (e.g., calling
    a method on a dynamically resolved object).

    Args:
        func: Async callable to execute.
        *args: Positional arguments for func.
        max_retries: Maximum retry attempts.
        min_wait: Minimum wait between retries in seconds.
        max_wait: Maximum wait between retries in seconds.
        retryable_exceptions: Exception types that trigger retry.
        context: Optional dict of context values for logging.
        **kwargs: Keyword arguments for func.

    Returns:
        The return value of func.

    Raises:
        The last exception if all retries are exhausted.
    """
    exceptions = tuple(retryable_exceptions or DEFAULT_RETRYABLE_EXCEPTIONS)
    ctx = context or {}

    last_exception: Exception | None = None

    for attempt in range(1, max_retries + 2):
        try:
            return await func(*args, **kwargs)
        except exceptions as exc:
            last_exception = exc
            if attempt <= max_retries:
                wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
                logger.warning(
                    "retrying after error",
                    function=func.__name__,
                    attempt=attempt,
                    max_retries=max_retries,
                    wait_seconds=wait_time,
                    error=str(exc),
                    **ctx,
                )
                import asyncio
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    "all retries exhausted",
                    function=func.__name__,
                    total_attempts=attempt,
                    error=str(exc),
                    **ctx,
                )
                raise
    # Should never reach here, but satisfies type checker
    raise last_exception  # type: ignore[misc]
