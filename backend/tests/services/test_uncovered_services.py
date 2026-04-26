"""Service tests for uncovered services: TopicService, PodcastService,
GenerationResultService."""

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.topic_service import TopicService, topic_service
from app.services.podcast_service import PodcastService
from app.services.generation_result_service import GenerationResultService
from app.schemas.podcast import PodcastCreate


class TestTopicService:
    def test_list_topics_returns_all(self, tmp_path, monkeypatch):
        topics_config = {
            "topics": [
                {"id": "t1", "name": "Topic 1", "description": "Desc 1"},
                {"id": "t2", "name": "Topic 2", "description": "Desc 2"},
            ]
        }
        config_path = tmp_path / "topics.json"
        config_path.write_text(json.dumps(topics_config, ensure_ascii=False))

        from app.core.config import Settings
        monkeypatch.setattr(
            Settings, "topics_config_path",
            property(lambda self: config_path),
        )

        svc = TopicService()
        topics = svc.list_topics()
        assert len(topics) == 2
        assert topics[0]["id"] in ("t1", "t2")
        assert topics[0]["name"] in ("Topic 1", "Topic 2")
        assert "description" in topics[0]

    def test_list_topics_empty(self, tmp_path, monkeypatch):
        config_path = tmp_path / "topics.json"
        config_path.write_text(json.dumps({"topics": []}))

        from app.core.config import Settings
        monkeypatch.setattr(
            Settings, "topics_config_path",
            property(lambda self: config_path),
        )

        svc = TopicService()
        assert svc.list_topics() == []

    def test_topic_service_singleton(self):
        assert topic_service is not None
        assert isinstance(topic_service, TopicService)


class TestPodcastService:
    def test_create_and_list(self, db_session):
        svc = PodcastService(db_session)
        p = svc.create_podcast(PodcastCreate(title="Svc Podcast", event_key="svc:podcast"))
        assert p.id is not None

        podcasts = svc.list_podcasts()
        assert len(podcasts) == 1

    def test_get_podcast(self, db_session):
        svc = PodcastService(db_session)
        created = svc.create_podcast(PodcastCreate(title="Target", event_key="svc:target"))
        found = svc.get_podcast(created.id)
        assert found.title == "Target"

    def test_get_podcast_not_found(self, db_session):
        svc = PodcastService(db_session)
        assert svc.get_podcast(999) is None

    def test_upsert_creates_when_event_key_missing(self, db_session):
        svc = PodcastService(db_session)
        status, podcast = svc.upsert_podcast(PodcastCreate(title="Unique", event_key="svc:unique"))
        assert status == "created"
        assert podcast is not None
        assert podcast.event_key == "svc:unique"

    def test_upsert_skips_duplicate_event_key_by_default(self, db_session):
        svc = PodcastService(db_session)
        first_status, first = svc.upsert_podcast(PodcastCreate(title="First", event_key="svc:duplicate"))
        second_status, second = svc.upsert_podcast(PodcastCreate(title="Second", event_key="svc:duplicate"))

        assert first_status == "created"
        assert first is not None
        assert second_status == "skipped"
        assert second is None
        podcasts = svc.list_podcasts()
        assert len(podcasts) == 1
        assert podcasts[0].title == "First"

    def test_upsert_updates_duplicate_event_key_when_forced(self, db_session):
        svc = PodcastService(db_session)
        svc.upsert_podcast(PodcastCreate(title="First", event_key="svc:forced", summary="old"))
        status, updated = svc.upsert_podcast(
            PodcastCreate(title="Second", event_key="svc:forced", summary="new"),
            force=True,
        )

        assert status == "updated"
        assert updated is not None
        assert updated.title == "Second"
        assert updated.summary == "new"


class TestGenerationResultService:
    def test_save_when_files_missing(self, tmp_path):
        messages = []

        async def fake_add_log(task_id, msg):
            messages.append(msg)

        svc = GenerationResultService(tmp_path)
        asyncio.run(svc.save_generated_podcast("task-1", fake_add_log))
        assert any("未能找到生成的文件" in m for m in messages)

    def test_save_success(self, tmp_path, db_session):
        script = {"title": "My Podcast", "intro": "Welcome to the show"}
        (tmp_path / "podcast_script.json").write_text(
            json.dumps(script, ensure_ascii=False))
        (tmp_path / "audio").mkdir()
        (tmp_path / "audio" / "podcast_full.mp3").write_text("fake audio data")

        messages = []

        async def fake_add_log(task_id, msg):
            messages.append(msg)

        with patch("app.services.generation_result_service.SessionLocal", return_value=db_session):
            svc = GenerationResultService(tmp_path)
            asyncio.run(svc.save_generated_podcast("task-1", fake_add_log))
        assert any("已成功添加到列表" in m for m in messages)
        assert (tmp_path / "audio" / "podcast_task-1.mp3").exists()
        assert (tmp_path / "audio" / "podcast_task-1.json").exists()

    def test_normalize_display_title_falls_back_for_slug(self):
        assert GenerationResultService._normalize_display_title(
            "21-tim-cook-is-stepping-down-as-ceo-of-apple"
        ) == "本期新闻深度解读"

    def test_normalize_display_title_keeps_chinese_title(self):
        assert GenerationResultService._normalize_display_title(
            "苹果权力结构生变，Tim Cook 时代走到哪一步"
        ) == "苹果权力结构生变，Tim Cook 时代"

    def test_save_exception_handled(self, tmp_path):
        script = {"title": "Test"}
        (tmp_path / "podcast_script.json").write_text(
            json.dumps(script, ensure_ascii=False))
        (tmp_path / "audio").mkdir()
        (tmp_path / "audio" / "podcast_full.mp3").write_text("audio")

        messages = []

        async def fake_add_log(task_id, msg):
            messages.append(msg)

        with patch("app.services.generation_result_service.SessionLocal") as mock_sess:
            mock_db = MagicMock()
            mock_db.commit.side_effect = RuntimeError("DB error")
            mock_sess.return_value = mock_db

            svc = GenerationResultService(tmp_path)
            asyncio.run(svc.save_generated_podcast("task-2", fake_add_log))
            assert any("入库过程中出现错误" in m for m in messages)
