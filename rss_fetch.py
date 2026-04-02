import json
import feedparser
import os
from pathlib import Path
from datetime import datetime

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
    
    for feed_info in enabled_feeds:
        feed_url = feed_info['url']
        feed_name = feed_info['name']
        feed_id = feed_info['id']
        
        print(f"正在爬取: {feed_name}...", end=" ", flush=True)
        
        try:
            # 解析 RSS
            d = feedparser.parse(feed_url)
            
            if d.get('status') == 404:
                print("失败 (404)")
                continue
            
            feed_data = {
                "id": feed_id,
                "name": feed_name,
                "category": feed_info.get('category', 'general'),
                "last_updated": datetime.now().isoformat(),
                "entries": []
            }
            
            # 提取前 5 条内容
            for entry in d.entries[:5]:
                entry_data = {
                    "title": entry.get('title', 'No Title'),
                    "link": entry.get('link', ''),
                    "published": entry.get('published', entry.get('updated', 'Unknown Date')),
                    "summary": entry.get('summary', entry.get('description', ''))
                }
                feed_data['entries'].append(entry_data)
            
            if not feed_data['entries']:
                print("失败 (无内容)")
                continue

            all_fetched_data.append(feed_data)
            print("成功")

        except Exception as e:
            print(f"失败 ({e})")

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
