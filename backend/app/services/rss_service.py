import json
import re
import warnings
from datetime import datetime, timezone
from pathlib import Path as Path

import feedparser

warnings.filterwarnings("ignore", category=DeprecationWarning, module="feedparser")


class RSSService:
    def __init__(self, config_path: str | Path, output_dir: str | Path):
        self.config_path = Path(config_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> list[dict]:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f).get("feeds", [])

    def fetch_feeds(self) -> list[dict]:
        feeds = self.load_config()
        enabled_feeds = [f for f in feeds if f.get("enabled", False)]

        all_fetched_data = []
        for feed_info in enabled_feeds:
            feed_url = feed_info["url"]
            feed_name = feed_info["name"]
            feed_id = feed_info["id"]

            d = feedparser.parse(feed_url)
            if d.get("status") == 404:
                continue

            feed_data = {
                "id": feed_id,
                "name": feed_name,
                "category": feed_info.get("category", "general"),
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "entries": [],
            }

            for entry in d.entries[:5]:
                feed_data["entries"].append({
                    "title": entry.get("title", "No Title"),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", entry.get("updated", "Unknown Date")),
                    "summary": entry.get("summary", entry.get("description", "")),
                })

            if feed_data["entries"]:
                all_fetched_data.append(feed_data)

        return all_fetched_data

    def save_rss_data(self, data: list[dict]) -> Path:
        output_path = self.output_dir / "rss_data.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return output_path

    def fetch_and_save(self) -> Path:
        data = self.fetch_feeds()
        return self.save_rss_data(data)

    def load_rss_news(self, rss_data_path: Path | None = None) -> str:
        if rss_data_path is None:
            rss_data_path = self.output_dir / "rss_data.json"

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
                    cleaned_summary = re.sub("<[^<]+?>", "", summary).strip()
                    if cleaned_summary:
                        item_lines.append(f"摘要: {cleaned_summary[:200]}...")
                if item_lines:
                    formatted_news.extend(item_lines)
                    formatted_news.append("")

        return "\n".join(formatted_news)
