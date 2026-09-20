"""Viva examination endpoints for the Phase 3 speech pipeline."""

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.answer import Answer
from app.models.consent import Consent
from app.models.course import Course
from app.models.question import Question
from app.models.topic import Topic
from app.models.user import User
from app.models.viva_session import VivaSession, VivaStatus
from app.services.speech_service import SpeechService
from app.utils.text import anonymise, clean_transcript

router = APIRouter(prefix="/viva", tags=["Viva Examination"])


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def start_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new viva session using the most recent course as the default target."""
    result = await db.execute(select(Course).order_by(Course.created_at.desc()).limit(1))
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No courses available for viva sessions")

    session = VivaSession(
        student_id=current_user.id,
        course_id=course.id,
        status=VivaStatus.IN_PROGRESS,
        max_questions=5,
        max_duration_sec=900,
        current_question_index=0,
        started_at=datetime.now(UTC),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {
        "id": session.id,
        "student_id": current_user.id,
        "course_id": course.id,
        "status": session.status.value,
        "max_questions": session.max_questions,
        "current_question_index": session.current_question_index,
        "started_at": session.started_at,
    }


@router.get("/sessions", status_code=status.HTTP_200_OK)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List viva sessions for the current user."""
    result = await db.execute(
        select(VivaSession).where(VivaSession.student_id == current_user.id).order_by(VivaSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": session.id,
            "student_id": session.student_id,
            "course_id": session.course_id,
            "status": session.status.value,
            "max_questions": session.max_questions,
            "current_question_index": session.current_question_index,
            "started_at": session.started_at,
        }
        for session in sessions
    ]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return a viva session summary for the current user."""
    result = await db.execute(select(VivaSession).where(VivaSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this session")

    return {
        "id": session.id,
        "student_id": session.student_id,
        "course_id": session.course_id,
        "status": session.status.value,
        "max_questions": session.max_questions,
        "current_question_index": session.current_question_index,
        "started_at": session.started_at,
        "finished_at": session.finished_at,
    }


@router.post("/sessions/{session_id}/next", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def next_question(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Stub: Request next viva question (Implemented in Phase 5)."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Viva question dispatch will be available in Phase 5",
    )


@router.post("/sessions/{session_id}/answer")
async def submit_answer(
    session_id: uuid.UUID,
    file: UploadFile = File(...),
    question_id: uuid.UUID | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Accept an uploaded audio answer, transcript it, and store the cleaned result."""
    session_result = await db.execute(select(VivaSession).where(VivaSession.id == session_id))
    session = session_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only answer your own viva session")

    if question_id is None:
        question_result = await db.execute(
            select(Question)
            .join(Topic, Question.topic_id == Topic.id)
            .where(Topic.course_id == session.course_id)
            .order_by(Question.created_at.desc())
            .limit(1)
        )
        question = question_result.scalar_one_or_none()
        if question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No question available for this session")
    else:
        question_result = await db.execute(select(Question).where(Question.id == question_id))
        question = question_result.scalar_one_or_none()
        if question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    consent_result = await db.execute(
        select(Consent)
        .where(Consent.user_id == current_user.id, Consent.audio_retention_consent.is_(True))
        .order_by(Consent.consented_at.desc())
        .limit(1)
    )
    consent = consent_result.scalar_one_or_none()
    has_consent = consent is not None and consent.audio_retention_consent is True and consent.revoked_at is None

    try:
        raw_bytes = await file.read()
    except Exception as exc:  # pragma: no cover - file read failure path
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to read uploaded audio file") from exc

    if not raw_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded audio is empty")

    started = time.perf_counter()
    stored_path = SpeechService.save_audio_upload(raw_bytes, session_id, current_user.id)
    transcription = SpeechService().transcribe(stored_path)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    transcript = clean_transcript(transcription.get("text", ""))
    transcript = anonymise(transcript)

    audio_path = stored_path if has_consent else None
    if not has_consent and Path(stored_path).exists():
        Path(stored_path).unlink(missing_ok=True)

    existing_answers_result = await db.execute(select(Answer).where(Answer.session_id == session_id))
    next_sequence = len(existing_answers_result.scalars().all()) + 1

    answer = Answer(
        session_id=session_id,
        question_id=question.id,
        sequence_number=next_sequence,
        transcript=transcript,
        audio_path=audio_path,
        transcription_confidence=transcription.get("confidence"),
        latency_ms=elapsed_ms,
    )
    db.add(answer)
    await db.commit()
    await db.refresh(answer)

    return {
        "answer_id": answer.id,
        "transcript": transcript,
        "audio_saved": bool(audio_path),
        "audio_path": audio_path,
        "confidence": transcription.get("confidence"),
        "latency_ms": elapsed_ms,
    }


@router.post("/sessions/{session_id}/finish", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def finish_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Stub: Finish viva session and finalize scoring (Implemented in Phase 5)."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Session finalization will be available in Phase 5",
    )
