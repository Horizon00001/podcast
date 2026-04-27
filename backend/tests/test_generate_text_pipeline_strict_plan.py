import json

from app.pipelines.generate_text_pipeline import build_generation_input


def test_build_generation_input_requires_valid_episode_plan_when_path_provided(tmp_path):
    plan_path = tmp_path / "bad_plan.json"
    plan_path.write_text("invalid json {{{")
    rss_data = [{
        "id": "f1",
        "name": "Feed",
        "entries": [
            {"title": "News", "link": "http://x", "published": "2024", "summary": "Summary"},
        ],
    }]
    rss_path = tmp_path / "rss_data.json"
    rss_path.write_text(json.dumps(rss_data, ensure_ascii=False))

    result = build_generation_input("general", rss_path, plan_path)

    assert result == ""
