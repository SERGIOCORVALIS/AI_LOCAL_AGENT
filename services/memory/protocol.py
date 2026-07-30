from __future__ import annotations

from typing import Protocol

from packages.memory import MemoryItem, MemoryKind


class MemoryBackend(Protocol):
    def initialize(self) -> None: ...

    def remember(
        self,
        kind: MemoryKind,
        key: str,
        value: str,
        tags: list[str] | None = None,
    ) -> MemoryItem: ...

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        offset: int = 0,
        kind: MemoryKind | None = None,
    ) -> list[MemoryItem]: ...

    def delete(self, memory_id: str) -> bool: ...

    def update(
        self,
        memory_id: str,
        *,
        kind: MemoryKind | None = None,
        key: str | None = None,
        value: str | None = None,
        tags: list[str] | None = None,
    ) -> MemoryItem | None: ...
