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
