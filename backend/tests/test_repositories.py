"""Repository layer tests using in-memory SQLite."""

from app.repositories.podcast_repository import PodcastRepository
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.generation_task_repository import GenerationTaskRepository
from app.schemas.podcast import PodcastCreate
from app.schemas.interaction import InteractionCreate
from app.models.user import User
from app.models.podcast import Podcast


class TestPodcastRepository:
    def test_list_empty(self, db_session):
        repo = PodcastRepository(db_session)
        assert repo.list_podcasts() == []

    def test_create_and_list(self, db_session):
        repo = PodcastRepository(db_session)
        p = repo.create_podcast(PodcastCreate(
            title="Episode 1", summary="Summary", category="tech",
        ))
        assert p.id is not None
        assert p.title == "Episode 1"
        podcasts = repo.list_podcasts()
        assert len(podcasts) == 1
        assert podcasts[0].id == p.id

    def test_list_order_by_published_at_desc(self, db_session):
        repo = PodcastRepository(db_session)
        p1 = repo.create_podcast(PodcastCreate(title="First"))
        p2 = repo.create_podcast(PodcastCreate(title="Second"))
        results = repo.list_podcasts()
        assert results[0].id >= results[1].id  # newer first

    def test_get_podcast_by_id(self, db_session):
        repo = PodcastRepository(db_session)
        created = repo.create_podcast(PodcastCreate(title="Target"))
        found = repo.get_podcast(created.id)
        assert found is not None
        assert found.title == "Target"

    def test_get_podcast_not_found(self, db_session):
        repo = PodcastRepository(db_session)
        assert repo.get_podcast(99999) is None

    def test_create_podcast_with_audio_and_script(self, db_session):
        repo = PodcastRepository(db_session)
        p = repo.create_podcast(PodcastCreate(
            title="Audio Episode",
            audio_url="/audio/test.mp3",
            script_path="/output/script.json",
        ))
        assert p.audio_url == "/audio/test.mp3"
        assert p.script_path == "/output/script.json"


class TestInteractionRepository:
    def _create_user_and_podcast(self, db_session):
        user = User(username="repouser", email="repo@test.com")
        podcast = Podcast(title="Repo Podcast")
        db_session.add_all([user, podcast])
        db_session.commit()
        return user.id, podcast.id

    def test_create_interaction(self, db_session):
        uid, pid = self._create_user_and_podcast(db_session)
        repo = InteractionRepository(db_session)
        i = repo.create_interaction(InteractionCreate(
            user_id=uid, podcast_id=pid, action="play",
        ))
        assert i.id is not None
        assert i.action == "play"
        assert i.listen_duration_ms is None

    def test_create_interaction_with_all_context(self, db_session):
        uid, pid = self._create_user_and_podcast(db_session)
        repo = InteractionRepository(db_session)
        i = repo.create_interaction(InteractionCreate(
            user_id=uid, podcast_id=pid, action="complete",
            listen_duration_ms=600000, progress_pct=100.0,
            session_id="sess-001", context_hour=14,
            context_weekday=3, context_bucket="afternoon",
        ))
        assert i.listen_duration_ms == 600000
        assert abs(i.progress_pct - 100.0) < 0.01
        assert i.session_id == "sess-001"

    def test_create_multiple_interactions_same_user_podcast(self, db_session):
        uid, pid = self._create_user_and_podcast(db_session)
        repo = InteractionRepository(db_session)
        i1 = repo.create_interaction(InteractionCreate(
            user_id=uid, podcast_id=pid, action="play"))
        i2 = repo.create_interaction(InteractionCreate(
            user_id=uid, podcast_id=pid, action="like"))
        assert i1.id != i2.id


class TestGenerationTaskRepository:
    def test_create_task(self, db_session):
        repo = GenerationTaskRepository(db_session)
        task = repo.create("t1", "default", "daily-news", "queued", "ok")
        assert task.task_id == "t1"
        assert task.status == "queued"
        assert task.logs == "[]"

    def test_get_task(self, db_session):
        repo = GenerationTaskRepository(db_session)
        repo.create("t2", "default", "daily-news", "queued", "")
        task = repo.get("t2")
        assert task is not None
        assert task.task_id == "t2"

    def test_get_nonexistent_task(self, db_session):
        repo = GenerationTaskRepository(db_session)
        assert repo.get("nonexistent") is None

    def test_update_task_status(self, db_session):
        repo = GenerationTaskRepository(db_session)
        repo.create("t3", "default", "daily-news", "queued", "")
        updated = repo.update("t3", status="running", message="Processing...")
        assert updated is not None
        assert updated.status == "running"
        assert updated.message == "Processing..."

    def test_update_nonexistent_task(self, db_session):
        repo = GenerationTaskRepository(db_session)
        assert repo.update("noexist", status="running") is None

    def test_append_log(self, db_session):
        repo = GenerationTaskRepository(db_session)
        repo.create("t4", "default", "daily-news", "queued", "")
        repo.append_log("t4", "Step 1: Start")
        repo.append_log("t4", "Step 2: Done")
        logs = repo.get_logs("t4")
        assert logs == ["Step 1: Start", "Step 2: Done"]

    def test_append_log_nonexistent_task(self, db_session):
        repo = GenerationTaskRepository(db_session)
        assert repo.append_log("noexist", "msg") is None

    def test_get_logs_nonexistent_task(self, db_session):
        repo = GenerationTaskRepository(db_session)
        assert repo.get_logs("noexist") == []

    def test_get_logs_empty(self, db_session):
        repo = GenerationTaskRepository(db_session)
        repo.create("t5", "default", "daily-news", "queued", "")
        assert repo.get_logs("t5") == []

    def test_create_task_with_custom_fields(self, db_session):
        repo = GenerationTaskRepository(db_session)
        task = repo.create("t-custom", "hacker-news", "daily-ai-brief",
                           "queued", "Custom task")
        assert task.rss_source == "hacker-news"
        assert task.topic == "daily-ai-brief"
