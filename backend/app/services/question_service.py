"""Service for turning context chunks into structured oral-exam questions."""

from __future__ import annotations

import uuid

from app.models.question import Question, QuestionDifficulty
from app.services.rag_service import chunk_text


class BaseLLMProvider:
    """Small protocol for question generation providers."""

    async def generate(self, prompt: str, schema: dict | None = None):
        """Generate a structured payload from a formatted prompt."""
        raise NotImplementedError


class LocalLLMProvider(BaseLLMProvider):
    """Fallback provider used when no external LLM backend is configured."""

    async def generate(self, prompt: str, schema: dict | None = None):
        """Produce simple exam questions from context text in a predictable shape."""
        context = prompt.split("Context:\n", 1)[-1]
        lines = [line.strip() for line in context.splitlines() if line.strip()]
        items: list[dict[str, object]] = []

        for index, line in enumerate(lines[:5], start=1):
            key_points = [piece.strip() for piece in line.split(".") if piece.strip()][:3]
            if not key_points:
                key_points = ["Key concept from the provided material"]
            items.append(
                {
                    "question": f"Explain the concept highlighted in point {index} from the supplied material.",
                    "key_points": key_points,
                    "difficulty": "medium" if index % 2 else "easy",
                }
            )

        if not items:
            items.append(
                {
                    "question": "Summarize the main idea described in the provided material.",
                    "key_points": ["Core concept", "Supporting evidence"],
                    "difficulty": "easy",
                }
            )

        return items


class QuestionService:
    """Generate and persist question-bank entries from topic context."""

    def __init__(self) -> None:
        self.prompt_name = "question_gen_v1"

    @staticmethod
    def _normalize_question(item: dict) -> dict:
        """Ensure generated output matches the expected schema."""
        difficulty = str(item.get("difficulty", "medium")).lower()
        if difficulty not in {"easy", "medium", "hard"}:
            difficulty = "medium"

        key_points = item.get("key_points") or item.get("expected_key_points") or ["Key point"]
        if not isinstance(key_points, list):
            key_points = [str(key_points)]

        return {
            "question": item.get("question") or item.get("question_text") or "Describe the key concept in this material.",
            "key_points": [str(point).strip() for point in key_points if str(point).strip()],
            "difficulty": difficulty,
        }

    async def generate_questions(
        self,
        topic_id: uuid.UUID,
        context_chunks: list[str],
        count: int = 5,
        llm_provider: BaseLLMProvider | None = None,
        db=None,
    ) -> list[dict]:
        """Generate structured questions from retrieved content and optionally store them."""
        if not context_chunks:
            context_chunks = ["No uploaded content available for this topic yet."]

        provider = llm_provider or LocalLLMProvider()
        flattened_chunks: list[str] = []
        for chunk in context_chunks:
            flattened_chunks.extend(chunk_text(chunk, chunk_size=120, overlap=20))
        context_text = "\n".join(flattened_chunks)
        prompt = (
            "You are generating oral-exam questions for a course topic.\n"
            "Return a JSON array of objects with fields: question, key_points, difficulty.\n"
            f"Topic ID: {topic_id}\n"
            f"Context:\n{context_text}\n"
            "Requirements: generate concise, exam-ready questions with 2-4 expected key points; difficulty must be easy, medium, or hard."
        )

        generated: list[dict] = []
        try:
            raw_response = await provider.generate(prompt, schema={"type": "array"})
            if isinstance(raw_response, list):
                generated = [self._normalize_question(item) for item in raw_response]
        except Exception:
            generated = []

        if not generated:
            fallback = [
                {
                    "question": "Explain the main concept covered by this material.",
                    "key_points": ["Identify the core topic", "Explain supporting details"],
                    "difficulty": "easy",
                },
                {
                    "question": "Describe how the main idea relates to the broader subject area.",
                    "key_points": ["Connect to the curriculum", "Give an example or application"],
                    "difficulty": "medium",
                },
            ]
            generated = fallback[:count]

        generated = generated[:count]
        for item in generated:
            item["difficulty"] = str(item["difficulty"]).lower()
            item["key_points"] = [str(point).strip() for point in item.get("key_points", []) if str(point).strip()]
            if not item["key_points"]:
                item["key_points"] = ["Core concept"]

        if db is not None:
            for item in generated:
                new_question = Question(
                    topic_id=topic_id,
                    question_text=item["question"],
                    expected_key_points=item["key_points"],
                    difficulty=QuestionDifficulty(item["difficulty"]),
                    prompt_version=self.prompt_name,
                    is_approved=False,
                )
                db.add(new_question)
            await db.commit()

        return generated
