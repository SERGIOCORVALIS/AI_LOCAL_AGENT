from __future__ import annotations

from packages.config import Settings
from services.memory.protocol import MemoryBackend
from services.memory.qdrant_store import QdrantMemoryStore
from services.memory.store import MemoryStore


def build_memory_backend(settings: Settings) -> MemoryBackend:
    qdrant_store = QdrantMemoryStore(
        url=settings.qdrant_url,
        collection=settings.qdrant_collection,
    )
    if qdrant_store.ping():
        return qdrant_store
    return MemoryStore(settings.memory_store_path)
