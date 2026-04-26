from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

from app.core.config import settings


class EmbeddingProvider:
    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


@dataclass
class LocalEmbeddingProvider(EmbeddingProvider):
    python_executable: str
    model: str
    device: str = "cpu"

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        worker_path = Path(__file__).with_name("local_embedding_worker.py")
        payload = json.dumps(
            {
                "model": self.model,
                "device": self.device,
                "texts": texts,
            }
        )
        result = subprocess.run(
            [self.python_executable, str(worker_path)],
            input=payload,
            capture_output=True,
            text=True,
            check=False,
            timeout=1200,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "local embedding worker failed")

        data = json.loads(result.stdout)
        vectors = data.get("vectors", [])
        if len(vectors) != len(texts):
            raise RuntimeError("local embedding response size mismatch")
        return vectors


@dataclass
class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    model: str
    base_url: str
    api_key: str | None = None

    def _resolve_embeddings_url(self) -> str:
        normalized = self.base_url.rstrip("/")
        if normalized.endswith("/embeddings"):
            return normalized
        return normalized + "/embeddings"

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        payload = json.dumps({"model": self.model, "input": texts}).encode("utf-8")
        request = urllib_request.Request(
            self._resolve_embeddings_url(),
            data=payload,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            },
            method="POST",
        )

        try:
            with urllib_request.urlopen(request, timeout=60) as response:
                body = response.read().decode("utf-8")
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"embedding request failed: {exc.code} {detail}") from exc
        except urllib_error.URLError as exc:
            raise RuntimeError(f"embedding request failed: {exc.reason}") from exc

        data = json.loads(body)
        vectors = [item.get("embedding", []) for item in data.get("data", [])]
        if len(vectors) != len(texts):
            raise RuntimeError("embedding response size mismatch")
        return vectors


@dataclass
class DashScopeEmbeddingProvider(EmbeddingProvider):
    model: str
    api_key: str
    base_url: str = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
    batch_size: int = 10

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        all_vectors = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            vectors = self._encode_batch(batch)
            all_vectors.extend(vectors)
        return all_vectors

    def _encode_batch(self, texts: list[str]) -> list[list[float]]:
        payload = json.dumps({"model": self.model, "input": {"texts": texts}}).encode("utf-8")
        request = urllib_request.Request(
            self.base_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib_request.urlopen(request, timeout=60) as response:
                body = response.read().decode("utf-8")
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"dashscope embedding request failed: {exc.code} {detail}") from exc
        except urllib_error.URLError as exc:
            raise RuntimeError(f"dashscope embedding request failed: {exc.reason}") from exc

        data = json.loads(body)
        vectors = [item.get("embedding", []) for item in data.get("output", {}).get("embeddings", [])]
        if len(vectors) != len(texts):
            raise RuntimeError("dashscope embedding response size mismatch")
        return vectors


class DisabledEmbeddingProvider(EmbeddingProvider):
    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        return []


class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider):
        self.provider = provider

    def is_enabled(self) -> bool:
        return settings.episode_embedding_enabled and not isinstance(self.provider, DisabledEmbeddingProvider)

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts or not self.is_enabled():
            return []
        return self.provider.encode_texts(texts)


def _build_provider() -> EmbeddingProvider:
    if not settings.episode_embedding_enabled:
        return DisabledEmbeddingProvider()

    provider_name = (settings.episode_embedding_provider or "openai_compatible").strip().lower()
    if provider_name == "dashscope":
        api_key = settings.episode_embedding_api_key or settings.dashscope_api_key
        if not api_key:
            return DisabledEmbeddingProvider()
        return DashScopeEmbeddingProvider(
            model=settings.episode_embedding_model,
            api_key=api_key,
        )
    if provider_name == "local":
        return LocalEmbeddingProvider(
            python_executable=settings.episode_embedding_python,
            model=settings.episode_embedding_model,
            device=settings.episode_embedding_device,
        )
    if provider_name == "openai_compatible":
        if not settings.episode_embedding_base_url:
            return DisabledEmbeddingProvider()
        return OpenAICompatibleEmbeddingProvider(
            model=settings.episode_embedding_model,
            base_url=settings.episode_embedding_base_url,
            api_key=settings.episode_embedding_api_key,
        )
    raise RuntimeError(f"unsupported embedding provider: {settings.episode_embedding_provider}")


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(_build_provider())
