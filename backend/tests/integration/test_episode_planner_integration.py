"""
集成测试：Episode Planner
测试完整的新闻聚类和规划流程
"""
import pytest
from pathlib import Path

from app.pipelines.episode_planner import (
    classify_items,
    cluster_by_similarity,
    dedupe_items,
    group_items_for_podcasts,
    merge_clusters_by_signature,
    build_podcast_plan,
    build_group_plan,
    merge_pending_groups,
    load_topic_profiles,
    build_episode_plan,
    format_plan_for_prompt,
)


class TestEpisodePlannerFullFlow:
    """完整的播客规划流程集成测试."""

    def test_classify_and_cluster_real_items(self):
        """测试真实新闻可直接聚类，不依赖前置分类."""
        items = [
            {
                "title": "OpenAI Releases GPT-5",
                "summary": "OpenAI announced a new AI model",
                "feed_name": "AI News",
                "category": "tech",
                "link": "http://example.com/1",
            },
            {
                "title": "Google AI Announces Gemini 2",
                "summary": "Google released new AI model",
                "feed_name": "Tech News",
                "category": "tech",
                "link": "http://example.com/2",
            },
            {
                "title": "Stock Market Update",
                "summary": "Markets fell today",
                "feed_name": "Finance",
                "category": "business",
                "link": "http://example.com/3",
            },
        ]

        grouped = group_items_for_podcasts(items, threshold=0.1)

        assert "general" in grouped
        assert sum(len(cluster) for cluster in grouped["general"]) == 3
        assert any(len(cluster) == 2 for cluster in grouped["general"])

    def test_group_items_produces_episode_groups(self):
        """测试 group_items_for_podcasts 产生正确的分组."""
        items = [
            {
                "title": "Apple CEO Announces New Product",
                "summary": "Tim Cook reveals new device",
                "feed_name": "Tech News",
                "category": "tech",
                "link": "http://example.com/1",
            },
            {
                "title": "Apple Stock Rises",
                "summary": "Apple shares up 5%",
                "feed_name": "Finance",
                "category": "business",
                "link": "http://example.com/2",
            },
            {
                "title": "Tesla Launches New Car",
                "summary": "Tesla announced new EV",
                "feed_name": "Auto News",
                "category": "tech",
                "link": "http://example.com/3",
            },
        ]

        grouped = group_items_for_podcasts(items, threshold=0.3)

        assert len(grouped) > 0
        assert "general" in grouped

    def test_deduped_duplicate_rss_entries_only_form_one_group(self):
        """重复 RSS 条目不应生成多个相同播客组."""
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

        unique_items = dedupe_items(items)
        grouped = merge_clusters_by_signature(group_items_for_podcasts(unique_items, threshold=0.3))

        assert len(unique_items) == 2
        total_groups = sum(len(groups) for groups in grouped.values())
        total_items = sum(len(group) for groups in grouped.values() for group in groups)

        assert total_groups == 2
        assert total_items == 2

    def test_build_podcast_plan_creates_valid_structure(self):
        """测试 build_podcast_plan 创建有效的计划结构."""
        items = [
            {
                "item_id": "1",
                "feed_id": "ai-news",
                "feed_name": "AI News",
                "category": "tech_ai",
                "title": "AI Model Released",
                "summary": "New AI model announced",
                "published": "2024-01-01",
                "link": "http://example.com/1",
            },
            {
                "item_id": "2",
                "feed_id": "ai-news",
                "feed_name": "AI News",
                "category": "tech_ai",
                "title": "AI Industry Growth",
                "summary": "AI market growing fast",
                "published": "2024-01-02",
                "link": "http://example.com/2",
            },
        ]

        plan = build_podcast_plan("tech_ai", items)

        assert plan.topic_id == "tech_ai"
        assert len(plan.selected_items) == 2
        assert len(plan.segments) > 0
        assert plan.closing_takeaway is not None

    def test_build_group_plan(self):
        """测试 build_group_plan 创建组计划."""
        items = [
            {
                "item_id": "1",
                "feed_id": "news",
                "feed_name": "News",
                "category": "tech_ai",
                "title": "AI News 1",
                "summary": "Summary 1",
                "published": "2024-01-01",
                "link": "http://1.com",
            },
            {
                "item_id": "2",
                "feed_id": "news",
                "feed_name": "News",
                "category": "tech_ai",
                "title": "AI News 2",
                "summary": "Summary 2",
                "published": "2024-01-02",
                "link": "http://2.com",
            },
        ]

        plan = build_group_plan("tech_ai", items, "Daily AI Update")

        assert plan.topic_id == "tech_ai"
        assert plan.topic_name == "Daily AI Update"
        assert len(plan.selected_items) == 2


class TestPendingGroupsMerging:
    """待处理组合并集成测试."""

    def test_merge_clusters_with_similar_items(self):
        """测试合并相似的待处理簇."""
        # 之前的待处理组
        pending_groups = [
            {
                "category": "tech_ai",
                "items": [
                    {
                        "title": "AI Model Part 1",
                        "summary": "First part of AI story",
                        "link": "http://part1.com",
                    }
                ],
            }
        ]

        new_items = [
            {
                "title": "AI Model Part 1 Continues",
                "summary": "Second part of the same AI story",
                "link": "http://part1-cont.com",
            },
            {
                "title": "Unrelated Sports News",
                "summary": "Sports update",
                "link": "http://sports.com",
            },
        ]

        remaining, generated, consumed = merge_pending_groups(
            pending_groups,
            new_items,
            threshold=0.2,
        )

        assert len(generated) == 1
        assert generated[0]["category"] == "general"
        assert consumed == ["http://part1-cont.com"]

    def test_merge_does_not_combine_different_topics(self):
        """测试不合并不同主题的组."""
        pending_groups = [
            {
                "category": "tech_ai",
                "items": [
                    {
                        "title": "AI News",
                        "summary": "AI update",
                        "link": "http://ai.com",
                    }
                ],
            }
        ]

        new_items = [
            {
                "title": "Business News",
                "summary": "Business update",
                "link": "http://biz.com",
            }
        ]

        remaining, generated, consumed = merge_pending_groups(
            pending_groups,
            new_items,
            threshold=0.5,
        )

        assert len(remaining) >= 1
        assert generated == []
        assert consumed == []


class TestEpisodePlanFormatting:
    """Episode plan 格式化集成测试."""

    def test_format_plan_for_prompt_complete(self):
        """测试完整的 plan 格式化输出."""
        from app.pipelines.episode_planner import EpisodePlan, PlannedNewsItem, EpisodeSegment

        plan = EpisodePlan(
            topic_id="tech_ai",
            topic_name="AI News",
            title_hint="AI Today",
            theme_statement="AI is advancing rapidly",
            audience="Tech enthusiasts",
            editorial_angle="Covering AI developments",
            selected_items=[
                PlannedNewsItem(
                    item_id="1",
                    feed_id="ai-news",
                    feed_name="AI News",
                    category="tech_ai",
                    title="AI Model Released",
                    summary="New AI model announced",
                    published="2024-01-01",
                    link="http://example.com/1",
                    score=1.5,
                    selection_reason="Direct match with topic",
                )
            ],
            segments=[
                EpisodeSegment(
                    segment_type="opening",
                    purpose="Introduce the topic",
                    item_refs=["1"],
                    segment_thesis="Start with the main story",
                )
            ],
            closing_takeaway="Remember to follow AI news",
        )

        formatted = format_plan_for_prompt(plan)

        assert "AI News" in formatted
        assert "AI Today" in formatted
        assert "Tech enthusiasts" in formatted
        assert "AI Model Released" in formatted
        assert "Remember to follow AI news" in formatted


class TestTFIDFAndCosineIntegration:
    """TF-IDF 和余弦相似度集成测试."""

    def test_clustering_with_real_text(self):
        """测试真实文本的聚类."""
        items = [
            {
                "title": "OpenAI GPT-5 Model Announcement",
                "summary": "OpenAI released their latest AI model GPT-5 with improved capabilities",
                "link": "http://1.com",
            },
            {
                "title": "Google Gemini 2 Release",
                "summary": "Google announced Gemini 2, their newest AI model",
                "link": "http://2.com",
            },
            {
                "title": "Football Match Results",
                "summary": "Local football team won the championship game 3-2",
                "link": "http://3.com",
            },
        ]

        # 聚类相似的新闻
        clusters = cluster_by_similarity(items, threshold=0.3)

        # AI 新闻应该在一起
        ai_items = [item for cluster in clusters for item in cluster
                   if "AI" in item.get("title", "") or "model" in item.get("summary", "").lower()]
        football_items = [item for cluster in clusters for item in cluster
                         if "football" in item.get("title", "").lower()]

        assert len(ai_items) == 2  # 两篇 AI 新闻
        assert len(football_items) == 1  # 一篇足球新闻
