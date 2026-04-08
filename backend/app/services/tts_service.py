import asyncio
import json
import re
import subprocess
from pathlib import Path

import edge_tts


class TTSService:
    VOICE_MAP = {
        "主持人A": "zh-CN-YunxiNeural",
        "主持人B": "zh-CN-XiaoxiaoNeural",
        "A": "zh-CN-YunxiNeural",
        "B": "zh-CN-XiaoxiaoNeural",
    }
    DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.audio_dir = self.output_dir / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self._cleanup_old_files()

    def _cleanup_old_files(self):
        for f in self.audio_dir.glob("segment_*.mp3"):
            f.unlink(missing_ok=True)

    def clean_text(self, text: str) -> str:
        return re.sub(r"[\(（].*?[\)）]", "", text).strip()

    def load_script(self, json_path: Path | str) -> dict:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def synthesize_podcast(self, json_path: Path | str) -> Path:
        data = self.load_script(json_path)
        sections = data.get("sections", [])

        all_dialogues = []
        for section in sections:
            dialogues = section.get("dialogues", [])
            for dialogue in dialogues:
                speaker = dialogue.get("speaker")
                content = dialogue.get("content")
                cleaned_content = self.clean_text(content)
                voice = self.VOICE_MAP.get(speaker, self.DEFAULT_VOICE)
                all_dialogues.append({
                    "voice": voice,
                    "text": cleaned_content,
                    "speaker": speaker,
                })

        temp_files = []
        for idx, d in enumerate(all_dialogues):
            temp_filename = str(self.audio_dir / f"segment_{idx:03d}.mp3")
            communicate = edge_tts.Communicate(d["text"], d["voice"])
            await communicate.save(temp_filename)
            temp_files.append(temp_filename)

        return await self.merge_audio_files(temp_files)

    async def merge_audio_files(self, temp_files: list[str]) -> Path:
        output_full = str(self.audio_dir / "podcast_full.mp3")
        list_file = str(self.audio_dir / "file_list.txt")

        with open(list_file, "w", encoding="utf-8") as f:
            for temp_file in temp_files:
                abs_path = Path(temp_file).resolve().as_posix()
                f.write(f"file '{abs_path}'\n")

        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", list_file, "-c", "copy", output_full,
                ],
                check=True,
                capture_output=True,
            )
        finally:
            if Path(list_file).exists():
                Path(list_file).unlink()
            for f in temp_files:
                if Path(f).exists():
                    Path(f).unlink()

        return Path(output_full)
