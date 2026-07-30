from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from packages.memory import MemoryItem, MemoryKind


class MemoryStore:
    """Simple JSON-backed preference and rule memory."""

    def __init__(self, path: Path) -> None:
        self._path = path

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
        lowered_query = query.lower()
        items = [
            MemoryItem.model_validate(record)
            for record in self._load_all()
            if (
                kind is None or record["kind"] == kind
            ) and (
                lowered_query in record["key"].lower()
                or lowered_query in record["value"].lower()
                or any(lowered_query in tag.lower() for tag in record["tags"])
            )
        ]
        return items[offset : offset + limit]

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
