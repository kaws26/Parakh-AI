"""Document request and response schemas for content ingestion."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    """Public document metadata returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic_id: uuid.UUID
    filename: str
    file_path: str
    content_hash: str | None = None
    status: DocumentStatus
    chunk_count: int = 0
    created_at: datetime


class DocumentUploadResponse(DocumentResponse):
    """Schema for upload responses, including a small file summary."""

    pass
