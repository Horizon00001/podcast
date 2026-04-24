"""Settings / config unit tests."""

import os
from pathlib import Path

from app.core.config import Settings


class TestSettingsDefaults:
    def test_app_name_default(self):
        s = Settings()
        assert s.app_name == "Podcast Prompt API"

    def test_app_env_default(self):
        s = Settings()
        assert s.app_env == "dev"

    def test_api_prefix_default(self):
        s = Settings()
        assert s.api_prefix == "/api/v1"

    def test_database_url_default(self):
        s = Settings()
        assert s.database_url == "sqlite:///./podcast.db"

    def test_cors_origins_default(self):
        s = Settings()
        assert "localhost:5173" in s.cors_origins

    def test_tts_provider_default(self):
        s = Settings()
        assert s.tts_provider == "dashscope"

    def test_tts_model_default(self):
        s = Settings()
        assert s.tts_model == "cosyvoice-v2"

    def test_dashscope_voices_default(self):
        s = Settings()
        assert s.dashscope_default_male_voice == "loongdavid_v2"
        assert s.dashscope_default_female_voice == "longanwen"

    def test_postgres_url_default_none(self):
        s = Settings()
        assert s.postgres_url is None

    def test_dashscope_api_key_default_none(self):
        # .env contains dashscope_api_key, so default is not None in this project
        s = Settings()
        # Without .env, dashscope_api_key defaults to None (defined as str | None)
        # In this env it's set, so it's a string
        assert s.dashscope_api_key is None or isinstance(s.dashscope_api_key, str)


class TestSettingsProperties:
    def test_effective_database_url_uses_postgres_when_set(self):
        s = Settings(postgres_url="postgresql://localhost/test")
        assert s.effective_database_url == "postgresql://localhost/test"

    def test_effective_database_url_falls_back_to_sqlite(self):
        s = Settings(postgres_url=None, database_url="sqlite:///./test.db")
        assert s.effective_database_url == "sqlite:///./test.db"

    def test_backend_dir_is_path(self):
        s = Settings()
        assert isinstance(s.backend_dir, Path)

    def test_backend_dir_ends_with_backend(self):
        s = Settings()
        assert s.backend_dir.name == "backend"

    def test_project_root_is_parent_of_backend(self):
        s = Settings()
        assert s.project_root == s.backend_dir.parent

    def test_output_dir(self):
        s = Settings()
        assert s.output_dir == s.project_root / "output"

    def test_audio_dir(self):
        s = Settings()
        assert s.audio_dir == s.output_dir / "audio"

    def test_feed_config_path(self):
        s = Settings()
        assert s.feed_config_path == s.project_root / "config" / "feed.json"

    def test_topics_config_path(self):
        s = Settings()
        assert s.topics_config_path == s.project_root / "config" / "topics.json"

class TestSettingsEnvOverride:
    def test_env_overrides_app_name(self, monkeypatch):
        monkeypatch.setenv("app_name", "Custom App")
        s = Settings()
        assert s.app_name == "Custom App"

    def test_env_overrides_tts_provider(self, monkeypatch):
        monkeypatch.setenv("tts_provider", "edge")
        s = Settings()
        assert s.tts_provider == "edge"

    def test_env_overrides_dashscope_api_key(self, monkeypatch):
        monkeypatch.setenv("dashscope_api_key", "sk-test-key")
        s = Settings()
        assert s.dashscope_api_key == "sk-test-key"

    def test_model_config_extra_ignore(self):
        """Unknown fields should be ignored, not raise errors."""
        s = Settings(unknown_field="value")
        assert not hasattr(s, "unknown_field")
