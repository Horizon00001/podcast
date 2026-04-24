"""Pydantic schema validation tests for all schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.podcast import PodcastBase, PodcastCreate, PodcastResponse
from app.schemas.user import UserCreate, UserResponse
from app.schemas.interaction import InteractionCreate, InteractionResponse
from app.schemas.recommendation import RecommendationItem, RecommendationResponse
from app.schemas.generation import (
    RSSSource, RSSSourceListResponse,
    TopicOption, TopicOptionListResponse,
    GenerationTriggerRequest, GenerationTriggerResponse, GenerationTaskStatusResponse,
)
from app.schemas.script import AudioEffect, DialogueTurn, PodcastSection, PodcastScript


class TestPodcastSchemas:
    def test_podcast_base_requires_title(self):
        PodcastBase(title="Hello")
        with pytest.raises(ValidationError):
            PodcastBase()

    def test_podcast_base_default_summary(self):
        p = PodcastBase(title="T")
        assert p.summary == ""
        assert p.category == "general"

    def test_podcast_create_defaults(self):
        p = PodcastCreate(title="T")
        assert p.audio_url == ""
        assert p.script_path == ""

    def test_podcast_response_from_attributes(self):
        """Verify PodcastResponse can work with orm_mode style data."""
        p = PodcastResponse(
            id=1, title="Test", summary="S", category="tech",
            audio_url="/a.mp3", script_path="/s.json",
            published_at="2024-01-01T00:00:00",
        )
        assert p.id == 1
        assert p.title == "Test"


class TestUserSchemas:
    def test_user_create_valid(self):
        u = UserCreate(username="alice", email="alice@example.com")
        assert u.username == "alice"

    def test_user_create_invalid_email(self):
        with pytest.raises(ValidationError):
            UserCreate(username="bob", email="not-an-email")

    def test_user_create_missing_email(self):
        with pytest.raises(ValidationError):
            UserCreate(username="bob")

    def test_user_response_fields(self):
        u = UserResponse(
            id=1, username="carol", email="carol@test.com",
            created_at="2024-01-01T00:00:00",
        )
        assert u.id == 1
        assert u.email == "carol@test.com"


class TestInteractionSchemas:
    def test_interaction_create_valid(self):
        i = InteractionCreate(user_id=1, podcast_id=2, action="play")
        assert i.action == "play"

    def test_interaction_create_all_actions(self):
        for action in ["play", "pause", "resume", "like", "favorite", "skip", "complete"]:
            i = InteractionCreate(user_id=1, podcast_id=1, action=action)
            assert i.action == action

    def test_interaction_create_invalid_action(self):
        with pytest.raises(ValidationError):
            InteractionCreate(user_id=1, podcast_id=1, action="unknown")

    def test_interaction_create_optional_fields_default_none(self):
        i = InteractionCreate(user_id=1, podcast_id=1, action="play")
        assert i.listen_duration_ms is None
        assert i.progress_pct is None
        assert i.session_id is None
        assert i.context_hour is None
        assert i.context_weekday is None
        assert i.context_bucket is None

    def test_interaction_create_with_all_fields(self):
        i = InteractionCreate(
            user_id=1, podcast_id=2, action="complete",
            listen_duration_ms=120000, progress_pct=100.0,
            session_id="sess-xyz", context_hour=10,
            context_weekday=1, context_bucket="morning",
        )
        assert i.listen_duration_ms == 120000
        assert i.progress_pct == 100.0

    def test_interaction_response_includes_id(self):
        i = InteractionResponse(
            id=42, user_id=1, podcast_id=2, action="like",
            created_at="2024-01-01T00:00:00",
        )
        assert i.id == 42


class TestRecommendationSchemas:
    def test_recommendation_item(self):
        item = RecommendationItem(podcast_id=1, score=0.85, reason="热门内容")
        assert item.score == 0.85

    def test_recommendation_response(self):
        resp = RecommendationResponse(
            user_id=1, strategy="hybrid-v1", request_id="req-test-1",
            items=[RecommendationItem(podcast_id=1, score=0.9, reason="协同过滤")],
        )
        assert resp.strategy == "hybrid-v1"
        assert len(resp.items) == 1

    def test_recommendation_response_empty_items(self):
        resp = RecommendationResponse(user_id=1, strategy="hybrid-v1", request_id="req-test-2", items=[])
        assert resp.items == []


class TestGenerationSchemas:
    def test_rss_source(self):
        s = RSSSource(id="hn", name="Hacker News", url="https://hn.rss", category="tech")
        assert s.id == "hn"

    def test_topic_option(self):
        t = TopicOption(id="daily-news", name="每日新闻", description="综合新闻")
        assert t.id == "daily-news"

    def test_generation_trigger_request_defaults(self):
        r = GenerationTriggerRequest()
        assert r.rss_source == "default"
        assert r.topic == "daily-news"

    def test_generation_trigger_response(self):
        r = GenerationTriggerResponse(task_id="abc", status="queued", message="ok")
        assert r.task_id == "abc"

    def test_generation_task_status_response(self):
        r = GenerationTaskStatusResponse(
            task_id="t1", status="running", message="...",
            rss_source="default", topic="daily-news",
            created_at="2024-01-01T00:00:00", updated_at="2024-01-01T00:01:00",
        )
        assert r.status == "running"


class TestAudioEffectSchema:
    def test_valid_effect_types(self):
        for etype in ("music", "effect", "silence"):
            effect = AudioEffect(effect_type=etype, description="desc", duration="10s")
            assert effect.effect_type == etype

    def test_invalid_effect_type(self):
        with pytest.raises(ValidationError):
            AudioEffect(effect_type="invalid", description="x", duration="1s")


class TestDialogueTurnSchema:
    def test_valid_speakers(self):
        for speaker in ("A", "B"):
            d = DialogueTurn(speaker=speaker, content="Hello")
            assert d.speaker == speaker

    def test_default_emotion(self):
        d = DialogueTurn(speaker="A", content="Hi")
        assert d.emotion == ""

    def test_with_emotion(self):
        d = DialogueTurn(speaker="A", content="Wow!", emotion="excited")
        assert d.emotion == "excited"

    def test_invalid_speaker(self):
        with pytest.raises(ValidationError):
            DialogueTurn(speaker="C", content="Hello")


class TestPodcastSectionSchema:
    def test_valid_section(self):
        section = PodcastSection(
            section_type="opening",
            dialogues=[
                DialogueTurn(speaker="A", content="你好"),
                DialogueTurn(speaker="B", content="你好啊"),
            ],
        )
        assert section.section_type == "opening"
        assert section.summary == ""

    def test_section_with_less_than_two_dialogues(self):
        with pytest.raises(ValueError, match="至少需要 2 句对话"):
            PodcastSection(
                section_type="opening",
                dialogues=[DialogueTurn(speaker="A", content="Hello")],
            )

    def test_section_consecutive_same_speaker(self):
        with pytest.raises(ValueError, match="连续相同说话者"):
            PodcastSection(
                section_type="main_content",
                dialogues=[
                    DialogueTurn(speaker="A", content="1"),
                    DialogueTurn(speaker="A", content="2"),
                ],
            )

    def test_section_valid_alternating(self):
        section = PodcastSection(
            section_type="main_content",
            dialogues=[
                DialogueTurn(speaker="A", content="1"),
                DialogueTurn(speaker="B", content="2"),
                DialogueTurn(speaker="A", content="3"),
            ],
        )
        assert len(section.dialogues) == 3

    def test_section_all_valid_types(self):
        for stype in ("opening", "transition", "main_content", "closing"):
            section = PodcastSection(
                section_type=stype,
                dialogues=[
                    DialogueTurn(speaker="A", content="a"),
                    DialogueTurn(speaker="B", content="b"),
                ],
            )
            assert section.section_type == stype

    def test_section_with_audio_effect(self):
        effect = AudioEffect(effect_type="music", description="开场音乐", duration="10s")
        section = PodcastSection(
            section_type="opening",
            audio_effect=effect,
            dialogues=[
                DialogueTurn(speaker="A", content="a"),
                DialogueTurn(speaker="B", content="b"),
            ],
        )
        assert section.audio_effect.effect_type == "music"


class TestPodcastScriptSchema:
    def make_section(self, speaker_a_count=2, speaker_b_count=2, section_type="main_content"):
        dialogues = []
        for i in range(max(speaker_a_count, speaker_b_count)):
            if i < speaker_a_count:
                dialogues.append(DialogueTurn(speaker="A", content=f"A{i}"))
            if i < speaker_b_count:
                dialogues.append(DialogueTurn(speaker="B", content=f"B{i}"))
        return PodcastSection(section_type=section_type, dialogues=dialogues)

    def test_valid_full_script(self):
        script = PodcastScript(
            title="今日新闻",
            intro="欢迎收听",
            sections=[
                self.make_section(),
                self.make_section(),
            ],
            total_duration="5分钟",
        )
        assert script.title == "今日新闻"

    def test_consecutive_same_speaker_caught_by_section(self):
        """Section validator rejects non-alternating dialogues before Script sees it."""
        with pytest.raises(ValueError, match="连续相同说话者"):
            PodcastSection(
                section_type="opening",
                dialogues=[
                    DialogueTurn(speaker="A", content="1"),
                    DialogueTurn(speaker="A", content="2"),
                ],
            )

    def test_script_validator_requires_both_speakers(self):
        """Empty sections = no speakers → Script-level validator raises."""
        with pytest.raises(ValueError, match="必须同时包含 A 与 B"):
            PodcastScript(
                title="T", intro="I",
                sections=[],  # no sections = no speakers
                total_duration="1min",
            )

    def test_format_for_output(self):
        script = PodcastScript(
            title="AI播客",
            intro="本期讨论AI进展",
            sections=[
                PodcastSection(
                    section_type="opening",
                    audio_effect=AudioEffect(effect_type="music", description="开场", duration="5s"),
                    dialogues=[
                        DialogueTurn(speaker="A", content="大家好", emotion=""),
                        DialogueTurn(speaker="B", content="你好", emotion=""),
                    ],
                ),
                PodcastSection(
                    section_type="closing",
                    dialogues=[
                        DialogueTurn(speaker="A", content="再见"),
                        DialogueTurn(speaker="B", content="下次见"),
                    ],
                ),
            ],
            total_duration="2分钟",
        )
        output = script.format_for_output()
        assert "AI播客" in output
        assert "[MUSIC]" in output
        assert "A：" in output
        assert "B：" in output

    def test_format_for_output_with_emotion(self):
        script = PodcastScript(
            title="Test", intro="Intro",
            sections=[
                PodcastSection(
                    section_type="opening",
                    dialogues=[
                        DialogueTurn(speaker="A", content="Wow!", emotion="excited"),
                        DialogueTurn(speaker="B", content="Great!", emotion="happy"),
                    ],
                ),
            ],
            total_duration="1min",
        )
        output = script.format_for_output()
        assert "（excited）" in output
        assert "（happy）" in output
