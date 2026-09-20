"""Consent request and response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConsentCreate(BaseModel):
    """Payload to grant or record privacy consent."""

    audio_retention_consent: bool = False
    transcript_consent: bool = True
    session_id: uuid.UUID | None = None


class ConsentResponse(BaseModel):
    """Response payload for recorded consent."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    session_id: uuid.UUID | None
    audio_retention_consent: bool
    transcript_consent: bool
    consented_at: datetime
    revoked_at: datetime | None
