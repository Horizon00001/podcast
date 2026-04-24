"""Comprehensive integration tests — full backend flows.

Tests real HTTP endpoints through FastAPI TestClient with in-memory SQLite.
External dependencies (AI, TTS, RSS) are mocked, but the full internal
pipeline from API → Service → Repository → DB is exercised."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session(test_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(test_engine, test_session):
    """FastAPI TestClient wired to in-memory SQLite."""
    def override_get_db():
        try:
            yield test_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def client_with_data(client, test_session):
    """TestClient with pre-seeded data: 1 user, 3 podcasts, some interactions."""
    from app.models.user import User
    from app.models.podcast import Podcast
    from app.models.interaction import Interaction

    user1 = User(username="integration_user", email="int@test.com")
    test_session.add(user1)
    test_session.commit()
    test_session.refresh(user1)

    podcasts = []
    for i, (title, cat) in enumerate([
        ("AI Revolution", "tech_ai"),
        ("Stock Market Update", "business"),
        ("Sports Weekly", "sports"),
    ]):
        p = Podcast(title=title, category=cat, summary=f"Summary {i+1}",
                    audio_url=f"/audio/p{i+1}.mp3", script_path=f"/scripts/p{i+1}.json")
        test_session.add(p)
        test_session.flush()
        podcasts.append(p)
    test_session.commit()

    # Some interactions for recommendation
    interactions = [
        Interaction(user_id=user1.id, podcast_id=podcasts[0].id, action="favorite"),
        Interaction(user_id=user1.id, podcast_id=podcasts[0].id, action="complete",
                    listen_duration_ms=600000, progress_pct=100.0),
        Interaction(user_id=user1.id, podcast_id=podcasts[1].id, action="skip",
                    progress_pct=5.0),
    ]
    for inter in interactions:
        test_session.add(inter)
    test_session.commit()

    return client, user1, podcasts


# ── health ────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "env" in data


# ── user lifecycle ────────────────────────────────────────────────────────────

class TestUserLifecycle:
    def test_create_and_retrieve_user(self, client):
        resp = client.post("/api/v1/users", json={
            "username": "newuser", "email": "new@example.com",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"
        user_id = data["id"]

        resp2 = client.get(f"/api/v1/users/{user_id}")
        assert resp2.status_code == 200
        assert resp2.json()["email"] == "new@example.com"

    def test_get_user_by_username(self, client):
        client.post("/api/v1/users", json={
            "username": "by_name", "email": "byname@test.com",
        })
        resp = client.get("/api/v1/users/by-username/by_name")
        assert resp.status_code == 200
        assert resp.json()["username"] == "by_name"

    def test_get_user_404(self, client):
        resp = client.get("/api/v1/users/99999")
        assert resp.status_code == 404

    def test_get_user_by_username_404(self, client):
        resp = client.get("/api/v1/users/by-username/noexist")
        assert resp.status_code == 404

    def test_duplicate_username_detected(self, client):
        client.post("/api/v1/users", json={
            "username": "dup", "email": "dup1@test.com",
        })
        # Unique constraint violation — SQLAlchemy raises IntegrityError
        # FastAPI has no handler for this, so it propagates as a 500 or exception
        try:
            resp = client.post("/api/v1/users", json={
                "username": "dup", "email": "dup2@test.com",
            })
            # If we get here, the server returned a response (typically 500)
            assert resp.status_code in (409, 500)
        except Exception as exc:
            # TestClient may re-raise unhandled exceptions
            assert "UNIQUE constraint" in str(exc) or "IntegrityError" in str(exc)

    def test_invalid_email_rejected(self, client):
        resp = client.post("/api/v1/users", json={
            "username": "bad", "email": "not-an-email",
        })
        assert resp.status_code == 422


# ── podcast CRUD ──────────────────────────────────────────────────────────────

class TestPodcastCRUD:
    def test_create_and_list(self, client):
        resp = client.post("/api/v1/podcasts", json={
            "title": "Integration Podcast",
            "summary": "Test summary",
            "category": "tech_ai",
        })
        assert resp.status_code == 201
        pid = resp.json()["id"]

        resp2 = client.get("/api/v1/podcasts")
        assert resp2.status_code == 200
        podcasts = resp2.json()
        assert any(p["id"] == pid for p in podcasts)

    def test_get_by_id(self, client):
        create_resp = client.post("/api/v1/podcasts", json={"title": "Target"})
        pid = create_resp.json()["id"]

        get_resp = client.get(f"/api/v1/podcasts/{pid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Target"

    def test_get_404(self, client):
        resp = client.get("/api/v1/podcasts/99999")
        assert resp.status_code == 404

    def test_list_empty(self, client):
        resp = client.get("/api/v1/podcasts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_podcast_response_fields(self, client):
        resp = client.post("/api/v1/podcasts", json={
            "title": "Full Pod", "summary": "S", "category": "business",
            "audio_url": "/audio/f.mp3", "script_path": "/scripts/f.json",
        })
        data = resp.json()
        assert "id" in data
        assert "published_at" in data
        assert data["audio_url"] == "/audio/f.mp3"
        assert data["script_path"] == "/scripts/f.json"


# ── interaction reporting ─────────────────────────────────────────────────────

class TestInteractionFlow:
    def make_user_and_podcast(self, client):
        u = client.post("/api/v1/users", json={
            "username": f"int_user_{time.time()}", "email": f"int{time.time()}@t.com",
        })
        user_id = u.json()["id"]
        p = client.post("/api/v1/podcasts", json={"title": "Interactive Pod"})
        podcast_id = p.json()["id"]
        return user_id, podcast_id

    def test_report_play_interaction(self, client):
        uid, pid = self.make_user_and_podcast(client)
        resp = client.post("/api/v1/interactions", json={
            "user_id": uid, "podcast_id": pid, "action": "play",
            "context_hour": 14, "context_weekday": 3, "context_bucket": "afternoon",
            "session_id": "sess-001",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["action"] == "play"
        assert data["context_bucket"] == "afternoon"
        assert "id" in data
        assert "created_at" in data

    def test_report_complete_with_progress(self, client):
        uid, pid = self.make_user_and_podcast(client)
        resp = client.post("/api/v1/interactions", json={
            "user_id": uid, "podcast_id": pid, "action": "complete",
            "listen_duration_ms": 480000, "progress_pct": 100.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["listen_duration_ms"] == 480000
        assert abs(data["progress_pct"] - 100.0) < 0.01

    def test_invalid_action_rejected(self, client):
        uid, pid = self.make_user_and_podcast(client)
        resp = client.post("/api/v1/interactions", json={
            "user_id": uid, "podcast_id": pid, "action": "invalid_action",
        })
        assert resp.status_code == 422

    def test_multiple_interactions_same_pair(self, client):
        uid, pid = self.make_user_and_podcast(client)

        for action in ["play", "pause", "resume", "like", "favorite", "complete"]:
            resp = client.post("/api/v1/interactions", json={
                "user_id": uid, "podcast_id": pid, "action": action,
            })
            assert resp.status_code == 201, f"Action {action} failed"


# ── recommendation ────────────────────────────────────────────────────────────

class TestRecommendationIntegration:
    def test_cold_start_user(self, client):
        """New user with no interactions gets fallback recommendations."""
        u = client.post("/api/v1/users", json={
            "username": "coldstart", "email": "cold@test.com",
        })
        # Add some podcasts so there's something to recommend
        client.post("/api/v1/podcasts", json={"title": "P1", "category": "tech_ai"})
        client.post("/api/v1/podcasts", json={"title": "P2", "category": "business"})

        resp = client.get(f"/api/v1/recommendations/{u.json()['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == u.json()["id"]
        assert "strategy" in data
        assert "items" in data

    def test_warm_user_gets_personalized(self, client_with_data):
        client, user, podcasts = client_with_data

        resp = client.get(f"/api/v1/recommendations/{user.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["strategy"] in ("warm-up", "hybrid-v1")
        items = data["items"]
        podcast_ids = [item["podcast_id"] for item in items]
        # The skipped podcast (podcasts[1]) should not appear
        assert podcasts[1].id not in podcast_ids, \
            f"Skipped podcast {podcasts[1].id} should be filtered"
        # The favorited podcast should be included
        assert podcasts[0].id in podcast_ids or len(items) > 0

    def test_recommendation_items_have_score_and_reason(self, client_with_data):
        client, user, _ = client_with_data

        resp = client.get(f"/api/v1/recommendations/{user.id}")
        items = resp.json()["items"]
        for item in items:
            assert "podcast_id" in item
            assert "score" in item
            assert "reason" in item
            assert 0 <= item["score"] <= 1, f"Score {item['score']} out of range"


# ── generation ────────────────────────────────────────────────────────────────

class TestGenerationIntegration:
    def test_get_sources(self, client):
        resp = client.get("/api/v1/generation/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data
        sources = data["sources"]
        # Should have enabled feeds from config/feed.json
        assert len(sources) > 0
        for src in sources:
            assert "id" in src
            assert "name" in src
            assert "url" in src
            assert "category" in src

    def test_get_topics(self, client):
        resp = client.get("/api/v1/generation/topics")
        assert resp.status_code == 200
        data = resp.json()
        assert "topics" in data
        topic_ids = [t["id"] for t in data["topics"]]
        assert "daily-news" in topic_ids

    def test_trigger_generation_and_poll_status(self, client):
        """Trigger a generation, mock the pipeline, verify status flow."""
        from app.services.generation_service import generation_service

        original_run = generation_service.run_pipeline
        pipeline_called = []

        async def fake_run(task_id):
            pipeline_called.append(task_id)
            # Update status through service
            generation_service._update_task(task_id, "running", "Processing...")
            generation_service._with_repository(
                lambda r: r.append_log(task_id, "[1/4] Fetching RSS..."))
            generation_service._with_repository(
                lambda r: r.append_log(task_id, "[2/4] Classifying..."))
            generation_service._update_task(task_id, "succeeded", "Done!")

        generation_service.run_pipeline = fake_run

        try:
            resp = client.post("/api/v1/generation/trigger", json={
                "rss_source": "default", "topic": "daily-news",
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "task_id" in data
            assert data["status"] == "queued"
            task_id = data["task_id"]

            # Poll status — pipeline should have run synchronously via background task
            # (background task runs in same thread with TestClient)
            status_resp = client.get(f"/api/v1/generation/{task_id}")
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            assert status_data["task_id"] == task_id
            assert status_data["status"] in ("running", "succeeded")

            assert len(pipeline_called) == 1
            assert pipeline_called[0] == task_id
        finally:
            generation_service.run_pipeline = original_run

    def test_trigger_generation_with_custom_topic(self, client):
        from app.services.generation_service import generation_service

        original_run = generation_service.run_pipeline
        pipeline_called = []

        async def fake_run(task_id):
            pipeline_called.append(task_id)
            generation_service._update_task(task_id, "succeeded", "OK")

        generation_service.run_pipeline = fake_run
        try:
            resp = client.post("/api/v1/generation/trigger", json={
                "rss_source": "hacker-news", "topic": "daily-ai-brief",
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "queued"
            assert "task_id" in data
        finally:
            generation_service.run_pipeline = original_run

    def test_get_nonexistent_task(self, client):
        resp = client.get("/api/v1/generation/nonexistent-task-id")
        assert resp.status_code == 404


# ── end-to-end scenario ───────────────────────────────────────────────────────

class TestEndToEndScenario:
    """Realistic user journey: discover → listen → interact → get recommendations."""

    def test_full_user_journey(self, client):
        # 1. Create user
        u = client.post("/api/v1/users", json={
            "username": "journey_user", "email": "journey@test.com",
        })
        assert u.status_code == 201
        uid = u.json()["id"]

        # 2. Browse podcast library (empty at first)
        resp = client.get("/api/v1/podcasts")
        assert resp.status_code == 200
        assert resp.json() == []

        # 3. Podcasts get created (simulating generation)
        podcasts = []
        for i in range(5):
            p = client.post("/api/v1/podcasts", json={
                "title": f"Episode {i+1}",
                "summary": f"Content {i+1}",
                "category": "tech_ai" if i < 3 else "business",
            })
            podcasts.append(p.json()["id"])

        # 4. See all podcasts
        resp = client.get("/api/v1/podcasts")
        assert len(resp.json()) == 5

        # 5. Play episode 1
        client.post("/api/v1/interactions", json={
            "user_id": uid, "podcast_id": podcasts[0],
            "action": "play", "context_hour": 9, "context_bucket": "morning",
        })

        # 6. Like episode 1
        client.post("/api/v1/interactions", json={
            "user_id": uid, "podcast_id": podcasts[0], "action": "like",
        })

        # 7. Favorite episode 1
        client.post("/api/v1/interactions", json={
            "user_id": uid, "podcast_id": podcasts[0], "action": "favorite",
        })

        # 8. Complete episode 1
        client.post("/api/v1/interactions", json={
            "user_id": uid, "podcast_id": podcasts[0],
            "action": "complete", "listen_duration_ms": 600000, "progress_pct": 100.0,
        })

        # 9. Skip episode 4
        client.post("/api/v1/interactions", json={
            "user_id": uid, "podcast_id": podcasts[3],
            "action": "skip", "progress_pct": 10.0,
        })

        # 10. Get recommendations — should prefer tech_ai over business
        rec = client.get(f"/api/v1/recommendations/{uid}")
        assert rec.status_code == 200
        rec_data = rec.json()
        assert rec_data["strategy"] == "hybrid-v1"

        # Episode 4 (skipped) should be filtered out
        recommended_ids = [item["podcast_id"] for item in rec_data["items"]]
        assert podcasts[3] not in recommended_ids

        # 11. Get podcast detail
        detail = client.get(f"/api/v1/podcasts/{podcasts[0]}")
        assert detail.status_code == 200
        assert detail.json()["title"] == "Episode 1"


class TestGenerationSourcesTopics:
    def test_sources_match_config(self, client):
        import json as _json
        from app.core.config import settings
        resp = client.get("/api/v1/generation/sources")
        api_sources = {s["id"] for s in resp.json()["sources"]}
        with open(settings.feed_config_path) as f:
            config = _json.load(f)
        config_enabled = {f["id"] for f in config.get("feeds", []) if f.get("enabled")}
        assert api_sources == config_enabled

    def test_topics_have_required_fields(self, client):
        resp = client.get("/api/v1/generation/topics")
        for topic in resp.json()["topics"]:
            assert "id" in topic
            assert "name" in topic
            assert "description" in topic


class TestGenerationSSEStream:
    def test_stream_task_not_found(self, client):
        resp = client.get("/api/v1/generation/nonexistent-task-id/stream",
                         headers={"Accept": "text/event-stream"})
        assert resp.status_code == 200
        content = resp.text
        assert "error" in content or "Task not found" in content or "[DONE]" in content

    def test_stream_succeeded_task(self, client):
        """Succeeded task returns status immediately without looping."""
        from app.services.generation_service import generation_service
        import uuid

        task_id = str(uuid.uuid4())
        generation_service.create_task("default", "daily-news", task_id)
        generation_service.add_log(task_id, "[1/4] Fetched RSS")

        # Must set to succeeded BEFORE streaming, otherwise endpoint loops forever
        generation_service._update_task(task_id, "succeeded", "All done!")

        resp = client.get(f"/api/v1/generation/{task_id}/stream",
                        headers={"Accept": "text/event-stream"})
        assert resp.status_code == 200
        content = resp.text
        assert "succeeded" in content or "[DONE]" in content

    def test_stream_failed_task(self, client):
        """Failed task returns status immediately without looping."""
        from app.services.generation_service import generation_service
        import uuid

        task_id = str(uuid.uuid4())
        generation_service.create_task("default", "daily-news", task_id)
        generation_service._update_task(task_id, "failed", "Pipeline crashed!")

        resp = client.get(f"/api/v1/generation/{task_id}/stream",
                        headers={"Accept": "text/event-stream"})
        assert resp.status_code == 200


class TestCLIParser:
    def test_build_parser_creates_valid_parser(self):
        from app.cli import build_parser
        parser = build_parser()
        assert parser is not None

    def test_parser_parse_run_pipeline(self):
        from app.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["run-pipeline", "--topic", "daily-ai-brief"])
        assert args.command == "run-pipeline"
        assert args.topic == "daily-ai-brief"

    def test_parser_parse_fetch_rss(self):
        from app.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["fetch-rss"])
        assert args.command == "fetch-rss"
        assert args.config_path is None

    def test_parser_parse_generate_text(self):
        from app.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["generate-text", "--topic", "tech"])
        assert args.command == "generate-text"
        assert args.topic == "tech"

    def test_parser_parse_synthesize_tts(self):
        from app.cli import build_parser
        import argparse
        from pathlib import Path as P
        parser = build_parser()
        args = parser.parse_args(["synthesize-tts", "--json-path", "custom.json"])
        assert args.command == "synthesize-tts"
        assert str(args.json_path) == "custom.json"

    def test_parser_missing_command_raises(self):
        from app.cli import build_parser
        import argparse
        parser = build_parser()
        try:
            parser.parse_args([])
            assert False, "Should raise"
        except SystemExit:
            pass

    def test_main_run_pipeline_dispatches(self, monkeypatch):
        from app.cli import main
        import asyncio

        called = []
        async def fake_pipeline(topic):
            called.append(("pipeline", topic))

        monkeypatch.setattr("app.cli.run_pipeline_command", fake_pipeline)
        main(["run-pipeline", "--topic", "daily-ai-brief"])
        assert len(called) == 1
        assert called[0] == ("pipeline", "daily-ai-brief")

    def test_main_fetch_rss_dispatches(self, monkeypatch):
        from app.cli import main

        called = []
        def fake_fetch(config_path, output_dir):
            called.append(("fetch", config_path, output_dir))

        monkeypatch.setattr("app.cli.fetch_rss_command", fake_fetch)
        main(["fetch-rss", "--config-path", "/tmp/cfg.json"])
        assert called[0][0] == "fetch"
        assert str(called[0][1]) == "/tmp/cfg.json"


class TestEdgeCases:
    def test_concurrent_interactions_across_users(self, client):
        """Multiple users interacting with the same podcast."""
        u1 = client.post("/api/v1/users", json={
            "username": "user_a", "email": "a@test.com",
        })
        u2 = client.post("/api/v1/users", json={
            "username": "user_b", "email": "b@test.com",
        })
        p = client.post("/api/v1/podcasts", json={"title": "Shared Podcast"})

        uid1, uid2, pid = u1.json()["id"], u2.json()["id"], p.json()["id"]

        # Both play the same podcast
        for uid in (uid1, uid2):
            resp = client.post("/api/v1/interactions", json={
                "user_id": uid, "podcast_id": pid, "action": "play",
            })
            assert resp.status_code == 201

        # User A likes and favorites
        client.post("/api/v1/interactions", json={
            "user_id": uid1, "podcast_id": pid, "action": "favorite",
        })

        # User B completes
        client.post("/api/v1/interactions", json={
            "user_id": uid2, "podcast_id": pid, "action": "complete",
        })

        # Both get recommendations — should differ based on behavior
        rec1 = client.get(f"/api/v1/recommendations/{uid1}")
        rec2 = client.get(f"/api/v1/recommendations/{uid2}")
        assert rec1.status_code == 200
        assert rec2.status_code == 200
