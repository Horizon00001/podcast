import json
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.podcast import PodcastCreate
from app.services.podcast_service import PodcastService


@dataclass
class BackfillCounters:
    scanned: int = 0
    eligible: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass
class BackfillResult:
    counters: BackfillCounters
    messages: list[str]


class PodcastBackfillService:
    def __init__(self, db: Session, podcasts_root: Path | None = None):
        self._podcast_service = PodcastService(db)
        self._podcasts_root = podcasts_root or (settings.output_dir / "podcasts")

    def backfill(self, dry_run: bool = False, force: bool = False) -> BackfillResult:
        counters = BackfillCounters()
        messages: list[str] = []

        for podcast_dir in sorted(self._iter_podcast_dirs()):
            counters.scanned += 1
            try:
                payload = self._build_payload(podcast_dir)
            except FileNotFoundError as exc:
                counters.skipped += 1
                messages.append(f"SKIP {podcast_dir}: {exc}")
                continue
            except (json.JSONDecodeError, ValueError) as exc:
                counters.failed += 1
                messages.append(f"FAIL {podcast_dir}: {exc}")
                continue

            counters.eligible += 1
            status = self._podcast_service.upsert_podcast(payload, dry_run=dry_run, force=force)
            if status == "created":
                counters.created += 1
            elif status == "updated":
                counters.updated += 1
            else:
                counters.skipped += 1
            messages.append(f"{status.upper()} {podcast_dir}")

        return BackfillResult(counters=counters, messages=messages)

    def _iter_podcast_dirs(self):
        if not self._podcasts_root.exists():
            return []
        return [path for path in self._podcasts_root.glob("*/*") if path.is_dir()]

    def _build_payload(self, podcast_dir: Path) -> PodcastCreate:
        script_json_path = podcast_dir / "podcast_script.json"
        audio_path = podcast_dir / "audio" / "podcast_full.mp3"
        if not script_json_path.exists():
            raise FileNotFoundError("missing podcast_script.json")
        if not audio_path.exists():
            raise FileNotFoundError("missing audio/podcast_full.mp3")

        with open(script_json_path, "r", encoding="utf-8") as f:
            script_data = json.load(f)

        title = script_data.get("title", "未命名播客")
        summary = script_data.get("intro", "")
        category = podcast_dir.parent.name
        audio_url = f"/audio/podcasts/{category}/{podcast_dir.name}/audio/podcast_full.mp3"
        script_path = f"output/podcasts/{category}/{podcast_dir.name}/podcast_script.json"

        script_text_path = podcast_dir / "podcast_script.txt"
        timing_path = podcast_dir / "podcast_timing.json"
        plan_path = podcast_dir / "episode_plan.json"

        source_items = []
        if plan_path.exists():
            with open(plan_path, "r", encoding="utf-8") as f:
                plan_data = json.load(f)
            source_items = plan_data.get("items", [])

        return PodcastCreate(
            title=title,
            summary=summary,
            category=category,
            audio_url=audio_url,
            script_path=script_path,
            script_json=json.dumps(script_data, ensure_ascii=False),
            script_text=script_text_path.read_text(encoding="utf-8") if script_text_path.exists() else "",
            timing_json=timing_path.read_text(encoding="utf-8") if timing_path.exists() else "",
            source_items_json=json.dumps(source_items, ensure_ascii=False),
            published_at=self._audio_generated_at(audio_path),
        )

    @staticmethod
    def _audio_generated_at(audio_path: Path) -> datetime:
        return datetime.fromtimestamp(audio_path.stat().st_mtime)
