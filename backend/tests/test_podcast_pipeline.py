from app.pipelines import podcast_pipeline


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
    }


def test_summarize_grouped_items_handles_empty_input():
    summary = podcast_pipeline._summarize_grouped_items({})

    assert summary == {
        "category_count": 0,
        "total_clusters": 0,
        "single_item_clusters": 0,
        "multi_item_clusters": 0,
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
