"""Course management endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, require_role
from app.models.course import Course
from app.models.user import User, UserRole
from app.schemas.course import CourseCreate, CourseResponse, CourseUpdate

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    current_user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> CourseResponse:
    """Create a new course. Restricted to teachers and admins."""
    code_check = await db.execute(select(Course).where(Course.code == payload.code))
    if code_check.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course with code '{payload.code}' already exists",
        )

    course = Course(
        teacher_id=current_user.id,
        name=payload.name,
        code=payload.code,
        description=payload.description,
    )
    db.add(course)
    await db.commit()

    result = await db.execute(
        select(Course).options(selectinload(Course.topics)).where(Course.id == course.id)
    )
    course_loaded = result.scalar_one()
    return CourseResponse.model_validate(course_loaded)


@router.get("", response_model=list[CourseResponse])
async def list_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CourseResponse]:
    """List courses. Teachers see their own courses; students see all available courses."""
    query = select(Course).options(selectinload(Course.topics))
    if current_user.role == UserRole.TEACHER:
        query = query.where(Course.teacher_id == current_user.id)

    result = await db.execute(query.order_by(Course.created_at.desc()))
    courses = result.scalars().all()
    return [CourseResponse.model_validate(c) for c in courses]


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CourseResponse:
    """Get details of a single course including its topics."""
    result = await db.execute(
        select(Course).options(selectinload(Course.topics)).where(Course.id == course_id)
    )
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    return CourseResponse.model_validate(course)


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: uuid.UUID,
    payload: CourseUpdate,
    current_user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> CourseResponse:
    """Update a course. Only the creator teacher or admin can modify."""
    result = await db.execute(
        select(Course).options(selectinload(Course.topics)).where(Course.id == course_id)
    )
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    if current_user.role == UserRole.TEACHER and course.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to edit this course",
        )

    if payload.code is not None and payload.code != course.code:
        code_check = await db.execute(select(Course).where(Course.code == payload.code))
        if code_check.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Course with code '{payload.code}' already exists",
            )
        course.code = payload.code

    if payload.name is not None:
        course.name = payload.name
    if payload.description is not None:
        course.description = payload.description

    await db.commit()
    await db.refresh(course)
    return CourseResponse.model_validate(course)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a course. Only the creator teacher or admin can delete."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    if current_user.role == UserRole.TEACHER and course.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this course",
        )

    await db.delete(course)
    await db.commit()
