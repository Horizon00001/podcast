import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import feedparser
import requests


RSS_FETCH_TIMEOUT_SECONDS = 5


def _fetch_single_feed(feed_info):
    feed_url = feed_info["url"]
    feed_name = feed_info["name"]
    feed_id = feed_info["id"]

    try:
        response = requests.get(
            feed_url,
            timeout=RSS_FETCH_TIMEOUT_SECONDS,
            headers={"User-Agent": "PodcastPipeline/1.0"},
        )
        response.raise_for_status()
        d = feedparser.parse(response.content)

        if d.get("status") == 404:
            return {"feed_id": feed_id, "feed_name": feed_name, "success": False, "message": "失败 (404)", "feed_data": None}

        feed_data = {
            "id": feed_id,
            "name": feed_name,
            "category": feed_info.get("category", "general"),
            "last_updated": datetime.now().isoformat(),
            "entries": [],
        }

        for entry in d.entries[:20]:
            feed_data["entries"].append(
                {
                    "title": entry.get("title", "No Title"),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", entry.get("updated", "Unknown Date")),
                    "summary": entry.get("summary", entry.get("description", "")),
                }
            )

        if not feed_data["entries"]:
            return {"feed_id": feed_id, "feed_name": feed_name, "success": False, "message": "失败 (无内容)", "feed_data": None}

        return {"feed_id": feed_id, "feed_name": feed_name, "success": True, "message": "成功", "feed_data": feed_data}
    except requests.Timeout:
        return {
            "feed_id": feed_id,
            "feed_name": feed_name,
            "success": False,
            "message": f"超时跳过 ({RSS_FETCH_TIMEOUT_SECONDS}s)",
            "feed_data": None,
        }
    except Exception as e:
        return {"feed_id": feed_id, "feed_name": feed_name, "success": False, "message": f"失败 ({e})", "feed_data": None}


def fetch_rss_feeds(config_path, output_dir, selected_source_ids=None, extra_feeds=None, log_callback=print):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        log_callback(f"Error reading config file: {e}")
        return

    feeds_to_fetch = config.get("feeds", [])
    if extra_feeds:
        feeds_to_fetch = [*feeds_to_fetch, *extra_feeds]

    if selected_source_ids is not None:
        selected_source_ids = set(selected_source_ids)
        feeds_to_fetch = [f for f in feeds_to_fetch if f.get("id") in selected_source_ids]

    enabled_feeds = [f for f in feeds_to_fetch if f.get("enabled", False)]

    all_fetched_data = []

    if not enabled_feeds:
        log_callback("[RSS Queue] 没有可抓取的 RSS 源")
        output_path = output_dir / "rss_data.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        return

    log_callback(f"[RSS Queue] 本轮计划抓取 {len(enabled_feeds)} 个 RSS 源")
    for feed_info in enabled_feeds:
        log_callback(f"[RSS Source] 排队抓取 {feed_info['name']} ({feed_info['id']})")

    max_workers = min(8, len(enabled_feeds))
    indexed_results = {}
    future_to_index = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for index, feed_info in enumerate(enabled_feeds):
            log_callback(f"[RSS Start] {feed_info['name']} ({feed_info['id']})")
            future = executor.submit(_fetch_single_feed, feed_info)
            future_to_index[future] = index

        for future in as_completed(future_to_index):
            index = future_to_index[future]
            result = future.result()
            indexed_results[index] = result
            log_callback(f"[RSS Done] {result['feed_name']} ({result['feed_id']}) -> {result['message']}")

    for index in range(len(enabled_feeds)):
        result = indexed_results.get(index)
        if result and result["success"] and result["feed_data"]:
            all_fetched_data.append(result["feed_data"])

    output_path = output_dir / "rss_data.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_fetched_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        log_callback(f"Error saving data: {e}")
