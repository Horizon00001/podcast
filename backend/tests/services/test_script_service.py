import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from pydantic_ai.exceptions import UnexpectedModelBehavior

from app.schemas.script import (
    AudioEffect,
    DialogueTurn,
    PodcastSection,
    PodcastScript,
)
from app.services.script_service import ScriptService


class TestScriptServiceModels:
    """Test Pydantic models in script_service."""

    def test_audio_effect_basic(self):
        effect = AudioEffect(
            effect_type="music",
            description="Intro music",
            duration="10s",
        )
        assert effect.effect_type == "music"
        assert effect.description == "Intro music"
        assert effect.duration == "10s"

    def test_dialogue_turn_basic(self):
        dialogue = DialogueTurn(speaker="A", content="Hello everyone")
        assert dialogue.speaker == "A"
        assert dialogue.content == "Hello everyone"
        assert dialogue.emotion == ""

    def test_dialogue_turn_with_emotion(self):
        dialogue = DialogueTurn(speaker="B", content="Welcome", emotion="excited")
        assert dialogue.emotion == "excited"


class TestPodcastSectionValidator:
    """Test PodcastSection model validator."""

    def test_validate_alternating_dialogues_valid(self):
        section = PodcastSection(
            section_type="main_content",
            dialogues=[
                DialogueTurn(speaker="A", content="First"),
                DialogueTurn(speaker="B", content="Second"),
                DialogueTurn(speaker="A", content="Third"),
            ],
        )
        assert len(section.dialogues) == 3

    def test_validate_alternating_dialogues_raises_on_consecutive_same_speaker(self):
        with pytest.raises(ValueError, match="检测到连续相同说话者"):
            PodcastSection(
                section_type="main_content",
                dialogues=[
                    DialogueTurn(speaker="A", content="First"),
                    DialogueTurn(speaker="A", content="Second"),  # Invalid!
                ],
            )

    def test_validate_alternating_dialogues_raises_on_less_than_two(self):
        with pytest.raises(ValueError, match="每个段落至少需要 2 句对话"):
            PodcastSection(
                section_type="main_content",
                dialogues=[
                    DialogueTurn(speaker="A", content="Only one"),
                ],
            )


class TestPodcastScriptValidator:
    """Test PodcastScript model validator."""

    def test_validate_both_speakers_present_valid(self):
        script = PodcastScript(
            title="Test Podcast",
            intro="Welcome",
            sections=[
                PodcastSection(
                    section_type="opening",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Hello"),
                        DialogueTurn(speaker="B", content="Hi there"),
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
                        DialogueTurn(speaker="A", content="Bye"),
                        DialogueTurn(speaker="B", content="See you"),
                    ],
                ),
            ],
            total_duration="10分钟",
        )
        assert script.title == "Test Podcast"

    def test_validate_both_speakers_present_raises_when_missing_a(self):
        # PodcastSection validator catches consecutive same speakers before PodcastScript validator
        # So we get the section-level error instead of the script-level error
        with pytest.raises(ValueError, match="检测到连续相同说话者"):
            PodcastScript(
                title="Test",
                intro="Intro",
                sections=[
                    PodcastSection(
                        section_type="main_content",
                        dialogues=[
                            DialogueTurn(speaker="B", content="Only B"),
                            DialogueTurn(speaker="B", content="Still B"),
                        ],
                    )
                ],
                total_duration="5分钟",
            )

    def test_validate_both_speakers_present_raises_when_missing_b(self):
        # Same as above - section validator runs first
        with pytest.raises(ValueError, match="检测到连续相同说话者"):
            PodcastScript(
                title="Test",
                intro="Intro",
                sections=[
                    PodcastSection(
                        section_type="main_content",
                        dialogues=[
                            DialogueTurn(speaker="A", content="Only A"),
                            DialogueTurn(speaker="A", content="Still A"),
                        ],
                    )
                ],
                total_duration="5分钟",
            )


class TestPodcastScriptFormatForOutput:
    """Test PodcastScript.format_for_output method."""

    def test_format_for_output_basic(self):
        script = PodcastScript(
            title="AI News Today",
            intro="Daily AI updates",
            sections=[
                PodcastSection(
                    section_type="opening",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Hello everyone"),
                        DialogueTurn(speaker="B", content="Welcome to the show"),
                    ],
                ),
                PodcastSection(
                    section_type="main_content",
                    dialogues=[
                        DialogueTurn(speaker="A", content="What happened today?"),
                        DialogueTurn(speaker="B", content="Here is the main story."),
                    ],
                ),
                PodcastSection(
                    section_type="closing",
                    dialogues=[
                        DialogueTurn(speaker="A", content="That is all for today."),
                        DialogueTurn(speaker="B", content="See you next time."),
                    ],
                )
            ],
            total_duration="8分钟",
        )

        output = script.format_for_output()

        assert "标题：AI News Today" in output
        assert "简介：Daily AI updates" in output
        assert "时长：8分钟" in output
        assert "A：Hello everyone" in output
        assert "B：Welcome to the show" in output

    def test_format_for_output_with_emotion(self):
        script = PodcastScript(
            title="Test",
            intro="Intro",
            sections=[
                PodcastSection(
                    section_type="opening",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Intro"),
                        DialogueTurn(speaker="B", content="Start"),
                    ],
                ),
                PodcastSection(
                    section_type="main_content",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Great news!", emotion="excited"),
                        DialogueTurn(speaker="B", content="That's interesting"),
                    ],
                ),
                PodcastSection(
                    section_type="closing",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Bye"),
                        DialogueTurn(speaker="B", content="See you"),
                    ],
                )
            ],
            total_duration="5分钟",
        )

        output = script.format_for_output()

        assert "（excited）" in output

    def test_format_for_output_with_audio_effect(self):
        script = PodcastScript(
            title="Test",
            intro="Intro",
            sections=[
                PodcastSection(
                    section_type="opening",
                    audio_effect=AudioEffect(effect_type="music", description="Intro theme", duration="10s"),
                    dialogues=[
                        DialogueTurn(speaker="A", content="Hello"),
                        DialogueTurn(speaker="B", content="Hi"),
                    ],
                ),
                PodcastSection(
                    section_type="main_content",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Main topic"),
                        DialogueTurn(speaker="B", content="Main analysis"),
                    ],
                ),
                PodcastSection(
                    section_type="closing",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Bye"),
                        DialogueTurn(speaker="B", content="See you"),
                    ],
                )
            ],
            total_duration="5分钟",
        )

        output = script.format_for_output()

        assert "[MUSIC]" in output or "[music]" in output.lower()
        assert "Intro theme" in output


class TestScriptServiceWriteScriptFiles:
    """Test ScriptService._write_script_files method."""

    def test_write_script_files_creates_files(self, tmp_path):
        script = PodcastScript(
            title="Test Podcast",
            intro="Welcome",
            sections=[
                PodcastSection(
                    section_type="opening",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Intro"),
                        DialogueTurn(speaker="B", content="Start"),
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
                        DialogueTurn(speaker="A", content="Bye"),
                        DialogueTurn(speaker="B", content="See you"),
                    ],
                )
            ],
            total_duration="5分钟",
        )

        txt_path = tmp_path / "script.txt"
        json_path = tmp_path / "script.json"

        ScriptService._write_script_files(script, txt_path, json_path)

        assert txt_path.exists()
        assert json_path.exists()

        # Check txt content
        txt_content = txt_path.read_text(encoding="utf-8")
        assert "标题：Test Podcast" in txt_content
        assert "A：Hello" in txt_content

        # Check json content
        json_content = json.loads(json_path.read_text(encoding="utf-8"))
        assert json_content["title"] == "Test Podcast"
        assert json_content["sections"][0]["dialogues"][0]["speaker"] == "A"


class TestScriptServiceNormalization:
    def test_normalize_script_inserts_transition_after_first_main_content(self):
        script = PodcastScript(
            title="Test Podcast",
            intro="Welcome",
            sections=[
                PodcastSection(
                    section_type="opening",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Hello"),
                        DialogueTurn(speaker="B", content="Hi there"),
                    ],
                ),
                PodcastSection(
                    section_type="main_content",
                    dialogues=[
                        DialogueTurn(speaker="A", content="First topic"),
                        DialogueTurn(speaker="B", content="First analysis"),
                    ],
                ),
                PodcastSection(
                    section_type="main_content",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Second topic"),
                        DialogueTurn(speaker="B", content="Second analysis"),
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
            total_duration="8分钟",
        )

        normalized = ScriptService._normalize_script(script)

        assert [section.section_type for section in normalized.sections] == [
            "opening",
            "main_content",
            "transition",
            "main_content",
            "closing",
        ]
        assert normalized.sections[2].audio_effect is None

    def test_normalize_script_keeps_existing_transition(self):
        script = PodcastScript(
            title="Test Podcast",
            intro="Welcome",
            sections=[
                PodcastSection(
                    section_type="opening",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Hello"),
                        DialogueTurn(speaker="B", content="Hi there"),
                    ],
                ),
                PodcastSection(
                    section_type="transition",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Switch"),
                        DialogueTurn(speaker="B", content="Continue"),
                    ],
                ),
                PodcastSection(
                    section_type="main_content",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Topic"),
                        DialogueTurn(speaker="B", content="Analysis"),
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
            total_duration="6分钟",
        )

        normalized = ScriptService._normalize_script(script)

        assert [section.section_type for section in normalized.sections] == [
            "opening",
            "transition",
            "main_content",
            "closing",
        ]


class TestScriptServiceInitialization:
    """Test ScriptService initialization."""

    def test_init_creates_output_dir(self, tmp_path):
        output_dir = tmp_path / "output"
        service = ScriptService(project_root=tmp_path, output_dir=output_dir)

        assert output_dir.exists()

    def test_init_sets_prompt_path(self, tmp_path):
        # Create a mock prompt file
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Test prompt", encoding="utf-8")

        service = ScriptService(project_root=tmp_path, output_dir=tmp_path / "output")

        assert service.prompt_path == prompt_file


class TestScriptServiceFallback:
    def test_generate_and_save_falls_back_to_run(self, monkeypatch, tmp_path):
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Test prompt", encoding="utf-8")

        service = ScriptService(project_root=tmp_path, output_dir=tmp_path / "output")
        test_script = PodcastScript(
            title="Fallback Script",
            intro="Intro",
            sections=[
                PodcastSection(
                    section_type="opening",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Intro"),
                        DialogueTurn(speaker="B", content="Start"),
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
                        DialogueTurn(speaker="A", content="Bye"),
                        DialogueTurn(speaker="B", content="See you"),
                    ],
                ),
            ],
            total_duration="5分钟",
        )

        class MockRunStreamResult:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            def stream_output(self, debounce_by=None):
                async def _raise_unexpected_model_behavior():
                    raise UnexpectedModelBehavior("streaming failed")
                    yield  # pragma: no cover

                return _raise_unexpected_model_behavior()

        mock_agent_instance = MagicMock()
        mock_agent_instance.run_stream = MagicMock(return_value=MockRunStreamResult())
        mock_agent_instance.run = AsyncMock(return_value=MagicMock(output=test_script))

        with patch.object(type(service), "agent", PropertyMock(return_value=mock_agent_instance)):
            txt_path, json_path = asyncio.run(service.generate_and_save("some news content"))

        assert txt_path.exists()
        assert json_path.exists()
        assert "标题：Fallback Script" in txt_path.read_text(encoding="utf-8")
        assert mock_agent_instance.run_stream.called
        assert mock_agent_instance.run.called


class TestScriptServiceModelDump:
    """Test PodcastScript model_dump output."""

    def test_model_dump_includes_all_fields(self):
        script = PodcastScript(
            title="Test",
            intro="Intro",
            sections=[
                PodcastSection(
                    section_type="opening",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Intro"),
                        DialogueTurn(speaker="B", content="Start"),
                    ],
                ),
                PodcastSection(
                    section_type="main_content",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Hello"),
                        DialogueTurn(speaker="B", content="Hi"),
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
            total_duration="5分钟",
        )

        data = script.model_dump()

        assert "title" in data
        assert "intro" in data
        assert "sections" in data
        assert "total_duration" in data
        assert data["sections"][0]["section_type"] == "opening"


def _make_script(title: str, num_sections: int) -> PodcastScript:
    """Build a PodcastScript with *num_sections* main_content sections."""
    sections = [
        PodcastSection(
            section_type="opening",
            dialogues=[
                DialogueTurn(speaker="A", content="Opening A"),
                DialogueTurn(speaker="B", content="Opening B"),
            ],
        )
    ]
    for i in range(num_sections):
        sections.append(
            PodcastSection(
                section_type="main_content",
                dialogues=[
                    DialogueTurn(speaker="A", content=f"Section {i} A opening"),
                    DialogueTurn(speaker="B", content=f"Section {i} B response"),
                ],
            )
        )
    sections.append(
        PodcastSection(
            section_type="closing",
            dialogues=[
                DialogueTurn(speaker="A", content="Closing A"),
                DialogueTurn(speaker="B", content="Closing B"),
            ],
        )
    )
    return PodcastScript(
        title=title,
        intro="Intro text",
        sections=sections,
        total_duration=f"{num_sections * 3}分钟",
    )


class TestScriptServiceDuration:
    def test_write_script_files_recomputes_duration(self, tmp_path):
        script = PodcastScript(
            title="Duration Test",
            intro="Intro",
            sections=[
                PodcastSection(
                    section_type="opening",
                    dialogues=[
                        DialogueTurn(speaker="A", content="你好吗" * 20),
                        DialogueTurn(speaker="B", content="我很好" * 20),
                    ],
                ),
                PodcastSection(
                    section_type="main_content",
                    dialogues=[
                        DialogueTurn(speaker="A", content="继续聊" * 40),
                        DialogueTurn(speaker="B", content="继续分析" * 40),
                    ],
                ),
                PodcastSection(
                    section_type="closing",
                    dialogues=[
                        DialogueTurn(speaker="A", content="最后总结" * 10),
                        DialogueTurn(speaker="B", content="感谢收听" * 10),
                    ],
                ),
            ],
            total_duration="99分钟",
        )

        txt_path = tmp_path / "script.txt"
        json_path = tmp_path / "script.json"

        ScriptService._write_script_files(script, txt_path, json_path)

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["total_duration"] == "3分钟"


def _make_stream_ctx(scripts: list[PodcastScript]):
    """Return an async context manager whose stream_output yields each script."""

    class _Ctx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def stream_output(self, debounce_by=None):
            for s in scripts:
                yield s

    return _Ctx()


class TestScriptServiceStreamingSections:
    """Test generate_and_save_streaming_sections with mocked agent."""

    def test_no_callback_works(self, monkeypatch, tmp_path):
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Test", encoding="utf-8")
        service = ScriptService(project_root=tmp_path, output_dir=tmp_path / "output")
        script = _make_script("Test", 2)

        mock_agent = MagicMock()
        mock_agent.run_stream = MagicMock(return_value=_make_stream_ctx([script]))

        with patch.object(type(service), "agent", PropertyMock(return_value=mock_agent)):
            txt_path, json_path = asyncio.run(
                service.generate_and_save_streaming_sections("news", on_section_ready=None)
            )

        assert txt_path.exists()
        assert json_path.exists()

    def test_callback_called_for_stable_sections(self, monkeypatch, tmp_path):
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Test", encoding="utf-8")
        service = ScriptService(project_root=tmp_path, output_dir=tmp_path / "output")

        # Simulate progressive generation: 1 section → 2 sections → 3 sections.
        s1 = _make_script("T", 1)
        s2 = _make_script("T", 2)
        s3 = _make_script("T", 3)

        mock_agent = MagicMock()
        mock_agent.run_stream = MagicMock(return_value=_make_stream_ctx([s1, s2, s3]))

        calls = []

        async def cb(index, data, is_streaming):
            calls.append((index, data["section_type"], is_streaming))

        with patch.object(type(service), "agent", PropertyMock(return_value=mock_agent)):
            asyncio.run(
                service.generate_and_save_streaming_sections("news", on_section_ready=cb)
            )

        assert len(calls) == 6
        assert calls[0] == (0, "opening", True)
        assert calls[1] == (1, "main_content", True)
        assert calls[2] == (2, "transition", True)
        assert calls[3] == (3, "main_content", True)
        assert calls[4] == (4, "main_content", True)
        assert calls[5] == (5, "closing", False)

    def test_final_sections_flushed_after_stream(self, monkeypatch, tmp_path):
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Test", encoding="utf-8")
        service = ScriptService(project_root=tmp_path, output_dir=tmp_path / "output")

        # Only one yield with all 3 sections — nothing flushed mid-stream.
        s_final = _make_script("T", 3)
        mock_agent = MagicMock()
        mock_agent.run_stream = MagicMock(return_value=_make_stream_ctx([s_final]))

        calls = []

        async def cb(index, data, is_streaming):
            calls.append((index, is_streaming))

        with patch.object(type(service), "agent", PropertyMock(return_value=mock_agent)):
            asyncio.run(
                service.generate_and_save_streaming_sections("news", on_section_ready=cb)
            )

        assert len(calls) == 6
        assert calls == [(0, True), (1, True), (2, True), (3, True), (4, True), (5, False)]

    def test_empty_script_raises(self, monkeypatch, tmp_path):
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Test", encoding="utf-8")
        service = ScriptService(project_root=tmp_path, output_dir=tmp_path / "output")

        mock_agent = MagicMock()
        # Stream that yields nothing → final_script stays None.
        mock_agent.run_stream = MagicMock(return_value=_make_stream_ctx([]))

        with patch.object(type(service), "agent", PropertyMock(return_value=mock_agent)):
            with pytest.raises(RuntimeError, match="脚本生成失败"):
                asyncio.run(
                    service.generate_and_save_streaming_sections("news", on_section_ready=None)
                )

    def test_fallback_to_run(self, monkeypatch, tmp_path):
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Test", encoding="utf-8")
        service = ScriptService(project_root=tmp_path, output_dir=tmp_path / "output")

        fallback_script = _make_script("Fallback", 2)

        class _FailingCtx:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            def stream_output(self, debounce_by=None):
                async def _raise():
                    raise UnexpectedModelBehavior("stream failed")
                    yield
                return _raise()

        mock_agent = MagicMock()
        mock_agent.run_stream = MagicMock(return_value=_FailingCtx())
        mock_agent.run = AsyncMock(return_value=MagicMock(output=fallback_script))

        calls = []

        async def cb(index, data, is_streaming):
            calls.append((index, data["section_type"], is_streaming))

        with patch.object(type(service), "agent", PropertyMock(return_value=mock_agent)):
            txt_path, json_path = asyncio.run(
                service.generate_and_save_streaming_sections("news", on_section_ready=cb)
            )

        assert mock_agent.run_stream.called
        assert mock_agent.run.called
        assert len(calls) == 5
        assert calls == [
            (0, "opening", True),
            (1, "main_content", True),
            (2, "transition", True),
            (3, "main_content", True),
            (4, "closing", False),
        ]
        assert txt_path.exists()
        assert json_path.exists()
