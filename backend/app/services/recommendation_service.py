import math
import re
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.interaction import Interaction
from app.models.podcast import Podcast
from app.schemas.recommendation import RecommendationItem, RecommendationResponse


ACTION_WEIGHT = {
    "favorite": 5.0,
    "like": 3.0,
    "complete": 3.0,
    "play": 1.0,
    "resume": 0.5,
    "pause": 0.0,
    "skip": -2.0,
}
POSITIVE_ACTIONS = {"favorite", "like", "play", "complete"}
NEGATIVE_ACTIONS = {"skip"}


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db

    def get_recommendations(self, user_id: int, limit: int = 20) -> RecommendationResponse:
        podcasts = self.db.query(Podcast).all()
        if not podcasts:
            return RecommendationResponse(user_id=user_id, strategy="hybrid-v1", items=[])

        interactions = self.db.query(Interaction).all()
        user_actions: dict[int, list[str]] = defaultdict(list)
        user_positive_score: dict[int, float] = defaultdict(float)
        user_skipped: set[int] = set()
        user_item_weights: dict[int, float] = defaultdict(float)
        user_recent_interactions: list[Interaction] = []

        for row in interactions:
            action = self._normalize_action(row.action, row)
            user_actions[row.podcast_id].append(action)
            if row.user_id != user_id:
                continue

            weight = ACTION_WEIGHT.get(action, 0.0)
            if action == "skip":
                weight = self._skip_weight(row)
            elif action == "play":
                weight = self._play_weight(row)

            user_item_weights[row.podcast_id] += weight
            if action in POSITIVE_ACTIONS:
                user_positive_score[row.podcast_id] += weight
                user_recent_interactions.append(row)
            elif action in NEGATIVE_ACTIONS:
                user_skipped.add(row.podcast_id)

        hot_score = self._build_hot_score(user_actions)
        cf_score = self._build_cf_score(interactions, user_positive_score)
        content_score = self._build_content_score(podcasts, user_positive_score)
        fresh_score = self._build_freshness_score(podcasts)
        sequence_score = self._build_sequence_score(podcasts, user_recent_interactions)

        interacted_items = set(user_item_weights.keys())
        candidates = [p.id for p in podcasts if p.id not in interacted_items and p.id not in user_skipped]
        if not candidates:
            candidates = [p.id for p in podcasts if p.id not in user_skipped]

        ranked: list[tuple[int, float, str]] = []
        for podcast_id in candidates:
            cf = cf_score.get(podcast_id, 0.0)
            content = content_score.get(podcast_id, 0.0)
            hot = hot_score.get(podcast_id, 0.0)
            fresh = fresh_score.get(podcast_id, 0.0)
            sequence = sequence_score.get(podcast_id, 0.0)

            final_score = 0.40 * cf + 0.25 * content + 0.15 * hot + 0.10 * sequence + 0.10 * fresh
            reason = self._reason_text(cf, content, hot, fresh, sequence)
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
        return RecommendationResponse(user_id=user_id, strategy="hybrid-v1", items=items)

    def _build_hot_score(self, user_actions: dict[int, list[str]]) -> dict[int, float]:
        raw: dict[int, float] = {}
        for podcast_id, actions in user_actions.items():
            score = sum(ACTION_WEIGHT.get(action, 0.0) for action in actions)
            raw[podcast_id] = max(score, 0.0)
        return self._normalize(raw)

    def _build_cf_score(
        self,
        interactions: list[Interaction],
        user_positive_score: dict[int, float],
    ) -> dict[int, float]:
        if not user_positive_score:
            return {}

        positive_by_user: dict[int, set[int]] = defaultdict(set)
        for row in interactions:
            if row.action in POSITIVE_ACTIONS:
                positive_by_user[row.user_id].add(row.podcast_id)

        item_freq: dict[int, int] = defaultdict(int)
        cooccur: dict[tuple[int, int], float] = defaultdict(float)

        for items in positive_by_user.values():
            if not items:
                continue
            norm = 1.0 / math.sqrt(len(items))
            for i in items:
                item_freq[i] += 1
                for j in items:
                    if i == j:
                        continue
                    cooccur[(i, j)] += norm

        score: dict[int, float] = defaultdict(float)
        for base_item, base_weight in user_positive_score.items():
            for (i, j), cij in cooccur.items():
                if i != base_item:
                    continue
                denom = math.sqrt(item_freq.get(i, 1) * item_freq.get(j, 1))
                sim = cij / denom if denom else 0.0
                score[j] += sim * base_weight

        return self._normalize(score)

    def _build_content_score(
        self,
        podcasts: list[Podcast],
        user_positive_score: dict[int, float],
    ) -> dict[int, float]:
        if not user_positive_score:
            return {}

        documents: dict[int, list[str]] = {}
        df: dict[str, int] = defaultdict(int)
        for podcast in podcasts:
            text = " ".join(
                [
                    podcast.title or "",
                    podcast.summary or "",
                    getattr(podcast, "category", "") or "",
                ]
            )
            tokens = self._tokenize(text)
            documents[podcast.id] = tokens
            for token in set(tokens):
                df[token] += 1

        total_docs = max(len(documents), 1)
        vectors: dict[int, dict[str, float]] = {}
        for podcast_id, tokens in documents.items():
            tf: dict[str, float] = defaultdict(float)
            for token in tokens:
                tf[token] += 1.0
            length = max(len(tokens), 1)
            vec = {}
            for token, count in tf.items():
                idf = math.log((1 + total_docs) / (1 + df[token])) + 1.0
                vec[token] = (count / length) * idf
            vectors[podcast_id] = vec

        profile: dict[str, float] = defaultdict(float)
        for podcast_id, weight in user_positive_score.items():
            for token, value in vectors.get(podcast_id, {}).items():
                profile[token] += value * weight

        score: dict[int, float] = {}
        for podcast_id, vec in vectors.items():
            score[podcast_id] = self._cosine(profile, vec)
        return self._normalize(score)

    def _build_freshness_score(self, podcasts: list[Podcast]) -> dict[int, float]:
        now = datetime.now(UTC)
        freshness: dict[int, float] = {}
        half_life_days = 7.0
        for podcast in podcasts:
            published = podcast.published_at
            if published.tzinfo is None:
                published = published.replace(tzinfo=UTC)
            age_days = max((now - published).total_seconds() / 86400.0, 0.0)
            freshness[podcast.id] = math.exp(-age_days / half_life_days)
        return self._normalize(freshness)

    def _reason_text(self, cf: float, content: float, hot: float, fresh: float, sequence: float = 0.0) -> str:
        reason_signals = {
            "与你历史喜好相似": cf,
            "与你常听内容主题一致": content,
            "近期全站热度较高": hot,
            "发布时间较新": fresh,
            "与你最近的收听序列相近": sequence,
        }
        return max(reason_signals.items(), key=lambda item: item[1])[0]

    def _normalize_action(self, action: str, row: Interaction) -> str:
        if action == "skip" and row.progress_pct is not None:
            return "skip"
        return action

    def _play_weight(self, row: Interaction) -> float:
        duration = row.listen_duration_ms or 0
        progress = row.progress_pct or 0.0
        if duration >= 10 * 60 * 1000 or progress >= 85:
            return 3.0
        if duration >= 3 * 60 * 1000 or progress >= 50:
            return 2.0
        if duration >= 30 * 1000 or progress >= 10:
            return 1.0
        return 0.5

    def _skip_weight(self, row: Interaction) -> float:
        progress = row.progress_pct
        if progress is None:
            return -2.0
        if progress <= 10:
            return -3.0
        if progress <= 50:
            return -2.0
        return -1.0

    def _recency_weight(self, row: Interaction) -> float:
        bucket = row.context_bucket or ""
        if bucket in {"morning", "commute", "evening"}:
            return 1.5
        if row.context_hour is not None and 7 <= row.context_hour <= 23:
            return 1.0
        return 0.5

    def _build_sequence_score(
        self,
        podcasts: list[Podcast],
        user_recent_interactions: list[Interaction],
    ) -> dict[int, float]:
        if not user_recent_interactions:
            return {}

        recent_items = sorted(user_recent_interactions, key=lambda row: row.created_at, reverse=True)[:5]
        recent_profile: dict[str, float] = defaultdict(float)

        for index, row in enumerate(recent_items):
            podcast = next((item for item in podcasts if item.id == row.podcast_id), None)
            if not podcast:
                continue
            recency = 1.0 / (index + 1)
            text = " ".join([
                podcast.title or "",
                podcast.summary or "",
                getattr(podcast, "category", "") or "",
            ])
            tokens = self._tokenize(text)
            weight = recency * self._play_weight(row)
            for token in tokens:
                recent_profile[token] += weight

        score: dict[int, float] = {}
        for podcast in podcasts:
            text = " ".join([
                podcast.title or "",
                podcast.summary or "",
                getattr(podcast, "category", "") or "",
            ])
            tokens = self._tokenize(text)
            vec: dict[str, float] = defaultdict(float)
            for token in tokens:
                vec[token] += 1.0
            score[podcast.id] = self._cosine(recent_profile, vec)

        return self._normalize(score)

    def _normalize(self, values: dict[int, float]) -> dict[int, float]:
        if not values:
            return {}
        max_value = max(values.values())
        if max_value <= 0:
            return {k: 0.0 for k in values}
        return {k: v / max_value for k, v in values.items()}

    def _tokenize(self, text: str) -> list[str]:
        # 同时支持英文词和连续中文词，便于中英混合标题/摘要匹配。
        return [token.lower() for token in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", text)]

    def _cosine(self, left: dict[str, float], right: dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        dot = sum(value * right.get(token, 0.0) for token, value in left.items())
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)
