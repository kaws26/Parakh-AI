"""Pydantic schemas export."""

from app.schemas.consent import ConsentCreate, ConsentResponse
from app.schemas.course import (
    CourseCreate,
    CourseResponse,
    CourseUpdate,
    TopicCreate,
    TopicResponse,
    TopicUpdate,
)
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse

__all__ = [
    "ConsentCreate",
    "ConsentResponse",
    "CourseCreate",
    "CourseResponse",
    "CourseUpdate",
    "TokenResponse",
    "TopicCreate",
    "TopicResponse",
    "TopicUpdate",
    "UserCreate",
    "UserLogin",
    "UserResponse",
]
