import json
from pathlib import Path
from typing import Iterable


def _format_cluster_items(cluster_items: Iterable[dict]) -> str:
    formatted_news = []
    for item in cluster_items:
        item_lines = []
        title = (item.get("title") or "").strip()
        if title:
            item_lines.append(f"标题: {title}")
        summary = (item.get("summary") or "").strip()
        if summary:
            item_lines.append(f"摘要: {summary[:400]}")
        feed_name = (item.get("feed_name") or "").strip()
        if feed_name:
            item_lines.append(f"来源: {feed_name}")
        published = (item.get("published") or "").strip()
        if published:
            item_lines.append(f"发布时间: {published}")
        link = (item.get("link") or "").strip()
        if link:
            item_lines.append(f"链接: {link}")
        if item_lines:
            formatted_news.extend(item_lines)
            formatted_news.append("")
    return "\n".join(formatted_news).strip()


def build_generation_input(topic: str, rss_data_path: Path | None = None, cluster_items: list[dict] | None = None) -> str:
    if cluster_items is not None:
        news_content = _format_cluster_items(cluster_items)
        if not news_content:
            return ""
        return (
            f"节目主题: {topic}\n"
            "下面是同一组 embedding 聚类得到的新闻素材。请你自己判断它们的共同主线，"
            "决定本期节目的最佳结构和转场，不要机械地逐条罗列，也不要假设第一条一定是主线。"
            "如果某条素材更像导读、合集或背景补充，可以降低它的权重。\n\n"
            f"候选新闻组:\n{news_content}"
        )

    if rss_data_path is None or not rss_data_path.exists():
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
