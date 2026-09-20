"""Document database model for uploaded syllabi and lecture materials."""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.topic import Topic


class DocumentStatus(enum.StrEnum):
    """Processing and embedding status of a document."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    EMBEDDED = "embedded"
    ERROR = "error"


class Document(Base):
    """Document entity uploaded to support topic RAG retrieval."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False, length=20),
        default=DocumentStatus.UPLOADED,
        nullable=False,
    )
    chunk_count: Mapped[int] = mapped_column(
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
    topic: Mapped["Topic"] = relationship(
        "Topic",
        back_populates="documents",
    )
