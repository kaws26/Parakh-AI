.PHONY: help install dev dev-backend dev-frontend test lint format migrate build clean

help:
	@echo "Available commands:"
	@echo "  make install       Install backend and frontend dependencies"
	@echo "  make dev-backend   Start FastAPI backend development server"
	@echo "  make dev-frontend  Start Vite React frontend development server"
	@echo "  make test          Run backend pytest suite"
	@echo "  make lint          Check code formatting and linting with Ruff"
	@echo "  make format        Auto-format code with Ruff"
	@echo "  make migrate       Run database migrations with Alembic"
	@echo "  make build         Build frontend production bundle"

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest

lint:
	cd backend && ruff check app tests && ruff format --check app tests

format:
	cd backend && ruff check --fix app tests && ruff format app tests

migrate:
	cd backend && alembic upgrade head

build:
	cd frontend && npm run build

clean:
	rm -rf backend/.pytest_cache backend/.ruff_cache backend/.mypy_cache
	rm -rf frontend/dist
