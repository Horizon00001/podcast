from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class SpeechProvider(Protocol):
    async def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str | None = None,
        style: str | None = None,
    ) -> Path:
        ...


class EdgeTTSProvider:
    FALLBACK_VOICES = (
        "zh-CN-XiaoxiaoNeural",
        "zh-CN-YunxiNeural",
        "zh-CN-YunyangNeural",
        "zh-CN-XiaoyiNeural",
    )

    def __init__(self, default_voice: str = "zh-CN-XiaoxiaoNeural"):
        self.default_voice = default_voice

    async def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str | None = None,
        style: str | None = None,
    ) -> Path:
        del style

        try:
            import edge_tts
        except ModuleNotFoundError as exc:
            raise RuntimeError("edge_tts is not installed") from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)
        voices_to_try = [voice or self.default_voice]
        for fallback_voice in self.FALLBACK_VOICES:
            if fallback_voice not in voices_to_try:
                voices_to_try.append(fallback_voice)

        last_error: Exception | None = None
        for candidate_voice in voices_to_try:
            try:
                communicate = edge_tts.Communicate(text, candidate_voice)
                await communicate.save(str(output_path))
                return output_path
            except Exception as exc:
                last_error = exc
                continue

        if last_error:
            raise last_error
        return output_path


class DashScopeTTSProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "cosyvoice-v2",
        male_voice: str | None = None,
        female_voice: str | None = None,
        base_websocket_api_url: str = "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
    ):
        self.api_key = api_key
        self.model = model
        self.male_voice = male_voice or "loongdavid_v2"
        self.female_voice = female_voice or "longanwen"
        self.base_websocket_api_url = base_websocket_api_url

    def _resolve_voice_id(self, voice: str | None) -> str:
        if voice == "male":
            return self.male_voice
        if voice == "female" or not voice:
            return self.female_voice
        return voice

    async def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str | None = None,
        style: str | None = None,
    ) -> Path:
        del style

        output_path.parent.mkdir(parents=True, exist_ok=True)
        voice_id = self._resolve_voice_id(voice)

        try:
            import dashscope
            from dashscope.audio.tts_v2 import SpeechSynthesizer
        except ModuleNotFoundError as exc:
            raise RuntimeError("dashscope is not installed") from exc

        dashscope.api_key = self.api_key
        dashscope.base_websocket_api_url = self.base_websocket_api_url
        synthesizer = SpeechSynthesizer(model=self.model, voice=voice_id)
        audio = synthesizer.call(text)

        audio_bytes = self._coerce_audio_bytes(audio)
        if not audio_bytes:
            raise RuntimeError(f"DashScope TTS returned empty audio for voice={voice_id}")

        output_path.write_bytes(audio_bytes)
        return output_path

    @staticmethod
    def _coerce_audio_bytes(audio: object) -> bytes:
        if isinstance(audio, bytes):
            return audio

        if isinstance(audio, bytearray):
            return bytes(audio)

        if isinstance(audio, str):
            path = Path(audio)
            if path.exists():
                return path.read_bytes()
            try:
                return bytes.fromhex(audio)
            except ValueError:
                return audio.encode("utf-8")

        if isinstance(audio, dict):
            for key in ("audio", "result", "data"):
                value = audio.get(key)
                if isinstance(value, (bytes, bytearray)):
                    return bytes(value)
                if isinstance(value, str):
                    path = Path(value)
                    if path.exists():
                        return path.read_bytes()
                    try:
                        return bytes.fromhex(value)
                    except ValueError:
                        continue

        for attr in ("audio", "result", "data"):
            if hasattr(audio, attr):
                value = getattr(audio, attr)
                if isinstance(value, (bytes, bytearray)):
                    return bytes(value)
                if isinstance(value, str):
                    path = Path(value)
                    if path.exists():
                        return path.read_bytes()
                    try:
                        return bytes.fromhex(value)
                    except ValueError:
                        continue

        if hasattr(audio, "read"):
            try:
                value = audio.read()
                if isinstance(value, (bytes, bytearray)):
                    return bytes(value)
            except Exception:
                pass

        return b""


def create_speech_provider() -> SpeechProvider:
    tts_provider = os.getenv("TTS_PROVIDER", "dashscope").lower()
    if tts_provider == "dashscope":
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is required when tts_provider=dashscope")
        return DashScopeTTSProvider(
            api_key=api_key,
            model=os.getenv("TTS_MODEL", "cosyvoice-v2"),
            male_voice=os.getenv("DASHSCOPE_DEFAULT_MALE_VOICE", "loongdavid_v2"),
            female_voice=os.getenv("DASHSCOPE_DEFAULT_FEMALE_VOICE", "longanwen"),
            base_websocket_api_url=os.getenv(
                "DASHSCOPE_BASE_WEBSOCKET_API_URL",
                "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
            ),
        )

    return EdgeTTSProvider(default_voice="zh-CN-XiaoxiaoNeural")
