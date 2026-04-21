import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.rss_service import RSSService


class TestRSSServiceLoadConfig:
    """Test RSSService.load_config method."""

    def test_load_config(self, tmp_path):
        config_file = tmp_path / "feeds.json"
        config_data = {
            "feeds": [
                {"id": "feed1", "name": "Feed 1", "url": "http://example.com/feed1", "enabled": True, "category": "tech"},
                {"id": "feed2", "name": "Feed 2", "url": "http://example.com/feed2", "enabled": False, "category": "business"},
            ]
        }
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        service = RSSService(config_path=config_file, output_dir=tmp_path / "output")
        result = service.load_config()

        assert len(result) == 2
        assert result[0]["id"] == "feed1"
        assert result[1]["id"] == "feed2"


class TestRSSServiceSaveRSSData:
    """Test RSSService.save_rss_data method."""

    def test_save_rss_data(self, tmp_path):
        service = RSSService(config_path=tmp_path / "feeds.json", output_dir=tmp_path / "output")

        data = [
            {
                "id": "feed1",
                "name": "AI News",
                "category": "tech",
                "last_updated": "2024-01-01",
                "entries": [
                    {"title": "AI Model Released", "link": "http://example.com/1", "published": "2024-01-01", "summary": "New AI model"},
                ],
            }
        ]

        result_path = service.save_rss_data(data)

        assert result_path.exists()
        loaded = json.loads(result_path.read_text(encoding="utf-8"))
        assert loaded[0]["id"] == "feed1"
        assert len(loaded[0]["entries"]) == 1


class TestRSSServiceLoadRSSNews:
    """Test RSSService.load_rss_news method."""

    def test_load_rss_news_basic(self, tmp_path):
        rss_data_file = tmp_path / "rss_data.json"
        rss_data = [
            {
                "id": "feed1",
                "name": "AI News",
                "category": "tech",
                "entries": [
                    {
                        "title": "AI Model Released",
                        "link": "http://example.com/1",
                        "published": "2024-01-01",
                        "summary": "<p>New AI model announced</p>",
                    },
                ],
            }
        ]
        rss_data_file.write_text(json.dumps(rss_data), encoding="utf-8")

        service = RSSService(config_path=tmp_path / "feeds.json", output_dir=tmp_path)
        result = service.load_rss_news(rss_data_file)

        assert "AI Model Released" in result
        assert "标题:" in result
        assert "<p>" not in result  # HTML should be stripped

    def test_load_rss_news_file_not_exists(self, tmp_path):
        service = RSSService(config_path=tmp_path / "feeds.json", output_dir=tmp_path)
        result = service.load_rss_news(tmp_path / "nonexistent.json")

        assert result == ""

    def test_load_rss_news_no_entries(self, tmp_path):
        rss_data_file = tmp_path / "rss_data.json"
        rss_data = [{"id": "feed1", "name": "Empty Feed", "category": "tech", "entries": []}]
        rss_data_file.write_text(json.dumps(rss_data), encoding="utf-8")

        service = RSSService(config_path=tmp_path / "feeds.json", output_dir=tmp_path)
        result = service.load_rss_news(rss_data_file)

        assert result == ""


class TestRSSServiceFetchAndSave:
    """Test RSSService.fetch_and_save method."""

    def test_fetch_and_save_returns_path(self, tmp_path):
        # Create a minimal config
        config_file = tmp_path / "feeds.json"
        config_data = {
            "feeds": [
                {"id": "test", "name": "Test", "url": "http://example.com/rss", "enabled": True, "category": "tech"},
            ]
        }
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        service = RSSService(config_path=config_file, output_dir=tmp_path / "output")

        # Mock feedparser.parse to avoid real network calls
        mock_feed = MagicMock()
        mock_feed.get.return_value = 200
        mock_feed.entries = []

        with patch("feedparser.parse", return_value=mock_feed):
            result = service.fetch_and_save()

        assert isinstance(result, Path)


class TestRSSServiceInitialization:
    """Test RSSService initialization."""

    def test_init_creates_output_dir(self, tmp_path):
        output_dir = tmp_path / "output"
        service = RSSService(config_path=tmp_path / "feeds.json", output_dir=output_dir)

        assert output_dir.exists()
