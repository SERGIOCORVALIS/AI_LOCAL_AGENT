from __future__ import annotations

import hashlib
import math
import re

from services.llm import OllamaClient

HASHED_FALLBACK_DIMENSION = 64
# Backward-compatible alias used by older tests/imports.
EMBEDDING_DIMENSION = HASHED_FALLBACK_DIMENSION


def hashed_embed_text(
    text: str,
    dimensions: int = HASHED_FALLBACK_DIMENSION,
) -> list[float]:
    """Deterministic local hashed n-gram embedding fallback."""
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    if not normalized:
        return [0.0] * dimensions

    vector = [0.0] * dimensions
    tokens = re.findall(r"[a-z0-9_]+", normalized)
    grams = tokens + [
        normalized[index : index + 3]
        for index in range(max(len(normalized) - 2, 1))
    ]
    for gram in grams:
        digest = hashlib.sha256(gram.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign

    return _l2_normalize(vector)


def resize_vector(vector: list[float], dimensions: int) -> list[float]:
    """Project an arbitrary embedding to a fixed size, then L2-normalize."""
    if dimensions <= 0:
        return []
    if not vector:
        return [0.0] * dimensions
    if len(vector) == dimensions:
        return _l2_normalize(vector)
    if len(vector) > dimensions:
        bucketed = [0.0] * dimensions
        for index, value in enumerate(vector):
            bucketed[index % dimensions] += float(value)
        return _l2_normalize(bucketed)
    padded = list(vector) + [0.0] * (dimensions - len(vector))
    return _l2_normalize(padded)


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


class EmbeddingService:
    """Ollama embeddings (native dims) with deterministic hashed fallback."""

    def __init__(
        self,
        ollama_client: OllamaClient | None = None,
        model: str = "nomic-embed-text",
        dimensions: int | None = None,
        prefer_native: bool = True,
    ) -> None:
        self._ollama = ollama_client
        self._model = model
        # If set, always project to this size. None = keep Ollama native size.
        self._fixed_dimensions = dimensions
        self._prefer_native = prefer_native
        self._native_dimensions: int | None = None
        self._last_backend = "hashed"

    @property
    def backend(self) -> str:
        return self._last_backend

    @property
    def dimensions(self) -> int:
        if self._fixed_dimensions is not None:
            return self._fixed_dimensions
        if self._native_dimensions is not None:
            return self._native_dimensions
        return HASHED_FALLBACK_DIMENSION

    @property
    def model(self) -> str:
        return self._model

    def ensure_ready(self) -> int:
        """Probe embeddings once so native dimension is known before Qdrant init."""
        self.embed("dimension-probe")
        return self.dimensions

    def embed(self, text: str) -> list[float]:
        if self._ollama is not None:
            vector = self._ollama.embed(self._model, text)
            if vector is not None:
                self._last_backend = "ollama"
                if self._prefer_native and self._fixed_dimensions is None:
                    self._native_dimensions = len(vector)
                    return _l2_normalize([float(value) for value in vector])
                target = self._fixed_dimensions or HASHED_FALLBACK_DIMENSION
                return resize_vector(vector, target)

        self._last_backend = "hashed"
        return hashed_embed_text(text, self.dimensions)


def embed_text(text: str, dimensions: int = HASHED_FALLBACK_DIMENSION) -> list[float]:
    """Backward-compatible helper; uses hashed embeddings unless a service is used."""
    return hashed_embed_text(text, dimensions=dimensions)
