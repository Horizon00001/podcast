import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from app.services.tts_service import TTSService
from app.services.audio_plan import RenderPlan, RenderPlanItem


class TestTTSServiceCleanText:
    """Test clean_text method - removes parenthetical content."""

    def setup_method(self):
        """Create TTSService with mocked dependencies."""
        mock_provider = MagicMock()
        self.service = TTSService(output_dir="/tmp/test_audio", speech_provider=mock_provider)

    def test_clean_text_removes_parentheses(self):
        assert self.service.clean_text("Hello (world)") == "Hello"
        assert self.service.clean_text("测试 (annotation)") == "测试"
        assert self.service.clean_text("Hello（中文括号）") == "Hello"

    def test_clean_text_removes_all_parenthetical(self):
        result = self.service.clean_text("Start (note) middle (another) end")
        assert "(" not in result
        assert ")" not in result
        assert "（" not in result
        assert "）" not in result

    def test_clean_text_no_parentheses(self):
        assert self.service.clean_text("Plain text") == "Plain text"

    def test_clean_text_empty(self):
        assert self.service.clean_text("") == ""

    def test_clean_text_whitespace_only(self):
        assert self.service.clean_text("   ") == ""

    def test_clean_text_strips_whitespace(self):
        assert self.service.clean_text("  Hello (world)  ") == "Hello"


class TestTTSServiceLoadScript:
    """Test load_script method."""

    def test_load_script(self, tmp_path):
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        script_path = tmp_path / "test_script.json"
        script_content = '{"title": "Test", "sections": []}'
        script_path.write_text(script_content, encoding="utf-8")

        result = service.load_script(script_path)

        assert result["title"] == "Test"
        assert result["sections"] == []

    def test_load_script_from_string_path(self, tmp_path):
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        script_path = tmp_path / "test_script.json"
        script_content = '{"title": "Test2"}'
        script_path.write_text(script_content, encoding="utf-8")

        result = service.load_script(str(script_path))

        assert result["title"] == "Test2"


class TestTTSServiceFindExistingAsset:
    """Test _find_existing_asset static method."""

    def test_find_existing_asset_found(self, tmp_path):
        existing_file = tmp_path / "existing.mp3"
        existing_file.write_text("dummy", encoding="utf-8")

        candidates = [
            tmp_path / "nonexistent1.mp3",
            existing_file,
            tmp_path / "nonexistent2.mp3",
        ]

        result = TTSService._find_existing_asset(candidates)

        assert result == existing_file

    def test_find_existing_asset_not_found(self, tmp_path):
        candidates = [
            tmp_path / "nonexistent1.mp3",
            tmp_path / "nonexistent2.mp3",
        ]

        result = TTSService._find_existing_asset(candidates)

        assert result is None

    def test_list_library_assets_filters_audio_files(self, tmp_path):
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=MagicMock())
        library_dir = tmp_path / "library"
        library_dir.mkdir()
        audio_file = library_dir / "clip.mp3"
        text_file = library_dir / "notes.txt"
        audio_file.write_text("dummy", encoding="utf-8")
        text_file.write_text("ignore", encoding="utf-8")

        assets = service._list_library_assets(library_dir)

        assert assets == [audio_file]

    def test_pick_music_asset_prefers_library_asset(self, tmp_path):
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=MagicMock())
        library_dir = tmp_path / "library"
        library_dir.mkdir()
        library_asset = library_dir / "clip.mp3"
        library_asset.write_text("library", encoding="utf-8")
        legacy_asset = tmp_path / "legacy.mp3"
        legacy_asset.write_text("legacy", encoding="utf-8")

        with patch("app.services.tts_service.random.choice", return_value=library_asset) as choice_mock:
            selected = service._pick_music_asset(library_dir, [legacy_asset])

        assert selected == library_asset
        choice_mock.assert_called_once_with([library_asset])

    def test_pick_music_asset_falls_back_to_legacy_candidates(self, tmp_path):
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=MagicMock())
        library_dir = tmp_path / "missing-library"
        legacy_asset = tmp_path / "legacy.mp3"
        legacy_asset.write_text("legacy", encoding="utf-8")

        selected = service._pick_music_asset(library_dir, [legacy_asset])

        assert selected == legacy_asset


class TestTTSServiceInjectDefaultAssets:
    """Test _inject_default_assets method."""

    def test_inject_default_assets_no_music_items(self, tmp_path):
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        # Create a plan without music
        plan = RenderPlan(
            title="Test",
            items=[
                RenderPlanItem(item_type="speech", text="Hello", voice="male"),
            ],
        )

        # Patch _find_existing_asset to return a fake path
        fake_music = tmp_path / "fake_music.mp3"
        fake_music.write_text("dummy", encoding="utf-8")

        with patch.object(TTSService, "_find_existing_asset", return_value=fake_music):
            result = service._inject_default_assets(plan)

        # Should have added opening music and silence at the start
        assert len(result.items) == 3
        assert result.items[0].item_type == "music"
        assert result.items[0].metadata["role"] == "opening_theme"
        assert result.items[1].item_type == "silence"

    def test_inject_default_assets_can_skip_fallback_opening(self, tmp_path):
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        plan = RenderPlan(
            title="Test",
            items=[RenderPlanItem(item_type="speech", text="Hello", voice="male")],
        )

        fake_music = tmp_path / "fake_music.mp3"
        fake_music.write_text("dummy", encoding="utf-8")

        with patch.object(TTSService, "_find_existing_asset", return_value=fake_music):
            result = service._inject_default_assets(plan, inject_fallback_opening=False)

        assert len(result.items) == 1
        assert result.items[0].item_type == "speech"

    def test_inject_default_assets_with_existing_music(self, tmp_path):
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        fake_music = tmp_path / "fake_music.mp3"
        fake_music.write_text("dummy", encoding="utf-8")

        plan = RenderPlan(
            title="Test",
            items=[
                RenderPlanItem(
                    item_type="music",
                    asset_path=None,
                    metadata={"role": "opening_theme"},
                ),
                RenderPlanItem(item_type="speech", text="Hello"),
            ],
        )

        with patch.object(TTSService, "_find_existing_asset", return_value=fake_music):
            result = service._inject_default_assets(plan)

        # Music items should have asset_path set
        music_items = [item for item in result.items if item.item_type == "music"]
        for item in music_items:
            if item.metadata.get("role") == "opening_theme":
                assert item.asset_path == fake_music
                assert item.volume == 0.24
                assert item.fade_out_ms == 1800

    def test_inject_default_assets_uses_transition_music_for_transition_sting(self, tmp_path):
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        opening_music = tmp_path / "opening.mp3"
        transition_music = tmp_path / "transition_music_5s.mp3"
        opening_music.write_text("opening", encoding="utf-8")
        transition_music.write_text("transition", encoding="utf-8")

        plan = RenderPlan(
            title="Test",
            items=[
                RenderPlanItem(item_type="music", metadata={"role": "opening_theme"}),
                RenderPlanItem(item_type="music", metadata={"role": "transition_sting"}),
            ],
        )

        def find_existing_asset(candidates):
            if candidates == service.opening_music_candidates:
                return opening_music
            if candidates == service.transition_music_candidates:
                return transition_music
            return None

        with patch.object(TTSService, "_find_existing_asset", side_effect=find_existing_asset):
            result = service._inject_default_assets(plan)

        assert result.items[0].asset_path == opening_music
        assert result.items[1].asset_path == transition_music
        assert result.items[1].volume == 0.20
        assert result.items[1].fade_out_ms == 350

    def test_inject_default_assets_uses_closing_library_for_closing_tail(self, tmp_path):
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        opening_music = tmp_path / "opening.mp3"
        closing_music = tmp_path / "closing.mp3"
        opening_music.write_text("opening", encoding="utf-8")
        closing_music.write_text("closing", encoding="utf-8")

        plan = RenderPlan(
            title="Test",
            items=[
                RenderPlanItem(item_type="music", metadata={"role": "opening_theme"}),
                RenderPlanItem(item_type="music", metadata={"role": "closing_tail"}),
            ],
        )

        def pick_music_asset(library_dir, legacy_candidates):
            if library_dir == service.opening_library_dir:
                return opening_music
            if library_dir == service.transition_library_dir:
                return None
            if library_dir == service.closing_library_dir:
                return closing_music
            return None

        with patch.object(TTSService, "_pick_music_asset", side_effect=pick_music_asset):
            result = service._inject_default_assets(plan)

        assert result.items[0].asset_path == opening_music
        assert result.items[1].asset_path == closing_music
        assert result.items[1].volume == 0.20
        assert result.items[1].fade_out_ms == 2600


class TestTTSServiceBuildRenderPlan:
    """Test build_render_plan method."""

    def test_build_render_plan(self, tmp_path):
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        script_data = {
            "title": "Test Podcast",
            "sections": [
                {
                    "section_type": "main_content",
                    "dialogues": [
                        {"speaker": "A", "content": "Hello"},
                    ],
                }
            ],
        }

        fake_music = tmp_path / "fake_music.mp3"
        fake_music.write_text("dummy", encoding="utf-8")

        with patch.object(TTSService, "_find_existing_asset", return_value=fake_music):
            plan = service.build_render_plan(script_data)

        assert plan.title == "Test Podcast"
        assert len(plan.items) > 0

    def test_build_section_render_plan_does_not_inject_opening_theme(self, tmp_path):
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        section = {
            "section_type": "main_content",
            "dialogues": [
                {"speaker": "A", "content": "Hello"},
                {"speaker": "B", "content": "World"},
            ],
        }

        fake_music = tmp_path / "fake_music.mp3"
        fake_music.write_text("dummy", encoding="utf-8")

        with patch.object(TTSService, "_find_existing_asset", return_value=fake_music):
            plan = service.build_section_render_plan("Test Podcast", section)

        assert all(item.metadata.get("role") != "opening_theme" for item in plan.items)
        assert all(item.metadata.get("role") != "opening_voice_delay" for item in plan.items)

    def test_build_render_plan_include_trailing_gap(self, tmp_path):
        mock_provider = MagicMock()
        service = TTSService(output_dir=tmp_path / "audio", speech_provider=mock_provider)

        script_data = {
            "title": "Test",
            "sections": [
                {
                    "section_type": "closing",
                    "dialogues": [
                        {"speaker": "A", "content": "Goodbye"},
                    ],
                }
            ],
        }

        fake_music = tmp_path / "fake_music.mp3"
        fake_music.write_text("dummy", encoding="utf-8")

        with patch.object(TTSService, "_find_existing_asset", return_value=fake_music):
            plan = service.build_render_plan(script_data, include_trailing_gap=True)

        # Should have trailing gap
        has_trailing_silence = any(
            item.item_type == "silence" and item.metadata.get("section_type") == "closing"
            for item in plan.items[-3:]
        )
        assert has_trailing_silence


class TestTTSServiceSecondsToMs:
    """Test _seconds_to_ms static method."""

    def test_seconds_to_ms_basic(self):
        assert TTSService._seconds_to_ms(1.0) == 1000
        assert TTSService._seconds_to_ms(0.5) == 500

    def test_seconds_to_ms_zero(self):
        assert TTSService._seconds_to_ms(0.0) == 0

    def test_seconds_to_ms_negative(self):
        # Negative values should become 0
        assert TTSService._seconds_to_ms(-1.0) == 0
