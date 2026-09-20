"""Prompt version database model for reproducible LLM evals."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PromptVersion(Base):
    """Versioned prompt template record for question generation and LLM judge."""

    __tablename__ = "prompt_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
