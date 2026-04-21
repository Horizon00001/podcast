import asyncio
from pathlib import Path

from app.pipelines.episode_planner import (
    PENDING_GROUPS_FILENAME,
    build_group_name,
    build_group_plan,
    classify_items,
    group_items_for_podcasts,
    load_pending_groups,
    load_rss_items,
    merge_clusters_by_signature,
    merge_pending_groups,
    save_episode_plan,
    save_pending_groups,
)
from app.pipelines.generate_text_pipeline import build_generation_input
from app.pipelines.rss_pipeline import fetch_rss_feeds
from app.services.script_service import ScriptService
from app.services.tts_service import TTSService


async def run_pipeline(topic: str = "daily-news"):
    base_dir = Path(__file__).resolve().parents[3]
    config_path = base_dir / "config" / "feed.json"
    output_dir = base_dir / "output"
    rss_data_path = output_dir / "rss_data.json"
    podcasts_dir = output_dir / "podcasts"
    pending_groups_path = podcasts_dir / PENDING_GROUPS_FILENAME

    print("=" * 50)
    print("开始执行播客生成全流程（4 步）")
    print("=" * 50)

    def log(message: str):
        print(message, flush=True)

    log("\n[1/4] 抓取 RSS 数据")
    fetch_rss_feeds(config_path, output_dir)
    if not rss_data_path.exists():
        raise FileNotFoundError(f"未生成 RSS 数据文件: {rss_data_path}")

    log("\n[2/4] 分类并聚类新闻")
    all_items = load_rss_items(rss_data_path)
    pending_groups, used_item_links = load_pending_groups(pending_groups_path)
    used_link_set = set(used_item_links)
    fresh_items = [item for item in all_items if item.get("link") not in used_link_set]

    categorized = classify_items(fresh_items)
    remaining_pending, revived_groups, consumed_links = merge_pending_groups(pending_groups, categorized)
    consumed_link_set = set(consumed_links)
    fresh_items = [item for item in fresh_items if item.get("link") not in consumed_link_set]

    grouped_items = merge_clusters_by_signature(group_items_for_podcasts(fresh_items))
    print(f"已分类到类别数: {len(grouped_items)}")

    generated_links = set()

    async def run_group_pipeline(category: str, group_items: list[dict], group_index: int):
        group_title = group_items[0].get("title", category) if group_items else category
        group_slug = build_group_name(group_items, group_title)
        group_dir = podcasts_dir / category / f"{group_index:02d}-{group_slug}"
        group_dir.mkdir(parents=True, exist_ok=True)
        group_label = f"{category}/{group_dir.name}"

        log(f"\n[组开始] {group_label}，新闻数={len(group_items)}")

        plan = build_group_plan(category, group_items, group_title)
        episode_plan_path = group_dir / "episode_plan.json"
        save_episode_plan(plan, episode_plan_path)

        news_content = build_generation_input(topic=category, rss_data_path=rss_data_path, episode_plan_path=episode_plan_path)
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
            log(f"[Section Ready] {group_label} {describe_section(section_index, section_data)}")

            async def render_section() -> Path:
                log(f"[TTS Start] {group_label} {describe_section(section_index, section_data)}")
                audio_path = await tts_service.synthesize_section(
                    title=plan.title_hint,
                    section=section_data,
                    section_index=section_index,
                    include_trailing_gap=include_trailing_gap,
                )
                log(f"[TTS Done] {group_label} {describe_section(section_index, section_data)} -> {audio_path}")
                return audio_path

            section_tasks.append(asyncio.create_task(render_section()))

        log(f"[Script Start] {group_label}")
        await script_service.generate_and_save_streaming_sections(news_content, on_section_ready=on_section_ready)
        log(f"[Script Done] {group_label}")

        script_json_path = group_dir / "podcast_script.json"
        if not script_json_path.exists():
            raise FileNotFoundError(f"未生成播客脚本文件: {script_json_path}")

        log(f"[TTS Wait] {group_label} waiting for {len(section_tasks)} section tasks")
        section_files = await asyncio.gather(*section_tasks)
        log(f"[Merge Start] {group_label} merging {len(section_files)} section files")
        await tts_service.merge_section_audio_files(section_files)
        log(f"[Group Done] {group_label} -> {group_dir / 'audio' / 'podcast_full.mp3'}")
        generated_links.update(item.get("link", "") for item in group_items if item.get("link"))

    tasks = []
    log("\n[3/4] 生成脚本并合成音频")
    for category, clusters in grouped_items.items():
        for index, cluster in enumerate(clusters, start=1):
            if len(cluster) < 2:
                remaining_pending.append(
                    {
                        "group_id": f"{category}-{index}-{build_group_name(cluster, cluster[0].get('title', category) if cluster else category)}",
                        "category": category,
                        "items": cluster,
                        "created_at": None,
                    }
                )
                continue
            tasks.append(run_group_pipeline(category, cluster, index))

    for revived_index, revived in enumerate(revived_groups, start=1):
        tasks.append(run_group_pipeline(revived["category"], revived["items"], revived_index))

    if tasks:
        await asyncio.gather(*tasks)

    if generated_links:
        used_link_set.update(generated_links)

    log("\n[4/4] 保存待处理分组和使用记录")
    save_pending_groups(remaining_pending, sorted(used_link_set), pending_groups_path)

    print("\n" + "=" * 50)
    print("全流程执行完成")
    print(f"RSS 数据: {rss_data_path}")
    print(f"播客目录: {podcasts_dir}")
    print(f"待补充文件: {pending_groups_path}")
    print("=" * 50)
