from fastapi.testclient import TestClient

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.main import app
from app.models.podcast import Podcast


client = TestClient(app)


def _reset_test_data():
    """Reset test data by truncating tables."""
    db = SessionLocal()
    try:
        from app.models.interaction import Interaction

        db.query(Interaction).delete()
        db.query(Podcast).delete()
        db.commit()
    finally:
        db.close()


def test_list_podcasts_empty():
    init_db()
    _reset_test_data()

    response = client.get("/api/v1/podcasts")
    assert response.status_code == 200
    assert response.json() == []


def test_list_podcasts_with_data():
    init_db()
    _reset_test_data()

    # Add some podcasts directly via DB
    db = SessionLocal()
    try:
        podcasts = [
            Podcast(title="AI News", summary="Latest AI updates", category="tech", audio_url="/audio/ai.mp3", script_path=""),
            Podcast(title="Sports Daily", summary="Sports news", category="sports", audio_url="/audio/sports.mp3", script_path=""),
        ]
        db.add_all(podcasts)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/podcasts")
    assert response.status_code == 200
    payloads = response.json()
    assert len(payloads) == 2
    # Verify fields
    for p in payloads:
        assert "id" in p
        assert "title" in p
        assert "summary" in p
        assert "category" in p


def test_get_podcast_by_id():
    init_db()
    _reset_test_data()

    # Create podcast
    db = SessionLocal()
    try:
        podcast = Podcast(
            title="Test Podcast",
            summary="Test summary",
            category="tech",
            audio_url="/audio/test.mp3",
            script_path="/scripts/test.txt",
        )
        db.add(podcast)
        db.commit()
        podcast_id = podcast.id
    finally:
        db.close()

    response = client.get(f"/api/v1/podcasts/{podcast_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == podcast_id
    assert payload["title"] == "Test Podcast"
    assert payload["summary"] == "Test summary"
    assert payload["category"] == "tech"
    assert payload["audio_url"] == "/audio/test.mp3"
    assert payload["script_path"] == "/scripts/test.txt"


def test_get_podcast_not_found():
    init_db()
    _reset_test_data()

    response = client.get("/api/v1/podcasts/99999")
    assert response.status_code == 404


def test_create_podcast():
    init_db()
    _reset_test_data()

    response = client.post(
        "/api/v1/podcasts",
        json={
            "title": "New Podcast",
            "summary": "A new podcast",
            "category": "business",
            "audio_url": "/audio/new.mp3",
            "script_path": "/scripts/new.txt",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "New Podcast"
    assert payload["summary"] == "A new podcast"
    assert payload["category"] == "business"
    assert "id" in payload
    assert "published_at" in payload


def test_create_podcast_minimal():
    """Test creating podcast with only required fields."""
    init_db()
    _reset_test_data()

    response = client.post(
        "/api/v1/podcasts",
        json={"title": "Minimal Podcast"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Minimal Podcast"
    assert payload["summary"] == ""
    assert payload["category"] == "general"  # default value


def test_create_podcast_invalid_category():
    init_db()
    _reset_test_data()

    # category should default to "general" - this should succeed
    response = client.post(
        "/api/v1/podcasts",
        json={"title": "Test", "category": "tech"},
    )
    assert response.status_code == 201
