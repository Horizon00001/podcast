"""
集成测试：CLI 命令路由
验证子命令能正确分发到对应实现。
"""

import asyncio as py_asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import app.cli as cli


class TestPodcastBackendCLI:
    """Podcast backend CLI 集成测试."""

    def test_fetch_rss_command_dispatches_to_pipeline(self, monkeypatch, tmp_path):
        """测试 fetch-rss 子命令能调用 RSS 抓取实现。"""
        captured = {}

        def fake_fetch_rss_feeds(config_path, output_dir):
            captured["config_path"] = config_path
            captured["output_dir"] = output_dir

        monkeypatch.setattr(cli, "fetch_rss_feeds", fake_fetch_rss_feeds)

        cli.main([
            "fetch-rss",
            "--config-path",
            str(tmp_path / "feed.json"),
            "--output-dir",
            str(tmp_path / "rss-output"),
        ])

        assert captured["config_path"] == tmp_path / "feed.json"
        assert captured["output_dir"] == tmp_path / "rss-output"

    def test_generate_text_command_dispatches_async_flow(self, monkeypatch, tmp_path):
        """测试 generate-text 子命令会进入异步脚本生成流程。"""
        captured = {}

        async def fake_generate_text_command(*, topic, episode_plan_path, rss_data_path, output_dir):
            captured["topic"] = topic
            captured["episode_plan_path"] = episode_plan_path
            captured["rss_data_path"] = rss_data_path
            captured["output_dir"] = output_dir

        monkeypatch.setattr(cli, "generate_text_command", fake_generate_text_command)
        monkeypatch.setattr(cli.asyncio, "run", py_asyncio.run)

        cli.main([
            "generate-text",
            "--topic",
            "tech",
            "--episode-plan-path",
            str(tmp_path / "episode_plan.json"),
            "--rss-data-path",
            str(tmp_path / "rss_data.json"),
            "--output-dir",
            str(tmp_path / "generated"),
        ])

        assert captured["topic"] == "tech"
        assert captured["episode_plan_path"] == tmp_path / "episode_plan.json"
        assert captured["rss_data_path"] == tmp_path / "rss_data.json"
        assert captured["output_dir"] == tmp_path / "generated"

    def test_synthesize_tts_command_dispatches_async_flow(self, monkeypatch, tmp_path):
        """测试 synthesize-tts 子命令会进入异步合成流程。"""
        captured = {}

        async def fake_synthesize_tts_command(json_path, output_dir):
            captured["json_path"] = json_path
            captured["output_dir"] = output_dir

        monkeypatch.setattr(cli, "synthesize_tts_command", fake_synthesize_tts_command)
        monkeypatch.setattr(cli.asyncio, "run", py_asyncio.run)

        cli.main([
            "synthesize-tts",
            "--json-path",
            str(tmp_path / "podcast_script.json"),
            "--output-dir",
            str(tmp_path / "audio-output"),
        ])

        assert captured["json_path"] == tmp_path / "podcast_script.json"
        assert captured["output_dir"] == tmp_path / "audio-output"
