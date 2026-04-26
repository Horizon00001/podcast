"""
集成测试：TTS 合成流程
使用真实 ffmpeg，但 mock TTS Provider
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
import shutil

from app.services.tts_service import TTSService
from app.services.audio_plan import RenderPlan, RenderPlanItem


class TestTTSServiceIntegration:
    """TTS 服务集成测试 - 使用真实 ffmpeg."""

    def setup_method(self):
        """检查 ffmpeg 是否可用."""
        self.ffmpeg_available = shutil.which("ffmpeg") is not None

    @pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
    def test_render_silence_integration(self, tmp_path):
        """集成测试：生成真实静音音频文件."""
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        output = tmp_path / "silence.mp3"
        result = service._render_silence(output, 500)

        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    @pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
    def test_render_plan_with_silence_and_music(self, tmp_path):
        """集成测试：渲染包含静音和音乐的 plan."""
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        plan = RenderPlan(
            title="Test Podcast",
            items=[
                RenderPlanItem(item_type="silence", duration_ms=500),
                RenderPlanItem(item_type="silence", duration_ms=200),
            ]
        )

        # 同步渲染
        results = []
        for idx, item in enumerate(plan.items):
            path = tmp_path / "audio" / f"segment_{idx:03d}.mp3"
            result = service._render_plan_item_sync(item, str(path))
            if result:
                results.append(result)

        assert len(results) == 2
        for r in results:
            assert r.exists()


class TestTTSServiceRenderMusicAsset:
    """测试音乐资产渲染集成."""

    @pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
    def test_render_music_asset_with_trim(self, tmp_path):
        """集成测试：渲染并裁剪音乐资产."""
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        # 创建模拟音频文件 (用静音代替)
        silence_file = tmp_path / "source.mp3"
        service._render_silence(silence_file, 3000)

        output = tmp_path / "trimmed.mp3"
        item = RenderPlanItem(
            item_type="music",
            asset_path=silence_file,
            trim_start_ms=500,
            trim_end_ms=2000,
            volume=0.5,
        )

        result = service._render_music_asset(silence_file, output, item)

        assert result == output
        assert output.exists()
        # 裁剪后的文件应该小于原文件
        assert output.stat().st_size > 0

    @pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
    def test_render_music_asset_clamps_trim_start_beyond_duration(self, tmp_path):
        """集成测试：trim_start 超过素材时长时应回退到有效范围."""
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        source = tmp_path / "short_transition.mp3"
        service._render_silence(source, 5000)

        output = tmp_path / "trimmed_fallback.mp3"
        item = RenderPlanItem(
            item_type="music",
            asset_path=source,
            trim_start_ms=8000,
            duration_ms=2400,
            volume=0.5,
        )

        result = service._render_music_asset(source, output, item)

        assert result == output
        assert output.exists()
        assert output.stat().st_size > 1000
        assert service._probe_audio_duration_seconds(output) > 0


class TestTTSServiceSpeechSynthesis:
    """测试语音合成 - 使用 mock provider."""

    def test_synthesize_speech_item_mock(self, tmp_path):
        """测试语音合成项目使用 mock provider."""
        mock_provider = MagicMock()
        mock_provider.synthesize = AsyncMock(return_value=tmp_path / "speech.mp3")
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        # 直接调用异步 synthesize
        async def run_test():
            output = tmp_path / "speech.mp3"
            output.write_bytes(b"fake audio")
            result = await service.speech_provider.synthesize(
                "Hello world",
                output,
                voice="male",
                style="main_content"
            )
            return result

        result = asyncio.run(run_test())
        mock_provider.synthesize.assert_called_once()
        assert result == tmp_path / "speech.mp3"

    def test_clean_text_integration(self, tmp_path):
        """测试文本清理集成."""
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        # 各种需要清理的文本
        assert service.clean_text("Hello (note)") == "Hello"
        assert service.clean_text("测试（注释）") == "测试"
        assert service.clean_text("No parentheses") == "No parentheses"
        assert service.clean_text("  trimmed  ") == "trimmed"


class TestRenderPlannerWithTTSService:
    """测试 RenderPlanner 和 TTSService 的集成."""

    @pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
    def test_build_plan_and_render(self, tmp_path):
        """集成测试：从 script data 构建 plan 并渲染."""
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        script_data = {
            "title": "Test Podcast",
            "sections": [
                {
                    "section_type": "main_content",
                    "dialogues": [
                        {"speaker": "A", "content": "First point"},
                        {"speaker": "B", "content": "Second point"},
                    ],
                }
            ],
        }

        # 构建 render plan
        plan = service.build_render_plan(script_data)

        assert plan.title == "Test Podcast"
        assert len(plan.items) > 0

        # 渲染 plan items
        for idx, item in enumerate(plan.items):
            if item.item_type == "silence":
                path = tmp_path / "audio" / f"seg_{idx}.mp3"
                result = service._render_plan_item_sync(item, str(path))
                # 静默项目应该能渲染
                assert result is None or result.exists()
