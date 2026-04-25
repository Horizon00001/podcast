import asyncio
import json
import re
import subprocess
import shutil
from pathlib import Path

from app.core.config import settings

from .audio_plan import RenderPlan, RenderPlanItem, RenderPlanner
from .speech_provider import SpeechProvider, create_speech_provider


class TTSService:
    MUSIC_FILES = [
        "opening_theme_10s_fadeout.mp3",
        "background_music.mp3",
    ]
    TRANSITION_MUSIC_FILES = [
        "transition_music_5s.mp3",
    ]

    def __init__(self, output_dir: str | Path, speech_provider: SpeechProvider | None = None):
        self.output_dir = Path(output_dir)
        self.audio_dir = self.output_dir / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.assets_audio_dir = settings.project_root / "assets" / "audio"
        self.opening_music_candidates = []
        for fname in self.MUSIC_FILES:
            self.opening_music_candidates.append(self.assets_audio_dir / fname)
        for fname in self.MUSIC_FILES:
            self.opening_music_candidates.append(self.audio_dir / fname)
        self.transition_music_candidates = []
        for fname in self.TRANSITION_MUSIC_FILES:
            self.transition_music_candidates.append(self.assets_audio_dir / fname)
        for fname in self.TRANSITION_MUSIC_FILES:
            self.transition_music_candidates.append(self.audio_dir / fname)
        self._cleanup_old_files()
        self.speech_provider = speech_provider or create_speech_provider()

    def _cleanup_old_files(self):
        for f in self.audio_dir.glob("segment_*.mp3"):
            f.unlink(missing_ok=True)
        for f in self.audio_dir.glob("section_*.mp3"):
            f.unlink(missing_ok=True)
        for f in self.audio_dir.glob("*_segment_*.mp3"):
            f.unlink(missing_ok=True)

    def clean_text(self, text: str) -> str:
        return re.sub(r"[\(（].*?[\)）]", "", text).strip()

    def load_script(self, json_path: Path | str) -> dict:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def build_render_plan(self, data: dict, include_trailing_gap: bool = False) -> RenderPlan:
        plan = RenderPlanner.build_from_script(data, force_trailing_gap=include_trailing_gap)
        return self._inject_default_assets(plan)

    def build_section_render_plan(self, title: str, section: dict, include_trailing_gap: bool = False) -> RenderPlan:
        return self.build_render_plan(
            {
                "title": title,
                "sections": [section],
            },
            include_trailing_gap=include_trailing_gap,
        )

    def _inject_default_assets(self, plan: RenderPlan) -> RenderPlan:
        opening_music = self._find_existing_asset(self.opening_music_candidates)
        if not opening_music:
            return plan
        transition_music = self._find_existing_asset(self.transition_music_candidates)

        music_items = [item for item in plan.items if item.item_type == "music"]
        for item in music_items:
            role = item.metadata.get("role") if item.metadata else None
            if item.asset_path is None:
                item.asset_path = transition_music if role == "transition_sting" and transition_music else opening_music

            if role == "opening_theme":
                if item.volume is None:
                    item.volume = 0.24
                if item.fade_out_ms is None:
                    item.fade_out_ms = 1800
            elif role == "transition_sting":
                if item.volume is None:
                    item.volume = 0.20
                if item.fade_out_ms is None:
                    item.fade_out_ms = 350
            elif role == "closing_tail":
                if item.volume is None:
                    item.volume = 0.20
                if item.fade_out_ms is None:
                    item.fade_out_ms = 2600
            else:
                if item.volume is None:
                    item.volume = 0.22
                if item.fade_out_ms is None:
                    item.fade_out_ms = 1300

        if not music_items:
            plan.items.insert(
                0,
                RenderPlanItem(
                    item_type="music",
                    asset_path=opening_music,
                    volume=0.24,
                    fade_out_ms=1800,
                    duration_ms=10000,
                    metadata={"role": "opening_theme"},
                ),
            )
            plan.items.insert(
                1,
                RenderPlanItem(
                    item_type="silence",
                    duration_ms=420,
                    metadata={"role": "opening_voice_delay"},
                ),
            )

        return plan

    @staticmethod
    def _find_existing_asset(candidates: list[Path]) -> Path | None:
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    async def synthesize_podcast(self, json_path: Path | str) -> Path:
        data = self.load_script(json_path)
        plan = self.build_render_plan(data)

        return await self._render_plan(plan, self.audio_dir / "podcast_full.mp3", "segment")

    async def synthesize_section(
        self,
        title: str,
        section: dict,
        section_index: int,
        include_trailing_gap: bool,
    ) -> Path:
        plan = self.build_section_render_plan(title, section, include_trailing_gap=include_trailing_gap)
        output_path = self.audio_dir / f"section_{section_index:03d}.mp3"
        temp_prefix = f"section_{section_index:03d}_segment"
        return await self._render_plan(plan, output_path, temp_prefix)

    async def merge_section_audio_files(self, section_files: list[Path | str]) -> Path:
        ordered_files = [str(Path(path)) for path in section_files if Path(path).exists()]
        return await self.merge_audio_files(ordered_files, output_path=self.audio_dir / "podcast_full.mp3")

    async def _render_plan(self, plan: RenderPlan, output_path: Path, temp_prefix: str) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        tasks = [
            asyncio.to_thread(
                self._render_plan_item_sync,
                item,
                str(self.audio_dir / f"{temp_prefix}_{idx:03d}.mp3"),
            )
            for idx, item in enumerate(plan.items)
        ]
        rendered_paths = await asyncio.gather(*tasks)

        timing_data = self._build_timing_data(plan.items, rendered_paths)
        timing_path = output_path.parent / f"{output_path.stem}_timing.json"
        with open(timing_path, "w", encoding="utf-8") as f:
            json.dump(timing_data, f, ensure_ascii=False, indent=2)

        temp_files = [str(path) for path in rendered_paths if path]
        return await self.merge_audio_files(temp_files, output_path=output_path)

    def _render_plan_item_sync(self, item: RenderPlanItem, temp_filename: str) -> Path | None:
        if item.item_type == "speech":
            cleaned_text = self.clean_text(item.text or "")
            if not cleaned_text:
                return None

            output_path = Path(temp_filename)
            return asyncio.run(
                self.speech_provider.synthesize(
                    cleaned_text,
                    output_path,
                    voice=item.voice,
                    style=item.style,
                )
            )

        if item.item_type == "silence":
            duration_ms = item.duration_ms or 0
            if duration_ms <= 0:
                return None
            return self._render_silence(Path(temp_filename), duration_ms)

        asset_path = item.asset_path
        if asset_path and asset_path.exists():
            if item.item_type == "music":
                return self._render_music_asset(asset_path, Path(temp_filename), item)
            output_path = Path(temp_filename)
            shutil.copy2(asset_path, output_path)
            return output_path

        return None

    async def _render_plan_item(self, item: RenderPlanItem, temp_filename: str) -> Path | None:
        if item.item_type == "speech":
            cleaned_text = self.clean_text(item.text or "")
            if not cleaned_text:
                return None

            output_path = Path(temp_filename)
            return await self.speech_provider.synthesize(
                cleaned_text,
                output_path,
                voice=item.voice,
                style=item.style,
            )

        if item.item_type == "silence":
            duration_ms = item.duration_ms or 0
            if duration_ms <= 0:
                return None
            return self._render_silence(Path(temp_filename), duration_ms)

        asset_path = item.asset_path
        if asset_path and asset_path.exists():
            if item.item_type == "music":
                return self._render_music_asset(asset_path, Path(temp_filename), item)
            output_path = Path(temp_filename)
            shutil.copy2(asset_path, output_path)
            return output_path

        return None

    def _render_music_asset(self, asset_path: Path, output_path: Path, item: RenderPlanItem) -> Path:
        ffmpeg_bin = self._get_ffmpeg_binary()
        filters = []
        input_args = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(asset_path),
        ]

        trim_start_sec = (item.trim_start_ms or 0) / 1000
        trim_end_sec = (item.trim_end_ms or 0) / 1000
        if trim_start_sec > 0 or trim_end_sec > 0:
            trim_args = []
            if trim_start_sec > 0:
                trim_args.extend(["-ss", f"{trim_start_sec}"])
            if trim_end_sec > 0:
                trim_args.extend(["-t", f"{trim_end_sec}"])
            input_args = [ffmpeg_bin, "-y", *trim_args, "-i", str(asset_path)]

        if item.volume is not None:
            filters.append(f"volume={item.volume}")
        if item.fade_out_ms:
            duration = self._probe_audio_duration_seconds(asset_path)
            if duration > 0:
                fade_start = max(duration - (item.fade_out_ms / 1000), 0)
                filters.append(f"afade=t=out:st={fade_start}:d={item.fade_out_ms / 1000}")

        if filters:
            input_args.extend(["-af", ",".join(filters)])

        input_args.extend([
            "-c:a",
            "libmp3lame",
            "-b:a",
            "256k",
            str(output_path),
        ])

        subprocess.run(input_args, check=True, capture_output=True)
        return output_path

    def _probe_audio_duration_seconds(self, asset_path: Path) -> float:
        try:
            import mutagen
            from mutagen.mp3 import MP3

            audio = MP3(asset_path)
            return float(audio.info.length)
        except Exception:
            return 0.0

    @staticmethod
    def _seconds_to_ms(seconds: float) -> int:
        return int(max(seconds, 0) * 1000)

    def _build_timing_data(self, items: list[RenderPlanItem], rendered_paths: list) -> list[dict]:
        timing = []
        cumulative_ms = 0

        for item, path in zip(items, rendered_paths):
            if path is not None:
                duration_ms = self._seconds_to_ms(self._probe_audio_duration_seconds(Path(str(path))))
            elif item.item_type == "speech":
                duration_ms = 0
            else:
                duration_ms = item.duration_ms or 0

            entry = {
                "item_type": item.item_type,
                "start_ms": cumulative_ms,
                "end_ms": cumulative_ms + duration_ms,
                "duration_ms": duration_ms,
            }
            if item.speaker:
                entry["speaker"] = item.speaker
            if item.text:
                entry["text"] = item.text
            if item.metadata:
                entry["metadata"] = item.metadata

            timing.append(entry)
            cumulative_ms += duration_ms

        return timing

    def _render_silence(self, output_path: Path, duration_ms: int) -> Path:
        duration_sec = max(duration_ms, 1) / 1000
        ffmpeg_bin = self._get_ffmpeg_binary()
        subprocess.run(
            [
                ffmpeg_bin,
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r=44100:cl=stereo",
                "-t",
                f"{duration_sec}",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "256k",
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )
        return output_path

    def _get_ffmpeg_binary(self) -> str:
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg

        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            raise FileNotFoundError("找不到可用的 ffmpeg，可安装系统 ffmpeg 或 imageio_ffmpeg")

    async def merge_audio_files(self, temp_files: list[str], output_path: Path | str | None = None) -> Path:
        output_full = Path(output_path) if output_path else self.audio_dir / "podcast_full.mp3"
        list_file = output_full.with_name(f"{output_full.stem}_file_list.txt")

        with open(list_file, "w", encoding="utf-8") as f:
            for temp_file in temp_files:
                abs_path = Path(temp_file).resolve().as_posix()
                f.write(f"file '{abs_path}'\n")

        try:
            subprocess.run(
                [self._get_ffmpeg_binary(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c:a", "libmp3lame", "-b:a", "256k", str(output_full)],
                check=True,
                capture_output=True,
            )
        finally:
            if list_file.exists():
                list_file.unlink()
            for f in temp_files:
                if Path(f).exists():
                    Path(f).unlink()

        return output_full
