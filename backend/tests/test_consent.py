"""Tests for privacy and consent endpoints."""

import pytest
from httpx import AsyncClient

from tests.test_courses import create_user_and_get_token


@pytest.mark.asyncio
async def test_record_and_get_consent(client: AsyncClient) -> None:
    """Student can record consent and retrieve their consent history."""
    token = await create_user_and_get_token(
        client, "privacy.user@viva.edu", "student", "Privacy User"
    )

    # 1. Record consent
    response = await client.post(
        "/api/consent",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "audio_retention_consent": True,
            "transcript_consent": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["audio_retention_consent"] is True
    assert data["transcript_consent"] is True
    assert "id" in data

    # 2. Retrieve consent records
    get_res = await client.get(
        "/api/consent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 200
    records = get_res.json()
    assert len(records) >= 1
    assert records[0]["audio_retention_consent"] is True


@pytest.mark.asyncio
async def test_revoke_consent(client: AsyncClient) -> None:
    """User can revoke their active audio retention consent."""
    token = await create_user_and_get_token(
        client, "revoke.user@viva.edu", "student", "Revoke User"
    )

    # Grant consent first
    await client.post(
        "/api/consent",
        headers={"Authorization": f"Bearer {token}"},
        json={"audio_retention_consent": True, "transcript_consent": True},
    )

    # Revoke consent
    revoke_res = await client.post(
        "/api/consent/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert revoke_res.status_code == 200
    data = revoke_res.json()
    assert data["revoked_at"] is not None
    assert data["audio_retention_consent"] is False


@pytest.mark.asyncio
async def test_revoke_consent_no_active_returns_404(client: AsyncClient) -> None:
    """Attempting to revoke consent when none is active returns 404."""
    token = await create_user_and_get_token(
        client, "no.consent@viva.edu", "student", "No Consent User"
    )
    response = await client.post(
        "/api/consent/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
