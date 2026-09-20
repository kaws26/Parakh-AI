"""Tests for authentication and user endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_student_success(client: AsyncClient) -> None:
    """Verify that a student can register and receive a valid JWT token."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "alice@student.viva.edu",
            "password": "securepassword123",
            "full_name": "Alice Smith",
            "role": "student",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@student.viva.edu"
    assert data["user"]["role"] == "student"
    assert data["user"]["full_name"] == "Alice Smith"


@pytest.mark.asyncio
async def test_register_teacher_success(client: AsyncClient) -> None:
    """Verify that a teacher can register."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "prof.john@viva.edu",
            "password": "teacherpassword123",
            "full_name": "Professor John",
            "role": "teacher",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["role"] == "teacher"


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client: AsyncClient) -> None:
    """Duplicate email registration must fail with 409 Conflict."""
    payload = {
        "email": "bob@student.viva.edu",
        "password": "mypassword123",
        "full_name": "Bob Jones",
        "role": "student",
    }
    r1 = await client.post("/api/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = await client.post("/api/auth/register", json=payload)
    assert r2.status_code == 409
    assert "already registered" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    """Verify login with correct credentials returns valid JWT."""
    # Register first
    await client.post(
        "/api/auth/register",
        json={
            "email": "charlie@viva.edu",
            "password": "correctpassword",
            "full_name": "Charlie Day",
            "role": "student",
        },
    )

    # Login
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "charlie@viva.edu",
            "password": "correctpassword",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "charlie@viva.edu"


@pytest.mark.asyncio
async def test_login_invalid_password_returns_401(client: AsyncClient) -> None:
    """Login with wrong password must return 401."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "dave@viva.edu",
            "password": "realpassword123",
            "full_name": "Dave Miller",
            "role": "student",
        },
    )

    response = await client.post(
        "/api/auth/login",
        json={
            "email": "dave@viva.edu",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user_returns_401(client: AsyncClient) -> None:
    """Login with unregistered email returns 401."""
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "nobody@viva.edu",
            "password": "whateverpassword",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient) -> None:
    """Authenticated user can fetch their own profile."""
    reg = await client.post(
        "/api/auth/register",
        json={
            "email": "eve@viva.edu",
            "password": "evepassword123",
            "full_name": "Eve Adams",
            "role": "student",
        },
    )
    token = reg.json()["access_token"]

    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "eve@viva.edu"
    assert data["full_name"] == "Eve Adams"


@pytest.mark.asyncio
async def test_get_me_unauthenticated_returns_401(client: AsyncClient) -> None:
    """Accessing /api/auth/me without token returns 401."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token_returns_401(client: AsyncClient) -> None:
    """Accessing /api/auth/me with bogus token returns 401."""
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert response.status_code == 401
