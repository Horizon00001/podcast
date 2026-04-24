"""Pipeline unit tests — RSS, text generation, episode planning."""

import json
from pathlib import Path

from app.pipelines.rss_pipeline import _fetch_single_feed, fetch_rss_feeds
from app.pipelines.generate_text_pipeline import (
    build_generation_input,
    load_episode_plan,
)
from app.pipelines.episode_planner import (
    EpisodePlan,
    EpisodeSegment,
    PlannedNewsItem,
    format_plan_for_prompt,
)


class FakeFeedParserResult:
    """Mimics feedparser result: supports both dict .get() and attribute .entries."""

    def __init__(self, status=200, entries=None):
        self._status = status
        self.entries = entries or []

    def get(self, key, default=None):
        if key == "status":
            return self._status
        return default


def _fake_entry(title="T", link="http://x", published="2024-01-01", summary="S"):
    return {
        "title": title,
        "link": link,
        "published": published,
        "summary": summary,
    }


class TestFetchSingleFeed:
    def test_fetch_single_feed_success(self, monkeypatch):
        result_obj = FakeFeedParserResult(entries=[
            _fake_entry("Test Article", "https://example.com/1",
                        "Mon, 01 Jan 2024", "A test summary"),
        ])
        monkeypatch.setattr("feedparser.parse", lambda url: result_obj)

        result = _fetch_single_feed({
            "id": "test", "name": "Test Feed",
            "url": "https://example.com/rss", "category": "tech",
        })
        assert result["success"] is True
        assert result["feed_data"]["name"] == "Test Feed"
        assert len(result["feed_data"]["entries"]) == 1
        assert result["feed_data"]["entries"][0]["title"] == "Test Article"

    def test_fetch_single_feed_404(self, monkeypatch):
        monkeypatch.setattr("feedparser.parse", lambda url: FakeFeedParserResult(status=404))
        result = _fetch_single_feed({
            "id": "dead", "name": "Dead Feed",
            "url": "https://example.com/dead",
        })
        assert result["success"] is False
        assert "404" in result["message"]

    def test_fetch_single_feed_empty(self, monkeypatch):
        monkeypatch.setattr("feedparser.parse", lambda url: FakeFeedParserResult(entries=[]))
        result = _fetch_single_feed({
            "id": "empty", "name": "Empty Feed",
            "url": "https://example.com/empty",
        })
        assert result["success"] is False
        assert "无内容" in result["message"]

    def test_fetch_single_feed_exception(self, monkeypatch):
        def raise_error(url):
            raise RuntimeError("Network error")
        monkeypatch.setattr("feedparser.parse", raise_error)
        result = _fetch_single_feed({
            "id": "err", "name": "Error Feed",
            "url": "https://example.com/err",
        })
        assert result["success"] is False
        assert "Network error" in result["message"]

    def test_fetch_entries_up_to_20(self, monkeypatch):
        result_obj = FakeFeedParserResult(entries=[
            _fake_entry(f"Item {i}", f"http://x/{i}")
            for i in range(25)
        ])
        monkeypatch.setattr("feedparser.parse", lambda url: result_obj)
        result = _fetch_single_feed({
            "id": "many", "name": "Many", "url": "http://x/rss",
        })
        assert len(result["feed_data"]["entries"]) == 20


class TestFetchRSSFeeds:
    def test_fetch_rss_feeds_writes_output(self, tmp_path, monkeypatch):
        config = {"feeds": [
            {"id": "f1", "name": "Feed 1", "url": "http://x/rss", "enabled": True},
        ]}
        config_path = tmp_path / "feed.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False))
        output_dir = tmp_path / "output"

        monkeypatch.setattr("feedparser.parse",
                            lambda url: FakeFeedParserResult(
                                entries=[_fake_entry("News")]))

        fetch_rss_feeds(str(config_path), str(output_dir))
        rss_path = output_dir / "rss_data.json"
        assert rss_path.exists()
        data = json.loads(rss_path.read_text())
        assert len(data) == 1
        assert data[0]["name"] == "Feed 1"

    def test_fetch_rss_feeds_only_enabled(self, tmp_path, monkeypatch):
        config = {"feeds": [
            {"id": "f1", "name": "Enabled", "url": "http://x/rss", "enabled": True},
            {"id": "f2", "name": "Disabled", "url": "http://y/rss", "enabled": False},
        ]}
        config_path = tmp_path / "feed.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False))
        output_dir = tmp_path / "output"

        call_count = [0]
        def fake_parse(url):
            call_count[0] += 1
            return FakeFeedParserResult(entries=[_fake_entry("T")])

        monkeypatch.setattr("feedparser.parse", fake_parse)
        fetch_rss_feeds(str(config_path), str(output_dir))
        assert call_count[0] == 1

    def test_fetch_rss_feeds_no_enabled(self, tmp_path, monkeypatch):
        config = {"feeds": [
            {"id": "f1", "name": "Off", "url": "http://x/rss", "enabled": False},
        ]}
        config_path = tmp_path / "feed.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False))
        output_dir = tmp_path / "output"

        fetch_rss_feeds(str(config_path), str(output_dir))
        rss_path = output_dir / "rss_data.json"
        assert json.loads(rss_path.read_text()) == []


class TestLoadEpisodePlan:
    def test_load_valid_plan(self, tmp_path):
        plan_data = {
            "topic_id": "daily-news",
            "topic_name": "Daily News",
            "title_hint": "Today's Headlines",
            "theme_statement": "Theme",
            "audience": "General",
            "editorial_angle": "Neutral",
            "selected_items": [
                {"item_id": "1", "feed_id": "f1", "feed_name": "Feed",
                 "category": "tech", "title": "Article",
                 "summary": "Summary", "published": "2024-01-01",
                 "link": "http://x", "score": 1.0, "selection_reason": "hot"},
            ],
            "segments": [
                {"segment_type": "opening", "purpose": "Intro",
                 "item_refs": [], "segment_thesis": "Welcome"},
            ],
            "closing_takeaway": "Goodbye",
        }
        plan_path = tmp_path / "episode_plan.json"
        plan_path.write_text(json.dumps(plan_data, ensure_ascii=False))

        plan = load_episode_plan(plan_path)
        assert plan is not None
        assert plan.topic_id == "daily-news"
        assert len(plan.selected_items) == 1
        assert isinstance(plan.selected_items[0], PlannedNewsItem)
        assert isinstance(plan.segments[0], EpisodeSegment)

    def test_load_missing_file(self, tmp_path):
        plan = load_episode_plan(tmp_path / "nonexistent.json")
        assert plan is None

    def test_load_invalid_json(self, tmp_path):
        plan_path = tmp_path / "bad.json"
        plan_path.write_text("not json")
        plan = load_episode_plan(plan_path)
        assert plan is None


class TestBuildGenerationInput:
    def test_with_episode_plan(self, tmp_path):
        plan_data = {
            "topic_id": "tech", "topic_name": "Tech News",
            "title_hint": "Title", "theme_statement": "Theme",
            "audience": "Devs", "editorial_angle": "Neutral",
            "selected_items": [
                {"item_id": "1", "feed_id": "f1", "feed_name": "F",
                 "category": "tech", "title": "AI News",
                 "summary": "Something", "published": "2024-01-01",
                 "link": "http://x", "score": 1.0, "selection_reason": "hot"},
            ],
            "segments": [
                {"segment_type": "main_content", "purpose": "Main",
                 "item_refs": ["1"], "segment_thesis": "AI is growing"},
            ],
            "closing_takeaway": "Stay informed",
        }
        plan_path = tmp_path / "plan.json"
        plan_path.write_text(json.dumps(plan_data, ensure_ascii=False))

        result = build_generation_input("tech", tmp_path / "rss.json", plan_path)
        assert "Tech News" in result
        assert "AI is growing" in result

    def test_fallback_to_rss_data(self, tmp_path):
        rss_data = [{
            "id": "f1", "name": "Feed",
            "entries": [
                {"title": "News", "link": "http://x",
                 "published": "2024", "summary": "Summary text here"},
            ],
        }]
        rss_path = tmp_path / "rss_data.json"
        rss_path.write_text(json.dumps(rss_data, ensure_ascii=False))

        result = build_generation_input("tech", rss_path)
        assert "节目主题: tech" in result
        assert "标题: News" in result
        assert "摘要" in result

    def test_fallback_missing_rss_data(self, tmp_path):
        result = build_generation_input("tech", tmp_path / "missing.json")
        assert result == ""

    def test_fallback_empty_rss_entries(self, tmp_path):
        rss_path = tmp_path / "rss.json"
        rss_path.write_text(json.dumps([{"id": "f1", "name": "F", "entries": []}]))
        result = build_generation_input("tech", rss_path)
        assert result == ""

    def test_plan_load_failure_falls_back(self, tmp_path):
        plan_path = tmp_path / "bad_plan.json"
        plan_path.write_text("invalid json {{{")
        rss_data = [{
            "id": "f1", "name": "F",
            "entries": [{"title": "T", "link": "http://x",
                         "published": "2024", "summary": "S"}],
        }]
        rss_path = tmp_path / "rss.json"
        rss_path.write_text(json.dumps(rss_data, ensure_ascii=False))

        result = build_generation_input("tech", rss_path, plan_path)
        assert "标题: T" in result


class TestFormatPlanForPrompt:
    def test_basic_format(self):
        plan = EpisodePlan(
            topic_id="tech",
            topic_name="Tech News",
            title_hint="Today's Tech",
            theme_statement="The latest in tech",
            audience="Developers",
            editorial_angle="Technical deep-dive",
            selected_items=[
                PlannedNewsItem(
                    item_id="1", feed_id="f1", feed_name="Feed",
                    category="tech", title="AI breakthrough",
                    summary="Details", published="2024-01-01",
                    link="http://x", score=0.95, selection_reason="hot topic",
                ),
            ],
            segments=[
                EpisodeSegment(
                    segment_type="main_content", purpose="Main content",
                    item_refs=["1"], segment_thesis="AI is evolving fast",
                ),
            ],
            closing_takeaway="Stay tuned",
        )
        output = format_plan_for_prompt(plan)
        assert "Tech News" in output
        assert "AI breakthrough" in output
        assert "Developers" in output
