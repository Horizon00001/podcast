import math
import re
import uuid
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
                bucket = row.context_bucket or self._guess_bucket(row.context_hour)
                bucket_profiles[bucket][row.podcast_id] += weight
            elif action in NEGATIVE_ACTIONS:
                user_skipped.add(row.podcast_id)

        pos_count = len(user_recent_interactions)

        # Seed content signal from preference tags (cold-start only)
        if pos_count == 0:
            preference_categories = self._load_user_preferences(user_id)
            if preference_categories:
                user_positive_score = self._seed_preference_score(podcasts, preference_categories)

        # Time-segmented content profile: blend current bucket with global
        now_bucket = self._current_bucket()
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

        hot_score = self._build_hot_score(user_actions)
        cf_score = self._build_cf_score(interactions, user_positive_score)
        content_score = self._build_content_score(podcasts, content_profile)
        fresh_score = self._build_freshness_score(podcasts)
        sequence_score = self._build_sequence_score(podcasts, user_recent_interactions)

        interacted_items = set(user_item_weights.keys())
        candidates = [p.id for p in podcasts if p.id not in interacted_items and p.id not in user_skipped]
        if not candidates:
            candidates = [p.id for p in podcasts if p.id not in user_skipped]

        strategy, cold_w, hybrid_w = self._strategy_blend(pos_count)

        ranked: list[tuple[int, float, str]] = []
        for podcast_id in candidates:
            cf = cf_score.get(podcast_id, 0.0)
            content = content_score.get(podcast_id, 0.0)
            hot = hot_score.get(podcast_id, 0.0)
            fresh = fresh_score.get(podcast_id, 0.0)
            sequence = sequence_score.get(podcast_id, 0.0)

            cold_score = 0.40 * hot + 0.30 * fresh + 0.30 * content
            hybrid_score = 0.40 * cf + 0.25 * content + 0.15 * hot + 0.10 * sequence + 0.10 * fresh
            final_score = cold_w * cold_score + hybrid_w * hybrid_score

            reason = self._reason_text(cf, content, hot, fresh, sequence, strategy)
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
        return RecommendationResponse(user_id=user_id, strategy=strategy, request_id=req_id, time_context=time_context, items=items)

    def _load_user_preferences(self, user_id: int) -> list[str]:
        import json

        from app.models.user import User

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.preferences:
            return []
        try:
            data = json.loads(user.preferences)
            return data.get("categories", [])
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _current_bucket() -> str:
        hour = datetime.now(UTC).hour
        if 6 <= hour < 12:
            return "morning"
        if 12 <= hour < 18:
            return "afternoon"
        if 18 <= hour < 23:
            return "evening"
        return "night"

    @staticmethod
    def _guess_bucket(context_hour: int | None) -> str:
        if context_hour is None:
            return "afternoon"
        if 6 <= context_hour < 12:
            return "morning"
        if 12 <= context_hour < 18:
            return "afternoon"
        if 18 <= context_hour < 23:
            return "evening"
        return "night"

    def _seed_preference_score(
        self, podcasts: list[Podcast], categories: list[str]
    ) -> dict[int, float]:
        score: dict[int, float] = {}
        category_set = set(categories)
        for podcast in podcasts:
            pc = getattr(podcast, "category", "") or ""
            if pc in category_set:
                score[podcast.id] = 1.0
            else:
                score[podcast.id] = 0.3
        return score

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

    def _strategy_blend(self, pos_count: int) -> tuple[str, float, float]:
        """Return (strategy_name, cold_weight, hybrid_weight).

        Ramp-up: n=0 → pure cold-start; n=1-2 → warm-up blend; n≥3 → pure hybrid.
        """
        if pos_count == 0:
            return ("cold-start", 1.0, 0.0)
        if pos_count <= 2:
            hybrid_ratio = pos_count / 3.0
            return ("warm-up", 1.0 - hybrid_ratio, hybrid_ratio)
        return ("hybrid-v1", 0.0, 1.0)

    def _reason_text(
        self,
        cf: float,
        content: float,
        hot: float,
        fresh: float,
        sequence: float = 0.0,
        strategy: str = "hybrid-v1",
    ) -> str:
        if strategy == "cold-start":
            reason_signals = {
                "全站热门推荐": hot,
                "新发布的播客": fresh,
            }
        elif strategy == "warm-up":
            reason_signals = {
                "全站热门推荐": hot,
                "新发布的播客": fresh,
                "与你历史喜好相似": cf,
            }
        else:
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
        now = datetime.now(UTC)
        created = row.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        days_ago = max((now - created).total_seconds() / 86400.0, 0.0)
        return math.exp(-days_ago / 7.0)

    def _build_sequence_score(
        self,
        podcasts: list[Podcast],
        user_recent_interactions: list[Interaction],
    ) -> dict[int, float]:
        if not user_recent_interactions:
            return {}

        # Deduplicate: keep only the most recent interaction per podcast
        seen: dict[int, Interaction] = {}
        for row in sorted(user_recent_interactions, key=lambda r: r.created_at, reverse=True):
            if row.podcast_id not in seen:
                seen[row.podcast_id] = row
        recent_items = sorted(seen.values(), key=lambda r: r.created_at, reverse=True)[:5]

        # Compute DF from the podcast corpus for IDF weighting
        df: dict[str, int] = defaultdict(int)
        for podcast in podcasts:
            text = " ".join([
                podcast.title or "",
                podcast.summary or "",
                getattr(podcast, "category", "") or "",
            ])
            tokens = set(self._tokenize(text))
            for token in tokens:
                df[token] += 1
        total_docs = max(len(podcasts), 1)

        recent_profile: dict[str, float] = defaultdict(float)
        for row in recent_items:
            podcast = next((item for item in podcasts if item.id == row.podcast_id), None)
            if not podcast:
                continue
            recency = self._recency_weight(row)
            text = " ".join([
                podcast.title or "",
                podcast.summary or "",
                getattr(podcast, "category", "") or "",
            ])
            tokens = self._tokenize(text)

            action = self._normalize_action(row.action, row)
            if action in ("play", "complete"):
                importance = self._play_weight(row)
            else:
                importance = ACTION_WEIGHT.get(action, 1.0)
            weight = recency * importance

            for token in tokens:
                idf = math.log((1 + total_docs) / (1 + df.get(token, 0))) + 1.0
                recent_profile[token] += weight * idf

        score: dict[int, float] = {}
        for podcast in podcasts:
            text = " ".join([
                podcast.title or "",
                podcast.summary or "",
                getattr(podcast, "category", "") or "",
            ])
            tokens = self._tokenize(text)
            tf: dict[str, float] = defaultdict(float)
            for token in tokens:
                tf[token] += 1.0
            length = max(len(tokens), 1)
            vec: dict[str, float] = {}
            for token, count in tf.items():
                idf = math.log((1 + total_docs) / (1 + df.get(token, 0))) + 1.0
                vec[token] = (count / length) * idf
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
