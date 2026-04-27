from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Protocol, runtime_checkable


logger = logging.getLogger(__name__)


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
        "zh-CN-YunyangNeural",
        "zh-CN-YunxiNeural",
        "zh-CN-XiaoyiNeural",
    )

    VOICE_MAP = {
        "male": "zh-CN-YunyangNeural",
        "female": "zh-CN-XiaoxiaoNeural",
    }

    def __init__(self, default_voice: str = "zh-CN-XiaoxiaoNeural"):
        self.default_voice = default_voice

    def _resolve_voice(self, voice: str | None) -> str | None:
        if voice in self.VOICE_MAP:
            return self.VOICE_MAP[voice]
        return voice

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
        voices_to_try = [self._resolve_voice(voice) or self.default_voice]
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
        request_timeout_seconds: float = 180.0,
        timeout_retries: int = 2,
    ):
        self.api_key = api_key
        self.model = model
        self.male_voice = male_voice or "loongdavid_v2"
        self.female_voice = female_voice or "longanwen"
        self.base_websocket_api_url = base_websocket_api_url
        self.request_timeout_seconds = request_timeout_seconds
        self.timeout_retries = max(int(timeout_retries), 0)

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
        last_timeout: TimeoutError | None = None
        for attempt in range(self.timeout_retries + 1):
            synthesizer = SpeechSynthesizer(model=self.model, voice=voice_id)
            try:
                audio = await asyncio.wait_for(
                    asyncio.to_thread(synthesizer.call, text),
                    timeout=self.request_timeout_seconds,
                )
                break
            except TimeoutError as exc:
                last_timeout = exc
                logger.warning(
                    "DashScope TTS timeout for voice=%s attempt=%s/%s timeout=%ss",
                    voice_id,
                    attempt + 1,
                    self.timeout_retries + 1,
                    self.request_timeout_seconds,
                )
                if attempt >= self.timeout_retries:
                    raise RuntimeError(
                        "DashScope TTS request timed out "
                        f"after {self.request_timeout_seconds}s for voice={voice_id} "
                        f"(attempts={self.timeout_retries + 1})"
                    ) from exc
        else:
            raise RuntimeError(f"DashScope TTS request failed unexpectedly for voice={voice_id}") from last_timeout

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
            request_timeout_seconds=float(os.getenv("DASHSCOPE_TTS_TIMEOUT_SECONDS", "180")),
            timeout_retries=int(os.getenv("DASHSCOPE_TTS_TIMEOUT_RETRIES", "2")),
        )

    return EdgeTTSProvider(default_voice="zh-CN-XiaoxiaoNeural")
