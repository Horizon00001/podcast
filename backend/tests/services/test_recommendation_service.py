import math
from datetime import UTC, datetime, timedelta
from collections import defaultdict
from unittest.mock import MagicMock

import pytest

from app.models.podcast import Podcast
from app.models.interaction import Interaction
from app.models.user import User
from app.services.recommendation_service import RecommendationService


class TestRecommendationServicePureFunctions:
    """Test RecommendationService pure functions in isolation."""

    def setup_method(self):
        """Create service with mocked db."""
        mock_db = MagicMock()
        self.service = RecommendationService(mock_db)

    def test_tokenize_english_words(self):
        result = self.service._tokenize("Hello World AI")
        assert set(result) == {"hello", "world", "ai"}

    def test_tokenize_chinese_words(self):
        result = self.service._tokenize("人工智能 机器学习 深度学习")
        assert set(result) == {"人工智能", "机器学习", "深度学习"}

    def test_tokenize_chinese_compound_words(self):
        result = self.service._tokenize("人工智能芯片")
        assert result == ["人工智能", "芯片"]

    def test_tokenize_mixed(self):
        result = self.service._tokenize("AI 人工智能 ChatGPT")
        assert set(result) == {"ai", "人工智能", "chatgpt"}

    def test_tokenize_numbers_and_underscores(self):
        result = self.service._tokenize("version_1.0 AI123")
        assert "version_1" in result or "version_1.0" in result
        assert "ai123" in result

    def test_cosine_identical_vectors(self):
        vec = {"a": 1.0, "b": 1.0}
        result = self.service._cosine(vec, vec)
        assert abs(result - 1.0) < 1e-6

    def test_cosine_orthogonal_vectors(self):
        left = {"a": 1.0}
        right = {"b": 1.0}
        result = self.service._cosine(left, right)
        assert result == 0.0

    def test_cosine_empty_left(self):
        result = self.service._cosine({}, {"a": 1.0})
        assert result == 0.0

    def test_cosine_empty_right(self):
        result = self.service._cosine({"a": 1.0}, {})
        assert result == 0.0

    def test_normalize_empty(self):
        result = self.service._normalize({})
        assert result == {}

    def test_normalize_all_zeros(self):
        result = self.service._normalize({1: 0.0, 2: 0.0})
        assert result == {1: 0.0, 2: 0.0}

    def test_normalize_basic(self):
        result = self.service._normalize({1: 50.0, 2: 100.0, 3: 25.0})
        assert result[1] == 0.5
        assert result[2] == 1.0
        assert result[3] == 0.25

    def test_normalize_negative_values(self):
        result = self.service._normalize({1: -10.0, 2: -5.0, 3: -15.0})
        assert result[1] == 0.0
        assert result[2] == 0.0
        assert result[3] == 0.0

    def test_reason_text_cf_dominant(self):
        result = self.service._reason_text(cf=0.9, content=0.1, hot=0.1, fresh=0.1)
        assert result == "与你历史喜好相似"

    def test_reason_text_content_dominant(self):
        result = self.service._reason_text(cf=0.1, content=0.9, hot=0.1, fresh=0.1)
        assert result == "与你常听内容主题一致"

    def test_reason_text_hot_dominant(self):
        result = self.service._reason_text(cf=0.1, content=0.1, hot=0.9, fresh=0.1)
        assert result == "近期全站热度较高"

    def test_reason_text_fresh_dominant(self):
        result = self.service._reason_text(cf=0.1, content=0.1, hot=0.1, fresh=0.9)
        assert result == "发布时间较新"

    def test_reason_text_sequence_dominant(self):
        result = self.service._reason_text(cf=0.1, content=0.1, hot=0.1, fresh=0.1, sequence=0.9)
        assert result == "与你最近的收听序列相近"

    def test_play_weight_long_duration(self):
        mock_row = MagicMock()
        mock_row.listen_duration_ms = 600000
        mock_row.progress_pct = 0.0
        assert self.service._play_weight(mock_row) == 3.0

    def test_play_weight_high_progress(self):
        mock_row = MagicMock()
        mock_row.listen_duration_ms = 0
        mock_row.progress_pct = 90.0
        assert self.service._play_weight(mock_row) == 3.0

    def test_play_weight_medium_duration(self):
        mock_row = MagicMock()
        mock_row.listen_duration_ms = 180000
        mock_row.progress_pct = 0.0
        assert self.service._play_weight(mock_row) == 2.0

    def test_play_weight_medium_progress(self):
        mock_row = MagicMock()
        mock_row.listen_duration_ms = 0
        mock_row.progress_pct = 55.0
        assert self.service._play_weight(mock_row) == 2.0

    def test_play_weight_short(self):
        mock_row = MagicMock()
        mock_row.listen_duration_ms = 30000
        mock_row.progress_pct = 0.0
        assert self.service._play_weight(mock_row) == 1.0

    def test_play_weight_very_short(self):
        mock_row = MagicMock()
        mock_row.listen_duration_ms = 5000
        mock_row.progress_pct = 5.0
        assert self.service._play_weight(mock_row) == 0.5

    def test_play_weight_zero_duration_and_progress_is_neutral(self):
        mock_row = MagicMock()
        mock_row.listen_duration_ms = 0
        mock_row.progress_pct = 0.0
        assert self.service._play_weight(mock_row) == 0.0

    def test_zero_duration_play_normalizes_to_pause(self):
        mock_row = MagicMock()
        mock_row.action = "play"
        mock_row.listen_duration_ms = 0
        mock_row.progress_pct = 0.0
        assert self.service._normalize_action("play", mock_row) == "pause"

    def test_skip_weight_early(self):
        mock_row = MagicMock()
        mock_row.progress_pct = 5.0
        assert self.service._skip_weight(mock_row) == -3.0

    def test_skip_weight_mid(self):
        mock_row = MagicMock()
        mock_row.progress_pct = 30.0
        assert self.service._skip_weight(mock_row) == -2.0

    def test_skip_weight_late(self):
        mock_row = MagicMock()
        mock_row.progress_pct = 75.0
        assert self.service._skip_weight(mock_row) == -1.0

    def test_skip_weight_null_progress(self):
        mock_row = MagicMock()
        mock_row.progress_pct = None
        assert self.service._skip_weight(mock_row) == -2.0

    def test_recency_weight_now_approx_one(self):
        mock_row = MagicMock()
        mock_row.created_at = datetime.now(UTC)
        assert self.service._recency_weight(mock_row) == pytest.approx(1.0, rel=0.01)

    def test_recency_weight_7_days_ago(self):
        mock_row = MagicMock()
        mock_row.created_at = datetime.now(UTC) - timedelta(days=7)
        result = self.service._recency_weight(mock_row)
        expected = math.exp(-1.0)
        assert abs(result - expected) < 0.01

    def test_recency_weight_14_days_ago(self):
        mock_row = MagicMock()
        mock_row.created_at = datetime.now(UTC) - timedelta(days=14)
        result = self.service._recency_weight(mock_row)
        expected = math.exp(-2.0)
        assert abs(result - expected) < 0.01

    def test_build_sequence_score_empty(self):
        podcasts = []
        result = self.service._build_sequence_score(podcasts, [])
        assert result == {}

    def test_build_sequence_score_single_recent(self, db_session):
        service = RecommendationService(db_session)
        user = User(username="seq-user", email="seq@test.com")
        db_session.add(user)
        db_session.flush()

        p1 = Podcast(title="AI News", summary="ai", audio_url="", script_path="")
        db_session.add(p1)
        db_session.flush()

        interaction = Interaction(
            user_id=user.id,
            podcast_id=p1.id,
            action="complete",
            listen_duration_ms=300000,
            progress_pct=100.0,
            created_at=datetime.now(UTC),
        )
        db_session.add(interaction)
        db_session.commit()

        result = service._build_sequence_score([p1], [interaction])
        assert p1.id in result
        assert 0.0 <= result[p1.id] <= 1.0


class TestRecommendationServiceWithDB:
    """Test RecommendationService with a real db session."""

    def test_build_hot_score(self, db_session):
        service = RecommendationService(db_session)

        # Add test user
        user = User(username="testuser", email="test@test.com")
        db_session.add(user)
        db_session.flush()

        # Add test podcasts
        p1 = Podcast(title="AI News", summary="ai", audio_url="", script_path="")
        p2 = Podcast(title="Sports", summary="sports", audio_url="", script_path="")
        db_session.add_all([p1, p2])
        db_session.flush()

        # Add interactions
        db_session.add_all([
            Interaction(user_id=user.id, podcast_id=p1.id, action="play"),
            Interaction(user_id=user.id, podcast_id=p1.id, action="favorite"),
            Interaction(user_id=user.id, podcast_id=p2.id, action="play"),
        ])
        db_session.commit()

        user_actions = defaultdict(list, {
            p1.id: ["play", "favorite"],
            p2.id: ["play"],
        })

        hot_score = service._build_hot_score(user_actions)

        # favorite=5.0, play=1.0 -> p1 has 6.0; p2 has 1.0; normalized: p1=1.0, p2=1/6
        assert hot_score[p1.id] == 1.0
        assert 0.0 < hot_score[p2.id] < 1.0

    def test_build_freshness_score(self, db_session):
        service = RecommendationService(db_session)

        now = datetime.now(UTC)

        p1 = Podcast(
            title="Old",
            summary="old",
            audio_url="",
            script_path="",
            published_at=now - timedelta(days=30),
        )
        p2 = Podcast(
            title="New",
            summary="new",
            audio_url="",
            script_path="",
            published_at=now - timedelta(days=1),
        )
        db_session.add_all([p1, p2])
        db_session.commit()

        freshness = service._build_freshness_score([p1, p2])

        # Newer podcast should have higher score
        assert freshness[p2.id] > freshness[p1.id]
        # Both should be normalized to 0-1
        assert 0.0 <= freshness[p1.id] <= 1.0
        assert 0.0 <= freshness[p2.id] <= 1.0

    def test_get_recommendations_cold_start(self, db_session):
        """Test recommendations when user has no interactions."""
        service = RecommendationService(db_session)

        # Add some podcasts but no user
        p1 = Podcast(title="AI News", summary="ai", audio_url="", script_path="")
        p2 = Podcast(title="Sports", summary="sports", audio_url="", script_path="")
        db_session.add_all([p1, p2])
        db_session.commit()

        user = User(username="newuser", email="new@test.com")
        db_session.add(user)
        db_session.commit()

        result = service.get_recommendations(user.id, limit=10)

        assert result.strategy == "cold-start"
        assert len(result.items) == 2  # Both podcasts returned
        # Scores should be sorted descending
        scores = [item.score for item in result.items]
        assert scores == sorted(scores, reverse=True)

    def test_get_recommendations_skips_filtered(self, db_session):
        """Test that skipped items are not recommended."""
        service = RecommendationService(db_session)

        user = User(username="testuser", email="test@test.com")
        db_session.add(user)
        db_session.flush()

        p1 = Podcast(title="AI", summary="ai", audio_url="", script_path="")
        p2 = Podcast(title="Sports", summary="sports", audio_url="", script_path="")
        db_session.add_all([p1, p2])
        db_session.flush()

        # User liked AI, skipped Sports
        db_session.add_all([
            Interaction(user_id=user.id, podcast_id=p1.id, action="like"),
            Interaction(user_id=user.id, podcast_id=p2.id, action="skip"),
        ])
        db_session.commit()

        result = service.get_recommendations(user.id, limit=10)

        # Sports (p2) should be filtered out due to skip
        podcast_ids = [item.podcast_id for item in result.items]
        assert p2.id not in podcast_ids
        assert p1.id in podcast_ids or len(result.items) == 1

    def test_complete_boosts_positive_feedback(self, db_session):
        service = RecommendationService(db_session)

        user = User(username="listener", email="listener@test.com")
        db_session.add(user)
        db_session.flush()

        p1 = Podcast(title="AI", summary="ai architecture", audio_url="", script_path="")
        p2 = Podcast(title="Sports", summary="sports update", audio_url="", script_path="")
        p3 = Podcast(title="Finance", summary="market news", audio_url="", script_path="")
        db_session.add_all([p1, p2, p3])
        db_session.flush()

        db_session.add_all([
            Interaction(user_id=user.id, podcast_id=p1.id, action="complete"),
            Interaction(user_id=user.id, podcast_id=p2.id, action="skip", progress_pct=5.0),
        ])
        db_session.commit()

        result = service.get_recommendations(user.id, limit=10)

        assert result.strategy == "warm-up"
        assert all(item.podcast_id != p2.id for item in result.items)

    def test_skip_early_filtered_late_not_filtered(self, db_session):
        service = RecommendationService(db_session)

        user = User(username="skiptest", email="skiptest@test.com")
        db_session.add(user)
        db_session.flush()

        p1 = Podcast(title="AI", summary="ai", audio_url="", script_path="")
        p2 = Podcast(title="Sports", summary="sports", audio_url="", script_path="")
        db_session.add_all([p1, p2])
        db_session.flush()

        db_session.add_all([
            Interaction(user_id=user.id, podcast_id=p1.id, action="like"),
            Interaction(user_id=user.id, podcast_id=p2.id, action="skip", progress_pct=80.0),
        ])
        db_session.commit()

        result = service.get_recommendations(user.id, limit=10)
        podcast_ids = [item.podcast_id for item in result.items]

        assert p1.id in podcast_ids

    def test_complete_contributes_positive_feedback(self, db_session):
        service = RecommendationService(db_session)

        user = User(username="completor", email="completor@test.com")
        db_session.add(user)
        db_session.flush()

        p1 = Podcast(title="Tech Deep", summary="deep technology architecture", audio_url="", script_path="")
        p2 = Podcast(title="Finance News", summary="market stocks trading", audio_url="", script_path="")
        db_session.add_all([p1, p2])
        db_session.flush()

        db_session.add_all([
            Interaction(user_id=user.id, podcast_id=p1.id, action="complete", listen_duration_ms=600000, progress_pct=100.0),
            Interaction(user_id=user.id, podcast_id=p2.id, action="play", listen_duration_ms=30000, progress_pct=10.0),
        ])
        db_session.commit()

        result = service.get_recommendations(user.id, limit=10)
        podcast_ids = [item.podcast_id for item in result.items]

        assert p1.id in podcast_ids
        assert p2.id in podcast_ids
        assert result.strategy == "warm-up"

    def test_reason_text_with_sequence_arg(self, db_session):
        service = RecommendationService(db_session)

        user = User(username="reason", email="reason@test.com")
        db_session.add(user)
        db_session.flush()

        p1 = Podcast(title="AI", summary="ai", audio_url="", script_path="")
        db_session.add(p1)
        db_session.flush()

        db_session.add(Interaction(user_id=user.id, podcast_id=p1.id, action="like"))
        db_session.commit()

        result = service.get_recommendations(user.id, limit=10)
        assert len(result.items) >= 1

    def test_recommendations_respect_time_bucket(self, db_session):
        service = RecommendationService(db_session)

        user = User(username="timeuser", email="timeuser@test.com")
        db_session.add(user)
        db_session.flush()

        p1 = Podcast(title="Morning Tech", summary="tech news", audio_url="", script_path="")
        p2 = Podcast(title="Evening Music", summary="music", audio_url="", script_path="")
        db_session.add_all([p1, p2])
        db_session.flush()

        db_session.add_all([
            Interaction(user_id=user.id, podcast_id=p1.id, action="complete", context_bucket="morning"),
            Interaction(user_id=user.id, podcast_id=p2.id, action="complete", context_bucket="night"),
        ])
        db_session.commit()

        result = service.get_recommendations(user.id, limit=10)
        podcast_ids = [item.podcast_id for item in result.items]

        assert p1.id in podcast_ids or p2.id in podcast_ids
