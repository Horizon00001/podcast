import asyncio
import json
import random
import re
import subprocess
import shutil
from pathlib import Path

from app.core.config import settings

from .audio_plan import RenderPlan, RenderPlanItem, RenderPlanner
from .speech_provider import SpeechProvider, create_speech_provider


class TTSService:
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
    OPENING_LIBRARY_DIR = "opening"
    TRANSITION_LIBRARY_DIR = "transition"
    CLOSING_LIBRARY_DIR = "closing"
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
        self.opening_library_dir = self.assets_audio_dir / self.OPENING_LIBRARY_DIR
        self.transition_library_dir = self.assets_audio_dir / self.TRANSITION_LIBRARY_DIR
        self.closing_library_dir = self.assets_audio_dir / self.CLOSING_LIBRARY_DIR
        self.opening_music_candidates = self._build_legacy_candidates(self.MUSIC_FILES)
        self.transition_music_candidates = self._build_legacy_candidates(self.TRANSITION_MUSIC_FILES)
        self.closing_music_candidates = self._build_legacy_candidates(self.MUSIC_FILES)
        self._cleanup_old_files()
        self.speech_provider = speech_provider or create_speech_provider()

    def _build_legacy_candidates(self, filenames: list[str]) -> list[Path]:
        candidates: list[Path] = []
        for fname in filenames:
            candidates.append(self.assets_audio_dir / fname)
        for fname in filenames:
            candidates.append(self.audio_dir / fname)
        return candidates

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

    def build_render_plan(
        self,
        data: dict,
        include_trailing_gap: bool = False,
        inject_fallback_opening: bool = True,
    ) -> RenderPlan:
        plan = RenderPlanner.build_from_script(data, force_trailing_gap=include_trailing_gap)
        return self._inject_default_assets(plan, inject_fallback_opening=inject_fallback_opening)

    def build_section_render_plan(self, title: str, section: dict, include_trailing_gap: bool = False) -> RenderPlan:
        return self.build_render_plan(
            {
                "title": title,
                "sections": [section],
            },
            include_trailing_gap=include_trailing_gap,
            inject_fallback_opening=False,
        )

    def _inject_default_assets(self, plan: RenderPlan, inject_fallback_opening: bool = True) -> RenderPlan:
        opening_music = self._pick_music_asset(self.opening_library_dir, self.opening_music_candidates)
        if not opening_music:
            return plan
        transition_music = self._pick_music_asset(self.transition_library_dir, self.transition_music_candidates)
        closing_music = self._pick_music_asset(self.closing_library_dir, self.closing_music_candidates)

        music_items = [item for item in plan.items if item.item_type == "music"]
        for item in music_items:
            role = item.metadata.get("role") if item.metadata else None
            if item.asset_path is None:
                if role == "transition_sting" and transition_music:
                    item.asset_path = transition_music
                elif role == "closing_tail" and closing_music:
                    item.asset_path = closing_music
                else:
                    item.asset_path = opening_music

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

        if inject_fallback_opening and not music_items:
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

    def _pick_music_asset(self, library_dir: Path, legacy_candidates: list[Path]) -> Path | None:
        library_assets = self._list_library_assets(library_dir)
        if library_assets:
            return random.choice(library_assets)
        return self._find_existing_asset(legacy_candidates)

    def _list_library_assets(self, library_dir: Path) -> list[Path]:
        if not library_dir.exists() or not library_dir.is_dir():
            return []
        return sorted(
            [
                path for path in library_dir.iterdir()
                if path.is_file() and path.suffix.lower() in self.AUDIO_EXTENSIONS
            ]
        )

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
        ordered_files = [str(Path(path)) for path in section_files if path and Path(path).exists()]
        if not ordered_files:
            raise RuntimeError(f"No valid section files to merge: {section_files}")
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

        temp_files = [str(path) for path in rendered_paths if path and path.exists()]
        if not temp_files:
            raise RuntimeError(f"No audio files generated for plan: {output_path}")
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
        asset_duration = self._probe_audio_duration_seconds(asset_path)

        # Some cue defaults assume a longer source clip than the bundled asset.
        # Clamp the trim window so ffmpeg does not emit a zero-duration mp3.
        if asset_duration > 0 and trim_start_sec >= asset_duration:
            trim_start_sec = 0
            if trim_end_sec <= 0:
                target_duration_ms = item.duration_ms or 0
                if target_duration_ms > 0:
                    trim_end_sec = min(target_duration_ms / 1000, asset_duration)

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
            duration = asset_duration
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
