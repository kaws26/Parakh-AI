"""Score override database model for teacher audits."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.answer import Answer
    from app.models.user import User


class ScoreOverride(Base):
    """Teacher override record for an automated viva answer score."""

    __tablename__ = "score_overrides"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    answer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("answers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    override_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    justification: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    answer: Mapped["Answer"] = relationship(
        "Answer",
        back_populates="score_override",
    )
    teacher: Mapped["User"] = relationship(
        "User",
        back_populates="score_overrides",
    )
