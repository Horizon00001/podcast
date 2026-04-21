import pytest

from app.services.audio_plan import RenderPlanner, RenderPlan, RenderPlanItem


class TestRenderPlannerParseDuration:
    """Test _parse_duration_to_ms method."""

    def test_parse_milliseconds(self):
        assert RenderPlanner._parse_duration_to_ms("500ms") == 500
        assert RenderPlanner._parse_duration_to_ms("500 毫秒") == 500

    def test_parse_seconds(self):
        assert RenderPlanner._parse_duration_to_ms("10s") == 10000
        assert RenderPlanner._parse_duration_to_ms("10 秒") == 10000

    def test_parse_minutes(self):
        assert RenderPlanner._parse_duration_to_ms("2min") == 120000
        assert RenderPlanner._parse_duration_to_ms("2 分钟") == 120000
        assert RenderPlanner._parse_duration_to_ms("2 分") == 120000

    def test_parse_decimal(self):
        assert RenderPlanner._parse_duration_to_ms("1.5s") == 1500

    def test_parse_empty(self):
        assert RenderPlanner._parse_duration_to_ms("") == 0

    def test_parse_no_unit_defaults_to_ms(self):
        assert RenderPlanner._parse_duration_to_ms("100") == 100


class TestRenderPlannerVoiceMap:
    """Test VOICE_MAP constant."""

    def test_voice_map_values(self):
        assert RenderPlanner.VOICE_MAP["主持人A"] == "male"
        assert RenderPlanner.VOICE_MAP["主持人B"] == "female"
        assert RenderPlanner.VOICE_MAP["A"] == "male"
        assert RenderPlanner.VOICE_MAP["B"] == "female"

    def test_default_voice(self):
        assert RenderPlanner.DEFAULT_VOICE == "female"


class TestRenderPlannerBuildFromScript:
    """Test build_from_script method."""

    def test_build_from_empty_script(self):
        script_data = {"title": "Test Podcast", "sections": []}
        plan = RenderPlanner.build_from_script(script_data)

        assert plan.title == "Test Podcast"
        assert len(plan.items) == 0

    def test_build_opening_section(self):
        script_data = {
            "title": "Test",
            "sections": [
                {
                    "section_type": "opening",
                    "audio_effect": {"duration": "10s", "description": "intro music"},
                    "dialogues": [
                        {"speaker": "A", "content": "Hello everyone"},
                        {"speaker": "B", "content": "Welcome to the show"},
                    ],
                }
            ],
        }
        plan = RenderPlanner.build_from_script(script_data)

        # Should have opening music, silence, then two dialogues
        item_types = [item.item_type for item in plan.items]
        assert "music" in item_types  # Opening music
        assert "silence" in item_types  # Gap after opening music

        # Check dialogues
        speech_items = [item for item in plan.items if item.item_type == "speech"]
        assert len(speech_items) == 2
        assert speech_items[0].text == "Hello everyone"
        assert speech_items[0].voice == "male"
        assert speech_items[1].text == "Welcome to the show"
        assert speech_items[1].voice == "female"

    def test_build_transition_section(self):
        script_data = {
            "title": "Test",
            "sections": [
                {
                    "section_type": "transition",
                    "audio_effect": {"effect_type": "effect", "duration": "2s"},
                    "dialogues": [
                        {"speaker": "A", "content": "Now let's talk about AI"},
                    ],
                }
            ],
        }
        plan = RenderPlanner.build_from_script(script_data)

        item_types = [item.item_type for item in plan.items]
        assert "music" in item_types  # Transition sting
        assert "silence" in item_types  # Gap after transition

    def test_build_main_content_section(self):
        script_data = {
            "title": "Test",
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
        plan = RenderPlanner.build_from_script(script_data)

        speech_items = [item for item in plan.items if item.item_type == "speech"]
        assert len(speech_items) == 2
        # main_content alone (last section) has no trailing gap unless force_trailing_gap=True
        # Only opening/transition sections add internal gaps
        silence_items = [item for item in plan.items if item.item_type == "silence"]
        # The main_content section doesn't add its own gap when it's the last section
        # Use force_trailing_gap to add trailing gap
        assert len(silence_items) == 0

        # With force_trailing_gap, should have trailing silence
        plan_with_gap = RenderPlanner.build_from_script(script_data, force_trailing_gap=True)
        silence_with_gap = [item for item in plan_with_gap.items if item.item_type == "silence"]
        assert len(silence_with_gap) >= 1

    def test_build_closing_section(self):
        script_data = {
            "title": "Test",
            "sections": [
                {
                    "section_type": "closing",
                    "audio_effect": {"effect_type": "music", "duration": "8s"},
                    "dialogues": [
                        {"speaker": "A", "content": "Thanks for listening"},
                    ],
                }
            ],
        }
        plan = RenderPlanner.build_from_script(script_data)

        speech_items = [item for item in plan.items if item.item_type == "speech"]
        assert len(speech_items) == 1
        # Closing should have trailing gap
        silence_items = [item for item in plan.items if item.item_type == "silence"]
        assert len(silence_items) >= 1

    def test_multiple_sections(self):
        script_data = {
            "title": "Multi Section",
            "sections": [
                {
                    "section_type": "opening",
                    "dialogues": [{"speaker": "A", "content": "Welcome"}],
                },
                {
                    "section_type": "main_content",
                    "dialogues": [{"speaker": "B", "content": "Content"}],
                },
                {
                    "section_type": "closing",
                    "dialogues": [{"speaker": "A", "content": "Goodbye"}],
                },
            ],
        }
        plan = RenderPlanner.build_from_script(script_data)

        # Should have gaps between sections
        silence_items = [item for item in plan.items if item.item_type == "silence"]
        assert len(silence_items) >= 2  # Gaps after opening and main_content

    def test_dialogue_speaker_mapping(self):
        script_data = {
            "title": "Test",
            "sections": [
                {
                    "section_type": "main_content",
                    "dialogues": [
                        {"speaker": "主持人A", "content": "Host A speaking"},
                        {"speaker": "主持人B", "content": "Host B speaking"},
                        {"speaker": "C", "content": "Unknown speaker uses default"},
                    ],
                }
            ],
        }
        plan = RenderPlanner.build_from_script(script_data)

        speech_items = [item for item in plan.items if item.item_type == "speech"]
        assert speech_items[0].voice == "male"  # 主持人A
        assert speech_items[1].voice == "female"  # 主持人B
        assert speech_items[2].voice == "female"  # Unknown defaults to female

    def test_dialogue_emotion_metadata(self):
        script_data = {
            "title": "Test",
            "sections": [
                {
                    "section_type": "main_content",
                    "dialogues": [
                        {"speaker": "A", "content": "Happy text", "emotion": "excited"},
                    ],
                }
            ],
        }
        plan = RenderPlanner.build_from_script(script_data)

        speech_items = [item for item in plan.items if item.item_type == "speech"]
        assert speech_items[0].metadata["emotion"] == "excited"
        assert speech_items[0].metadata["section_type"] == "main_content"

    def test_force_trailing_gap(self):
        script_data = {
            "title": "Test",
            "sections": [
                {
                    "section_type": "closing",
                    "dialogues": [{"speaker": "A", "content": "End"}],
                }
            ],
        }
        plan_normal = RenderPlanner.build_from_script(script_data, force_trailing_gap=False)

        # Count gaps at the end
        trailing_gaps_normal = sum(
            1 for item in plan_normal.items[-3:] if item.item_type == "silence"
        )

        plan_forced = RenderPlanner.build_from_script(script_data, force_trailing_gap=True)

        # With force_trailing_gap, should have trailing silence
        trailing_gaps_forced = sum(
            1 for item in plan_forced.items[-3:] if item.item_type == "silence"
        )

        assert trailing_gaps_forced >= trailing_gaps_normal


class TestRenderPlannerHelperMethods:
    """Test _build_* helper methods."""

    def test_build_opening_cues(self):
        effect = {"duration": "10s", "description": "intro"}
        cues = RenderPlanner._build_opening_cues(effect)

        assert len(cues) == 2
        assert cues[0].item_type == "music"
        assert cues[0].duration_ms == 10000
        assert cues[1].item_type == "silence"
        assert cues[1].duration_ms == 420

    def test_build_opening_cues_no_effect(self):
        cues = RenderPlanner._build_opening_cues(None)

        assert len(cues) == 2
        assert cues[0].item_type == "music"
        assert cues[0].duration_ms == 10000  # default

    def test_build_transition_cues(self):
        effect = {"effect_type": "effect", "duration": "2s", "description": "transition sound"}
        cues = RenderPlanner._build_transition_cues(effect)

        assert len(cues) == 3
        # effect, music, silence
        assert cues[0].item_type == "effect"
        assert cues[1].item_type == "music"
        assert cues[1].metadata["role"] == "transition_sting"
        assert cues[2].item_type == "silence"

    def test_build_closing_suffix_cues_with_music(self):
        effect = {"effect_type": "music", "duration": "9s", "description": "outro music"}
        cues = RenderPlanner._build_closing_suffix_cues(effect)

        assert len(cues) == 2
        assert cues[0].item_type == "silence"  # voice_to_tail gap
        assert cues[1].item_type == "music"
        assert cues[1].metadata["role"] == "closing_tail"

    def test_build_closing_suffix_cues_without_music(self):
        effect = {"effect_type": "effect", "duration": "2s"}
        cues = RenderPlanner._build_closing_suffix_cues(effect)

        assert len(cues) == 0

    def test_build_generic_effect_item(self):
        effect = {"effect_type": "effect", "duration": "3s", "description": "sound effect"}
        item = RenderPlanner._build_generic_effect_item("main_content", effect)

        assert item.item_type == "effect"
        assert item.duration_ms == 3000
        assert item.metadata["section_type"] == "main_content"
        assert item.metadata["description"] == "sound effect"

    def test_build_generic_effect_item_invalid_type(self):
        effect = {"effect_type": "unknown", "duration": "1s"}
        item = RenderPlanner._build_generic_effect_item("main_content", effect)

        assert item.item_type == "effect"  # Falls back to effect


class TestRenderPlanItem:
    """Test RenderPlanItem dataclass."""

    def test_render_plan_item_creation(self):
        item = RenderPlanItem(
            item_type="speech",
            text="Hello",
            voice="male",
            duration_ms=5000,
        )

        assert item.item_type == "speech"
        assert item.text == "Hello"
        assert item.voice == "male"
        assert item.duration_ms == 5000

    def test_render_plan_item_defaults(self):
        item = RenderPlanItem(item_type="silence")

        assert item.item_type == "silence"
        assert item.duration_ms is None
        assert item.text is None
        assert item.voice is None
        assert item.metadata == {}


class TestRenderPlan:
    """Test RenderPlan dataclass."""

    def test_render_plan_creation(self):
        items = [
            RenderPlanItem(item_type="music", duration_ms=10000),
            RenderPlanItem(item_type="silence", duration_ms=500),
        ]
        plan = RenderPlan(title="Test Podcast", items=items)

        assert plan.title == "Test Podcast"
        assert len(plan.items) == 2

    def test_render_plan_empty_items(self):
        plan = RenderPlan(title="Empty Podcast")
        assert len(plan.items) == 0
