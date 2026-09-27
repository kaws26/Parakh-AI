"""Ollama-backed LLM provider for local evaluation fallback."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import get_settings
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Provider that calls a local Ollama server via the HTTP API."""

    def __init__(self, base_url: str | None = None, model: str = "llama3.2") -> None:
        settings = get_settings()
        self.base_url = base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or getattr(settings, "OLLAMA_MODEL", "llama3.2:3b")

    async def generate(self, prompt: str, schema: dict | None = None) -> Any:
        """Call the local Ollama API and parse the JSON payload."""
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if schema is not None:
            payload["format"] = schema

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{self.base_url.rstrip('/')}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            raise RuntimeError(
                f"Local AI is unavailable. Start Ollama and download the configured model '{self.model}'."
            ) from exc

        raw_text = data.get("response")
        if isinstance(raw_text, dict):
            return raw_text
        if isinstance(raw_text, list):
            return {"items": raw_text}
        if raw_text is None:
            return data

        text = str(raw_text).strip()
        if not text:
            return data

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                return json.loads(text.replace("\n", ""))
            except json.JSONDecodeError:
                logger.warning("Ollama returned non-JSON payload: %s", text[:200])
                return {"text": text}
