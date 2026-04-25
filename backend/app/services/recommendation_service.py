import json
import uuid
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.interaction import Interaction
from app.models.podcast import Podcast
from app.models.user import User
from app.schemas.recommendation import RecommendationItem, RecommendationResponse
from app.services.recommendation import StrategyFactory
from app.services.recommendation.scoring import (
    ACTION_WEIGHT,
    NEGATIVE_ACTIONS,
    POSITIVE_ACTIONS,
    ScoreContext,
    build_cf_score,
    build_content_score,
    build_freshness_score,
    build_hot_score,
    build_sequence_score,
    compute_reason_text,
    cosine_similarity,
    current_bucket,
    guess_bucket,
    normalize_action,
    normalize_scores,
    play_weight,
    recency_weight,
    seed_preference_score,
    skip_weight,
    tokenize,
)


class RecommendationService:
    # Backward-compatible static method proxies for existing tests.
    _tokenize = staticmethod(tokenize)
    _cosine = staticmethod(cosine_similarity)
    _normalize = staticmethod(normalize_scores)
    _play_weight = staticmethod(play_weight)
    _skip_weight = staticmethod(skip_weight)
    _recency_weight = staticmethod(recency_weight)
    _current_bucket = staticmethod(current_bucket)
    _guess_bucket = staticmethod(guess_bucket)
    _normalize_action = staticmethod(normalize_action)
    _build_hot_score = staticmethod(build_hot_score)
    _build_cf_score = staticmethod(build_cf_score)
    _build_content_score = staticmethod(build_content_score)
    _build_freshness_score = staticmethod(build_freshness_score)
    _build_sequence_score = staticmethod(build_sequence_score)
    _seed_preference_score = staticmethod(seed_preference_score)
    _reason_text = staticmethod(compute_reason_text)

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_recommendations(self, user_id: int, limit: int = 20) -> RecommendationResponse:
        req_id = f"rec_{uuid.uuid4().hex[:12]}"
        podcasts = self.db.query(Podcast).all()
        if not podcasts:
            return RecommendationResponse(user_id=user_id, strategy="hybrid-v1", request_id=req_id, time_context="global", items=[])

        interactions = self.db.query(Interaction).all()
        user_actions: dict[int, list[str]] = defaultdict(list)
        user_positive_score: dict[int, float] = defaultdict(float)
        user_skipped: set[int] = set()
        user_item_weights: dict[int, float] = defaultdict(float)
        user_recent_interactions: list[Interaction] = []

        # Per-bucket positive profiles for time-segmented recommendations
        bucket_profiles: dict[str, dict[int, float]] = {
            "morning": defaultdict(float),
            "afternoon": defaultdict(float),
            "evening": defaultdict(float),
            "night": defaultdict(float),
        }

        for row in interactions:
            action = normalize_action(row.action, row)
            user_actions[row.podcast_id].append(action)
            if row.user_id != user_id:
                continue

            weight = ACTION_WEIGHT.get(action, 0.0)
            if action == "skip":
                weight = skip_weight(row)
            elif action == "play":
                weight = play_weight(row)

            user_item_weights[row.podcast_id] += weight
            if action in POSITIVE_ACTIONS:
                user_positive_score[row.podcast_id] += weight
                user_recent_interactions.append(row)
                bucket = row.context_bucket or guess_bucket(row.context_hour)
                bucket_profiles[bucket][row.podcast_id] += weight
            elif action in NEGATIVE_ACTIONS:
                user_skipped.add(row.podcast_id)

        pos_count = len(user_recent_interactions)

        # Seed content signal from preference tags (cold-start only)
        if pos_count == 0:
            preference_categories = self._load_user_preferences(user_id)
            if preference_categories:
                user_positive_score = seed_preference_score(podcasts, preference_categories)

        # Time-segmented content profile: blend current bucket with global
        now_bucket = current_bucket()
        time_profile = bucket_profiles.get(now_bucket, {})
        time_count = sum(1 for v in time_profile.values() if v > 0)
        if time_count >= 3:
            content_profile = time_profile
            time_context = now_bucket
        elif time_count > 0:
            merge_w = time_count / 3.0
            content_profile = {}
            all_pids = set(time_profile.keys()) | set(user_positive_score.keys())
            for pid in all_pids:
                content_profile[pid] = merge_w * time_profile.get(pid, 0) + (1 - merge_w) * user_positive_score.get(pid, 0)
            time_context = f"{now_bucket}+global"
        else:
            content_profile = user_positive_score
            time_context = "global"

        hot_score = build_hot_score(user_actions)
        cf_score = build_cf_score(interactions, user_positive_score)
        content_score = build_content_score(podcasts, content_profile)
        fresh_score = build_freshness_score(podcasts)
        sequence_score = build_sequence_score(podcasts, user_recent_interactions)

        interacted_items = set(user_item_weights.keys())
        candidates = [p.id for p in podcasts if p.id not in interacted_items and p.id not in user_skipped]
        if not candidates:
            candidates = [p.id for p in podcasts if p.id not in user_skipped]

        # --- Strategy-based scoring ---
        strategy = StrategyFactory.get_strategy(pos_count)

        ranked: list[tuple[int, float, str]] = []
        for podcast_id in candidates:
            ctx = ScoreContext(
                cf=cf_score.get(podcast_id, 0.0),
                content=content_score.get(podcast_id, 0.0),
                hot=hot_score.get(podcast_id, 0.0),
                fresh=fresh_score.get(podcast_id, 0.0),
                sequence=sequence_score.get(podcast_id, 0.0),
            )
            final_score = strategy.compute_score(ctx)
            reason = strategy.select_reason(ctx)
            ranked.append((podcast_id, final_score, reason))

        ranked.sort(key=lambda item: item[1], reverse=True)
        items = [
            RecommendationItem(
                podcast_id=podcast_id,
                score=round(score, 4),
                reason=reason,
            )
            for podcast_id, score, reason in ranked[:limit]
        ]
        return RecommendationResponse(user_id=user_id, strategy=strategy.name, request_id=req_id, time_context=time_context, items=items)

    # ------------------------------------------------------------------
    # Instance methods (need self.db)
    # ------------------------------------------------------------------

    def _load_user_preferences(self, user_id: int) -> list[str]:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.preferences:
            return []
        try:
            data = json.loads(user.preferences)
            return data.get("categories", [])
        except (json.JSONDecodeError, TypeError):
            return []
