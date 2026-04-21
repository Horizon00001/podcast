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

        assert result.strategy == "hybrid-v1"
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
