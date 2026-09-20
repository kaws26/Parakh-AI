"""Retry helpers for transient LLM and network call failures."""

from __future__ import annotations

import time
from collections.abc import Callable
from functools import wraps
from typing import Any


def retry_on_transient(max_retries: int = 3, delay_seconds: float = 0.2):
    """Retry a function when a transient exception occurs."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Exception | None = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:  # pragma: no cover - defensive retry wrapper
                    last_error = exc
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay_seconds * (attempt + 1))
            if last_error is not None:
                raise last_error
            raise RuntimeError("Retry loop exited without a result")

        return wrapper

    return decorator
