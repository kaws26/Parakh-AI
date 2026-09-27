import pytest

from app.services.eval_service import (
    EmbeddingSimilarityScorer,
    LLMJudgeScorer,
    RubricScore,
    ScoreFusion,
)


class MockJudgingProvider:
    async def generate(self, prompt: str, schema: dict | None = None):
        return {
            "correctness": 8,
            "completeness": 7,
            "clarity": 9,
            "justification": "The answer addresses the main idea and explains it clearly.",
        }


class InvalidThenValidMockJudgingProvider:
    def __init__(self):
        self.calls = 0

    async def generate(self, prompt: str, schema: dict | None = None):
        self.calls += 1
        if self.calls == 1:
            raise ValueError("malformed JSON")
        return {
            "correctness": 6,
            "completeness": 8,
            "clarity": 7,
            "justification": "Good answer with some gaps.",
        }


def test_embedding_similarity_scorer_relevant_text_scores_high():
    scorer = EmbeddingSimilarityScorer()
    score = scorer.score(
        "Polymorphism allows different objects to respond to the same method through dynamic dispatch.",
        ["Polymorphism", "dynamic dispatch", "inheritance"],
    )
    assert score > 0.6


def test_embedding_similarity_scorer_unrelated_text_scores_low():
    scorer = EmbeddingSimilarityScorer()
    score = scorer.score("I had pizza for lunch yesterday.", ["polymorphism", "inheritance"])
    assert score < 0.2


def test_score_fusion_handles_extreme_weights():
    assert ScoreFusion.fuse(0.8, 0.6, weights=(1.0, 0.0)) == pytest.approx(0.8)
    assert ScoreFusion.fuse(0.8, 0.6, weights=(0.0, 1.0)) == pytest.approx(0.6)
    assert ScoreFusion.fuse(0.8, 0.6, weights=(0.4, 0.6)) == pytest.approx(0.68)


@pytest.mark.asyncio
async def test_llm_judge_parses_valid_score():
    scorer = LLMJudgeScorer(provider=MockJudgingProvider())
    result = await scorer.score(
        question="What is polymorphism?",
        transcript="Polymorphism allows objects of different types to respond to the same method.",
        key_points=["Dynamic dispatch", "Method overriding"],
    )
    assert isinstance(result, RubricScore)
    assert result.correctness == 8
    assert result.completeness == 7
    assert result.clarity == 9
    assert result.llm_score > 0


@pytest.mark.asyncio
async def test_llm_judge_retries_on_invalid_response():
    provider = InvalidThenValidMockJudgingProvider()
    scorer = LLMJudgeScorer(provider=provider)
    result = await scorer.score(
        question="What is polymorphism?",
        transcript="Polymorphism is the ability of objects to respond differently to the same method call.",
        key_points=["Dynamic dispatch", "Method overriding"],
    )
    assert isinstance(result, RubricScore)
    assert result.correctness == 6
    assert provider.calls >= 2
