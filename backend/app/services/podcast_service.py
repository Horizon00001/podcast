import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.podcast_repository import PodcastRepository
from app.schemas.podcast import PodcastCreate, ScriptLineResponse
from app.schemas.script import PodcastScript

ESTIMATED_CHARS_PER_SECOND = 4.0
MAX_PODCAST_TITLE_LENGTH = 20


def _resolve_script_path(script_path: str) -> Path:
    p = Path(script_path)
    if p.is_absolute():
        return p
    return settings.project_root / p


def normalize_podcast_title(title: str) -> str:
    normalized = (title or "").strip()
    if not normalized:
        return "未命名播客"
    return normalized[:MAX_PODCAST_TITLE_LENGTH]


def _flatten_to_script_lines(script: PodcastScript) -> list[ScriptLineResponse]:
    lines = []
    line_id = 0
    cumulative_ms = 0

    for section in script.sections:
        for dialogue in section.dialogues:
            speaker = "host" if dialogue.speaker == "A" else "guest"
            text = dialogue.content
            char_count = len(text)
            duration_ms = int((char_count / ESTIMATED_CHARS_PER_SECOND) * 1000)
            if duration_ms < 500:
                duration_ms = 500

            lines.append(ScriptLineResponse(
                id=line_id + 1,
                speaker=speaker,
                text=text,
                startTime=cumulative_ms,
                endTime=cumulative_ms + duration_ms,
            ))
            cumulative_ms += duration_ms
            line_id += 1

    return lines


def _flatten_from_timing(timing_path: Path) -> list[ScriptLineResponse]:
    with open(timing_path, "r", encoding="utf-8") as f:
        timing_data = json.load(f)

    lines = []
    line_id = 0

    for entry in timing_data:
        if entry.get("item_type") != "speech":
            continue
        speaker = "host" if entry.get("speaker") in ("A", "主持人A") else "guest"
        lines.append(ScriptLineResponse(
            id=line_id + 1,
            speaker=speaker,
            text=entry.get("text", ""),
            startTime=entry["start_ms"],
            endTime=entry["end_ms"],
        ))
        line_id += 1

    return lines


class PodcastService:
    def __init__(self, db: Session):
        self.repository = PodcastRepository(db)

    def list_podcasts(self):
        return self.repository.list_podcasts()

    def get_podcast(self, podcast_id: int):
        return self.repository.get_podcast(podcast_id)

    def get_podcast_by_event_key(self, event_key: str):
        return self.repository.get_by_event_key((event_key or "").strip())

    def create_podcast(self, payload: PodcastCreate):
        normalized_payload = payload.model_copy(update={"title": normalize_podcast_title(payload.title)})
        return self.repository.create_podcast(normalized_payload)

    def upsert_podcast(self, payload: PodcastCreate, force: bool = False) -> tuple[str, object | None]:
        normalized_payload = payload.model_copy(
            update={
                "title": normalize_podcast_title(payload.title),
                "event_key": (payload.event_key or "").strip(),
            }
        )
        existing = self.repository.get_by_event_key(normalized_payload.event_key)
        if existing is None:
            return "created", self.repository.create_podcast(normalized_payload)
        if not force:
            return "skipped", None
        return "updated", self.repository.update_podcast(existing, normalized_payload)

    def get_podcast_script(self, podcast_id: int) -> list[ScriptLineResponse]:
        podcast = self.repository.get_podcast(podcast_id)
        if not podcast:
            return []

        script_path = podcast.script_path
        if not script_path:
            return []

        full_path = _resolve_script_path(script_path)
        if not full_path.exists():
            return []

        timing_path = full_path.parent / "podcast_timing.json"
        if timing_path.exists():
            return _flatten_from_timing(timing_path)

        with open(full_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        script = PodcastScript.model_validate(raw)
        return _flatten_to_script_lines(script)
