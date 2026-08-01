from __future__ import annotations

import logging
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING, Annotated

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from apps.api.admin import STATIC_DIR, render_admin_html
from packages.config import (
    SECRET_FIELDS,
    SETTINGS_ENV_KEYS,
    WRITABLE_FIELDS,
    Settings,
    default_env_path,
    field_to_env_value,
    load_settings,
    upsert_env_values,
)
from packages.core import Task
from packages.memory import MemoryKind
from services.memory import build_memory_backend
from services.observability import configure_logging
from services.orchestrator import OrchestratorRuntime
from services.orchestrator.capabilities import plan_actions_for_goal
from services.orchestrator.store import TaskStore
from services.quality import QualityEvaluator

if TYPE_CHECKING:
    from services.integrations.telegram_bot import TelegramBotService

LOGGER = logging.getLogger(__name__)

_PUBLIC_PATHS = frozenset({"/health", "/ready", "/openapi.json", "/docs", "/redoc"})


def _package_version() -> str:
    version_path = Path(__file__).resolve().parents[2] / "VERSION"
    if version_path.exists():
        value = version_path.read_text(encoding="utf-8").strip()
        if value:
            return value
    return "0.3.0"


def _extract_api_token(request: Request) -> str | None:
    header = request.headers.get("x-api-token")
    if header:
        return header.strip()
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def _should_start_telegram_polling(bot: TelegramBotService) -> bool:
    if not bot.is_ready():
        return False
    # Keep unit tests offline even when a local .env contains Telegram credentials.
    if "pytest" in sys.modules:
        return False
    return True


class RunTaskRequest(BaseModel):
    title: str
    goal: str


class ApproveTaskRequest(BaseModel):
    approved: bool = True
    reviewer: str = "operator"


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


class FsWatchStartRequest(BaseModel):
    seconds: float = Field(default=0.0, ge=0.0, le=30.0)


class UpdateSettingsRequest(BaseModel):
    """Partial settings update persisted to .env (applies after restart)."""

    updates: dict[str, object] = Field(default_factory=dict)
    clear_secrets: list[str] = Field(default_factory=list)


def _settings_public_snapshot(settings: Settings) -> dict[str, object]:
    values: dict[str, object] = {}
    for field_name in WRITABLE_FIELDS:
        if field_name in SECRET_FIELDS:
            continue
        raw = getattr(settings, field_name)
        if isinstance(raw, Path):
            values[field_name] = str(raw)
        else:
            values[field_name] = raw
    secrets = {
        name: {
            "configured": bool(getattr(settings, name)),
            "masked": "••••••••" if getattr(settings, name) else "",
        }
        for name in SECRET_FIELDS
    }
    return {
        "values": values,
        "secrets": secrets,
        "env_path": str(default_env_path()),
        "applies_after_restart": True,
        "compose_overrides_note": (
            "Docker Compose may override QDRANT_URL and OLLAMA_URL via environment."
        ),
    }


def _coerce_settings_updates(
    updates: dict[str, object],
    clear_secrets: list[str],
) -> dict[str, str]:
    env_updates: dict[str, str] = {}
    for field_name, value in updates.items():
        if field_name not in WRITABLE_FIELDS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown or non-writable settings field: {field_name}",
            )
        if field_name in SECRET_FIELDS and (value is None or str(value).strip() == ""):
            continue
        env_key = SETTINGS_ENV_KEYS[field_name]
        if field_name == "embedding_dimensions" and (value is None or value == ""):
            env_updates[env_key] = ""
            continue
        if field_name == "stt_language" and (value is None or str(value).strip() == ""):
            env_updates[env_key] = ""
            continue
        env_updates[env_key] = field_to_env_value(value)

    for field_name in clear_secrets:
        if field_name not in SECRET_FIELDS:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot clear non-secret field: {field_name}",
            )
        env_updates[SETTINGS_ENV_KEYS[field_name]] = ""
    return env_updates


def create_app() -> FastAPI:
    from services.integrations.telegram_bot import TelegramBotService

    settings = load_settings()
    settings.validate_production_guards()
    configure_logging(settings)
    runtime = OrchestratorRuntime(settings)
    memory_store = build_memory_backend(settings)
    task_store = TaskStore(settings.task_store_path)
    telegram_bot = TelegramBotService(settings=settings, runtime=runtime)
    watchdog = runtime.capabilities.watchdog
    started_at = monotonic()
    version = _package_version()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        memory_store.initialize()
        settings.runtime_log_path.parent.mkdir(parents=True, exist_ok=True)
        settings.backup_dir.mkdir(parents=True, exist_ok=True)
        if _should_start_telegram_polling(telegram_bot):
            telegram_bot.start_background()
            LOGGER.info("Telegram bot polling enabled for admin chat")
        else:
            LOGGER.info("Telegram bot polling skipped")
        try:
            yield
        finally:
            watchdog.stop()
            await telegram_bot.stop()

    api_app = FastAPI(
        title="Local AI Agent API",
        version=version,
        lifespan=lifespan,
    )

    allowed_hosts = list(settings.trusted_hosts)
    if "pytest" in sys.modules and "testserver" not in allowed_hosts:
        allowed_hosts.append("testserver")
    if allowed_hosts:
        api_app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    @api_app.middleware("http")
    async def api_token_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not settings.api_token_required:
            return await call_next(request)
        path = request.url.path
        if path in _PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return await call_next(request)
        expected = settings.api_token
        provided = _extract_api_token(request)
        if not expected or provided != expected:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API token"},
            )
        return await call_next(request)

    @api_app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "app_name": settings.app_name,
            "env": settings.env,
            "version": version,
        }

    @api_app.get("/ready")
    def ready() -> dict[str, object]:
        memory_ok = True
        try:
            memory_store.retrieve("", limit=1)
        except Exception:  # noqa: BLE001 - readiness must not raise
            memory_ok = False
        ollama_ok = runtime.ollama.ping()
        status = "ready" if memory_ok else "not_ready"
        return {
            "status": status,
            "memory_ok": memory_ok,
            "memory_backend": type(memory_store).__name__,
            "ollama_ok": ollama_ok,
            "sandbox_prefer_docker": settings.sandbox_prefer_docker,
            "api_token_required": settings.api_token_required,
            "bind_host": settings.api_bind_host,
        }

    @api_app.get("/status")
    def status() -> dict[str, object]:
        from services.perception.readiness import perception_readiness

        # Presence-only quality snapshot; doctor CLI runs the heavy tools.
        report = QualityEvaluator().evaluate(run_tools=False)
        embedder = getattr(memory_store, "embedder", None)
        agents = runtime.refresh_agents()
        return {
            "models": {
                "primary": settings.model_primary,
                "router": settings.model_router,
                "vision": settings.model_vision,
                "embed": settings.model_embed,
            },
            "models_resolved": agents.resolved.as_dict(),
            "ollama_url": settings.ollama_url,
            "ollama_online": agents.online,
            "sandbox_prefer_docker": settings.sandbox_prefer_docker,
            "memory_backend": type(memory_store).__name__,
            "memory_items": len(memory_store.retrieve("", limit=10_000)),
            "runtime_log_path": str(settings.runtime_log_path),
            "backup_dir": str(settings.backup_dir),
            "telegram": {
                "configured": telegram_bot.adapter.is_configured(),
                "available": telegram_bot.is_ready(),
            },
            "fs_watch": {
                "path": str(runtime.capabilities.watchdog.watch_path),
                "available": runtime.capabilities.watchdog.is_available(),
            },
            "perception": perception_readiness(
                embedder=embedder,
                ollama_client=runtime.ollama,
                vision_model=agents.resolved.vision,
                agents=agents.configured,
            ),
            "coding_agents": runtime.capabilities.coding_agents.readiness(),
            "web_search": {"provider": "duckduckgo"},
            "quality": report.model_dump(mode="json"),
            "quality_mode": "presence",
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
    def admin_ui() -> HTMLResponse:
        return HTMLResponse(render_admin_html(settings))

    @api_app.get("/admin/static/{asset_name}")
    def admin_static(asset_name: str) -> FileResponse:
        media_types = {
            "panel.css": "text/css",
            "panel.js": "application/javascript",
            "brand.png": "image/png",
        }
        if asset_name not in media_types:
            raise HTTPException(status_code=404, detail="Asset not found")
        path = STATIC_DIR / asset_name
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Asset not found")
        return FileResponse(path, media_type=media_types[asset_name])

    @api_app.get("/settings")
    def get_settings() -> dict[str, object]:
        return _settings_public_snapshot(settings)

    @api_app.put("/settings")
    def put_settings(payload: UpdateSettingsRequest) -> dict[str, object]:
        env_updates = _coerce_settings_updates(payload.updates, payload.clear_secrets)
        if not env_updates:
            raise HTTPException(status_code=400, detail="No settings changes provided")
        path = default_env_path()
        upsert_env_values(path, env_updates)
        return {
            "saved": True,
            "restart_required": True,
            "path": str(path),
            "updated_keys": sorted(env_updates.keys()),
        }

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
            actions=plan_actions_for_goal(payload.goal, payload.title),
        )
        return runtime.run_task(task).model_dump(mode="json")

    @api_app.get("/tasks/{task_id}")
    def get_task(task_id: str) -> dict[str, object]:
        task = runtime.resume_task(task_id)
        if task is None:
            return {"found": False, "task_id": task_id}
        return {"found": True, "task": task.model_dump(mode="json")}

    @api_app.post("/tasks/{task_id}/approve")
    def approve_task(task_id: str, payload: ApproveTaskRequest) -> dict[str, object]:
        result = runtime.continue_task(
            task_id,
            approved=payload.approved,
            reviewer=payload.reviewer,
        )
        task = runtime.resume_task(task_id)
        return {
            "result": result.model_dump(mode="json"),
            "task": None if task is None else task.model_dump(mode="json"),
        }

    @api_app.post("/voice/transcribe")
    def voice_transcribe(
        channel: Annotated[str, Query()] = "api",
        audio_path: Annotated[str, Query(min_length=1)] = "",
        language: Annotated[str | None, Query()] = None,
    ) -> dict[str, object]:
        from services.channels import ChannelGateway

        gateway = ChannelGateway()
        payload = gateway.ingest_voice(
            channel,
            transcript="",
            duration_seconds=0.0,
            audio_path=audio_path,
            language=language,
        )
        return payload.model_dump(mode="json")

    @api_app.post("/fs/watch/start")
    def fs_watch_start(payload: FsWatchStartRequest | None = None) -> dict[str, object]:
        adapter = runtime.capabilities.watchdog
        started = adapter.start()
        events: list[dict[str, object]] = []
        seconds = 0.0 if payload is None else payload.seconds
        if started and seconds > 0:
            events = adapter.poll_once(timeout_seconds=seconds)
        return {
            "started": started,
            "available": adapter.is_available(),
            "path": str(adapter.watch_path),
            "events": events,
        }

    @api_app.post("/fs/watch/stop")
    def fs_watch_stop() -> dict[str, object]:
        adapter = runtime.capabilities.watchdog
        adapter.stop()
        return {"stopped": True, "path": str(adapter.watch_path)}

    @api_app.get("/fs/watch/events")
    def fs_watch_events() -> dict[str, object]:
        adapter = runtime.capabilities.watchdog
        return {
            "path": str(adapter.watch_path),
            "events": adapter.drain_events(),
        }

    return api_app


app = create_app()


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)
