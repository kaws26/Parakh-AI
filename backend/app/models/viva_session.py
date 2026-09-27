"""Viva session database model."""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.answer import Answer
    from app.models.consent import Consent
    from app.models.course import Course
    from app.models.user import User


class VivaStatus(enum.StrEnum):
    """Lifecycle status of a viva exam session."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABORTED = "aborted"


class VivaSession(Base):
    """An oral examination session conducted with a student."""

    __tablename__ = "viva_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[VivaStatus] = mapped_column(
        Enum(VivaStatus, native_enum=False, length=20),
        default=VivaStatus.PENDING,
        nullable=False,
    )
    max_questions: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
    )
    max_duration_sec: Mapped[int] = mapped_column(
        Integer,
        default=900,
        nullable=False,
    )
    current_question_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    student: Mapped["User"] = relationship(
        "User",
        back_populates="viva_sessions",
    )
    course: Mapped["Course"] = relationship(
        "Course",
        back_populates="viva_sessions",
    )
    answers: Mapped[list["Answer"]] = relationship(
        "Answer",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Answer.sequence_number",
    )
    consents: Mapped[list["Consent"]] = relationship(
        "Consent",
        back_populates="session",
    )
