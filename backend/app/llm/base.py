"""Base interfaces for LLM-backed reasoning providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract interface implemented by LLM backends."""

    @abstractmethod
    async def generate(self, prompt: str, schema: dict | None = None):
        """Return structured output for a given prompt."""
        raise NotImplementedError
