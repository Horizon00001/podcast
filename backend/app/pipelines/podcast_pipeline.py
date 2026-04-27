import asyncio
import json
from pathlib import Path
from typing import Any, Callable

from app.pipelines.episode_planner import (
    USED_ITEM_LINKS_FILENAME,
    build_item_key,
    build_cluster_key,
    build_group_name,
    group_items_for_podcasts,
    load_rss_items,
    load_used_item_links,
    save_used_item_links,
    set_episode_planner_logger,
)
from app.pipelines.generate_text_pipeline import build_generation_input
from app.pipelines.rss_pipeline import fetch_rss_feeds
from app.schemas.podcast import PodcastCreate
from app.services.embedding_service import get_embedding_service
from app.services.podcast_service import PodcastService
from app.services.script_service import ScriptService
from app.services.tts_service import TTSService
from app.db.session import SessionLocal


def _summarize_grouped_items(grouped_items: dict[str, list[list[dict]]]) -> dict[str, int]:
    category_count = len(grouped_items)
    total_clusters = 0
    single_item_clusters = 0
    multi_item_clusters = 0

    for clusters in grouped_items.values():
        total_clusters += len(clusters)
        for cluster in clusters:
            if len(cluster) >= 2:
                multi_item_clusters += 1
            else:
                single_item_clusters += 1

    return {
        "category_count": category_count,
        "total_clusters": total_clusters,
        "single_item_clusters": single_item_clusters,
        "multi_item_clusters": multi_item_clusters,
    }


def _save_combined_timing(audio_dir: Path, group_dir: Path, filename: str) -> None:
    timing_files = sorted(audio_dir.glob("section_*_timing.json"))
    if not timing_files:
        return

    combined = []
    cumulative_offset = 0

    for tf in timing_files:
        with open(tf, "r", encoding="utf-8") as f:
            section_timing = json.load(f)

        for entry in section_timing:
            entry["start_ms"] += cumulative_offset
            entry["end_ms"] += cumulative_offset
            combined.append(entry)

        if section_timing:
            cumulative_offset = section_timing[-1]["end_ms"]

    output_path = group_dir / filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)


def _group_embedding_text(item: dict) -> str:
    return " ".join(
        part for part in [item.get("title", ""), item.get("summary", "")] if part
    )


def _average_vectors(vectors: list[list[float]]) -> list[float]:
    valid_vectors = [vector for vector in vectors if vector]
    if not valid_vectors:
        return []

    vector_size = len(valid_vectors[0])
    if any(len(vector) != vector_size for vector in valid_vectors):
        return []

    totals = [0.0] * vector_size
    for vector in valid_vectors:
        for index, value in enumerate(vector):
            totals[index] += value
    return [value / len(valid_vectors) for value in totals]


def _group_center_vector(group_items: list[dict]) -> list[float]:
    service = get_embedding_service()
    if not group_items or not service.is_enabled():
        return []

    texts = [_group_embedding_text(item) for item in group_items]
    if not any(texts):
        return []

    vectors = service.encode_texts(texts)
    return _average_vectors(vectors)


async def run_pipeline(
    topic: str = "daily-news",
    selected_source_ids: list[str] | None = None,
    extra_feeds: list[dict] | None = None,
    log_callback: Callable[[str], Any] = print,
    check_cancelled: Callable[[], bool] | None = None,
):
    base_dir = Path(__file__).resolve().parents[3]
    config_path = base_dir / "config" / "feed.json"
    output_dir = base_dir / "output"
    rss_data_path = output_dir / "rss_data.json"
    podcasts_dir = output_dir / "podcasts"
    used_item_links_path = podcasts_dir / USED_ITEM_LINKS_FILENAME

    log_callback("=" * 50)
    log_callback("开始执行播客生成全流程（4 步）")
    log_callback("=" * 50)

    def log(message: str):
        log_callback(message)

    set_episode_planner_logger(log)

    log("\n[1/4] 抓取 RSS 数据")
    try:
        fetch_rss_feeds(
            config_path,
            output_dir,
            selected_source_ids=selected_source_ids,
            extra_feeds=extra_feeds,
            log_callback=log,
        )
        if not rss_data_path.exists():
            raise FileNotFoundError(f"未生成 RSS 数据文件: {rss_data_path}")

        if check_cancelled and check_cancelled():
            log("\n[取消] 任务已取消，停止执行")
            raise asyncio.CancelledError("任务已取消")

        log("\n[2/4] 分类并聚类新闻")
        all_items = load_rss_items(rss_data_path)
        used_item_links = load_used_item_links(used_item_links_path)
        used_item_key_set = set(used_item_links)
        log(f"[Plan Load] RSS 去重后新闻数={len(all_items)}")
        log(f"[Plan Load] 已消费新闻键={len(used_item_key_set)}")

        fresh_items = [item for item in all_items if build_item_key(item) not in used_item_key_set]
        filtered_used_count = len(all_items) - len(fresh_items)
        log(f"[Plan Filter] 去除已消费新闻={filtered_used_count}，剩余新新闻={len(fresh_items)}")

        grouped_items = group_items_for_podcasts(fresh_items)
        grouped_summary = _summarize_grouped_items(grouped_items)
        log(
            f"[Plan Cluster] 输入新闻={len(fresh_items)}，输出分组={grouped_summary['total_clusters']}，单条组={grouped_summary['single_item_clusters']}，多条组={grouped_summary['multi_item_clusters']}"
        )
        log(
            f"[Plan Result] 可直接生成组={grouped_summary['multi_item_clusters']}，已跳过单条组={grouped_summary['single_item_clusters']}"
        )
        log_callback(f"已分类到类别数: {grouped_summary['category_count']}")

        generated_links = set()
        generated_groups: list[tuple[str, Path, str, str]] = []

        async def run_group_pipeline(category: str, group_items: list[dict], group_index: int):
            if check_cancelled and check_cancelled():
                log(f"\n[取消] 跳过组 {group_index}，任务已取消")
                raise asyncio.CancelledError("任务已取消")

            category = "general"
            group_title = group_items[0].get("title", category) if group_items else category
            event_key = build_cluster_key(category, group_items)
            group_slug = build_group_name(group_items, group_title)
            group_dir = podcasts_dir / category / f"{group_index:02d}-{group_slug}"
            group_dir.mkdir(parents=True, exist_ok=True)
            group_label = f"{category}/{group_dir.name}"

            log(f"\n[组开始] {group_label}，新闻数={len(group_items)}")

            news_content = build_generation_input(topic=group_title, cluster_items=group_items)
            if not news_content:
                raise ValueError(f"未能为分组 {group_dir.name} 构建脚本输入")

            script_service = ScriptService(project_root=base_dir, output_dir=group_dir)
            tts_service = TTSService(group_dir)
            section_tasks: list[asyncio.Task[Path]] = []

            def describe_section(section_index: int, section_data: dict) -> str:
                section_type = section_data.get("section_type", "main_content")
                dialogue_count = len(section_data.get("dialogues", []))
                return f"section={section_index + 1} type={section_type} lines={dialogue_count}"

            async def on_section_ready(section_index: int, section_data: dict, include_trailing_gap: bool):
                if check_cancelled and check_cancelled():
                    log(f"[取消] {group_label} 检测到取消，跳过后续合成")
                    return
                log(f"[Section Ready] {group_label} {describe_section(section_index, section_data)}")

                async def render_section() -> Path:
                    log(f"[TTS Start] {group_label} {describe_section(section_index, section_data)}")
                    audio_path = await tts_service.synthesize_section(
                        title=group_title,
                        section=section_data,
                        section_index=section_index,
                        include_trailing_gap=include_trailing_gap,
                    )
                    log(f"[TTS Done] {group_label} {describe_section(section_index, section_data)} -> {audio_path}")
                    return audio_path

                section_tasks.append(asyncio.create_task(render_section()))

            if check_cancelled and check_cancelled():
                log(f"\n[取消] {group_label} 脚本生成前检测到取消")
                raise asyncio.CancelledError("任务已取消")

            log(f"[Script Start] {group_label}")
            await script_service.generate_and_save_streaming_sections(news_content, on_section_ready=on_section_ready)
            log(f"[Script Done] {group_label}")

            script_json_path = group_dir / "podcast_script.json"
            if not script_json_path.exists():
                raise FileNotFoundError(f"未生成播客脚本文件: {script_json_path}")

            if check_cancelled and check_cancelled():
                log(f"\n[取消] {group_label} TTS 合成前检测到取消")
                raise asyncio.CancelledError("任务已取消")

            log(f"[TTS Wait] {group_label} waiting for {len(section_tasks)} section tasks")
            section_files = await asyncio.gather(*section_tasks)
            log(f"[Merge Start] {group_label} merging {len(section_files)} section files")
            await tts_service.merge_section_audio_files(section_files)
            _save_combined_timing(tts_service.audio_dir, group_dir, "podcast_timing.json")
            log(f"[Group Done] {group_label} -> {group_dir / 'audio' / 'podcast_full.mp3'}")
            generated_links.update(item.get("link", "") for item in group_items if item.get("link"))
            center_vector = _group_center_vector(group_items)
            generated_groups.append((group_label, group_dir, event_key, json.dumps(center_vector)))

        tasks = []
        log("\n[3/4] 生成脚本并合成音频")
        for category, clusters in grouped_items.items():
            for index, cluster in enumerate(clusters, start=1):
                if len(cluster) < 2:
                    log(
                        f"[Plan Skip] 跳过单条组 {category}/{index:02d}-{build_group_name(cluster, cluster[0].get('title', category) if cluster else category)}"
                    )
                    continue
                tasks.append(run_group_pipeline(category, cluster, index))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, asyncio.CancelledError):
                    log("[取消] 有分组被取消")
                elif isinstance(result, Exception):
                    log(f"[错误] 分组执行异常: {result}")

            if check_cancelled and check_cancelled():
                log("\n[取消] 任务已取消，停止执行")
                raise asyncio.CancelledError("任务已取消")

        if generated_links:
            used_item_key_set.update(
                build_item_key(item)
                for clusters in grouped_items.values()
                for cluster in clusters
                for item in cluster
                if len(cluster) >= 2
            )
        log("\n[4/4] 保存使用记录")
        save_used_item_links(sorted(used_item_key_set), used_item_links_path)

        log("\n[5/5] 保存到数据库")
        db = SessionLocal()
        saved_podcast_count = 0
        skipped_duplicate_count = 0
        try:
            podcast_service = PodcastService(db)
            for group_name, group_dir, event_key, content_vector in generated_groups:
                script_file = group_dir / "podcast_script.json"
                audio_file = group_dir / "audio" / "podcast_full.mp3"
                if not script_file.exists() or not audio_file.exists():
                    continue
                with open(script_file, "r", encoding="utf-8") as f:
                    script_data = json.load(f)
                title = script_data.get("title", "未命名播客")
                summary = script_data.get("intro", "")
                audio_url = f"/audio/podcasts/{group_name}/audio/podcast_full.mp3"
                script_path = f"output/podcasts/{group_name}/podcast_script.json"
                payload = PodcastCreate(
                    title=title,
                    summary=summary,
                    event_key=event_key,
                    content_vector=content_vector,
                    audio_url=audio_url,
                    script_path=script_path,
                )
                status, podcast = podcast_service.upsert_podcast(payload)
                if podcast is None:
                    skipped_duplicate_count += 1
                    log(f"⏭️ 已跳过重复事件: {title} ({event_key})")
                    continue
                saved_podcast_count += 1
                log(f"✅ 已{status}: {podcast.id} - {title}")
        finally:
            db.close()

        log(
            "[Pipeline Summary] "
            f"新新闻={len(fresh_items)} "
            f"总分组={grouped_summary['total_clusters']} "
            f"可生成组={grouped_summary['multi_item_clusters']} "
            f"完成组={len(generated_groups)} "
            f"入库成功={saved_podcast_count} "
            f"重复跳过={skipped_duplicate_count}"
        )
        log("[Pipeline Done] 播客生成任务已完成")
        log_callback("\n" + "=" * 50)
        log_callback("全流程执行完成")
        log_callback(f"RSS 数据: {rss_data_path}")
        log_callback(f"播客目录: {podcasts_dir}")
        log_callback(f"已消费新闻键文件: {used_item_links_path}")
        log_callback("=" * 50)
    finally:
        set_episode_planner_logger(None)
