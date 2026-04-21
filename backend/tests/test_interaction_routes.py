from fastapi.testclient import TestClient

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.main import app
from app.models.podcast import Podcast
from app.models.user import User


client = TestClient(app)


def _reset_test_data():
    """Reset test data by truncating tables."""
    db = SessionLocal()
    try:
        from app.models.interaction import Interaction

        db.query(Interaction).delete()
        db.query(Podcast).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def _create_test_user_and_podcast():
    """Helper to create a test user and podcast."""
    db = SessionLocal()
    try:
        user = User(username="testuser", email="test@test.com")
        podcast = Podcast(title="Test Podcast", summary="test", audio_url="", script_path="")
        db.add_all([user, podcast])
        db.flush()
        user_id = user.id
        podcast_id = podcast.id
        db.commit()
        return user_id, podcast_id
    finally:
        db.close()


def test_report_interaction_play():
    init_db()
    _reset_test_data()

    user_id, podcast_id = _create_test_user_and_podcast()

    response = client.post(
        "/api/v1/interactions",
        json={"user_id": user_id, "podcast_id": podcast_id, "action": "play"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["user_id"] == user_id
    assert payload["podcast_id"] == podcast_id
    assert payload["action"] == "play"
    assert "id" in payload
    assert "created_at" in payload


def test_report_interaction_like():
    init_db()
    _reset_test_data()

    user_id, podcast_id = _create_test_user_and_podcast()

    response = client.post(
        "/api/v1/interactions",
        json={"user_id": user_id, "podcast_id": podcast_id, "action": "like"},
    )
    assert response.status_code == 201
    assert response.json()["action"] == "like"


def test_report_interaction_favorite():
    init_db()
    _reset_test_data()

    user_id, podcast_id = _create_test_user_and_podcast()

    response = client.post(
        "/api/v1/interactions",
        json={"user_id": user_id, "podcast_id": podcast_id, "action": "favorite"},
    )
    assert response.status_code == 201
    assert response.json()["action"] == "favorite"


def test_report_interaction_skip():
    init_db()
    _reset_test_data()

    user_id, podcast_id = _create_test_user_and_podcast()

    response = client.post(
        "/api/v1/interactions",
        json={"user_id": user_id, "podcast_id": podcast_id, "action": "skip"},
    )
    assert response.status_code == 201
    assert response.json()["action"] == "skip"


def test_report_interaction_invalid_action():
    init_db()
    _reset_test_data()

    user_id, podcast_id = _create_test_user_and_podcast()

    response = client.post(
        "/api/v1/interactions",
        json={"user_id": user_id, "podcast_id": podcast_id, "action": "invalid"},
    )
    assert response.status_code == 422  # Validation error


def test_report_interaction_multiple_same_user_podcast():
    """Test that a user can record multiple interactions with the same podcast."""
    init_db()
    _reset_test_data()

    user_id, podcast_id = _create_test_user_and_podcast()

    # Record multiple interactions
    for action in ["play", "like", "favorite"]:
        response = client.post(
            "/api/v1/interactions",
            json={"user_id": user_id, "podcast_id": podcast_id, "action": action},
        )
        assert response.status_code == 201
