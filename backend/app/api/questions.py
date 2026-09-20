"""Question bank endpoints for generated and approved oral-exam questions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.models.document import Document
from app.models.question import Question, QuestionDifficulty
from app.models.topic import Topic
from app.models.user import User, UserRole
from app.schemas.question import QuestionGenerateRequest, QuestionResponse, QuestionUpdate
from app.services.document_service import DocumentService
from app.services.question_service import LocalLLMProvider, QuestionService
from app.services.rag_service import chunk_text

router = APIRouter(tags=["Questions"])


@router.post("/topics/{topic_id}/questions/generate", response_model=list[QuestionResponse])
async def generate_questions_for_topic(
    topic_id: uuid.UUID,
    payload: QuestionGenerateRequest,
    current_user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[QuestionResponse]:
    """Generate a set of oral-exam questions from uploaded topic material."""
    topic_result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = topic_result.scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")

    context_chunks: list[str] = []
    document_result = await db.execute(select(Document).where(Document.topic_id == topic_id))
    documents = document_result.scalars().all()
    for document in documents:
        file_path = document.file_path
        try:
            text = DocumentService.extract_text(document.filename, open(file_path, "rb").read())
            context_chunks.extend(chunk_text(text, chunk_size=512, overlap=64))
        except Exception:
            continue

    if not context_chunks:
        context_chunks = [topic.name]

    questions = await QuestionService().generate_questions(
        topic_id=topic_id,
        context_chunks=context_chunks,
        count=payload.count,
        llm_provider=LocalLLMProvider(),
        db=db,
    )

    saved_result = await db.execute(
        select(Question)
        .where(Question.topic_id == topic_id)
        .order_by(Question.created_at.desc())
        .limit(payload.count)
    )
    saved_questions = saved_result.scalars().all()
    return [QuestionResponse.model_validate(item) for item in saved_questions]


@router.get("/topics/{topic_id}/questions", response_model=list[QuestionResponse])
async def list_questions(
    topic_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[QuestionResponse]:
    """Retrieve the generated questions for a topic."""
    topic_result = await db.execute(select(Topic).where(Topic.id == topic_id))
    if topic_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")

    result = await db.execute(
        select(Question)
        .where(Question.topic_id == topic_id)
        .order_by(Question.created_at.desc())
    )
    return [QuestionResponse.model_validate(item) for item in result.scalars().all()]


@router.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    """Fetch a specific question by identifier."""
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return QuestionResponse.model_validate(question)


@router.put("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: uuid.UUID,
    payload: QuestionUpdate,
    current_user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    """Allow a teacher to revise or approve a generated question."""
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    if payload.question_text is not None:
        question.question_text = payload.question_text
    if payload.expected_key_points is not None:
        question.expected_key_points = payload.expected_key_points
    if payload.difficulty is not None:
        question.difficulty = QuestionDifficulty(payload.difficulty)
    if payload.is_approved is not None:
        question.is_approved = payload.is_approved

    await db.commit()
    await db.refresh(question)
    return QuestionResponse.model_validate(question)


@router.post("/questions/{question_id}/approve", response_model=QuestionResponse)
async def approve_question(
    question_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    """Mark a generated question as approved and ready for viva use."""
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    question.is_approved = True
    await db.commit()
    await db.refresh(question)
    return QuestionResponse.model_validate(question)
