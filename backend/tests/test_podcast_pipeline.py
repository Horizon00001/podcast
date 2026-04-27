from app.pipelines import podcast_pipeline
import json


def test_summarize_grouped_items_counts_clusters():
    grouped_items = {
        "general": [
            [{"title": "a"}, {"title": "b"}],
            [{"title": "c"}],
        ],
        "business": [
            [{"title": "d"}, {"title": "e"}, {"title": "f"}],
        ],
    }

    summary = podcast_pipeline._summarize_grouped_items(grouped_items)

    assert summary == {
        "category_count": 2,
        "total_clusters": 3,
        "single_item_clusters": 1,
        "multi_item_clusters": 2,
        "processable_clusters": 3,
    }


def test_summarize_grouped_items_handles_empty_input():
    summary = podcast_pipeline._summarize_grouped_items({})

    assert summary == {
        "category_count": 0,
        "total_clusters": 0,
        "single_item_clusters": 0,
        "multi_item_clusters": 0,
        "processable_clusters": 0,
    }


def test_summarize_grouped_items_distinguishes_single_and_multi_clusters():
    grouped_items = {
        "general": [
            [{"title": "a"}],
            [{"title": "b"}, {"title": "c"}],
            [{"title": "d"}],
        ]
    }

    summary = podcast_pipeline._summarize_grouped_items(grouped_items)

    assert summary["single_item_clusters"] == 2
    assert summary["multi_item_clusters"] == 1
    assert summary["processable_clusters"] == 3


def test_average_vectors_returns_mean_vector():
    result = podcast_pipeline._average_vectors([[1.0, 3.0], [3.0, 5.0]])
    assert result == [2.0, 4.0]


def test_group_center_vector_uses_embedding_service(monkeypatch):
    class FakeEmbeddingService:
        def is_enabled(self):
            return True

        def encode_texts(self, texts):
            assert texts == ["AI market", "AI chips"]
            return [[1.0, 0.0], [0.0, 1.0]]

    monkeypatch.setattr(podcast_pipeline, "get_embedding_service", lambda: FakeEmbeddingService())

    result = podcast_pipeline._group_center_vector([
        {"title": "AI", "summary": "market"},
        {"title": "AI", "summary": "chips"},
    ])

    assert result == [0.5, 0.5]


def test_save_generated_podcast_builds_payload_and_returns_success(tmp_path, monkeypatch):
    group_dir = tmp_path / "group"
    audio_dir = group_dir / "audio"
    audio_dir.mkdir(parents=True)
    (audio_dir / "podcast_full.mp3").write_bytes(b"audio")
    (group_dir / "podcast_script.json").write_text(
        json.dumps({"title": "测试播客", "intro": "摘要"}, ensure_ascii=False),
        encoding="utf-8",
    )

    captured = {}

    class FakePodcastService:
        def __init__(self, db):
            self.db = db

        def upsert_podcast(self, payload):
            captured["payload"] = payload
            return "created", type("Podcast", (), {"id": 42})()

    class FakeSession:
        def close(self):
            captured["closed"] = True

    monkeypatch.setattr(podcast_pipeline, "PodcastService", FakePodcastService)
    monkeypatch.setattr(podcast_pipeline, "SessionLocal", lambda: FakeSession())

    status, message = podcast_pipeline._save_generated_podcast(
        group_name="general/test",
        group_dir=group_dir,
        event_key="general:test:1",
        content_vector="[0.1, 0.2]",
    )

    assert status == "created"
    assert "42 - 测试播客" in message
    assert captured["payload"].audio_url == "/audio/podcasts/general/test/audio/podcast_full.mp3"
    assert captured["payload"].script_path == "output/podcasts/general/test/podcast_script.json"
    assert captured["closed"] is True
