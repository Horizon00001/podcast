import pytest
import types
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

from app.services.speech_provider import (
    EdgeTTSProvider,
    DashScopeTTSProvider,
    create_speech_provider,
)


class TestDashScopeTTSProviderResolveVoice:
    """Test DashScopeTTSProvider._resolve_voice_id."""

    def test_resolve_voice_male(self):
        provider = DashScopeTTSProvider(api_key="test-key", male_voice="loongdavid_v2", female_voice="longanwen")
        assert provider._resolve_voice_id("male") == "loongdavid_v2"

    def test_resolve_voice_female(self):
        provider = DashScopeTTSProvider(api_key="test-key", male_voice="loongdavid_v2", female_voice="longanwen")
        assert provider._resolve_voice_id("female") == "longanwen"

    def test_resolve_voice_none_defaults_to_female(self):
        provider = DashScopeTTSProvider(api_key="test-key", male_voice="loongdavid_v2", female_voice="longanwen")
        assert provider._resolve_voice_id(None) == "longanwen"

    def test_resolve_voice_custom(self):
        provider = DashScopeTTSProvider(api_key="test-key", male_voice="loongdavid_v2", female_voice="longanwen")
        assert provider._resolve_voice_id("custom_voice") == "custom_voice"


class TestDashScopeTTSProviderCoerceAudioBytes:
    """Test DashScopeTTSProvider._coerce_audio_bytes."""

    def test_coerce_bytes(self):
        result = DashScopeTTSProvider._coerce_audio_bytes(b"hello")
        assert result == b"hello"

    def test_coerce_bytearray(self):
        result = DashScopeTTSProvider._coerce_audio_bytes(bytearray(b"hello"))
        assert result == b"hello"

    def test_coerce_str_hex(self):
        result = DashScopeTTSProvider._coerce_audio_bytes("68656c6c6f")  # "hello" in hex
        assert result == b"hello"

    def test_coerce_dict_with_bytes(self):
        audio = {"audio": b"hello"}
        result = DashScopeTTSProvider._coerce_audio_bytes(audio)
        assert result == b"hello"

    def test_coerce_dict_with_result(self):
        audio = {"result": b"hello"}
        result = DashScopeTTSProvider._coerce_audio_bytes(audio)
        assert result == b"hello"

    def test_coerce_dict_with_data(self):
        audio = {"data": b"hello"}
        result = DashScopeTTSProvider._coerce_audio_bytes(audio)
        assert result == b"hello"

    def test_coerce_object_with_audio_attr(self):
        class FakeAudio:
            audio = b"hello"

        result = DashScopeTTSProvider._coerce_audio_bytes(FakeAudio())
        assert result == b"hello"

    def test_coerce_object_with_read_method(self):
        class FakeAudio:
            def read(self):
                return b"hello"

        result = DashScopeTTSProvider._coerce_audio_bytes(FakeAudio())
        assert result == b"hello"

    def test_coerce_returns_empty_on_unknown(self):
        result = DashScopeTTSProvider._coerce_audio_bytes(12345)
        assert result == b""


class TestDashScopeTTSProviderSynthesize:
    """Test DashScopeTTSProvider.synthesize - skip since it requires async real API calls."""

    def test_synthesize_is_async(self):
        """Verify synthesize is an async method."""
        import inspect
        assert inspect.iscoroutinefunction(DashScopeTTSProvider.synthesize)


class TestEdgeTTSProvider:
    """Test EdgeTTSProvider."""

    def test_edge_tts_init_default(self):
        provider = EdgeTTSProvider()
        assert provider.default_voice == "zh-CN-XiaoxiaoNeural"

    def test_edge_tts_init_custom(self):
        provider = EdgeTTSProvider(default_voice="zh-CN-YunxiNeural")
        assert provider.default_voice == "zh-CN-YunxiNeural"

    def test_edge_tts_fallback_voices(self):
        assert len(EdgeTTSProvider.FALLBACK_VOICES) > 0
        assert "zh-CN-XiaoxiaoNeural" in EdgeTTSProvider.FALLBACK_VOICES


class TestCreateSpeechProvider:
    """Test create_speech_provider function."""

    def test_create_dashscope_provider(self, monkeypatch):
        monkeypatch.setenv("TTS_PROVIDER", "dashscope")
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key-123")

        provider = create_speech_provider()

        assert isinstance(provider, DashScopeTTSProvider)
        assert provider.api_key == "test-key-123"

    def test_create_edge_tts_provider(self, monkeypatch):
        monkeypatch.setenv("TTS_PROVIDER", "edge")
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

        provider = create_speech_provider()

        assert isinstance(provider, EdgeTTSProvider)

    def test_create_dashscope_raises_without_api_key(self, monkeypatch):
        monkeypatch.setenv("TTS_PROVIDER", "dashscope")
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

        with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
            create_speech_provider()

    def test_create_speech_provider_default_is_dashscope(self, monkeypatch):
        monkeypatch.delenv("TTS_PROVIDER", raising=False)
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

        provider = create_speech_provider()

        assert isinstance(provider, DashScopeTTSProvider)
