from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.core.config import settings
from app.pipelines.generate_text_pipeline import build_generation_input
from app.pipelines.rss_pipeline import fetch_rss_feeds
from app.pipelines.podcast_pipeline import run_pipeline
from app.services.script_service import ScriptService
from app.services.tts_service import TTSService


def _default_output_dir() -> Path:
    return settings.output_dir


async def run_pipeline_command(topic: str) -> None:
    await run_pipeline(topic=topic)


def fetch_rss_command(config_path: Path | None = None, output_dir: Path | None = None) -> None:
    fetch_rss_feeds(config_path or settings.feed_config_path, output_dir or _default_output_dir())


async def generate_text_command(
    topic: str = "daily-news",
    episode_plan_path: Path | None = None,
    rss_data_path: Path | None = None,
    output_dir: Path | None = None,
) -> None:
    output_dir = output_dir or _default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    rss_data_path = rss_data_path or (output_dir / "rss_data.json")
    episode_plan_path = episode_plan_path or (output_dir / "episode_plan.json")
    script_service = ScriptService(project_root=settings.project_root, output_dir=output_dir)
    news_content = build_generation_input(topic, rss_data_path, episode_plan_path)
    if not news_content:
        print(">>> 错误：未获取到有效的新闻内容，请先运行 `python -m app.cli fetch-rss`")
        return
    await script_service.generate_and_save_streaming_sections(news_content)


async def synthesize_tts_command(json_path: Path | str, output_dir: Path | str) -> None:
    service = TTSService(output_dir)
    await service.synthesize_podcast(json_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Podcast backend CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_pipeline_parser = subparsers.add_parser("run-pipeline", help="Run the full podcast pipeline")
    run_pipeline_parser.add_argument("--topic", default="daily-news", help="Episode topic profile id or custom topic")

    fetch_rss_parser = subparsers.add_parser("fetch-rss", help="Fetch RSS feeds into rss_data.json")
    fetch_rss_parser.add_argument("--config-path", type=Path, default=None, help="Path to feed config JSON")
    fetch_rss_parser.add_argument("--output-dir", type=Path, default=None, help="Directory for generated RSS data")

    generate_text_parser = subparsers.add_parser("generate-text", help="Generate podcast script from RSS data")
    generate_text_parser.add_argument("--topic", default="daily-news", help="Episode topic or profile id")
    generate_text_parser.add_argument("--episode-plan-path", type=Path, default=None, help="Path to episode plan JSON")
    generate_text_parser.add_argument("--rss-data-path", type=Path, default=None, help="Path to rss_data.json")
    generate_text_parser.add_argument("--output-dir", type=Path, default=None, help="Directory for generated script files")

    synthesize_tts_parser = subparsers.add_parser("synthesize-tts", help="Synthesize podcast audio from script JSON")
    synthesize_tts_parser.add_argument("--json-path", type=Path, default=Path("output/podcast_script.json"), help="Path to podcast script JSON")
    synthesize_tts_parser.add_argument("--output-dir", type=Path, default=Path("output"), help="Directory for generated audio")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run-pipeline":
        asyncio.run(run_pipeline_command(args.topic))
        return

    if args.command == "fetch-rss":
        fetch_rss_command(args.config_path, args.output_dir)
        return

    if args.command == "generate-text":
        asyncio.run(
            generate_text_command(
                topic=args.topic,
                episode_plan_path=args.episode_plan_path,
                rss_data_path=args.rss_data_path,
                output_dir=args.output_dir,
            )
        )
        return

    if args.command == "synthesize-tts":
        asyncio.run(synthesize_tts_command(args.json_path, args.output_dir))
        return
