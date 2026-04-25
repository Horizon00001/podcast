import json
import re
import shutil
from pathlib import Path

from app.db.session import SessionLocal
from app.schemas.podcast import PodcastCreate
from app.services.podcast_service import PodcastService
from app.services.podcast_service import normalize_podcast_title


class GenerationResultService:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    async def save_generated_podcast(self, task_id: str, add_log) -> None:
        try:
            json_path = self.output_dir / "podcast_script.json"
            audio_path = self.output_dir / "audio" / "podcast_full.mp3"

            if not json_path.exists() or not audio_path.exists():
                await add_log(task_id, "⚠️ 未能找到生成的文件，入库失败")
                return

            with open(json_path, "r", encoding="utf-8") as file:
                script_data = json.load(file)

            title = self._normalize_display_title(script_data.get("title", "未命名播客"))
            summary = script_data.get("intro", "")

            final_audio_name = f"podcast_{task_id}.mp3"
            final_audio_path = self.output_dir / "audio" / final_audio_name
            shutil.copy2(audio_path, final_audio_path)

            final_script_name = f"podcast_{task_id}.json"
            final_script_path = self.output_dir / "audio" / final_script_name
            shutil.copy2(json_path, final_script_path)

            db = SessionLocal()
            try:
                podcast_service = PodcastService(db)
                payload = PodcastCreate(
                    title=title,
                    summary=summary,
                    audio_url=f"/audio/{final_audio_name}",
                    script_path=str(final_script_path),
                )
                podcast = podcast_service.create_podcast(payload)
                await add_log(task_id, f"✅ 播客已成功添加到列表: ID={podcast.id}")
            finally:
                db.close()

        except Exception as exc:
            await add_log(task_id, f"❌ 入库过程中出现错误: {str(exc)}")

    @staticmethod
    def _normalize_display_title(title: str) -> str:
        normalized = (title or "").strip()
        if not normalized:
            return "本期新闻深度解读"

        looks_like_slug = bool(re.fullmatch(r"\d+-[a-z0-9-]+", normalized.lower()))
        ascii_chars = sum(1 for char in normalized if ord(char) < 128)
        has_cjk = bool(re.search(r"[\u4e00-\u9fff]", normalized))
        mostly_ascii = ascii_chars / max(len(normalized), 1) > 0.7

        if looks_like_slug or (mostly_ascii and not has_cjk):
            return "本期新闻深度解读"

        return normalize_podcast_title(normalized)
