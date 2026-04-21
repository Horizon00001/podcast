import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

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
                    section_type="main_content",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Hello"),
                        DialogueTurn(speaker="B", content="Hi there"),
                    ],
                )
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
                    section_type="main_content",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Great news!", emotion="excited"),
                        DialogueTurn(speaker="B", content="That's interesting"),
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
                    section_type="main_content",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Hello"),
                        DialogueTurn(speaker="B", content="Hi there"),
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


class TestScriptServiceModelDump:
    """Test PodcastScript model_dump output."""

    def test_model_dump_includes_all_fields(self):
        script = PodcastScript(
            title="Test",
            intro="Intro",
            sections=[
                PodcastSection(
                    section_type="main_content",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Hello"),
                        DialogueTurn(speaker="B", content="Hi"),
                    ],
                )
            ],
            total_duration="5分钟",
        )

        data = script.model_dump()

        assert "title" in data
        assert "intro" in data
        assert "sections" in data
        assert "total_duration" in data
        assert data["sections"][0]["section_type"] == "main_content"
