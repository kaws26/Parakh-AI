"""FastAPI application initialization and core routes."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_router
from app.config import get_settings
from app.database import get_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown routines."""
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Automated oral examination system backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/api/health", tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Health check endpoint that verifies API liveness and database connectivity."""
    try:
        result = await db.execute(text("SELECT 1"))
        _ = result.scalar()
        db_status = "connected"
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {exc}",
        ) from exc

    return {
        "status": "ok",
        "db": db_status,
        "message": "Hello, Viva!",
    }


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint welcoming visitors to the Viva Voce API."""
    return {
        "app": settings.APP_NAME,
        "docs": "/docs",
        "health": "/api/health",
    }
