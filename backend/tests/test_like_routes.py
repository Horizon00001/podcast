from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as db_session_module
from app.db.base import Base
from app.db.init_db import init_db
from app.db.session import get_db
from app.main import app
from app.models.like import Like
from app.models.podcast import Podcast
from app.models.user import User


client = TestClient(app)

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
db_session_module.SessionLocal = TestingSessionLocal


def _reset_test_data() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _seed_user_and_podcast() -> tuple[int, int]:
    db = TestingSessionLocal()
    try:
        user = User(username="like-user", email="like@example.com")
        podcast = Podcast(
            title="Liked Podcast",
            summary="liked summary",
            audio_url="/audio/liked.mp3",
            script_path="",
            published_at=datetime.now(timezone.utc),
        )
        db.add_all([user, podcast])
        db.commit()
        db.refresh(user)
        db.refresh(podcast)
        return user.id, podcast.id
    finally:
        db.close()


def test_add_and_list_likes():
    init_db()
    _reset_test_data()
    user_id, podcast_id = _seed_user_and_podcast()

    create_response = client.post("/api/v1/likes", json={"user_id": user_id, "podcast_id": podcast_id})
    assert create_response.status_code == 201
    assert create_response.json()["user_id"] == user_id
    assert create_response.json()["podcast_id"] == podcast_id

    list_response = client.get(f"/api/v1/likes?user_id={user_id}")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 1
    assert payload[0]["podcast_id"] == podcast_id


def test_add_like_is_idempotent():
    init_db()
    _reset_test_data()
    user_id, podcast_id = _seed_user_and_podcast()

    first = client.post("/api/v1/likes", json={"user_id": user_id, "podcast_id": podcast_id})
    second = client.post("/api/v1/likes", json={"user_id": user_id, "podcast_id": podcast_id})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    db = TestingSessionLocal()
    try:
        assert db.query(Like).count() == 1
    finally:
        db.close()


def test_remove_like():
    init_db()
    _reset_test_data()
    user_id, podcast_id = _seed_user_and_podcast()
    client.post("/api/v1/likes", json={"user_id": user_id, "podcast_id": podcast_id})

    delete_response = client.delete(f"/api/v1/likes/{user_id}/{podcast_id}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"ok": True}

    list_response = client.get(f"/api/v1/likes?user_id={user_id}")
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_remove_missing_like_returns_404():
    init_db()
    _reset_test_data()
    user_id, podcast_id = _seed_user_and_podcast()

    response = client.delete(f"/api/v1/likes/{user_id}/{podcast_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Like not found"
