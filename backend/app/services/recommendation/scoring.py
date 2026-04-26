import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from app.models.interaction import Interaction
from app.models.podcast import Podcast
from app.services.text_tokenizer import tokenize_text


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


@dataclass
class ScoreContext:
    cf: float = 0.0
    content: float = 0.0
    hot: float = 0.0
    fresh: float = 0.0
    sequence: float = 0.0


# ---------------------------------------------------------------------------
# Tokenization & vector utilities
# ---------------------------------------------------------------------------


def tokenize(text: str) -> list[str]:
    return tokenize_text(text)


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(token, 0.0) for token, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def normalize_scores(values: dict[int, float]) -> dict[int, float]:
    if not values:
        return {}
    max_value = max(values.values())
    if max_value <= 0:
        return {k: 0.0 for k in values}
    return {k: v / max_value for k, v in values.items()}


# ---------------------------------------------------------------------------
# Interaction weighting helpers
# ---------------------------------------------------------------------------


def play_weight(row: Interaction) -> float:
    duration = row.listen_duration_ms or 0
    progress = row.progress_pct or 0.0
    if duration <= 0 and progress <= 0:
        return 0.0
    if duration >= 10 * 60 * 1000 or progress >= 85:
        return 3.0
    if duration >= 3 * 60 * 1000 or progress >= 50:
        return 2.0
    if duration >= 30 * 1000 or progress >= 10:
        return 1.0
    return 0.5


def skip_weight(row: Interaction) -> float:
    progress = row.progress_pct
    if progress is None:
        return -2.0
    if progress <= 10:
        return -3.0
    if progress <= 50:
        return -2.0
    return -1.0


def recency_weight(row: Interaction) -> float:
    now = datetime.now(UTC)
    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    days_ago = max((now - created).total_seconds() / 86400.0, 0.0)
    return math.exp(-days_ago / 7.0)


# ---------------------------------------------------------------------------
# Time bucket helpers
# ---------------------------------------------------------------------------


def current_bucket() -> str:
    hour = datetime.now(UTC).hour
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 23:
        return "evening"
    return "night"


def guess_bucket(context_hour: int | None) -> str:
    if context_hour is None:
        return "afternoon"
    if 6 <= context_hour < 12:
        return "morning"
    if 12 <= context_hour < 18:
        return "afternoon"
    if 18 <= context_hour < 23:
        return "evening"
    return "night"


def normalize_action(action: str, row: Interaction) -> str:
    if action == "play" and play_weight(row) <= 0:
        return "pause"
    if action == "skip" and row.progress_pct is not None:
        return "skip"
    return action


# ---------------------------------------------------------------------------
# Score builders
# ---------------------------------------------------------------------------


def build_hot_score(user_actions: dict[int, list[str]]) -> dict[int, float]:
    raw: dict[int, float] = {}
    for podcast_id, actions in user_actions.items():
        score = sum(ACTION_WEIGHT.get(action, 0.0) for action in actions)
        raw[podcast_id] = max(score, 0.0)
    return normalize_scores(raw)


def build_cf_score(
    interactions: list[Interaction],
    user_positive_score: dict[int, float],
) -> dict[int, float]:
    if not user_positive_score:
        return {}

    positive_by_user: dict[int, set[int]] = defaultdict(set)
    for row in interactions:
        action = normalize_action(row.action, row)
        if action in POSITIVE_ACTIONS:
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

    return normalize_scores(score)


def build_content_score(
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
        tokens = tokenize(text)
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
        score[podcast_id] = cosine_similarity(profile, vec)
    return normalize_scores(score)


def build_freshness_score(podcasts: list[Podcast]) -> dict[int, float]:
    now = datetime.now(UTC)
    freshness: dict[int, float] = {}
    half_life_days = 7.0
    for podcast in podcasts:
        published = podcast.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=UTC)
        age_days = max((now - published).total_seconds() / 86400.0, 0.0)
        freshness[podcast.id] = math.exp(-age_days / half_life_days)
    return normalize_scores(freshness)


def _sequence_text_tokens(podcast: Podcast) -> str:
    return " ".join([
        podcast.title or "",
        podcast.summary or "",
        getattr(podcast, "category", "") or "",
    ])


def build_sequence_score(
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
        tokens = set(tokenize(_sequence_text_tokens(podcast)))
        for tok in tokens:
            df[tok] += 1
    total_docs = max(len(podcasts), 1)

    recent_profile: dict[str, float] = defaultdict(float)
    for row in recent_items:
        podcast = next((item for item in podcasts if item.id == row.podcast_id), None)
        if not podcast:
            continue
        recency = recency_weight(row)
        tokens = tokenize(_sequence_text_tokens(podcast))

        action = normalize_action(row.action, row)
        if action in ("play", "complete"):
            importance = play_weight(row)
        else:
            importance = ACTION_WEIGHT.get(action, 1.0)
        weight = recency * importance

        for tok in tokens:
            idf = math.log((1 + total_docs) / (1 + df.get(tok, 0))) + 1.0
            recent_profile[tok] += weight * idf

    score: dict[int, float] = {}
    for podcast in podcasts:
        tokens = tokenize(_sequence_text_tokens(podcast))
        tf: dict[str, float] = defaultdict(float)
        for tok in tokens:
            tf[tok] += 1.0
        length = max(len(tokens), 1)
        vec: dict[str, float] = {}
        for tok, count in tf.items():
            idf = math.log((1 + total_docs) / (1 + df.get(tok, 0))) + 1.0
            vec[tok] = (count / length) * idf
        score[podcast.id] = cosine_similarity(recent_profile, vec)

    return normalize_scores(score)


# ---------------------------------------------------------------------------
# Cold-start helpers
# ---------------------------------------------------------------------------


def seed_preference_score(
    podcasts: list[Podcast], categories: list[str]
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


# ---------------------------------------------------------------------------
# Reason text
# ---------------------------------------------------------------------------


def compute_reason_text(
    cf: float = 0.0,
    content: float = 0.0,
    hot: float = 0.0,
    fresh: float = 0.0,
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
