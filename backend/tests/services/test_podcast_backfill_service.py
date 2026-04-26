import json
import os
from datetime import datetime

from app.models.podcast import Podcast
from app.services.podcast_backfill_service import PodcastBackfillService


def _write_backfill_fixture(base_dir, category="tech_ai", slug="01-sample", with_timing=True):
    podcast_dir = base_dir / category / slug
    audio_dir = podcast_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    (audio_dir / "podcast_full.mp3").write_bytes(b"fake-mp3")
    (podcast_dir / "podcast_script.json").write_text(
        json.dumps(
            {
                "title": "Sample Podcast",
                "intro": "Intro text",
                "sections": [
                    {
                        "section_type": "opening",
                        "dialogues": [
                            {"speaker": "A", "content": "Hello", "emotion": ""},
                            {"speaker": "B", "content": "Hi", "emotion": ""},
                        ],
                        "summary": "summary",
                    }
                ],
                "total_duration": "1min",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (podcast_dir / "podcast_script.txt").write_text("formatted script", encoding="utf-8")
    (podcast_dir / "episode_plan.json").write_text(
        json.dumps({"items": [{"title": "Source title", "link": "https://example.com"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    if with_timing:
        (podcast_dir / "podcast_timing.json").write_text(
            json.dumps([
                {"item_type": "speech", "speaker": "A", "text": "Hello", "start_ms": 0, "end_ms": 500},
            ], ensure_ascii=False),
            encoding="utf-8",
        )
    return podcast_dir


def test_backfill_creates_podcast(tmp_path, db_session):
    output_dir = tmp_path / "podcasts"
    podcast_dir = _write_backfill_fixture(output_dir)
    audio_path = podcast_dir / "audio" / "podcast_full.mp3"
    expected_timestamp = datetime(2026, 4, 25, 18, 46, 0).timestamp()
    os.utime(audio_path, (expected_timestamp, expected_timestamp))

    service = PodcastBackfillService(db_session, podcasts_root=output_dir)
    result = service.backfill()

    assert result.counters.created == 1
    podcasts = db_session.query(Podcast).all()
    assert len(podcasts) == 1
    assert podcasts[0].title == "Sample Podcast"
    assert podcasts[0].timing_json != ""
    assert podcasts[0].source_items_json != "[]"
    assert podcasts[0].published_at == datetime.fromtimestamp(expected_timestamp)


def test_backfill_updates_existing_podcast(tmp_path, db_session):
    output_dir = tmp_path / "podcasts"
    _write_backfill_fixture(output_dir, with_timing=True)
    existing = Podcast(
        title="Old",
        summary="",
        category="tech_ai",
        audio_url="/audio/podcasts/tech_ai/01-sample/audio/podcast_full.mp3",
        script_path="output/podcasts/tech_ai/01-sample/podcast_script.json",
        script_json="",
        script_text="",
        timing_json="",
        source_items_json="[]",
    )
    db_session.add(existing)
    db_session.commit()

    service = PodcastBackfillService(db_session, podcasts_root=output_dir)
    result = service.backfill()

    assert result.counters.updated == 1
    refreshed = db_session.query(Podcast).filter(Podcast.id == existing.id).first()
    assert refreshed is not None
    assert refreshed.summary == "Intro text"
    assert refreshed.script_json != ""
    assert refreshed.timing_json != ""


def test_backfill_skips_when_audio_missing(tmp_path, db_session):
    output_dir = tmp_path / "podcasts"
    podcast_dir = _write_backfill_fixture(output_dir)
    (podcast_dir / "audio" / "podcast_full.mp3").unlink()

    service = PodcastBackfillService(db_session, podcasts_root=output_dir)
    result = service.backfill()

    assert result.counters.skipped == 1
    assert db_session.query(Podcast).count() == 0
