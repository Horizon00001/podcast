from pathlib import Path
import sys
import types

from app.services.speech_provider import DashScopeTTSProvider


def test_dashscope_voice_resolution():
    provider = DashScopeTTSProvider(
        api_key="test-key",
        model="cosyvoice-v2",
        male_voice="loongdavid_v2",
        female_voice="loongluna_v2",
    )

    assert provider._resolve_voice_id("male") == "loongdavid_v2"
    assert provider._resolve_voice_id("female") == "loongluna_v2"
    assert provider._resolve_voice_id(None) == "loongluna_v2"
    assert provider._resolve_voice_id("custom_voice") == "custom_voice"


def test_dashscope_provider_writes_audio(monkeypatch, tmp_path):
    provider = DashScopeTTSProvider(api_key="test-key", model="cosyvoice-v2")

    class FakeSynthesizer:
        def __init__(self, model, voice):
            self.model = model
            self.voice = voice

        def call(self, text):
            return b"ID3"

    dashscope_module = types.ModuleType("dashscope")
    audio_module = types.ModuleType("dashscope.audio")
    tts_v2_module = types.ModuleType("dashscope.audio.tts_v2")
    tts_v2_module.SpeechSynthesizer = FakeSynthesizer
    audio_module.tts_v2 = tts_v2_module
    dashscope_module.audio = audio_module
    dashscope_module.api_key = None
    dashscope_module.base_websocket_api_url = None
    monkeypatch.setitem(sys.modules, "dashscope", dashscope_module)
    monkeypatch.setitem(sys.modules, "dashscope.audio", audio_module)
    monkeypatch.setitem(sys.modules, "dashscope.audio.tts_v2", tts_v2_module)

    output = tmp_path / "sample.mp3"
    result = __import__("asyncio").run(provider.synthesize("hello", output, voice="male"))

    assert result == output
    assert output.exists()
    assert output.read_bytes() == b"ID3"
