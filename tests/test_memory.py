from pathlib import Path

from packages.memory import MemoryKind
from services.memory import MemoryStore


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
    # JSON MemoryStore ranks with hashed vectors + substring boost (not live Ollama).
    store = MemoryStore(tmp_path / "semantic-memory.json")
    store.remember(
        kind=MemoryKind.PREFERENCE,
        key="style",
        value="prefer strict typing for code quality reviews",
        tags=["python"],
    )
    store.remember(
        kind=MemoryKind.RULE,
        key="egress",
        value="block outbound proxy",
        tags=["network"],
    )

    hits = store.retrieve("strict typing", limit=1)
    assert hits
    assert hits[0].key == "style"
