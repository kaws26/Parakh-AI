"""Topic database model."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.document import Document
    from app.models.question import Question


class Topic(Base):
    """Topic entity within a course."""

    __tablename__ = "topics"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    course: Mapped["Course"] = relationship(
        "Course",
        back_populates="topics",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="topic",
        cascade="all, delete-orphan",
    )
    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="topic",
        cascade="all, delete-orphan",
    )
