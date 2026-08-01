from pathlib import Path
from unittest.mock import MagicMock

from packages.memory import MemoryKind
from services.memory import MemoryStore
from services.memory.embeddings import EmbeddingService


def test_memory_store_remember_and_retrieve(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "test-memory.json")
    item = store.remember(
        kind=MemoryKind.PREFERENCE,
        key="code_style",
        value="strict typing and short functions",
        tags=["python", "style"],
    )
    store.remember(
        kind=MemoryKind.RULE,
        key="safety_rule",
        value="always dry run first",
        tags=["policy"],
    )

    hits = store.retrieve("strict")
    paged_hits = store.retrieve("", limit=1, offset=1)
    filtered_hits = store.retrieve("", kind=MemoryKind.RULE)

    assert hits
    assert hits[0].kind == MemoryKind.PREFERENCE
    assert len(paged_hits) == 1
    assert filtered_hits[0].kind == MemoryKind.RULE
    updated = store.update(str(item.id), value="updated value", tags=["updated"])
    assert updated is not None
    assert updated.value == "updated value"
    assert store.delete(str(item.id)) is True


def test_memory_store_semantic_retrieve_ranks_by_embeddings(tmp_path: Path) -> None:
    embedder = MagicMock(spec=EmbeddingService)

    def fake_embed(text: str) -> list[float]:
        lowered = text.lower()
        if "typing" in lowered or "strict" in lowered:
            return [1.0, 0.0, 0.0, 0.0]
        if "network" in lowered or "proxy" in lowered:
            return [0.0, 1.0, 0.0, 0.0]
        if "query about code quality" in lowered:
            return [0.9, 0.1, 0.0, 0.0]
        return [0.0, 0.0, 1.0, 0.0]

    embedder.embed.side_effect = fake_embed
    store = MemoryStore(tmp_path / "semantic-memory.json", embedder=embedder)
    store.remember(
        kind=MemoryKind.PREFERENCE,
        key="style",
        value="prefer strict typing",
        tags=["python"],
    )
    store.remember(
        kind=MemoryKind.RULE,
        key="egress",
        value="block outbound proxy",
        tags=["network"],
    )

    hits = store.retrieve("query about code quality", limit=1)
    assert hits
    assert hits[0].key == "style"
