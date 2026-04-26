"""Migration logic tests using a clean in-memory database."""

import pytest
from sqlalchemy import create_engine, inspect, text


@pytest.fixture
def clean_engine():
    """An empty in-memory SQLite engine with no tables."""
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()


@pytest.fixture
def patch_migration_engine(clean_engine, monkeypatch):
    """Make migration functions use the clean test engine."""
    monkeypatch.setattr("app.db.migrations.engine", clean_engine)
    monkeypatch.setattr("app.db.session.engine", clean_engine)
    return clean_engine


class TestEnsurePodcastsCategoryColumn:
    def test_noop_when_table_missing(self, clean_engine, monkeypatch):
        monkeypatch.setattr("app.db.migrations.engine", clean_engine)
        from app.db.migrations import _ensure_podcasts_category_column
        _ensure_podcasts_category_column()


class TestEnsurePodcastsEventKeyColumn:
    def test_noop_when_table_missing(self, clean_engine, monkeypatch):
        monkeypatch.setattr("app.db.migrations.engine", clean_engine)
        from app.db.migrations import _ensure_podcasts_event_key_column
        _ensure_podcasts_event_key_column()

    def test_adds_event_key_to_existing_table(self, clean_engine, monkeypatch):
        monkeypatch.setattr("app.db.migrations.engine", clean_engine)
        from app.db.migrations import _ensure_podcasts_event_key_column
        with clean_engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE podcasts (id INTEGER PRIMARY KEY, title VARCHAR(200))"
            ))
        _ensure_podcasts_event_key_column()
        inspector = inspect(clean_engine)
        columns = {c["name"] for c in inspector.get_columns("podcasts")}
        assert "event_key" in columns

    def test_noop_when_event_key_exists(self, clean_engine, monkeypatch):
        monkeypatch.setattr("app.db.migrations.engine", clean_engine)
        from app.db.migrations import _ensure_podcasts_event_key_column
        with clean_engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE podcasts ("
                "id INTEGER PRIMARY KEY, title VARCHAR(200), "
                "event_key VARCHAR(255) NOT NULL DEFAULT ''"
                ")"
            ))
        _ensure_podcasts_event_key_column()

    def test_adds_category_to_existing_table(self, clean_engine, monkeypatch):
        monkeypatch.setattr("app.db.migrations.engine", clean_engine)
        from app.db.migrations import _ensure_podcasts_category_column
        with clean_engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE podcasts (id INTEGER PRIMARY KEY, title VARCHAR(200))"
            ))
        _ensure_podcasts_category_column()
        inspector = inspect(clean_engine)
        columns = {c["name"] for c in inspector.get_columns("podcasts")}
        assert "category" in columns

    def test_noop_when_category_exists(self, clean_engine, monkeypatch):
        monkeypatch.setattr("app.db.migrations.engine", clean_engine)
        from app.db.migrations import _ensure_podcasts_category_column
        with clean_engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE podcasts ("
                "id INTEGER PRIMARY KEY, title VARCHAR(200), "
                "category VARCHAR(64) NOT NULL DEFAULT 'general'"
                ")"
            ))
        _ensure_podcasts_category_column()


class TestEnsureGenerationTasksTable:
    def test_creates_table_when_missing(self, clean_engine, monkeypatch):
        monkeypatch.setattr("app.db.migrations.engine", clean_engine)
        from app.db.migrations import _ensure_generation_tasks_table
        _ensure_generation_tasks_table()
        inspector = inspect(clean_engine)
        assert "generation_tasks" in inspector.get_table_names()

    def test_noop_when_table_exists(self, clean_engine, monkeypatch):
        monkeypatch.setattr("app.db.migrations.engine", clean_engine)
        from app.db.migrations import _ensure_generation_tasks_table
        _ensure_generation_tasks_table()
        _ensure_generation_tasks_table()

    def test_created_table_has_expected_columns(self, clean_engine, monkeypatch):
        monkeypatch.setattr("app.db.migrations.engine", clean_engine)
        from app.db.migrations import _ensure_generation_tasks_table
        _ensure_generation_tasks_table()
        inspector = inspect(clean_engine)
        columns = {c["name"] for c in inspector.get_columns("generation_tasks")}
        expected = {"task_id", "status", "message", "rss_source",
                    "topic", "logs", "created_at", "updated_at"}
        assert expected.issubset(columns)


class TestEnsureInteractionsColumns:
    def test_noop_when_table_missing(self, clean_engine, monkeypatch):
        monkeypatch.setattr("app.db.migrations.engine", clean_engine)
        from app.db.migrations import _ensure_interactions_columns
        _ensure_interactions_columns()

    def test_adds_missing_columns(self, clean_engine, monkeypatch):
        monkeypatch.setattr("app.db.migrations.engine", clean_engine)
        from app.db.migrations import _ensure_interactions_columns
        with clean_engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE interactions ("
                "id INTEGER PRIMARY KEY, user_id INTEGER, "
                "podcast_id INTEGER, action VARCHAR(32), created_at DATETIME"
                ")"
            ))
        _ensure_interactions_columns()
        inspector = inspect(clean_engine)
        columns = {c["name"] for c in inspector.get_columns("interactions")}
        for col in ("listen_duration_ms", "progress_pct", "session_id",
                    "context_hour", "context_weekday", "context_bucket"):
            assert col in columns, f"Expected column {col} to be added"

    def test_noop_when_columns_exist(self, clean_engine, monkeypatch):
        monkeypatch.setattr("app.db.migrations.engine", clean_engine)
        from app.db.migrations import _ensure_interactions_columns
        with clean_engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE interactions ("
                "id INTEGER PRIMARY KEY, user_id INTEGER, podcast_id INTEGER, "
                "action VARCHAR(32), listen_duration_ms INTEGER, "
                "progress_pct FLOAT, session_id VARCHAR(64), "
                "context_hour INTEGER, context_weekday INTEGER, "
                "context_bucket VARCHAR(32), created_at DATETIME"
                ")"
            ))
        _ensure_interactions_columns()


class TestRunMigrationsIntegration:
    def test_run_migrations_on_clean_db(self, clean_engine, monkeypatch):
        """Full run_migrations should work on a clean database."""
        monkeypatch.setattr("app.db.migrations.engine", clean_engine)
        from app.db.migrations import run_migrations
        run_migrations()
        inspector = inspect(clean_engine)
        tables = set(inspector.get_table_names())
        assert "generation_tasks" in tables
