"""Course database model."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.topic import Topic
    from app.models.user import User
    from app.models.viva_session import VivaSession


class Course(Base):
    """Course entity created by a teacher."""

    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    teacher: Mapped["User"] = relationship(
        "User",
        back_populates="courses",
    )
    topics: Mapped[list["Topic"]] = relationship(
        "Topic",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Topic.sort_order",
    )
    viva_sessions: Mapped[list["VivaSession"]] = relationship(
        "VivaSession",
        back_populates="course",
        cascade="all, delete-orphan",
    )
