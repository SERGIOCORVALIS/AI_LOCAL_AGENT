from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from time import monotonic
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from packages.config import Settings, load_settings
from packages.core import Action, Task
from packages.memory import MemoryKind
from services.memory import build_memory_backend
from services.observability import configure_logging
from services.orchestrator import OrchestratorRuntime
from services.orchestrator.store import TaskStore
from services.quality import QualityEvaluator


class RunTaskRequest(BaseModel):
    title: str
    goal: str


class CreateMemoryRequest(BaseModel):
    kind: MemoryKind
    key: str
    value: str
    tags: list[str] = Field(default_factory=list)


class UpdateMemoryRequest(BaseModel):
    kind: MemoryKind | None = None
    key: str | None = None
    value: str | None = None
    tags: list[str] | None = None


def create_app() -> FastAPI:
    settings = load_settings()
    configure_logging(settings)
    runtime = OrchestratorRuntime(settings)
    memory_store = build_memory_backend(settings)
    task_store = TaskStore(settings.task_store_path)
    started_at = monotonic()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        memory_store.initialize()
        settings.runtime_log_path.parent.mkdir(parents=True, exist_ok=True)
        settings.backup_dir.mkdir(parents=True, exist_ok=True)
        yield

    api_app = FastAPI(
        title="Local AI Agent API",
        version="0.2.0",
        lifespan=lifespan,
    )

    @api_app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "app_name": settings.app_name,
            "env": settings.env,
        }

    @api_app.get("/status")
    def status() -> dict[str, object]:
        report = QualityEvaluator().evaluate()
        return {
            "models": {
                "primary": settings.model_primary,
                "router": settings.model_router,
            },
            "memory_backend": type(memory_store).__name__,
            "memory_items": len(memory_store.retrieve("", limit=10_000)),
            "runtime_log_path": str(settings.runtime_log_path),
            "backup_dir": str(settings.backup_dir),
            "quality": report.model_dump(mode="json"),
        }

    @api_app.get("/metrics")
    def metrics() -> dict[str, object]:
        return {
            "app_name": settings.app_name,
            "uptime_seconds": round(monotonic() - started_at, 3),
            "memory_backend": type(memory_store).__name__,
            "memory_items": len(memory_store.retrieve("", limit=10_000)),
            "task_count": task_store.count(),
            "recent_task_count": len(task_store.list_recent(limit=5)),
            "audit_event_count": _count_lines(settings.audit_log_path),
            "log_file_exists": settings.runtime_log_path.exists(),
        }

    @api_app.get("/tasks/recent")
    def recent_tasks(
        limit: Annotated[int, Query(ge=1, le=100)] = 10,
    ) -> list[dict[str, object]]:
        return [task.model_dump(mode="json") for task in task_store.list_recent(limit=limit)]

    @api_app.get("/admin", response_class=HTMLResponse)
    def admin_ui() -> str:
        return _build_admin_html(settings)

    @api_app.get("/memory")
    def list_memory(
        q: Annotated[str, Query()] = "",
        kind: Annotated[MemoryKind | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, object]:
        items = memory_store.retrieve(
            q,
            limit=limit,
            offset=offset,
            kind=kind,
        )
        return {
            "items": [item.model_dump(mode="json") for item in items],
            "limit": limit,
            "offset": offset,
            "query": q,
            "kind": kind,
        }

    @api_app.get("/memory/search")
    def search_memory(
        q: Annotated[str, Query(min_length=1)],
        limit: Annotated[int, Query(ge=1, le=100)] = 10,
    ) -> list[dict[str, object]]:
        return [
            item.model_dump(mode="json")
            for item in memory_store.retrieve(q, limit=limit)
        ]

    @api_app.post("/memory")
    def create_memory(payload: CreateMemoryRequest) -> dict[str, object]:
        item = memory_store.remember(
            kind=payload.kind,
            key=payload.key,
            value=payload.value,
            tags=payload.tags,
        )
        return item.model_dump(mode="json")

    @api_app.delete("/memory/{memory_id}")
    def delete_memory(memory_id: str) -> dict[str, object]:
        return {"deleted": memory_store.delete(memory_id), "memory_id": memory_id}

    @api_app.patch("/memory/{memory_id}")
    def update_memory(
        memory_id: str,
        payload: UpdateMemoryRequest,
    ) -> dict[str, object]:
        item = memory_store.update(
            memory_id,
            kind=payload.kind,
            key=payload.key,
            value=payload.value,
            tags=payload.tags,
        )
        if item is None:
            return {"updated": False, "memory_id": memory_id}
        return {"updated": True, "item": item.model_dump(mode="json")}

    @api_app.post("/tasks/run")
    def run_task(payload: RunTaskRequest) -> dict[str, object]:
        task = Task(
            title=payload.title,
            goal=payload.goal,
            actions=[
                Action(
                    name="bootstrap",
                    description="API-triggered bootstrap action.",
                )
            ],
        )
        return runtime.run_task(task).model_dump(mode="json")

    return api_app


app = create_app()


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def _build_admin_html(settings: Settings) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{settings.admin_ui_title}</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 24px;
      background: #0f172a;
      color: #e2e8f0;
    }}
    h1, h2 {{ margin: 0 0 12px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: #111827;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 16px;
    }}
    pre {{ white-space: pre-wrap; word-break: break-word; }}
    button {{
      background: #2563eb;
      color: white;
      border: 0;
      padding: 10px 14px;
      border-radius: 8px;
      cursor: pointer;
    }}
    a {{ color: #93c5fd; }}
  </style>
</head>
<body>
  <h1>{settings.admin_ui_title}</h1>
  <p>Local management panel for status, metrics, tasks, and memory.</p>
  <p>
    <a href="/docs">Open API docs</a> |
    <a href="/status">Status JSON</a> |
    <a href="/metrics">Metrics JSON</a>
  </p>
  <p><button onclick="reloadAll()">Refresh dashboard</button></p>
  <div class="grid">
    <section class="card"><h2>Status</h2><pre id="status">Loading...</pre></section>
    <section class="card"><h2>Metrics</h2><pre id="metrics">Loading...</pre></section>
    <section class="card"><h2>Recent Tasks</h2><pre id="tasks">Loading...</pre></section>
    <section class="card"><h2>Latest Memory</h2><pre id="memory">Loading...</pre></section>
  </div>
  <script>
    async function fetchJson(url) {{
      const response = await fetch(url);
      if (!response.ok) {{
        throw new Error(`HTTP ${{response.status}} for ${{url}}`);
      }}
      return response.json();
    }}
    async function reloadAll() {{
      const mappings = [
        ['status', '/status'],
        ['metrics', '/metrics'],
        ['tasks', '/tasks/recent?limit=5'],
        ['memory', '/memory?limit=5'],
      ];
      for (const [targetId, url] of mappings) {{
        const element = document.getElementById(targetId);
        element.textContent = 'Loading...';
        try {{
          const payload = await fetchJson(url);
          element.textContent = JSON.stringify(payload, null, 2);
        }} catch (error) {{
          element.textContent = String(error);
        }}
      }}
    }}
    reloadAll();
  </script>
</body>
</html>"""
