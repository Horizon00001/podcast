import json
import hashlib
import math
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

from app.core.config import settings
from app.services.embedding_service import get_embedding_service
from app.services.text_tokenizer import spaced_tokens, tokenize_text


def _clean_text(value: str) -> str:
    return re.sub(r"<[^<]+?>", "", value or "").strip()


def _tokenize(value: str) -> str:
    return spaced_tokens(value)


@dataclass
class TopicProfile:
    id: str
    name: str
    description: str
    audience: str
    editorial_angle: str
    allowed_categories: List[str]
    preferred_keywords: List[str]
    excluded_keywords: List[str]
    structure_template: List[str]
    max_items: int


@dataclass
class PlannedNewsItem:
    item_id: str
    feed_id: str
    feed_name: str
    category: str
    title: str
    summary: str
    published: str
    link: str
    score: float
    selection_reason: str


@dataclass
class EpisodeSegment:
    segment_type: str
    purpose: str
    item_refs: List[str]
    segment_thesis: str


@dataclass
class EpisodePlan:
    topic_id: str
    topic_name: str
    title_hint: str
    theme_statement: str
    audience: str
    editorial_angle: str
    selected_items: List[PlannedNewsItem]
    segments: List[EpisodeSegment]
    closing_takeaway: str

    def to_dict(self) -> dict:
        return asdict(self)


PENDING_GROUPS_FILENAME = "pending_groups.json"
DEFAULT_CATEGORY_KEYWORDS = {
    "tech_ai": ["ai", "llm", "gpt", "openai", "deepseek", "anthropic", "gpu", "chip", "software", "model", "agent", "cloud", "developer", "tech", "robot", "automated", "algorithm", "apple", "google", "microsoft", "meta"],
    "business": ["market", "revenue", "funding", "acquisition", "ipo", "stock", "investment", "economy", "financial", "startup", "billion", "merger", "partnership", "财报", "融资", "并购", "上市"],
    "sports": ["sports", "racing", "nascar", "f1", "indycar", "formula", "football", "basketball", "soccer", "olympics", "athlete", "game", "score", "match", "team", "league", "nba", "mlb"],
}

GLOBAL_TOPIC_ANCHORS = [
    (r"apple.*ceo|ceo.*apple|tim cook|john ternus", "apple-ceo"),
    (r"anthropic|claude|openclaw|mythos", "anthropic-ai"),
    (r"yelp.*ai|ai.*yelp", "yelp-ai"),
    (r"vercel|context\.ai|third[- ]party ai", "vercel-security"),
    (r"robot|humanoid|android|machine learning|ai-informed", "robotics"),
    (r"deezer|music|song|audio.*ai|ai.*music", "ai-music"),
    (r"data center|datacenter|cloud|aws|openai|gpu|model|agent", "ai-infra"),
    (r"spacex|blue origin|new glenn|space", "space-tech"),
    (r"f1|formula 1|miami gp|grand prix|verstappen|wolff|domenicali|red bull", "f1-regs"),
    (r"indycar|penske|nascar", "american-racing"),
    (r"half[- ]marathon|marathon|race", "robot-half-marathon"),
    (r"sports car race|nurburgring|nürburgring", "endurance-race"),
    (r"ipo|funding|acquisition|revenue|market|financial|investment|stock|merger|partnership", "business-roundup"),
]


def _tokenize_search_text(value: str) -> str:
    return spaced_tokens(value)


def _build_item_search_text(item: dict) -> str:
    return _tokenize_search_text(f"{item.get('title', '')} {item.get('summary', '')} {item.get('feed_name', '')} {item.get('category', '')}")


def _category_matches(text: str, category: str, keywords: dict[str, list[str]]) -> bool:
    for keyword in keywords.get(category, []):
        if keyword and _tokenize_search_text(keyword) in text:
            return True
    return False


def classify_items(items: List[dict], keywords: dict[str, list[str]] | None = None) -> dict[str, list[dict]]:
    keywords = keywords or DEFAULT_CATEGORY_KEYWORDS
    categorized: dict[str, list[dict]] = {category: [] for category in keywords}
    categorized.setdefault("general", [])
    for item in items:
        searchable_text = _build_item_search_text(item)
        matched_categories = [category for category in keywords if _category_matches(searchable_text, category, keywords)]
        if not matched_categories:
            categorized["general"].append(item)
            continue
        for category in matched_categories:
            categorized.setdefault(category, []).append(item)
    return categorized


def _tfidf_vectors(items: List[dict]) -> dict[str, dict[str, float]]:
    documents: dict[str, list[str]] = {}
    df: dict[str, int] = defaultdict(int)
    for item in items:
        item_id = item.get("link") or item.get("item_id") or item.get("title") or str(id(item))
        tokens = tokenize_text(f"{item.get('title', '')} {item.get('summary', '')}")
        documents[item_id] = tokens
        for token in set(tokens):
            df[token] += 1
    total_docs = max(len(documents), 1)
    vectors: dict[str, dict[str, float]] = {}
    for item_id, tokens in documents.items():
        tf: dict[str, float] = defaultdict(float)
        for token in tokens:
            tf[token] += 1.0
        length = max(len(tokens), 1)
        vec: dict[str, float] = {}
        for token, count in tf.items():
            idf = math.log((1 + total_docs) / (1 + df[token])) + 1.0
            vec[token] = (count / length) * idf
        vectors[item_id] = vec
    return vectors


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(token, 0.0) for token, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _dense_cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def _similarity_key(item: dict) -> str:
    return item.get("link") or item.get("item_id") or item.get("title") or str(id(item))


def _embedding_text(item: dict) -> str:
    return " ".join(
        part for part in [
            item.get("title", ""),
            item.get("summary", ""),
            item.get("feed_name", ""),
            item.get("category", ""),
        ]
        if part
    )


def _embedding_vectors(items: List[dict]) -> dict[str, list[float]]:
    service = get_embedding_service()
    if not settings.episode_embedding_enabled or not service.is_enabled() or not items:
        return {}

    texts = [_embedding_text(item) for item in items]
    vectors = service.encode_texts(texts)
    return {
        _similarity_key(item): vector
        for item, vector in zip(items, vectors)
    }


def _normalize_title(title: str) -> str:
    title = (title or "").strip().lower()
    title = re.sub(r"['\"“”]", "", title)
    title = re.sub(r"[^\w\u4e00-\u9fff]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def dedupe_items(items: List[dict]) -> List[dict]:
    deduped: list[dict] = []
    seen_links: set[str] = set()
    seen_titles: set[str] = set()

    for item in items:
        link = (item.get("link") or "").strip()
        if link:
            if link in seen_links:
                continue
            seen_links.add(link)
            deduped.append(item)
            continue

        normalized_title = _normalize_title(item.get("title", ""))
        if normalized_title and normalized_title in seen_titles:
            continue
        if normalized_title:
            seen_titles.add(normalized_title)
        deduped.append(item)

    return deduped


def _anchor_for_item(item: dict) -> str:
    title = _normalize_title(item.get("title", ""))
    summary = _normalize_title(item.get("summary", ""))
    text = f"{title} {summary}"
    for pattern, anchor in GLOBAL_TOPIC_ANCHORS:
        if re.search(pattern, text):
            return anchor
    title_tokens = [token for token in title.split() if len(token) > 2]
    if title_tokens:
        return "-".join(title_tokens[:4])
    return "general-roundup"


def cluster_by_similarity(items: List[dict], threshold: float = 0.5) -> List[List[dict]]:
    if len(items) <= 1:
        return [items] if items else []
    embedding_vectors = _embedding_vectors(items)
    use_embeddings = bool(embedding_vectors)
    vectors = {} if use_embeddings else _tfidf_vectors(items)
    item_by_key = {_similarity_key(item): item for item in items}
    keys = list(item_by_key.keys())
    parent = {key: key for key in keys}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(left: str, right: str):
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for index, left_key in enumerate(keys):
        for right_key in keys[index + 1 :]:
            if use_embeddings:
                similarity = _dense_cosine(
                    embedding_vectors.get(left_key, []),
                    embedding_vectors.get(right_key, []),
                )
            else:
                similarity = _cosine(vectors.get(left_key, {}), vectors.get(right_key, {}))
            if similarity >= threshold:
                union(left_key, right_key)

    grouped: dict[str, list[dict]] = defaultdict(list)
    for key in keys:
        grouped[find(key)].append(item_by_key[key])
    return list(grouped.values())


def _safe_slug(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[\s/]+", "-", value)
    value = re.sub(r"[^\w\u4e00-\u9fff\-]+", "", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "untitled"


def _group_title(group_items: List[dict], category: str) -> str:
    if not group_items:
        return category
    candidates = [(item.get("title") or "").strip() for item in group_items if (item.get("title") or "").strip()]
    if not candidates:
        return category
    title = candidates[0]
    title = re.sub(r"^['\"“”]+|['\"“”]+$", "", title)
    title = re.split(r"[:：\-—|]", title, maxsplit=1)[0].strip()
    return title or category


def group_items_for_podcasts(items: List[dict], threshold: float = 0.5) -> dict[str, list[list[dict]]]:
    if settings.episode_embedding_enabled:
        clusters = cluster_by_similarity(dedupe_items(items), threshold=threshold)
        return {"general": clusters} if clusters else {}

    anchor_buckets: dict[str, list[dict]] = defaultdict(list)
    for item in dedupe_items(items):
        anchor_buckets[_anchor_for_item(item)].append(item)

    clusters: list[list[dict]] = []
    for bucket_items in anchor_buckets.values():
        if len(bucket_items) == 1:
            clusters.append(bucket_items)
            continue
        bucket_clusters = cluster_by_similarity(bucket_items, threshold=threshold)
        clusters.extend(bucket_clusters or [bucket_items])

    return {"general": clusters} if clusters else {}


def _cluster_signature(cluster: list[dict], category: str) -> str:
    items = " ".join(f"{item.get('title', '')} {item.get('summary', '')}" for item in cluster)
    items = _normalize_title(items)
    for pattern, anchor in GLOBAL_TOPIC_ANCHORS:
        if re.search(pattern, items):
            return anchor
    return _anchor_for_item(cluster[0]) if cluster else "general-roundup"


def build_cluster_key(category: str, cluster: list[dict]) -> str:
    if not cluster:
        return "general:empty"

    normalized_titles = sorted(
        title
        for title in (_normalize_title(item.get("title", "")) for item in cluster)
        if title
    )
    normalized_summaries = sorted(
        summary
        for summary in (_normalize_title(item.get("summary", "")) for item in cluster)
        if summary
    )
    normalized_links = sorted(
        link.strip().lower()
        for link in (item.get("link", "") for item in cluster)
        if link and link.strip()
    )
    published_values = sorted(
        (item.get("published") or "").strip().lower()
        for item in cluster
        if (item.get("published") or "").strip()
    )

    signature_text = " ".join(normalized_titles[:3] + normalized_summaries[:3])
    signature = None
    for pattern, anchor in GLOBAL_TOPIC_ANCHORS:
        if re.search(pattern, signature_text):
            signature = anchor
            break
    if signature is None:
        signature = "-".join((normalized_titles[0] if normalized_titles else "general").split()[:4]) or "general"

    title_basis = "|".join(normalized_titles[:3])
    link_basis = "|".join(normalized_links[:3])
    published_basis = published_values[0] if published_values else ""
    digest_source = "\n".join(["general", signature, title_basis, link_basis, published_basis])
    digest = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:16]
    return f"general:{signature}:{digest}"


def merge_clusters_by_signature(grouped: dict[str, list[list[dict]]]) -> dict[str, list[list[dict]]]:
    merged: dict[str, list[list[dict]]] = {}
    for category, clusters in grouped.items():
        signature_buckets: dict[str, list[dict]] = defaultdict(list)
        for cluster in clusters:
            signature_buckets[_cluster_signature(cluster, category)].extend(cluster)
        merged[category] = list(signature_buckets.values())
    return merged


def build_podcast_plan(category: str, items: List[dict]) -> EpisodePlan:
    profile_name = {"tech_ai": "今日 AI 快讯", "business": "一周商业头条", "sports": "今日新闻简报", "general": "今日新闻简报"}.get(category, "今日新闻简报")
    selected_items = [PlannedNewsItem(item_id=item.get("item_id") or _similarity_key(item), feed_id=item.get("feed_id") or item.get("feed_name") or "unknown", feed_name=item.get("feed_name") or item.get("feed_id") or "Unknown Feed", category=category, title=item.get("title", ""), summary=item.get("summary", ""), published=item.get("published", "Unknown Date"), link=item.get("link", ""), score=1.0, selection_reason="已通过相似度聚类归入本期播客素材") for item in items]
    top_story_title = selected_items[0].title if selected_items else profile_name
    theme_statement = f"本期围绕“{top_story_title}”组织内容，主线是：同一类别下聚类出的相关新闻形成一个可收听的主题包。"
    closing_takeaway = f"听完这一集，听众应该记住：{top_story_title} 这组新闻讲的是同一个主题的不同侧面。"
    segments: List[EpisodeSegment] = []
    if selected_items:
        segments.append(EpisodeSegment("opening", "用本组主题建立本期主线和听众期待。", [selected_items[0].item_id], f"先用最具代表性的新闻引出 {top_story_title} 的节目主线。"))
        for index, item in enumerate(selected_items):
            segments.append(EpisodeSegment("main_content", "展开本组内的一条核心新闻。", [item.item_id], f"把 {item.title} 讲透，作为第 {index + 1} 条核心素材。"))
        segments.append(EpisodeSegment("closing", "回收主线，总结本期节目真正想表达的判断。", [], closing_takeaway))
    return EpisodePlan(category, profile_name, f"{profile_name} | {top_story_title}", theme_statement, "泛科技与新闻播客听众", "围绕相似新闻聚类出的共同主线展开。", selected_items, segments, closing_takeaway)


def build_group_plan(category: str, items: List[dict], topic_name: str) -> EpisodePlan:
    selected_items = [PlannedNewsItem(item_id=item.get("item_id") or _similarity_key(item), feed_id=item.get("feed_id") or item.get("feed_name") or "unknown", feed_name=item.get("feed_name") or item.get("feed_id") or "Unknown Feed", category=category, title=item.get("title", ""), summary=item.get("summary", ""), published=item.get("published", "Unknown Date"), link=item.get("link", ""), score=1.0, selection_reason="已通过相似度聚类归入本期播客素材") for item in items]
    top_story_title = selected_items[0].title if selected_items else topic_name
    theme_statement = f"本期围绕“{top_story_title}”组织内容，主线是：同一主题下聚类出的相关新闻形成一个可收听的主题包。"
    closing_takeaway = f"听完这一集，听众应该记住：{top_story_title} 这组新闻讲的是同一个主题的不同侧面。"
    segments: List[EpisodeSegment] = []
    if selected_items:
        segments.append(EpisodeSegment("opening", "用本组主题建立本期主线和听众期待。", [selected_items[0].item_id], f"先用最具代表性的新闻引出 {top_story_title} 的节目主线。"))
        for index, item in enumerate(selected_items):
            segments.append(EpisodeSegment("main_content", "展开本组内的一条核心新闻。", [item.item_id], f"把 {item.title} 讲透，作为第 {index + 1} 条核心素材。"))
        segments.append(EpisodeSegment("closing", "回收主线，总结本期节目真正想表达的判断。", [], closing_takeaway))
    return EpisodePlan(category, topic_name, f"{topic_name} | {top_story_title}", theme_statement, "泛科技与新闻播客听众", "围绕相似新闻聚类出的共同主线展开。", selected_items, segments, closing_takeaway)


def build_group_name(items: List[dict], fallback: str) -> str:
    return _safe_slug(_group_title(items, fallback))


def save_pending_groups(pending_groups: list[dict], used_item_links: list[str], output_path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump({"pending_groups": pending_groups, "used_item_links": used_item_links}, file, ensure_ascii=False, indent=2)
    return output_path


def load_pending_groups(path: Path) -> tuple[list[dict], list[str]]:
    if not path.exists():
        return [], []
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data.get("pending_groups", []), data.get("used_item_links", [])


def merge_pending_groups(pending_groups: list[dict], new_items: list[dict], threshold: float = 0.5) -> tuple[list[dict], list[dict], list[str]]:
    generated_groups: list[dict] = []
    remaining_pending: list[dict] = []
    consumed_links: list[str] = []
    for pending_group in pending_groups:
        pending_items = list(pending_group.get("items", []))
        candidates = new_items
        pending_anchor = _anchor_for_item(pending_items[0]) if pending_items else "general-roundup"
        pending_vectors = _tfidf_vectors(pending_items) if pending_items else {}
        pending_centroid: dict[str, float] = defaultdict(float)
        for vec in pending_vectors.values():
            for token, value in vec.items():
                pending_centroid[token] += value
        matched: list[dict] = []
        for item in candidates:
            if item.get("link") in {existing.get("link") for existing in pending_items}:
                continue
            if _anchor_for_item(item) != pending_anchor:
                continue
            item_vec = _tfidf_vectors([item]).get(_similarity_key(item), {})
            if _cosine(pending_centroid, item_vec) >= threshold:
                matched.append(item)
        if matched:
            pending_items.extend(matched)
            consumed_links.extend(item.get("link", "") for item in matched if item.get("link"))
            pending_group["items"] = pending_items
            if len(pending_items) >= 2:
                generated_groups.append({"category": "general", "items": pending_items})
            else:
                remaining_pending.append(pending_group)
        else:
            remaining_pending.append(pending_group)
    return remaining_pending, generated_groups, consumed_links


def load_topic_profiles(config_path) -> Dict[str, TopicProfile]:
    with open(config_path, "r", encoding="utf-8") as file:
        raw_profiles = json.load(file).get("topics", [])
    profiles: Dict[str, TopicProfile] = {}
    for raw in raw_profiles:
        selection = raw.get("selection", {})
        profile = TopicProfile(raw["id"], raw.get("name", raw["id"]), raw.get("description", ""), raw.get("audience", "泛播客听众"), raw.get("editorial_angle", "围绕主题组织一集节目"), raw.get("allowed_categories", []), raw.get("preferred_keywords", []), raw.get("excluded_keywords", []), raw.get("structure_template", ["opening", "top_story", "closing"]), max(int(selection.get("max_items", 4)), 1))
        profiles[profile.id] = profile
    return profiles


def resolve_topic_profile(topic: str, config_path) -> TopicProfile:
    profiles = load_topic_profiles(config_path)
    if topic in profiles:
        return profiles[topic]
    normalized = (topic or "").strip() or "custom-topic"
    return TopicProfile(normalized, normalized, f"围绕 {normalized} 组织节目。", "泛播客听众", f"所有入选内容都应服务于 {normalized} 这个主题主线。", [], [normalized], [], ["opening", "top_story", "related_signals", "closing"], 4)


def load_rss_items(rss_data_path) -> List[dict]:
    with open(rss_data_path, "r", encoding="utf-8") as file:
        feeds = json.load(file)
    items = []
    for feed in feeds:
        for index, entry in enumerate(feed.get("entries", []), start=1):
            items.append({"item_id": f"{feed.get('id', 'feed')}-{index}", "feed_id": feed.get("id", "unknown"), "feed_name": feed.get("name", "Unknown Feed"), "category": feed.get("category", "general"), "title": (entry.get("title") or "").strip(), "summary": _clean_text(entry.get("summary", "")), "published": entry.get("published", "Unknown Date"), "link": entry.get("link", "")})
    return dedupe_items(items)


def _score_item(item: dict, profile: TopicProfile) -> Tuple[float, str]:
    score = 1.0
    reasons = []
    searchable_text = _tokenize(f"{item['title']} {item['summary']}")
    if not profile.allowed_categories or item["category"] in profile.allowed_categories:
        score += 1.2
        reasons.append("分类匹配节目主题")
    keyword_hits = 0
    for keyword in profile.preferred_keywords:
        if keyword and _tokenize(keyword) in searchable_text:
            keyword_hits += 1
    if keyword_hits:
        score += 1.5 * keyword_hits
        reasons.append(f"命中 {keyword_hits} 个主题关键词")
    excluded_hits = 0
    for keyword in profile.excluded_keywords:
        if keyword and _tokenize(keyword) in searchable_text:
            excluded_hits += 1
    if excluded_hits:
        score -= 2.0 * excluded_hits
        reasons.append("包含弱相关或应排除内容")
    if item["summary"]:
        score += 0.4
    if item["title"]:
        score += 0.3
    if not reasons:
        reasons.append("作为补充素材保留，用于支撑本期主题")
    return score, "；".join(reasons)


def select_items_for_topic(items: List[dict], profile: TopicProfile) -> List[PlannedNewsItem]:
    scored_items = []
    for item in items:
        score, reason = _score_item(item, profile)
        scored_items.append(PlannedNewsItem(item["item_id"], item["feed_id"], item["feed_name"], item["category"], item["title"], item["summary"], item["published"], item["link"], round(score, 2), reason))
    scored_items.sort(key=lambda item: item.score, reverse=True)
    selected: List[PlannedNewsItem] = []
    seen_titles: Set[str] = set()
    for item in scored_items:
        normalized_title = item.title.lower()
        if normalized_title in seen_titles:
            continue
        selected.append(item)
        seen_titles.add(normalized_title)
        if len(selected) >= profile.max_items:
            break
    if not selected and scored_items:
        selected = scored_items[:1]
    return selected


def _segment_purpose(segment_type: str, profile: TopicProfile) -> str:
    mapping = {"opening": f"用节目主题 {profile.name} 建立本期讨论范围和听众期待。", "top_story": "展开信息最充分、最值得优先讲清的核心新闻。", "related_signals": "比较其他新闻与核心新闻的关联度，关联弱时分别讲清，不强行并线。", "impact": "解释这些变化对听众和行业意味着什么。", "developer_impact": "把行业变化翻译成对程序员工具、协作和职业判断的具体影响。", "closing": "自然收束讨论，回到今天最站得住的几个重点。"}
    return mapping.get(segment_type, "围绕主题组织段落内容。")


def build_episode_plan(topic: str, rss_data_path, topics_config_path) -> EpisodePlan:
    profile = resolve_topic_profile(topic, topics_config_path)
    items = load_rss_items(rss_data_path)
    selected_items = select_items_for_topic(items, profile)
    top_story = selected_items[0] if selected_items else None
    top_story_title = top_story.title if top_story else profile.name
    theme_statement = f"本期围绕“{profile.name}”组织内容，优先讲清 {top_story_title}，再判断其他新闻是否足以支持 {profile.editorial_angle}；如果关联不足，就分别说明。"
    closing_takeaway = "听完这一集，听众应该记住：先记住最扎实的事实和判断，关联强再归纳，关联弱就保留边界。"
    segments: List[EpisodeSegment] = []
    related_item_ids = [item.item_id for item in selected_items[1:]]
    all_item_ids = [item.item_id for item in selected_items]
    for segment_type in profile.structure_template:
        if segment_type == "opening":
            item_refs = all_item_ids[:1]
            thesis = f"先用最具代表性的新闻把今天最值得关心的问题讲清。"
        elif segment_type == "top_story":
            item_refs = all_item_ids[:1]
            thesis = f"把 {top_story_title} 讲透，作为本期的核心故事。"
        elif segment_type == "related_signals":
            item_refs = related_item_ids
            thesis = "补充 1 到 3 条相关素材，先讲清各自事实，再判断它们是否真的构成同一趋势。"
        elif segment_type in {"impact", "developer_impact"}:
            item_refs = all_item_ids
            thesis = f"只翻译那些有足够事实支撑、且 {profile.audience} 真正需要关心的影响。"
        else:
            item_refs = []
            thesis = closing_takeaway
        segments.append(EpisodeSegment(segment_type, _segment_purpose(segment_type, profile), item_refs, thesis))
    return EpisodePlan(profile.id, profile.name, f"{profile.name} | {top_story_title}", theme_statement, profile.audience, profile.editorial_angle, selected_items, segments, closing_takeaway)


def save_episode_plan(plan: EpisodePlan, output_path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(plan.to_dict(), file, ensure_ascii=False, indent=2)
    return output_path


def format_plan_for_prompt(plan: EpisodePlan) -> str:
    lines = ["以下是已经完成选材和编排的播客节目计划，请围绕这个计划写成一集节目。先把事实讲清，再决定能否归纳共同主题；如果素材关联有限，不要强行并线。", f"节目主题: {plan.topic_name} ({plan.topic_id})", f"目标听众: {plan.audience}", f"节目角度: {plan.editorial_angle}", f"标题建议: {plan.title_hint}", f"本期优先线索: {plan.theme_statement}", "", "已选素材:"]
    for item in plan.selected_items:
        lines.extend([f"- {item.item_id} | {item.title}", f"  来源: {item.feed_name} / {item.category}", f"  摘要: {item.summary or '无'}", f"  入选原因: {item.selection_reason}"])
    lines.append("")
    lines.append("节目结构:")
    for segment in plan.segments:
        refs = ", ".join(segment.item_refs) if segment.item_refs else "无新增素材"
        lines.extend([f"- 段落类型: {segment.segment_type}", f"  目的: {segment.purpose}", f"  使用素材: {refs}", f"  这一段优先讲清的问题: {segment.segment_thesis}"])
    lines.extend(["", f"结尾可回收的重点: {plan.closing_takeaway}"])
    return "\n".join(lines)
