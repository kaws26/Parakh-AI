"""User database model."""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.consent import Consent
    from app.models.course import Course
    from app.models.score_override import ScoreOverride
    from app.models.viva_session import VivaSession


class UserRole(enum.StrEnum):
    """User roles."""

    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(Base):
    """User account entity representing students, teachers, and admins."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20),
        default=UserRole.STUDENT,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    courses: Mapped[list["Course"]] = relationship(
        "Course",
        back_populates="teacher",
        cascade="all, delete-orphan",
    )
    viva_sessions: Mapped[list["VivaSession"]] = relationship(
        "VivaSession",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    consents: Mapped[list["Consent"]] = relationship(
        "Consent",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    score_overrides: Mapped[list["ScoreOverride"]] = relationship(
        "ScoreOverride",
        back_populates="teacher",
    )
