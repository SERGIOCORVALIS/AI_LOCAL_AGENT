from __future__ import annotations

import sys

from packages.config import Settings
from services.llm import OllamaClient
from services.memory.embeddings import EmbeddingService
from services.memory.protocol import MemoryBackend
from services.memory.qdrant_store import QdrantMemoryStore
from services.memory.store import MemoryStore


def build_memory_backend(settings: Settings) -> MemoryBackend:
    if "pytest" in sys.modules:
        ollama: OllamaClient | None = OllamaClient(
            base_url="http://127.0.0.1:9",
            timeout=0.5,
        )
    else:
        ollama = OllamaClient(base_url=settings.ollama_url, timeout=30.0)
    embed_model = settings.model_embed
    if ollama is not None:
        resolved = ollama.resolve_model(embed_model)
        if resolved:
            embed_model = resolved
    embedder = EmbeddingService(
        ollama_client=ollama,
        model=embed_model,
        dimensions=settings.embedding_dimensions,
        prefer_native=settings.embedding_prefer_native,
    )
    qdrant_store = QdrantMemoryStore(
        url=settings.qdrant_url,
        collection=settings.qdrant_collection,
        embedder=embedder,
    )
    if qdrant_store.ping():
        return qdrant_store
    return MemoryStore(settings.memory_store_path, embedder=embedder)
