import json

from app.pipelines.generate_text_pipeline import build_generation_input


def test_build_generation_input_from_cluster_items():
    cluster_items = [
        {
            "title": "AI startup raises funding",
            "summary": "The company raised a new round to expand its developer tooling.",
            "feed_name": "Tech News",
            "published": "2026-04-27",
            "link": "https://example.com/ai-startup",
        },
        {
            "title": "Another AI tooling company launches agent platform",
            "summary": "The launch focuses on enterprise workflow automation.",
            "feed_name": "Industry Daily",
            "published": "2026-04-27",
            "link": "https://example.com/agent-platform",
        },
    ]

    result = build_generation_input("AI tooling", cluster_items=cluster_items)

    assert "节目主题: AI tooling" in result
    assert "同一组 embedding 聚类得到的新闻素材" in result
    assert "标题: AI startup raises funding" in result
    assert "来源: Tech News" in result
    assert "不要机械地逐条罗列" in result


def test_build_generation_input_from_rss_file(tmp_path):
    rss_data = [{
        "id": "f1",
        "name": "Feed",
        "entries": [
            {"title": "News", "link": "http://x", "published": "2024", "summary": "Summary text here"},
        ],
    }]
    rss_path = tmp_path / "rss_data.json"
    rss_path.write_text(json.dumps(rss_data, ensure_ascii=False))

    result = build_generation_input("tech", rss_path)

    assert "节目主题: tech" in result
    assert "标题: News" in result
    assert "原始新闻池" in result


def test_build_generation_input_returns_empty_for_missing_rss(tmp_path):
    result = build_generation_input("tech", tmp_path / "missing.json")
    assert result == ""


def test_build_generation_input_returns_empty_for_empty_cluster():
    result = build_generation_input("tech", cluster_items=[])
    assert result == ""
