"""Privacy and consent endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.consent import Consent
from app.models.user import User
from app.schemas.consent import ConsentCreate, ConsentResponse

router = APIRouter(prefix="/consent", tags=["Consent & Privacy"])


@router.post("", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def record_consent(
    payload: ConsentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsentResponse:
    """Record user consent for audio retention and transcription processing."""
    consent = Consent(
        user_id=current_user.id,
        session_id=payload.session_id,
        audio_retention_consent=payload.audio_retention_consent,
        transcript_consent=payload.transcript_consent,
        consented_at=datetime.now(UTC),
    )
    db.add(consent)
    await db.commit()
    await db.refresh(consent)
    return ConsentResponse.model_validate(consent)


@router.get("", response_model=list[ConsentResponse])
async def get_consent_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConsentResponse]:
    """Retrieve all consent records granted by the current user."""
    result = await db.execute(
        select(Consent)
        .where(Consent.user_id == current_user.id)
        .order_by(Consent.consented_at.desc())
    )
    records = result.scalars().all()
    return [ConsentResponse.model_validate(r) for r in records]


@router.post("/revoke", response_model=ConsentResponse)
async def revoke_consent(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsentResponse:
    """Revoke active consent for audio retention."""
    result = await db.execute(
        select(Consent)
        .where(Consent.user_id == current_user.id, Consent.revoked_at.is_(None))
        .order_by(Consent.consented_at.desc())
    )
    active_consent = result.scalars().first()
    if active_consent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active consent found to revoke",
        )

    active_consent.revoked_at = datetime.now(UTC)
    active_consent.audio_retention_consent = False
    await db.commit()
    await db.refresh(active_consent)
    return ConsentResponse.model_validate(active_consent)
