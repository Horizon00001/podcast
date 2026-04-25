from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.init_db import init_db
from app.db import session as db_session_module
from app.db.session import get_db
from app.main import app
from app.models.interaction import Interaction
from app.models.podcast import Podcast
from app.models.user import User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base


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
    db = TestingSessionLocal()
    try:
        db.query(Interaction).delete()
        db.query(Podcast).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def test_recommendations_cold_start_returns_hot_and_fresh_items():
    init_db()
    _reset_test_data()

    db = TestingSessionLocal()
    user_id = 0
    try:
        user = User(username="cold-user", email="cold@example.com")
        db.add(user)
        db.flush()
        user_id = user.id

        old_podcast = Podcast(
            title="Old hot",
            summary="old content",
            audio_url="/audio/old.mp3",
            script_path="",
            published_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
        new_podcast = Podcast(
            title="New hot",
            summary="new content",
            audio_url="/audio/new.mp3",
            script_path="",
            published_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add_all([old_podcast, new_podcast])
        db.flush()

        db.add_all(
            [
                Interaction(user_id=user.id, podcast_id=old_podcast.id, action="play", listen_duration_ms=30000, progress_pct=10.0),
                Interaction(user_id=user.id, podcast_id=new_podcast.id, action="play", listen_duration_ms=30000, progress_pct=10.0),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get(f"/api/v1/recommendations/{user_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["strategy"] == "warm-up"
    assert isinstance(payload["items"], list)


def test_recommendations_personalized_and_skip_filtered():
    init_db()
    _reset_test_data()

    db = TestingSessionLocal()
    user_a_id = 0
    p3_id = 0
    p4_id = 0
    try:
        user_a = User(username="user-a", email="user-a@example.com")
        user_b = User(username="user-b", email="user-b@example.com")
        db.add_all([user_a, user_b])
        db.flush()
        user_a_id = user_a.id

        p1 = Podcast(title="AI News", summary="ai model update", audio_url="", script_path="")
        p2 = Podcast(title="AI Weekly", summary="ai product release", audio_url="", script_path="")
        p3 = Podcast(title="Finance Daily", summary="market stocks", audio_url="", script_path="")
        p4 = Podcast(title="AI Deep Dive", summary="ai architecture", audio_url="", script_path="")
        db.add_all([p1, p2, p3, p4])
        db.flush()
        p3_id = p3.id
        p4_id = p4.id

        # user_a 偏好 AI，并跳过 finance
        db.add_all(
            [
                Interaction(user_id=user_a.id, podcast_id=p1.id, action="favorite"),
                Interaction(user_id=user_a.id, podcast_id=p2.id, action="like"),
                Interaction(user_id=user_a.id, podcast_id=p3.id, action="skip"),
            ]
        )

        # 其他用户的共现行为，帮助 itemCF 把 p4 关联到 AI 内容
        db.add_all(
            [
                Interaction(user_id=user_b.id, podcast_id=p1.id, action="like"),
                Interaction(user_id=user_b.id, podcast_id=p4.id, action="favorite"),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get(f"/api/v1/recommendations/{user_a_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["strategy"] == "warm-up"

    ids = [item["podcast_id"] for item in payload["items"]]
    scores = [item["score"] for item in payload["items"]]

    assert p3_id not in ids
    assert p4_id in ids
    assert scores == sorted(scores, reverse=True)
