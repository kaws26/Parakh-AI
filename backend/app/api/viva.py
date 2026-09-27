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
from app.models.viva_session import VivaSession
from app.schemas.viva import BehaviorFlagCreate, VivaConfig
from app.services.eval_service import evaluate_answer
from app.services.speech_service import SpeechService
from app.services.viva_orchestrator import VivaOrchestrator
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No courses available for viva sessions"
        )

    orchestrator = VivaOrchestrator(db)
    session = await orchestrator.start_session(
        student_id=current_user.id,
        course_id=course.id,
        config=VivaConfig(max_questions=5, max_duration_sec=900),
    )
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
        select(VivaSession)
        .where(VivaSession.student_id == current_user.id)
        .order_by(VivaSession.created_at.desc())
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this session"
        )

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


@router.post("/sessions/{session_id}/behavior-flags", status_code=status.HTTP_201_CREATED)
async def create_behavior_flag(
    session_id: uuid.UUID,
    payload: BehaviorFlagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Persist only a cue type and timestamp, never camera frames."""
    result = await db.execute(select(VivaSession).where(VivaSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this session")
    consent_result = await db.execute(
        select(Consent).where(
            Consent.user_id == current_user.id,
            Consent.session_id == session_id,
            Consent.camera_analysis_consent.is_(True),
            Consent.revoked_at.is_(None),
        )
    )
    if consent_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Camera cue analysis consent is required")

    flags = list((session.config or {}).get("behavior_flags", []))
    if len(flags) >= 100:
        raise HTTPException(status_code=429, detail="Session review cue limit reached")
    flag = {"cue_type": payload.cue_type, "occurred_at": datetime.now(UTC).isoformat()}
    updated_config = dict(session.config or {})
    updated_config["behavior_flags"] = [*flags, flag]
    session.config = updated_config
    await db.commit()
    return flag


@router.post("/sessions/{session_id}/next")
async def next_question(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the next question in the viva session or finalize it when all questions are consumed."""
    orchestrator = VivaOrchestrator(db)
    session = await orchestrator._get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session",
        )

    question = await orchestrator.get_next_question(session_id)
    if question is None:
        summary = await orchestrator.finish_session(session_id)
        return {
            "session_id": str(session_id),
            "status": summary["status"],
            "message": "Session completed; no further questions available.",
            "total_score": summary["total_score"],
        }

    refreshed_session = await orchestrator._get_session(session_id)
    return {
        "session_id": str(session_id),
        "question_id": str(question.id),
        "question_text": question.question_text,
        "expected_key_points": question.expected_key_points,
        "difficulty": question.difficulty.value,
        "current_question_index": refreshed_session.current_question_index if refreshed_session else 0,
    }


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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only answer your own viva session",
        )

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No question available for this session",
            )
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
    has_consent = (
        consent is not None
        and consent.audio_retention_consent is True
        and consent.revoked_at is None
    )

    try:
        raw_bytes = await file.read()
    except Exception as exc:  # pragma: no cover - file read failure path
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to read uploaded audio file"
        ) from exc

    if not raw_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded audio is empty"
        )

    started = time.perf_counter()
    stored_path = SpeechService.save_audio_upload(raw_bytes, session_id, current_user.id)
    try:
        transcription = SpeechService().transcribe(stored_path)
    except RuntimeError as exc:
        if Path(stored_path).exists():
            Path(stored_path).unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    transcript = clean_transcript(transcription.get("text", ""))
    transcript = anonymise(transcript)
    try:
        evaluation = await evaluate_answer(
            question=question.question_text,
            transcript=transcript,
            key_points=question.expected_key_points,
        )
    except RuntimeError as exc:
        if not has_consent and Path(stored_path).exists():
            Path(stored_path).unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    audio_path = stored_path if has_consent else None
    if not has_consent and Path(stored_path).exists():
        Path(stored_path).unlink(missing_ok=True)

    existing_answers_result = await db.execute(
        select(Answer).where(Answer.session_id == session_id)
    )
    next_sequence = len(existing_answers_result.scalars().all()) + 1

    answer = Answer(
        session_id=session_id,
        question_id=question.id,
        sequence_number=next_sequence,
        transcript=transcript,
        embedding_score=evaluation["embedding_score"],
        llm_score=evaluation["llm_score"],
        fused_score=evaluation["fused_score"],
        rubric_breakdown=evaluation["rubric"],
        llm_raw_response=evaluation["rubric"],
        audio_path=audio_path,
        transcription_confidence=transcription.get("confidence"),
        latency_ms=elapsed_ms,
    )
    db.add(answer)
    await db.commit()
    await db.refresh(answer)

    followup = None
    followup_error = None
    threshold = float((session.config or {}).get("follow_up_threshold", 0.4))
    if evaluation["fused_score"] < threshold and session.current_question_index < session.max_questions:
        try:
            followup = await VivaOrchestrator(db).generate_followup(
                session_id,
                missed_key_points=question.expected_key_points,
                previous_question=question.question_text,
                transcript=transcript,
            )
        except Exception:
            followup_error = "Adaptive follow-up unavailable. Check that Ollama is running with the configured model."

    return {
        "answer_id": answer.id,
        "transcript": transcript,
        "embedding_score": evaluation["embedding_score"],
        "llm_score": evaluation["llm_score"],
        "fused_score": evaluation["fused_score"],
        "rubric_breakdown": evaluation["rubric"],
        "audio_saved": bool(audio_path),
        "audio_path": audio_path,
        "confidence": transcription.get("confidence"),
        "latency_ms": elapsed_ms,
        "followup": ({
            "question_id": str(followup.id),
            "question_text": followup.question_text,
            "expected_key_points": followup.expected_key_points,
            "difficulty": followup.difficulty.value,
        } if followup else None),
        "followup_error": followup_error,
    }


@router.post("/sessions/{session_id}/finish")
async def finish_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Finalize a viva session and compute the aggregate score for all recorded answers."""
    orchestrator = VivaOrchestrator(db)
    session = await orchestrator._get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session",
        )

    summary = await orchestrator.finish_session(session_id)
    return {
        "session_id": str(session_id),
        "status": summary["status"],
        "total_score": summary["total_score"],
        "answers_count": summary["answers_count"],
        "finished_at": summary["finished_at"],
    }
