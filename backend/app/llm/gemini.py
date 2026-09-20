"""Gemini-backed LLM provider placeholder for future integration."""

from __future__ import annotations

from app.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    """Minimal provider implementation that can be extended for Gemini calls."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str, schema: dict | None = None):
        """Return a fallback payload unless the real Gemini SDK is configured."""
        return [
            {
                "question": "Describe the main idea from the supplied source material.",
                "key_points": ["Core concept", "Supporting evidence"],
                "difficulty": "medium",
            }
        ]
