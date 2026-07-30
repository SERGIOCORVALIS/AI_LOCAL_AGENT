from pathlib import Path

from packages.config import Settings
from services.memory import MemoryStore, QdrantMemoryStore, build_memory_backend


def test_memory_factory_falls_back_without_live_qdrant() -> None:
    backend = build_memory_backend(
        Settings(
            qdrant_url="http://127.0.0.1:65530",
            memory_store_path=Path("runtime/factory-memory.json"),
        )
    )

    assert isinstance(backend, MemoryStore)
    assert not isinstance(backend, QdrantMemoryStore)
