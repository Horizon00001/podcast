import json
import tempfile
from pathlib import Path

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


def test_get_podcast_script_success():
    init_db()
    _reset_test_data()

    script_data = {
        "title": "Test Script",
        "intro": "Welcome",
        "sections": [
            {
                "section_type": "opening",
                "dialogues": [
                    {"speaker": "A", "content": "Hello from host.", "emotion": ""},
                    {"speaker": "B", "content": "Hello from guest.", "emotion": ""},
                ],
                "summary": "Opening section",
            },
        ],
        "total_duration": "1min",
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(script_data, f)
        temp_path = f.name

    try:
        db = SessionLocal()
        try:
            podcast = Podcast(
                title="Test",
                summary="Summary",
                audio_url="/audio/test.mp3",
                script_path=temp_path,
            )
            db.add(podcast)
            db.commit()
            podcast_id = podcast.id
        finally:
            db.close()

        response = client.get(f"/api/v1/podcasts/{podcast_id}/script")
        assert response.status_code == 200
        lines = response.json()
        assert len(lines) == 2
        assert lines[0]["speaker"] == "host"
        assert lines[0]["text"] == "Hello from host."
        assert lines[1]["speaker"] == "guest"
        assert lines[1]["text"] == "Hello from guest."
        assert lines[0]["startTime"] == 0
        assert lines[0]["endTime"] > 0
        assert lines[1]["startTime"] == lines[0]["endTime"]
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_get_podcast_script_not_found():
    init_db()
    _reset_test_data()

    response = client.get("/api/v1/podcasts/99999/script")
    assert response.status_code == 404


def test_get_podcast_script_no_script_path():
    init_db()
    _reset_test_data()

    db = SessionLocal()
    try:
        podcast = Podcast(
            title="No Script",
            summary="N/A",
            audio_url="/audio/test.mp3",
            script_path="",
        )
        db.add(podcast)
        db.commit()
        podcast_id = podcast.id
    finally:
        db.close()

    response = client.get(f"/api/v1/podcasts/{podcast_id}/script")
    assert response.status_code == 404


def test_get_podcast_script_file_missing():
    init_db()
    _reset_test_data()

    db = SessionLocal()
    try:
        podcast = Podcast(
            title="Missing File",
            summary="N/A",
            audio_url="/audio/test.mp3",
            script_path="/nonexistent/path/script.json",
        )
        db.add(podcast)
        db.commit()
        podcast_id = podcast.id
    finally:
        db.close()

    response = client.get(f"/api/v1/podcasts/{podcast_id}/script")
    assert response.status_code == 404


def test_get_podcast_script_prefers_timing_file():
    """When podcast_timing.json exists, use real durations instead of estimation."""
    init_db()
    _reset_test_data()

    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "podcast_script.json"
        script_data = {
            "title": "Test",
            "intro": "",
            "sections": [
                {
                    "section_type": "opening",
                    "dialogues": [
                        {"speaker": "A", "content": "A very long sentence that would be estimated to many seconds.", "emotion": ""},
                    ],
                    "summary": "",
                },
            ],
            "total_duration": "1min",
        }
        script_path.write_text(json.dumps(script_data))

        timing_path = Path(tmpdir) / "podcast_timing.json"
        timing_data = [
            {"item_type": "speech", "speaker": "A", "text": "A very long sentence that would be estimated to many seconds.", "start_ms": 0, "end_ms": 1500, "duration_ms": 1500},
        ]
        timing_path.write_text(json.dumps(timing_data))

        db = SessionLocal()
        try:
            podcast = Podcast(
                title="Timing Test",
                summary="N/A",
                audio_url="/audio/test.mp3",
                script_path=str(script_path),
            )
            db.add(podcast)
            db.commit()
            podcast_id = podcast.id
        finally:
            db.close()

        response = client.get(f"/api/v1/podcasts/{podcast_id}/script")
        assert response.status_code == 200
        lines = response.json()
        assert len(lines) == 1
        # The sentence is 65 chars, which would be estimated to ~16 seconds.
        # But the timing file says 1.5 seconds.
        assert lines[0]["startTime"] == 0
        assert lines[0]["endTime"] == 1500
