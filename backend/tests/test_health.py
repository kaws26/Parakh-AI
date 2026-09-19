"""Tests for health check and root endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """Verify that /api/health returns 200 with status ok and db connected."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"
    assert "Hello, Viva!" in data.get("message", "")


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient) -> None:
    """Verify that root endpoint / returns 200 with app metadata."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "app" in data
    assert data["health"] == "/api/health"
