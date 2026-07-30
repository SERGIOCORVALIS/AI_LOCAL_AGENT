from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from packages.core import Task


class TaskStore:
    """JSON-backed persistence for resumable task state."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def save(self, task: Task) -> None:
        records = self._load_all()
        records[str(task.id)] = task.model_dump(mode="json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    def load(self, task_id: str) -> Task | None:
        records = self._load_all()
        payload = records.get(task_id)
        if payload is None:
            return None
        return Task.model_validate(payload)

    def count(self) -> int:
        return len(self._load_all())

    def list_recent(self, limit: int = 10) -> list[Task]:
        tasks = [
            Task.model_validate(payload)
            for payload in self._load_all().values()
        ]
        tasks.sort(key=lambda task: task.updated_at, reverse=True)
        return tasks[:limit]

    def _load_all(self) -> dict[str, dict[str, Any]]:
        if not self._path.exists():
            return {}
        raw_payload = json.loads(self._path.read_text(encoding="utf-8"))
        return cast(dict[str, dict[str, Any]], raw_payload)
