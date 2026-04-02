import asyncio
from pathlib import Path

from rss_fetch import fetch_rss_feeds
from generate_text import main as generate_script_main
from tts_synthesize import synthesize_podcast


async def run_pipeline():
    base_dir = Path(__file__).parent
    config_path = base_dir / "config" / "feed.json"
    output_dir = base_dir / "output"
    rss_data_path = output_dir / "rss_data.json"
    script_json_path = output_dir / "podcast_script.json"
    audio_output_dir = output_dir / "audio"

    print("=" * 50)
    print("开始执行播客生成全流程")
    print("=" * 50)

    print("\n[1/3] 抓取 RSS 数据")
    fetch_rss_feeds(config_path, output_dir)
    if not rss_data_path.exists():
        raise FileNotFoundError(f"未生成 RSS 数据文件: {rss_data_path}")

    print("\n[2/3] 生成播客脚本")
    await generate_script_main()
    if not script_json_path.exists():
        raise FileNotFoundError(f"未生成播客脚本文件: {script_json_path}")

    print("\n[3/3] 合成播客音频")
    await synthesize_podcast(str(script_json_path), str(audio_output_dir))

    print("\n" + "=" * 50)
    print("全流程执行完成")
    print(f"RSS 数据: {rss_data_path}")
    print(f"脚本 JSON: {script_json_path}")
    print(f"音频目录: {audio_output_dir}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_pipeline())
