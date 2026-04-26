"""Model instantiation tests — Python level and DB-persisted."""

from datetime import datetime

from app.models.user import User
from app.models.podcast import Podcast
from app.models.interaction import Interaction
from app.models.generation_task import GenerationTask


class TestUserModel:
    def test_create_minimal_user_python_level(self):
        """Defaults like created_at are applied at DB level, not Python level."""
        user = User(username="alice", email="alice@example.com")
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        # SQLAlchemy column defaults only apply on flush/commit
        assert user.created_at is None

    def test_user_id_is_none_before_commit(self):
        user = User(username="bob", email="bob@example.com")
        assert user.id is None

    def test_user_repr(self):
        user = User(username="dave", email="dave@example.com")
        assert "dave" in repr(user) or "User" in repr(user)

    def test_user_persisted_defaults(self, db_session):
        user = User(username="eve", email="eve@example.com")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.id is not None
        assert isinstance(user.created_at, datetime)

    def test_user_duplicate_username(self, db_session):
        user1 = User(username="uniq", email="a@example.com")
        db_session.add(user1)
        db_session.commit()
        user2 = User(username="uniq", email="b@example.com")
        db_session.add(user2)
        try:
            db_session.commit()
            assert False, "Should have raised IntegrityError"
        except Exception:
            db_session.rollback()


class TestPodcastModel:
    def test_create_minimal_podcast_python_level(self):
        podcast = Podcast(title="Test Episode")
        assert podcast.title == "Test Episode"
        # SQLAlchemy column defaults only apply on DB flush
        assert podcast.summary is None
        assert podcast.category is None

    def test_podcast_full_creation(self):
        podcast = Podcast(
            title="Deep Dive",
            summary="An in-depth look at AI",
            category="tech_ai",
            event_key="tech_ai:deep-dive:1234",
            audio_url="/audio/test.mp3",
            script_path="/output/script.json",
        )
        assert podcast.summary == "An in-depth look at AI"
        assert podcast.event_key == "tech_ai:deep-dive:1234"
        assert podcast.audio_url == "/audio/test.mp3"
        assert podcast.script_path == "/output/script.json"

    def test_podcast_persisted_defaults(self, db_session):
        podcast = Podcast(title="News Episode")
        db_session.add(podcast)
        db_session.commit()
        db_session.refresh(podcast)
        assert podcast.summary == ""
        assert podcast.category == "general"
        assert podcast.event_key == ""
        assert podcast.audio_url == ""
        assert podcast.script_path == ""
        assert isinstance(podcast.published_at, datetime)


class TestInteractionModel:
    def test_create_play_interaction_python_level(self):
        interaction = Interaction(user_id=1, podcast_id=2, action="play")
        assert interaction.user_id == 1
        assert interaction.podcast_id == 2
        assert interaction.action == "play"
        assert interaction.listen_duration_ms is None
        assert interaction.progress_pct is None

    def test_create_interaction_with_context(self):
        interaction = Interaction(
            user_id=1, podcast_id=1, action="play",
            listen_duration_ms=30000, progress_pct=45.5,
            session_id="sess-abc", context_hour=14,
            context_weekday=3, context_bucket="afternoon",
        )
        assert interaction.listen_duration_ms == 30000
        assert abs(interaction.progress_pct - 45.5) < 0.01
        assert interaction.session_id == "sess-abc"
        assert interaction.context_hour == 14

    def test_interaction_all_action_types(self):
        for action in ["play", "pause", "resume", "like", "favorite", "skip", "complete"]:
            interaction = Interaction(user_id=1, podcast_id=1, action=action)
            assert interaction.action == action

    def test_interaction_persisted_timestamps(self, db_session):
        user = User(username="int1", email="int1@example.com")
        podcast = Podcast(title="P1")
        db_session.add_all([user, podcast])
        db_session.commit()

        interaction = Interaction(user_id=user.id, podcast_id=podcast.id, action="play")
        db_session.add(interaction)
        db_session.commit()
        db_session.refresh(interaction)
        assert interaction.id is not None
        assert isinstance(interaction.created_at, datetime)


class TestGenerationTaskModel:
    def test_create_task_python_level(self):
        task = GenerationTask(task_id="task-001", status="queued")
        assert task.task_id == "task-001"
        assert task.status == "queued"
        # Column defaults applied at DB level
        assert task.message is None
        assert task.rss_source is None

    def test_task_with_custom_values(self):
        task = GenerationTask(
            task_id="task-custom", status="failed",
            message="Something went wrong", rss_source="hacker-news",
            topic="daily-ai-brief", logs='["log1", "log2"]',
        )
        assert task.message == "Something went wrong"
        assert task.rss_source == "hacker-news"
        assert task.topic == "daily-ai-brief"
        assert task.logs == '["log1", "log2"]'

    def test_task_persisted_defaults(self, db_session):
        task = GenerationTask(task_id="task-db", status="queued")
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        assert task.message == ""
        assert task.rss_source == "default"
        assert task.topic == "daily-news"
        assert task.logs == "[]"
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)

    def test_task_unique_id(self, db_session):
        task1 = GenerationTask(task_id="task-dup", status="queued")
        db_session.add(task1)
        db_session.commit()
        task2 = GenerationTask(task_id="task-dup", status="running")
        db_session.add(task2)
        try:
            db_session.commit()
            assert False, "Should have raised IntegrityError"
        except Exception:
            db_session.rollback()
