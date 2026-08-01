from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from packages.memory import MemoryItem, MemoryKind
from services.memory.embeddings import (
    HASHED_FALLBACK_DIMENSION,
    EmbeddingService,
    hashed_embed_text,
)


class MemoryStore:
    """JSON-backed memory with semantic retrieve via EmbeddingService."""

    def __init__(
        self,
        path: Path,
        embedder: EmbeddingService | None = None,
    ) -> None:
        self._path = path
        self._embedder = embedder or EmbeddingService()

    @property
    def embedder(self) -> EmbeddingService:
        return self._embedder

    def remember(
        self,
        kind: MemoryKind,
        key: str,
        value: str,
        tags: list[str] | None = None,
    ) -> MemoryItem:
        item = MemoryItem(kind=kind, key=key, value=value, tags=tags or [])
        records = self._load_all()
        records.append(item.model_dump(mode="json"))
        self._persist(records)
        return item

    def initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        offset: int = 0,
        kind: MemoryKind | None = None,
    ) -> list[MemoryItem]:
        items = [
            MemoryItem.model_validate(record)
            for record in self._load_all()
            if kind is None or record["kind"] == kind
        ]
        if not query.strip():
            return items[offset : offset + limit]

        # Local JSON store ranks with fast hashed vectors. Calling Ollama embed
        # per item would make every chat message take minutes.
        query_vector = hashed_embed_text(query, HASHED_FALLBACK_DIMENSION)
        scored: list[tuple[float, MemoryItem]] = []
        lowered = query.lower()
        for item in items:
            text = f"{item.kind}:{item.key}:{item.value}:{' '.join(item.tags)}"
            item_vector = hashed_embed_text(text, HASHED_FALLBACK_DIMENSION)
            score = self._cosine(query_vector, item_vector)
            if (
                lowered in item.key.lower()
                or lowered in item.value.lower()
                or any(lowered in tag.lower() for tag in item.tags)
            ):
                score += 0.15
            scored.append((score, item))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        ranked = [item for score, item in scored if score > 0.0]
        return ranked[offset : offset + limit]

    def delete(self, memory_id: str) -> bool:
        records = self._load_all()
        filtered_records = [
            record
            for record in records
            if str(MemoryItem.model_validate(record).id) != str(UUID(memory_id))
        ]
        deleted = len(filtered_records) != len(records)
        if deleted:
            self._persist(filtered_records)
        return deleted

    def update(
        self,
        memory_id: str,
        *,
        kind: MemoryKind | None = None,
        key: str | None = None,
        value: str | None = None,
        tags: list[str] | None = None,
    ) -> MemoryItem | None:
        records = self._load_all()
        target_id = str(UUID(memory_id))
        updated_item: MemoryItem | None = None

        for index, record in enumerate(records):
            item = MemoryItem.model_validate(record)
            if str(item.id) != target_id:
                continue
            updated_item = item.model_copy(
                update={
                    "kind": kind or item.kind,
                    "key": key or item.key,
                    "value": value or item.value,
                    "tags": tags if tags is not None else item.tags,
                }
            )
            records[index] = updated_item.model_dump(mode="json")
            break

        if updated_item is not None:
            self._persist(records)
        return updated_item

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        raw_payload = json.loads(self._path.read_text(encoding="utf-8"))
        return cast(list[dict[str, Any]], raw_payload)

    def _persist(self, records: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return dot / (left_norm * right_norm)
