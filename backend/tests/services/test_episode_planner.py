import math
import pytest

from app.pipelines.episode_planner import (
    _clean_text,
    _tokenize,
    build_cluster_key,
    classify_items,
    dedupe_items,
    _tfidf_vectors,
    cluster_by_similarity,
    _normalize_title,
    _anchor_for_item,
    _safe_slug,
    _group_title,
    group_items_for_podcasts,
    merge_clusters_by_signature,
    build_podcast_plan,
    build_group_plan,
    build_group_name,
    merge_pending_groups,
    _score_item,
    select_items_for_topic,
    format_plan_for_prompt,
    TopicProfile,
    EpisodePlan,
)


class TestEpisodePlannerCleanText:
    """Test _clean_text function."""

    def test_clean_text_removes_html_tags(self):
        assert _clean_text("<p>Hello</p>") == "Hello"
        assert _clean_text("<b>Bold</b>") == "Bold"

    def test_clean_text_handles_none(self):
        assert _clean_text(None) == ""

    def test_clean_text_strips_whitespace(self):
        assert _clean_text("  Hello  ") == "Hello"


class TestEpisodePlannerTokenize:
    """Test _tokenize function."""

    def test_tokenize_adds_spaces(self):
        assert _tokenize("hello") == " hello "
        assert _tokenize("") == "  "

    def test_tokenize_lowercase(self):
        assert _tokenize("HELLO") == " hello "

    def test_tokenize_segments_chinese_words(self):
        assert _tokenize("人工智能芯片") == " 人工智能 芯片 "


class TestEpisodePlannerNormalizeTitle:
    """Test _normalize_title function."""

    def test_normalize_title_lowercase(self):
        assert _normalize_title("HELLO WORLD") == "hello world"

    def test_normalize_title_removes_quotes(self):
        assert _normalize_title('"Hello"') == "hello"
        assert _normalize_title("'Hello'") == "hello"

    def test_normalize_title_handles_none(self):
        assert _normalize_title(None) == ""


class TestEpisodePlannerSafeSlug:
    """Test _safe_slug function."""

    def test_safe_slug_lowercase(self):
        assert _safe_slug("Hello World") == "hello-world"

    def test_safe_slug_handles_chinese(self):
        assert _safe_slug("中文标题") == "中文标题"

    def test_safe_slug_removes_special_chars(self):
        assert _safe_slug("test@#$%") == "test"

    def test_safe_slug_empty_returns_untitled(self):
        assert _safe_slug("") == "untitled"
        assert _safe_slug(None) == "untitled"


class TestEpisodePlannerClassifyItems:
    """Test classify_items function."""

    def test_classify_ai_items(self):
        items = [
            {"title": "OpenAI releases GPT-5", "summary": "New model", "feed_name": "AI News", "category": "tech"},
            {"title": "Stock market update", "summary": "Markets fall", "feed_name": "Finance", "category": "business"},
        ]
        result = classify_items(items)

        assert "tech_ai" in result
        assert "business" in result

    def test_classify_empty_list(self):
        result = classify_items([])
        # Returns dict with keys for each category
        assert isinstance(result, dict)


class TestEpisodePlannerDedupeItems:
    """Test dedupe_items function."""

    def test_dedupe_items_by_link(self):
        items = [
            {"title": "OnePlus Ace 6 specs", "link": "https://example.com/ace6", "summary": "first"},
            {"title": "OnePlus Ace 6 specs", "link": "https://example.com/ace6", "summary": "duplicate"},
            {"title": "OnePlus power bank", "link": "https://example.com/powerbank", "summary": "other"},
        ]

        result = dedupe_items(items)

        assert len(result) == 2
        assert [item["link"] for item in result] == [
            "https://example.com/ace6",
            "https://example.com/powerbank",
        ]

    def test_dedupe_items_by_normalized_title_when_link_missing(self):
        items = [
            {"title": "OpenAI Privacy Filter", "link": "", "summary": "first"},
            {"title": "OpenAI Privacy Filter!!!", "link": "", "summary": "duplicate"},
            {"title": "Different story", "link": "", "summary": "other"},
        ]

        result = dedupe_items(items)

        assert len(result) == 2
        assert result[0]["title"] == "OpenAI Privacy Filter"
        assert result[1]["title"] == "Different story"


class TestEpisodePlannerTfIdfVectors:
    """Test _tfidf_vectors function."""

    def test_tfidf_basic(self):
        items = [
            {"title": "AI News", "summary": "Artificial intelligence update", "link": "http://example.com/1"},
            {"title": "Tech Report", "summary": "Technology trends", "link": "http://example.com/2"},
        ]
        vectors = _tfidf_vectors(items)

        assert "http://example.com/1" in vectors
        assert "http://example.com/2" in vectors
        assert len(vectors["http://example.com/1"]) > 0

    def test_tfidf_single_item(self):
        items = [{"title": "AI", "summary": "Artificial intelligence", "link": "http://example.com/1"}]
        vectors = _tfidf_vectors(items)

        assert "http://example.com/1" in vectors

    def test_tfidf_uses_chinese_word_tokens(self):
        items = [
            {"title": "人工智能芯片", "summary": "人工智能芯片加速训练", "link": "http://example.com/1"},
        ]
        vectors = _tfidf_vectors(items)

        assert "人工智能" in vectors["http://example.com/1"]
        assert "芯片" in vectors["http://example.com/1"]


class TestEpisodePlannerCosine:
    """Test _cosine function from episode_planner module."""

    def test_cosine_identical_vectors(self):
        from app.pipelines.episode_planner import _cosine
        vec = {"a": 1.0, "b": 1.0}
        result = _cosine(vec, vec)
        assert abs(result - 1.0) < 1e-6

    def test_cosine_orthogonal_vectors(self):
        from app.pipelines.episode_planner import _cosine
        left = {"a": 1.0}
        right = {"b": 1.0}
        result = _cosine(left, right)
        assert result == 0.0

    def test_cosine_empty_vectors(self):
        from app.pipelines.episode_planner import _cosine
        assert _cosine({}, {"a": 1.0}) == 0.0
        assert _cosine({"a": 1.0}, {}) == 0.0

    def test_dense_cosine_identical_vectors(self):
        from app.pipelines.episode_planner import _dense_cosine

        assert _dense_cosine([0.1, 0.2], [0.1, 0.2]) == pytest.approx(0.05)

    def test_dense_cosine_mismatched_dimensions(self):
        from app.pipelines.episode_planner import _dense_cosine

        assert _dense_cosine([0.1], [0.1, 0.2]) == 0.0


class TestEpisodePlannerClusterBySimilarity:
    """Test cluster_by_similarity function."""

    def test_cluster_single_item(self):
        items = [{"title": "AI News", "link": "http://example.com/1"}]
        result = cluster_by_similarity(items)

        assert len(result) == 1
        assert len(result[0]) == 1

    def test_cluster_empty_list(self):
        result = cluster_by_similarity([])
        assert result == []

    def test_cluster_two_similar_items(self):
        items = [
            {"title": "AI Model Released by OpenAI", "link": "http://example.com/1"},
            {"title": "OpenAI Releases New AI Model", "link": "http://example.com/2"},
        ]
        result = cluster_by_similarity(items, threshold=0.3)

        # Both should be in same cluster
        assert len(result) == 1
        assert len(result[0]) == 2

    def test_build_cluster_key_is_stable_for_same_cluster(self):
        cluster = [
            {
                "title": "生化危机配音演员谈真人电影",
                "summary": "里昂配音演员表示对新导演谨慎乐观。",
                "link": "https://example.com/re1",
                "published": "2026-04-26",
            },
            {
                "title": "生化危机新作销量破 700 万",
                "summary": "安魂曲销量创下系列新纪录。",
                "link": "https://example.com/re2",
                "published": "2026-04-26",
            },
        ]

        first_key = build_cluster_key("tech_ai", cluster)
        second_key = build_cluster_key("tech_ai", list(reversed(cluster)))

        assert first_key == second_key
        assert first_key.startswith("general:")

    def test_cluster_with_embedding_similarity(self, monkeypatch):
        from app.pipelines import episode_planner

        items = [
            {"title": "维斯塔潘赢得F1迈阿密大奖赛", "summary": "红牛车手拿下冠军", "link": "http://example.com/cn"},
            {"title": "Verstappen dominates F1 Miami race", "summary": "Red Bull driver wins again", "link": "http://example.com/en"},
            {"title": "Apple releases new iPhone", "summary": "New smartphone lineup announced", "link": "http://example.com/apple"},
        ]

        class FakeEmbeddingService:
            def is_enabled(self):
                return True

            def encode_texts(self, texts):
                return [
                    [1.0, 0.0],
                    [0.95, 0.05],
                    [0.0, 1.0],
                ]

        monkeypatch.setattr(episode_planner.settings, "episode_embedding_enabled", True)
        monkeypatch.setattr(episode_planner.settings, "episode_embedding_weight", 0.9)
        monkeypatch.setattr(episode_planner, "get_embedding_service", lambda: FakeEmbeddingService())

        result = cluster_by_similarity(items, threshold=0.8)

        cluster_sizes = sorted(len(cluster) for cluster in result)
        assert cluster_sizes == [1, 2]

    def test_cluster_with_embedding_ignores_tfidf(self, monkeypatch):
        from app.pipelines import episode_planner

        items = [
            {"title": "Apple launched new iPhone", "summary": "new phone", "link": "http://example.com/en"},
            {"title": "苹果发布了新手机", "summary": "新手机发布", "link": "http://example.com/cn"},
        ]

        class FakeEmbeddingService:
            def is_enabled(self):
                return True

            def encode_texts(self, texts):
                return [
                    [1.0, 0.0],
                    [0.99, 0.01],
                ]

        monkeypatch.setattr(episode_planner.settings, "episode_embedding_enabled", True)
        monkeypatch.setattr(episode_planner, "get_embedding_service", lambda: FakeEmbeddingService())
        monkeypatch.setattr(episode_planner, "_tfidf_vectors", lambda items: (_ for _ in ()).throw(AssertionError("tfidf should not be used")))

        result = cluster_by_similarity(items, threshold=0.8)

        assert len(result) == 1
        assert len(result[0]) == 2


class TestEpisodePlannerAnchorForItem:
    """Test _anchor_for_item function."""

    def test_anchor_apple_ceo(self):
        item = {"title": "Apple CEO Tim Cook announces new product", "summary": ""}
        result = _anchor_for_item(item)
        assert result == "apple-ceo"

    def test_anchor_anthropic(self):
        item = {"title": "Anthropic releases Claude 4", "summary": ""}
        result = _anchor_for_item(item)
        assert result == "anthropic-ai"

    def test_anchor_f1(self):
        item = {"title": "Verstappen wins F1 race", "summary": ""}
        result = _anchor_for_item(item)
        assert result == "f1-regs"

    def test_anchor_fallback_returns_slug(self):
        item = {"title": "Random news", "summary": ""}
        result = _anchor_for_item(item)
        assert result == "random-news"


class TestEpisodePlannerGroupItems:
    """Test group_items_for_podcasts function."""

    def test_group_items_basic(self):
        from app.pipelines import episode_planner
        episode_planner.settings.episode_embedding_enabled = False
        items = [
            {"title": "Anthropic releases Claude update", "summary": "New Claude model news", "feed_name": "AI News", "category": "tech", "link": "http://1"},
            {"title": "Claude gets enterprise upgrade from Anthropic", "summary": "Anthropic AI product update", "feed_name": "Tech", "category": "news", "link": "http://2"},
        ]
        result = group_items_for_podcasts(items, threshold=0.1)

        assert "general" in result
        assert len(result["general"]) == 1
        assert len(result["general"][0]) == 2

    def test_group_items_empty(self):
        from app.pipelines import episode_planner
        episode_planner.settings.episode_embedding_enabled = False
        result = group_items_for_podcasts([])
        assert result == {}

    def test_group_items_dedupes_repeated_source_entries(self):
        from app.pipelines import episode_planner
        episode_planner.settings.episode_embedding_enabled = False
        items = [
            {
                "title": "一加 Ace 6 至尊版手机规格汇总：6.78 英寸直屏、天玑 9500 等，4 月 28 日发布",
                "summary": "一加 Ace 6 至尊版将搭载天玑 9500 芯片、8600mAh 双电芯电池，支持 120W 闪充。",
                "feed_name": "IT之家",
                "category": "tech_ai",
                "link": "https://www.ithome.com/0/943/431.htm",
            },
            {
                "title": "一加 Ace 6 至尊版手机规格汇总：6.78 英寸直屏、天玑 9500 等，4 月 28 日发布",
                "summary": "一加 Ace 6 至尊版将搭载天玑 9500 芯片、8600mAh 双电芯电池，支持 120W 闪充。",
                "feed_name": "IT之家",
                "category": "tech_ai",
                "link": "https://www.ithome.com/0/943/431.htm",
            },
            {
                "title": "一加 120W 超能舱超级闪充移动电源参数公布：15000mAh 容量，120W 高功率快充",
                "summary": "这款移动电源将在 4 月 28 日与 Ace 6 至尊版同台发布，可在 30 分钟内为 Ace 6 至尊版充电 68%。",
                "feed_name": "IT之家",
                "category": "tech_ai",
                "link": "https://www.ithome.com/0/943/636.htm",
            },
        ]

        result = merge_clusters_by_signature(group_items_for_podcasts(items, threshold=0.3))

        total_groups = sum(len(groups) for groups in result.values())
        total_items = sum(len(group) for groups in result.values() for group in groups)

        assert total_groups == 2
        assert total_items == 2

    def test_group_items_uses_embedding_without_anchor_buckets(self, monkeypatch):
        from app.pipelines import episode_planner

        items = [
            {"title": "Apple launched new iPhone", "summary": "new phone", "link": "http://example.com/en"},
            {"title": "苹果发布了新手机", "summary": "新手机发布", "link": "http://example.com/cn"},
            {"title": "如何做蛋糕", "summary": "厨房技巧", "link": "http://example.com/cake"},
        ]

        class FakeEmbeddingService:
            def is_enabled(self):
                return True

            def encode_texts(self, texts):
                return [
                    [1.0, 0.0],
                    [0.99, 0.01],
                    [0.0, 1.0],
                ]

        monkeypatch.setattr(episode_planner.settings, "episode_embedding_enabled", True)
        monkeypatch.setattr(episode_planner, "get_embedding_service", lambda: FakeEmbeddingService())

        grouped = group_items_for_podcasts(items, threshold=0.8)

        cluster_sizes = sorted(len(cluster) for cluster in grouped["general"])
        assert cluster_sizes == [1, 2]


class TestEpisodePlannerGroupTitle:
    """Test _group_title function."""

    def test_group_title_extracts_first(self):
        items = [
            {"title": "First Title: Subtitle"},
            {"title": "Second Title"},
        ]
        result = _group_title(items, "general")
        assert result == "First Title"

    def test_group_title_handles_empty(self):
        assert _group_title([], "general") == "general"


class TestEpisodePlannerBuildPodcastPlan:
    """Test build_podcast_plan function."""

    def test_build_podcast_plan_basic(self):
        items = [
            {"item_id": "1", "feed_id": "ai-news", "feed_name": "AI News", "category": "tech_ai", "title": "AI Model Released", "summary": "New AI model", "published": "2024-01-01", "link": "http://example.com/1"},
        ]
        result = build_podcast_plan("tech_ai", items)

        assert isinstance(result, EpisodePlan)
        assert result.topic_id == "tech_ai"
        assert len(result.selected_items) == 1
        assert len(result.segments) > 0

    def test_build_podcast_plan_empty_items(self):
        result = build_podcast_plan("tech_ai", [])

        assert isinstance(result, EpisodePlan)
        assert len(result.selected_items) == 0


class TestEpisodePlannerBuildGroupPlan:
    """Test build_group_plan function."""

    def test_build_group_plan_basic(self):
        items = [
            {"item_id": "1", "feed_id": "ai-news", "feed_name": "AI News", "category": "tech_ai", "title": "AI News", "summary": "AI summary", "published": "2024-01-01", "link": "http://example.com/1"},
        ]
        result = build_group_plan("tech_ai", items, "Daily AI")

        assert isinstance(result, EpisodePlan)
        assert result.topic_name == "Daily AI"


class TestEpisodePlannerBuildGroupName:
    """Test build_group_name function."""

    def test_build_group_name(self):
        items = [{"title": "First News: Subtitle"}]
        result = build_group_name(items, "general")

        assert "first-news" in result


class TestEpisodePlannerMergePendingGroups:
    """Test merge_pending_groups function."""

    def test_merge_pending_groups_no_match(self):
        pending = [{"category": "tech_ai", "items": [{"title": "Old AI news", "link": "http://old.com"}]}]
        new_items = [{"title": "New sports", "summary": "", "link": "http://new.com"}]

        remaining, generated, consumed = merge_pending_groups(pending, new_items, threshold=0.5)

        # Should not generate any new groups since topics don't match
        assert len(generated) == 0

    def test_merge_pending_groups_with_match(self):
        pending = [{"category": "tech_ai", "items": [{"title": "AI Model Part 1", "summary": "First part of AI story", "link": "http://part1.com"}]}]
        new_items = [{"title": "AI Model Part 2", "summary": "Second part continues the AI story", "link": "http://part2.com"}]

        remaining, generated, consumed = merge_pending_groups(pending, new_items, threshold=0.1)

        assert len(generated) == 1
        assert generated[0]["category"] == "general"
        assert consumed == ["http://part2.com"]


class TestEpisodePlannerScoreItem:
    """Test _score_item function."""

    def test_score_item_basic(self):
        item = {"title": "AI Model Released", "summary": "New AI model announced today", "category": "tech_ai", "link": "http://example.com/1"}
        profile = TopicProfile(
            id="tech_ai",
            name="AI News",
            description="",
            audience="",
            editorial_angle="",
            allowed_categories=["tech_ai"],
            preferred_keywords=["AI"],
            excluded_keywords=[],
            structure_template=["opening", "closing"],
            max_items=5,
        )
        score, reason = _score_item(item, profile)

        # Should have base score + category match + keyword hits
        assert score >= 1.0
        assert len(reason) > 0

    def test_score_item_excluded_keyword(self):
        item = {"title": "AI News", "summary": "Some content"}
        profile = TopicProfile(
            id="tech_ai",
            name="AI News",
            description="",
            audience="",
            editorial_angle="",
            allowed_categories=[],
            preferred_keywords=["AI"],
            excluded_keywords=["News"],
            structure_template=["opening", "closing"],
            max_items=5,
        )
        score, reason = _score_item(item, profile)

        assert "排除" in reason or "excluded" in reason.lower() or score < 2.0


class TestEpisodePlannerSelectItemsForTopic:
    """Test select_items_for_topic function."""

    def test_select_items_respects_max_items(self):
        items = [
            {"item_id": str(i), "feed_id": "news", "feed_name": "News", "category": "tech_ai", "title": f"Item {i}", "summary": "Summary", "published": "2024-01-01", "link": f"http://{i}.com"}
            for i in range(10)
        ]
        profile = TopicProfile(
            id="tech_ai",
            name="AI",
            description="",
            audience="",
            editorial_angle="",
            allowed_categories=[],
            preferred_keywords=[],
            excluded_keywords=[],
            structure_template=["opening", "closing"],
            max_items=3,
        )

        result = select_items_for_topic(items, profile)

        assert len(result) <= 3

    def test_select_items_deduplicates_by_title(self):
        items = [
            {"item_id": "1", "feed_id": "news", "feed_name": "News", "category": "tech_ai", "title": "Same Title", "summary": "Summary 1", "published": "2024-01-01", "link": "http://1.com"},
            {"item_id": "2", "feed_id": "news", "feed_name": "News", "category": "tech_ai", "title": "Same Title", "summary": "Summary 2", "published": "2024-01-02", "link": "http://2.com"},
        ]
        profile = TopicProfile(
            id="tech_ai",
            name="AI",
            description="",
            audience="",
            editorial_angle="",
            allowed_categories=[],
            preferred_keywords=[],
            excluded_keywords=[],
            structure_template=["opening", "closing"],
            max_items=5,
        )

        result = select_items_for_topic(items, profile)

        # Should deduplicate - only one entry for "Same Title"
        assert len(result) == 1


class TestEpisodePlannerFormatPlanForPrompt:
    """Test format_plan_for_prompt function."""

    def test_format_plan_for_prompt_basic(self):
        plan = EpisodePlan(
            topic_id="tech_ai",
            topic_name="AI News",
            title_hint="AI Today",
            theme_statement="AI is advancing",
            audience="Tech listeners",
            editorial_angle="Coverage of AI",
            selected_items=[],
            segments=[],
            closing_takeaway="Remember to follow AI news",
        )

        result = format_plan_for_prompt(plan)

        assert "AI News" in result
        assert "Tech listeners" in result
        assert "AI Today" in result
