"""Chunking, embedding, and retrieval helpers for RAG-backed questions."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path


def _tokenize(text: str) -> list[str]:
    """Return normalized lower-case tokens for lightweight, dependency-free RAG."""
    return re.findall(r"\b[\w'-]+\b", text.lower())


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Split a document into overlapping chunks using a simple token window."""
    if not text or not text.strip():
        return []

    tokens = _tokenize(text)
    if not tokens:
        return []
    if len(tokens) <= chunk_size:
        return [" ".join(tokens)]

    step = max(1, chunk_size - overlap)
    chunks: list[str] = []
    for start in range(0, len(tokens), step):
        end = min(len(tokens), start + chunk_size)
        chunk = " ".join(tokens[start:end])
        if chunk:
            chunks.append(chunk)
        if end == len(tokens):
            break
    return chunks


def _vector_from_text(text: str, dimension: int = 8) -> list[float]:
    """Create a deterministic embedding-like vector from text content."""
    tokens = _tokenize(text)
    if not tokens:
        return [0.0] * dimension

    vector = [0.0] * dimension
    for token in tokens:
        bucket = sum(ord(ch) for ch in token) % dimension
        vector[bucket] += 1.0

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return [0.0] * dimension
    return [value / norm for value in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b, strict=False))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def retrieve_relevant_chunks(
    query: str,
    chunks: list[str],
    top_k: int = 3,
) -> list[dict[str, float | str]]:
    """Rank chunks by similarity to the submitted query and return the best matches."""
    if not chunks:
        return []

    query_vector = _vector_from_text(query)
    scored: list[dict[str, float | str]] = []
    for chunk in chunks:
        chunk_vector = _vector_from_text(chunk)
        scored.append(
            {
                "text": chunk,
                "score": cosine_similarity(query_vector, chunk_vector),
            }
        )

    scored.sort(key=lambda item: float(item["score"]), reverse=True)
    return scored[:top_k]


def build_index(topic_id: str | object, chunks: list[str], index_dir: str | Path | None = None) -> dict:
    """Persist chunk embeddings to disk for later retrieval and question generation."""
    if index_dir is None:
        index_dir = Path("vector_store")
    else:
        index_dir = Path(index_dir)

    index_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "topic_id": str(topic_id),
        "chunks": chunks,
        "embeddings": [_vector_from_text(chunk) for chunk in chunks],
    }

    target = index_dir / f"topic_{topic_id}.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def load_index(topic_id: str | object, index_dir: str | Path | None = None) -> dict | None:
    """Load a saved topic index from disk when present."""
    if index_dir is None:
        index_dir = Path("vector_store")
    else:
        index_dir = Path(index_dir)

    target = index_dir / f"topic_{topic_id}.json"
    if not target.exists():
        return None

    return json.loads(target.read_text(encoding="utf-8"))
