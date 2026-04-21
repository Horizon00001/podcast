import json
from pathlib import Path
from typing import Optional

from app.pipelines.episode_planner import (
    EpisodePlan,
    EpisodeSegment,
    PlannedNewsItem,
    format_plan_for_prompt,
)


def load_episode_plan(episode_plan_path: Path) -> Optional[EpisodePlan]:
    if not episode_plan_path.exists():
        return None

    try:
        with open(episode_plan_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        selected_items = [PlannedNewsItem(**item) for item in raw.get("selected_items", [])]
        segments = [EpisodeSegment(**segment) for segment in raw.get("segments", [])]
        return EpisodePlan(
            topic_id=raw["topic_id"],
            topic_name=raw["topic_name"],
            title_hint=raw["title_hint"],
            theme_statement=raw["theme_statement"],
            audience=raw["audience"],
            editorial_angle=raw["editorial_angle"],
            selected_items=selected_items,
            segments=segments,
            closing_takeaway=raw["closing_takeaway"],
        )
    except Exception as e:
        print(f">>> 警告：读取节目计划失败，将回退到原始新闻内容模式: {e}")
        return None


def build_generation_input(topic: str, rss_data_path: Path, episode_plan_path: Optional[Path] = None) -> str:
    if episode_plan_path:
        plan = load_episode_plan(episode_plan_path)
        if plan is not None:
            return format_plan_for_prompt(plan)

    if not rss_data_path.exists():
        return ""

    with open(rss_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    formatted_news = []
    for feed in data:
        for entry in feed.get("entries", []):
            item_lines = []
            title = (entry.get("title") or "").strip()
            if title:
                item_lines.append(f"标题: {title}")
            summary = entry.get("summary")
            if summary:
                cleaned_summary = summary.strip()
                if cleaned_summary:
                    item_lines.append(f"摘要: {cleaned_summary[:200]}...")
            if item_lines:
                formatted_news.extend(item_lines)
                formatted_news.append("")

    news_content = "\n".join(formatted_news)
    if not news_content:
        return ""
    return f"节目主题: {topic}\n请围绕这个主题组织本期节目，而不是逐条罗列新闻。\n\n原始新闻池:\n{news_content}"
