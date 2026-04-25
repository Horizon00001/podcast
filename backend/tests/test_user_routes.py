from fastapi.testclient import TestClient

from app.db.init_db import init_db
from app.main import app


client = TestClient(app)


def _reset_test_data():
    """Reset test data by truncating tables."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        from app.models.interaction import Interaction
        from app.models.podcast import Podcast
        from app.models.user import User

        db.query(Interaction).delete()
        db.query(Podcast).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def test_create_user():
    init_db()
    _reset_test_data()

    response = client.post(
        "/api/v1/users",
        json={"username": "testuser", "email": "test@example.com"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["username"] == "testuser"
    assert payload["email"] == "test@example.com"
    assert "id" in payload
    assert "created_at" in payload


def test_create_user_duplicate_username():
    """Test that duplicate username raises an IntegrityError."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    init_db()
    _reset_test_data()

    # Create first user
    client.post(
        "/api/v1/users",
        json={"username": "duplicate", "email": "first@example.com"},
    )

    # Try to create second user with same username - should raise IntegrityError
    with pytest.raises(IntegrityError):
        client.post(
            "/api/v1/users",
            json={"username": "duplicate", "email": "second@example.com"},
        )


def test_create_user_invalid_email():
    init_db()
    _reset_test_data()

    response = client.post(
        "/api/v1/users",
        json={"username": "testuser", "email": "invalid-email"},
    )
    assert response.status_code == 422  # Validation error


def test_get_user_by_id():
    init_db()
    _reset_test_data()

    # Create user first
    create_response = client.post(
        "/api/v1/users",
        json={"username": "getbyid", "email": "getbyid@example.com"},
    )
    user_id = create_response.json()["id"]

    # Get user by id
    response = client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == user_id
    assert payload["username"] == "getbyid"


def test_get_user_by_id_not_found():
    init_db()
    _reset_test_data()

    response = client.get("/api/v1/users/99999")
    assert response.status_code == 404


def test_get_user_by_username():
    init_db()
    _reset_test_data()

    # Create user first
    client.post(
        "/api/v1/users",
        json={"username": "getbyname", "email": "getbyname@example.com"},
    )

    # Get user by username
    response = client.get("/api/v1/users/by-username/getbyname")
    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "getbyname"
    assert payload["email"] == "getbyname@example.com"


def test_get_user_by_username_not_found():
    init_db()
    _reset_test_data()

    response = client.get("/api/v1/users/by-username/nonexistent")
    assert response.status_code == 404


def test_user_preferences_round_trip():
    init_db()
    _reset_test_data()

    create_response = client.post(
        "/api/v1/users",
        json={"username": "prefs", "email": "prefs@example.com"},
    )
    user_id = create_response.json()["id"]

    default_response = client.get(f"/api/v1/users/{user_id}/preferences")
    assert default_response.status_code == 200
    assert default_response.json()["generation"]["topic"] == "daily-news"

    payload = {
        "subscription": {
            "categories": ["tech"],
            "rss_sources": ["hacker-news"],
            "custom_rss": [
                {
                    "id": "custom-example",
                    "name": "Example",
                    "url": "https://example.com/feed.xml",
                    "category": "tech",
                    "enabled": True,
                }
            ],
            "frequency": "daily",
        },
        "generation": {
            "topic": "daily-ai-brief",
            "max_items": 4,
            "use_subscriptions": True,
        },
        "settings": {
            "voice": "female",
            "language": "zh",
            "auto_cover": False,
            "console_mode": "verbose",
        },
    }

    update_response = client.put(f"/api/v1/users/{user_id}/preferences", json=payload)
    assert update_response.status_code == 200
    assert update_response.json()["subscription"]["rss_sources"] == ["hacker-news"]

    saved_response = client.get(f"/api/v1/users/{user_id}/preferences")
    assert saved_response.status_code == 200
    assert saved_response.json()["settings"]["console_mode"] == "verbose"
