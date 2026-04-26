from urllib import error as urllib_error

import pytest

from app.services import embedding_service
from app.services.embedding_service import (
    DashScopeEmbeddingProvider,
    DisabledEmbeddingProvider,
    EmbeddingService,
    OpenAICompatibleEmbeddingProvider,
)


class FakeHTTPResponse:
    def __init__(self, body: str):
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def close(self):
        return None


class TestOpenAICompatibleEmbeddingProvider:
    def test_resolve_embeddings_url(self):
        provider = OpenAICompatibleEmbeddingProvider(
            model="text-embedding-3-small",
            base_url="https://api.example.com/v1",
        )
        assert provider._resolve_embeddings_url() == "https://api.example.com/v1/embeddings"

    def test_encode_texts_success(self, monkeypatch):
        provider = OpenAICompatibleEmbeddingProvider(
            model="text-embedding-3-small",
            base_url="https://api.example.com/v1",
            api_key="secret",
        )

        def fake_urlopen(request, timeout):
            assert request.full_url == "https://api.example.com/v1/embeddings"
            assert request.headers["Authorization"] == "Bearer secret"
            return FakeHTTPResponse('{"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]}')

        monkeypatch.setattr(embedding_service.urllib_request, "urlopen", fake_urlopen)

        vectors = provider.encode_texts(["hello", "world"])
        assert vectors == [[0.1, 0.2], [0.3, 0.4]]

    def test_encode_texts_size_mismatch(self, monkeypatch):
        provider = OpenAICompatibleEmbeddingProvider(
            model="text-embedding-3-small",
            base_url="https://api.example.com/v1",
        )

        monkeypatch.setattr(
            embedding_service.urllib_request,
            "urlopen",
            lambda request, timeout: FakeHTTPResponse('{"data": [{"embedding": [0.1, 0.2]}]}'),
        )

        with pytest.raises(RuntimeError, match="size mismatch"):
            provider.encode_texts(["hello", "world"])

    def test_encode_texts_http_error(self, monkeypatch):
        provider = OpenAICompatibleEmbeddingProvider(
            model="text-embedding-3-small",
            base_url="https://api.example.com/v1",
        )

        def fake_urlopen(request, timeout):
            raise urllib_error.HTTPError(
                url=request.full_url,
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=FakeHTTPResponse('{"error": "bad key"}'),
            )

        monkeypatch.setattr(embedding_service.urllib_request, "urlopen", fake_urlopen)

        with pytest.raises(RuntimeError, match="401"):
            provider.encode_texts(["hello"])


class TestDashScopeEmbeddingProvider:
    def test_encode_texts_success(self, monkeypatch):
        provider = DashScopeEmbeddingProvider(
            model="text-embedding-v3",
            api_key="secret",
        )

        def fake_urlopen(request, timeout):
            assert request.full_url == provider.base_url
            assert request.headers["Authorization"] == "Bearer secret"
            return FakeHTTPResponse('{"output": {"embeddings": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]}}')

        monkeypatch.setattr(embedding_service.urllib_request, "urlopen", fake_urlopen)

        vectors = provider.encode_texts(["hello", "world"])
        assert vectors == [[0.1, 0.2], [0.3, 0.4]]

    def test_encode_texts_size_mismatch(self, monkeypatch):
        provider = DashScopeEmbeddingProvider(
            model="text-embedding-v3",
            api_key="secret",
        )

        monkeypatch.setattr(
            embedding_service.urllib_request,
            "urlopen",
            lambda request, timeout: FakeHTTPResponse('{"output": {"embeddings": [{"embedding": [0.1, 0.2]}]}}'),
        )

        with pytest.raises(RuntimeError, match="size mismatch"):
            provider.encode_texts(["hello", "world"])


class TestEmbeddingService:
    def test_disabled_provider_returns_empty(self, monkeypatch):
        monkeypatch.setattr(embedding_service.settings, "episode_embedding_enabled", False)
        service = EmbeddingService(DisabledEmbeddingProvider())
        assert service.encode_texts(["hello"]) == []

    def test_build_provider_returns_disabled_without_base_url(self, monkeypatch):
        monkeypatch.setattr(embedding_service.settings, "episode_embedding_enabled", True)
        monkeypatch.setattr(embedding_service.settings, "episode_embedding_provider", "openai_compatible")
        monkeypatch.setattr(embedding_service.settings, "episode_embedding_base_url", None)

        provider = embedding_service._build_provider()
        assert isinstance(provider, DisabledEmbeddingProvider)

    def test_build_provider_returns_dashscope(self, monkeypatch):
        monkeypatch.setattr(embedding_service.settings, "episode_embedding_enabled", True)
        monkeypatch.setattr(embedding_service.settings, "episode_embedding_provider", "dashscope")
        monkeypatch.setattr(embedding_service.settings, "episode_embedding_model", "text-embedding-v3")
        monkeypatch.setattr(embedding_service.settings, "episode_embedding_api_key", "secret")

        provider = embedding_service._build_provider()
        assert isinstance(provider, DashScopeEmbeddingProvider)

    def test_build_provider_returns_disabled_without_dashscope_key(self, monkeypatch):
        monkeypatch.setattr(embedding_service.settings, "episode_embedding_enabled", True)
        monkeypatch.setattr(embedding_service.settings, "episode_embedding_provider", "dashscope")
        monkeypatch.setattr(embedding_service.settings, "episode_embedding_api_key", None)
        monkeypatch.setattr(embedding_service.settings, "dashscope_api_key", None)

        provider = embedding_service._build_provider()
        assert isinstance(provider, DisabledEmbeddingProvider)
