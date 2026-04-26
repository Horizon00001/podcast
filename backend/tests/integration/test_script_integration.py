"""
集成测试：脚本生成服务
Mock pydantic-ai Agent，测试完整流程
"""
import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
import types

from app.services.script_service import ScriptService
from app.schemas.script import PodcastScript, PodcastSection, DialogueTurn


def create_test_script(title="Test Podcast", sections=None):
    """创建测试用 PodcastScript 对象."""
    if sections is None:
        sections = [
            PodcastSection(
                section_type="opening",
                dialogues=[
                    DialogueTurn(speaker="A", content="Welcome"),
                    DialogueTurn(speaker="B", content="Hello everyone"),
                ],
            ),
            PodcastSection(
                section_type="main_content",
                dialogues=[
                    DialogueTurn(speaker="A", content="Hello"),
                    DialogueTurn(speaker="B", content="Hi there"),
                ],
            ),
            PodcastSection(
                section_type="closing",
                dialogues=[
                    DialogueTurn(speaker="A", content="Goodbye"),
                    DialogueTurn(speaker="B", content="See you next time"),
                ],
            ),
        ]
    return PodcastScript(
        title=title,
        intro="Test intro",
        sections=sections,
        total_duration="5分钟",
    )


class TestScriptServiceIntegration:
    """ScriptService 集成测试."""

    def test_init_creates_directories(self, tmp_path):
        """集成测试：初始化时创建必要的目录."""
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("You are a podcast script generator.", encoding="utf-8")

        output_dir = tmp_path / "output" / "scripts"
        service = ScriptService(project_root=tmp_path, output_dir=output_dir)

        assert output_dir.exists()

    def test_write_script_files_creates_both_formats(self, tmp_path):
        """集成测试：同时生成 .txt 和 .json 文件."""
        script = create_test_script()

        txt_path = tmp_path / "script.txt"
        json_path = tmp_path / "script.json"

        ScriptService._write_script_files(script, txt_path, json_path)

        assert txt_path.exists()
        assert json_path.exists()

        # 验证 txt 内容
        txt_content = txt_path.read_text(encoding="utf-8")
        assert "标题：Test Podcast" in txt_content
        assert "A：Hello" in txt_content

        # 验证 json 内容
        json_data = json.loads(json_path.read_text(encoding="utf-8"))
        assert json_data["title"] == "Test Podcast"
        assert json_data["sections"][0]["dialogues"][0]["speaker"] == "A"

    def test_write_script_overwrites_existing(self, tmp_path):
        """集成测试：覆盖已存在的文件."""
        script1 = create_test_script(title="First")
        script2 = create_test_script(title="Second")

        txt_path = tmp_path / "script.txt"
        json_path = tmp_path / "script.json"

        # 写入第一个版本
        ScriptService._write_script_files(script1, txt_path, json_path)
        assert "标题：First" in txt_path.read_text()

        # 覆盖写入第二个版本
        ScriptService._write_script_files(script2, txt_path, json_path)
        assert "标题：Second" in txt_path.read_text()
        assert "标题：First" not in txt_path.read_text()

    def test_generate_and_save_completes_flow(self, monkeypatch, tmp_path):
        """集成测试：完整的生成-保存流程."""
        # 准备 prompt 文件
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Generate a podcast script.", encoding="utf-8")

        # 创建测试脚本
        test_script = create_test_script(title="Generated Script")

        # Mock Agent - 模拟 pydantic_ai.Agent
        async def mock_stream_output(_debounce=None):
            yield test_script

        class MockRunStreamResult:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            def stream_output(self, debounce_by=None):
                return mock_stream_output(None)

        mock_agent_instance = MagicMock()
        mock_agent_instance.run_stream = MagicMock(return_value=MockRunStreamResult())

        # 创建 service 并注入 mock agent
        service = ScriptService(project_root=tmp_path, output_dir=tmp_path / "output")

        with patch.object(type(service), "agent", PropertyMock(return_value=mock_agent_instance)):
            txt_path, json_path = asyncio.run(
                service.generate_and_save("some news content")
            )

        assert txt_path.exists()
        assert json_path.exists()
        assert "标题：Generated Script" in txt_path.read_text(encoding="utf-8")


class TestPodcastScriptModelIntegration:
    """PodcastScript 模型集成测试."""

    def test_valid_script_passes_validation(self):
        """测试有效脚本通过验证."""
        script = PodcastScript(
            title="Valid Podcast",
            intro="Introduction",
            sections=[
                PodcastSection(
                    section_type="opening",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Welcome"),
                        DialogueTurn(speaker="B", content="Hello everyone"),
                    ],
                ),
                PodcastSection(
                    section_type="main_content",
                    dialogues=[
                        DialogueTurn(speaker="A", content="First topic"),
                        DialogueTurn(speaker="B", content="Second topic"),
                    ],
                ),
                PodcastSection(
                    section_type="closing",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Goodbye"),
                        DialogueTurn(speaker="B", content="See you next time"),
                    ],
                ),
            ],
            total_duration="10分钟",
        )

        assert script.title == "Valid Podcast"
        assert len(script.sections) == 3

    def test_format_for_output_with_all_section_types(self):
        """测试各种段落类型的格式化输出."""
        script = PodcastScript(
            title="Full Podcast",
            intro="A complete podcast",
            sections=[
                PodcastSection(
                    section_type="opening",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Welcome"),
                        DialogueTurn(speaker="B", content="Hello"),
                    ],
                ),
                PodcastSection(
                    section_type="main_content",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Main content", emotion="excited"),
                        DialogueTurn(speaker="B", content="More content"),
                    ],
                ),
                PodcastSection(
                    section_type="closing",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Bye"),
                        DialogueTurn(speaker="B", content="See you"),
                    ],
                ),
            ],
            total_duration="10分钟",
        )

        output = script.format_for_output()

        assert "标题：Full Podcast" in output
        assert "简介：A complete podcast" in output
        assert "时长：10分钟" in output
        assert "A：Welcome" in output
        assert "B：Hello" in output
        assert "（excited）" in output

    def test_script_validation_rejects_invalid(self):
        """测试无效脚本被拒绝."""
        with pytest.raises(ValueError):
            # 缺少 B 说话者
            PodcastScript(
                title="Invalid",
                intro="Intro",
                sections=[
                    PodcastSection(
                        section_type="main_content",
                        dialogues=[
                            DialogueTurn(speaker="A", content="Only A"),
                            DialogueTurn(speaker="A", content="Still only A"),  # 连续 A
                        ],
                    )
                ],
                total_duration="5分钟",
            )


class TestDialogueTurnValidation:
    """对话轮次验证测试."""

    def test_dialogue_with_valid_speaker(self):
        """测试有效说话者."""
        a = DialogueTurn(speaker="A", content="Hello")
        b = DialogueTurn(speaker="B", content="Hi")

        assert a.speaker == "A"
        assert b.speaker == "B"

    def test_dialogue_with_emotion(self):
        """测试带情感标注的对话."""
        dialogue = DialogueTurn(
            speaker="A",
            content="Great news!",
            emotion="excited"
        )

        assert dialogue.emotion == "excited"

    def test_dialogue_default_emotion(self):
        """测试默认情感为空字符串."""
        dialogue = DialogueTurn(speaker="A", content="Hello")
        assert dialogue.emotion == ""
