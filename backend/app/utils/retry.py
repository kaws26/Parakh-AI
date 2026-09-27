"""Retry helpers for transient LLM, network, and rate limit failures."""

from __future__ import annotations

import asyncio
import inspect
import logging
import random
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


def is_transient_error(exc: Exception) -> bool:
    """Determine whether an exception represents a transient failure eligible for retry."""
    # Check for HTTP status codes commonly associated with transient/rate-limit issues
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status_code in {429, 500, 502, 503, 504}:
        return True

    exc_str = str(exc).lower()
    transient_indicators = [
        "rate limit",
        "429",
        "resource exhausted",
        "quota exceeded",
        "service unavailable",
        "503",
        "gateway timeout",
        "504",
        "connection reset",
        "timed out",
        "timeout",
    ]
    return any(indicator in exc_str for indicator in transient_indicators)


def retry_on_transient(
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    jitter: float = 0.2,
    retry_exceptions: tuple[type[Exception], ...] | None = None,
):
    """Decorator for retrying async or sync functions with exponential backoff and jitter.

    Handles transient network issues and API rate limits (e.g. 429 / 503).
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_error: Exception | None = None
                for attempt in range(max_retries):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as exc:
                        last_error = exc
                        if retry_exceptions and not isinstance(exc, retry_exceptions):
                            raise

                        if attempt == max_retries - 1:
                            logger.warning(
                                "Retry exhausted after %d attempts for %s: %s",
                                max_retries,
                                func.__name__,
                                exc,
                            )
                            raise

                        sleep_time = (initial_delay * (backoff_factor**attempt)) + random.uniform(
                            0, jitter
                        )
                        logger.info(
                            "Transient failure in %s (attempt %d/%d): %s. Retrying in %.2fs",
                            func.__name__,
                            attempt + 1,
                            max_retries,
                            exc,
                            sleep_time,
                        )
                        await asyncio.sleep(sleep_time)

                if last_error is not None:
                    raise last_error
                raise RuntimeError("Retry loop completed without returning or raising an error.")

            return async_wrapper

        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                import time

                last_error: Exception | None = None
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as exc:
                        last_error = exc
                        if retry_exceptions and not isinstance(exc, retry_exceptions):
                            raise

                        if attempt == max_retries - 1:
                            raise

                        sleep_time = (initial_delay * (backoff_factor**attempt)) + random.uniform(
                            0, jitter
                        )
                        time.sleep(sleep_time)

                if last_error is not None:
                    raise last_error
                raise RuntimeError("Retry loop completed without returning or raising an error.")

            return sync_wrapper

    return decorator
