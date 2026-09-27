"""Schemas for viva orchestration state and responses."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VivaConfig(BaseModel):
    """Session-level configuration for a viva exam."""

    max_questions: int = Field(default=5, ge=1, le=10)
    max_duration_sec: int = Field(default=900, ge=60)
    follow_up_threshold: float = Field(default=0.4, ge=0.0, le=1.0)


class BehaviorFlagCreate(BaseModel):
    """A privacy-preserving cue detected locally by the student's browser."""

    cue_type: str = Field(pattern="^(additional_faces|off_screen_gaze)$")


class VivaQuestionResponse(BaseModel):
    """Question payload returned when advancing a viva session."""

    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    question_id: uuid.UUID
    question_text: str
    expected_key_points: list[str] = Field(default_factory=list)
    difficulty: str = "medium"
    current_question_index: int = 0


class VivaSessionSummary(BaseModel):
    """Final summary returned after a viva is completed."""

    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    status: str
    total_score: float | None = None
    answers_count: int = 0
    finished_at: datetime | None = None
