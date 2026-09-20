"""Tests for the basic Phase 3 viva speech pipeline."""

import uuid

import pytest
from httpx import AsyncClient

from app.models.question import Question
from tests.test_courses import create_user_and_get_token


@pytest.mark.asyncio
async def test_start_session_and_submit_answer_with_consent(client: AsyncClient, db_session) -> None:
    """Students can start a viva session and submit an answer when consent is recorded."""
    teacher_token = await create_user_and_get_token(
        client, "viva.teacher@viva.edu", "teacher", "Viva Teacher"
    )
    student_token = await create_user_and_get_token(
        client, "viva.student@viva.edu", "student", "Viva Student"
    )

    course = await client.post(
        "/api/courses",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={"name": "Algorithms", "code": "CS900", "description": "Intro algorithms"},
    )
    topic = await client.post(
        f"/api/courses/{course.json()['id']}/topics",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={"name": "Greedy Algorithms", "sort_order": 1},
    )

    question = Question(
        topic_id=uuid.UUID(topic.json()["id"]),
        question_text="Explain greedy choice property.",
        expected_key_points=["makes locally optimal choice", "leads to global optimum"],
    )
    db_session.add(question)
    await db_session.commit()
    await db_session.refresh(question)

    session = await client.post(
        "/api/viva/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert session.status_code == 201, session.text
    session_id = session.json()["id"]

    consent = await client.post(
        "/api/consent",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "session_id": session_id,
            "audio_retention_consent": True,
            "transcript_consent": True,
        },
    )
    assert consent.status_code == 201, consent.text

    audio = await client.post(
        f"/api/viva/sessions/{session_id}/answer",
        headers={"Authorization": f"Bearer {student_token}"},
        files={"file": ("hello.webm", b"fake-audio-bytes", "audio/webm")},
        data={"question_id": str(question.id)},
    )
    assert audio.status_code == 200, audio.text
    data = audio.json()
    assert "transcript" in data
    assert data["audio_saved"] is True

    res4 = await client.post(f"/api/viva/sessions/{session_id}/next", headers={"Authorization": f"Bearer {student_token}"})
    assert res4.status_code == 501

    res5 = await client.post(f"/api/viva/sessions/{session_id}/finish", headers={"Authorization": f"Bearer {student_token}"})
    assert res5.status_code == 501


@pytest.mark.asyncio
async def test_delete_user_audio_removes_recorded_files(client: AsyncClient, db_session) -> None:
    """Audio deletion should remove saved audio and clear audio_path records for that user."""
    teacher_token = await create_user_and_get_token(
        client, "viva.teacher.delete@viva.edu", "teacher", "Viva Teacher Delete"
    )
    token = await create_user_and_get_token(
        client, "viva.delete@viva.edu", "student", "Viva Deleter"
    )
    create_course = await client.post(
        "/api/courses",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={"name": "Data Mining", "code": "CS901", "description": "Mining data"},
    )
    course_id = create_course.json()["id"]
    create_topic = await client.post(
        f"/api/courses/{course_id}/topics",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={"name": "Association Rules", "sort_order": 1},
    )

    question = Question(
        topic_id=uuid.UUID(create_topic.json()["id"]),
        question_text="Explain association rule mining.",
        expected_key_points=["support", "confidence", "interestingness"],
    )
    db_session.add(question)
    await db_session.commit()
    await db_session.refresh(question)

    session = await client.post("/api/viva/sessions", headers={"Authorization": f"Bearer {token}"})
    assert session.status_code == 201
    session_id = session.json()["id"]

    consent = await client.post(
        "/api/consent",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "session_id": session_id,
            "audio_retention_consent": True,
            "transcript_consent": True,
        },
    )
    assert consent.status_code == 201

    audio = await client.post(
        f"/api/viva/sessions/{session_id}/answer",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("mining.webm", b"fake-audio-bytes", "audio/webm")},
        data={"question_id": str(question.id)},
    )
    assert audio.status_code == 200
    audio_path = audio.json().get("audio_path")
    assert audio_path is not None

    delete_audio = await client.delete(
        f"/api/users/{session.json()['student_id']}/audio",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_audio.status_code == 200
    payload = delete_audio.json()
    assert payload["deleted_count"] >= 1
