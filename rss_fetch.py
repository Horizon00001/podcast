import json
import feedparser
import os
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


def _fetch_single_feed(feed_info):
    feed_url = feed_info['url']
    feed_name = feed_info['name']
    feed_id = feed_info['id']

    try:
        d = feedparser.parse(feed_url)

        if d.get('status') == 404:
            return {
                "feed_id": feed_id,
                "feed_name": feed_name,
                "success": False,
                "message": "失败 (404)",
                "feed_data": None,
            }

        feed_data = {
            "id": feed_id,
            "name": feed_name,
            "category": feed_info.get('category', 'general'),
            "last_updated": datetime.now().isoformat(),
            "entries": []
        }

        for entry in d.entries[:20]:
            entry_data = {
                "title": entry.get('title', 'No Title'),
                "link": entry.get('link', ''),
                "published": entry.get('published', entry.get('updated', 'Unknown Date')),
                "summary": entry.get('summary', entry.get('description', ''))
            }
            feed_data['entries'].append(entry_data)

        if not feed_data['entries']:
            return {
                "feed_id": feed_id,
                "feed_name": feed_name,
                "success": False,
                "message": "失败 (无内容)",
                "feed_data": None,
            }

        return {
            "feed_id": feed_id,
            "feed_name": feed_name,
            "success": True,
            "message": "成功",
            "feed_data": feed_data,
        }
    except Exception as e:
        return {
            "feed_id": feed_id,
            "feed_name": feed_name,
            "success": False,
            "message": f"失败 ({e})",
            "feed_data": None,
        }

def fetch_rss_feeds(config_path, output_dir):
    """
    根据配置文件爬取 RSS Feed 并保存结果
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 读取配置文件
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error reading config file: {e}")
        return

    feeds_to_fetch = config.get('feeds', [])
    enabled_feeds = [f for f in feeds_to_fetch if f.get('enabled', False)]
    
    all_fetched_data = []

    if not enabled_feeds:
        output_path = Path(output_dir) / "rss_data.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        return

    for feed_info in enabled_feeds:
        print(f"正在爬取: {feed_info['name']}... 已加入并发队列", flush=True)

    max_workers = min(8, len(enabled_feeds))
    indexed_results = {}
    future_to_index = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for index, feed_info in enumerate(enabled_feeds):
            future = executor.submit(_fetch_single_feed, feed_info)
            future_to_index[future] = index

        for future in as_completed(future_to_index):
            index = future_to_index[future]
            result = future.result()
            indexed_results[index] = result
            print(f"RSS 完成: {result['feed_name']} -> {result['message']}", flush=True)

    for index in range(len(enabled_feeds)):
        result = indexed_results.get(index)
        if result and result['success'] and result['feed_data']:
            all_fetched_data.append(result['feed_data'])

    # 保存所有抓取的数据
    output_path = Path(output_dir) / "rss_data.json"
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_fetched_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

if __name__ == "__main__":
    # 路径配置
    BASE_DIR = Path(__file__).parent
    CONFIG_PATH = BASE_DIR / "config" / "feed.json"
    OUTPUT_DIR = BASE_DIR / "output"
    
    fetch_rss_feeds(CONFIG_PATH, OUTPUT_DIR)
