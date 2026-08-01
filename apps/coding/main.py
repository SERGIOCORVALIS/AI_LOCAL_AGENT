"""HTTP gateway that runs coding CLIs inside the Docker sidecar."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from packages.config import load_settings
from services.integrations.coding_agents import CodingAgentsAdapter

DEFAULT_WORKSPACE = Path("/workspace")


class RunCodingAgentRequest(BaseModel):
    prompt: str = Field(min_length=1)
    agent: str | None = None
    model: str | None = None
    cwd: str | None = None
    timeout: float | None = Field(default=None, ge=1.0, le=3600.0)


def create_app(*, adapter: CodingAgentsAdapter | None = None) -> FastAPI:
    settings = load_settings()
    coding_model = (
        (settings.coding_agent_model or settings.model_primary).strip() or settings.model_primary
    )
    if adapter is None:
        adapter = CodingAgentsAdapter(
            default_agent=settings.coding_agent_default,
            model=coding_model,
            timeout_seconds=settings.coding_agent_timeout_seconds,
            enabled=settings.coding_agents_enabled,
        )
    api = FastAPI(title="Local AI Agent Coding Sidecar", version="0.3.0")

    @api.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "coding",
            "enabled": adapter.enabled,
        }

    @api.get("/agents")
    def agents() -> dict[str, object]:
        payload = adapter.readiness()
        payload["runtime"] = "docker-sidecar"
        payload["workspace"] = str(DEFAULT_WORKSPACE)
        return payload

    @api.post("/run")
    def run_agent(payload: RunCodingAgentRequest) -> dict[str, object]:
        if not adapter.enabled:
            raise HTTPException(status_code=503, detail="Coding agents disabled")

        preferred = payload.agent
        selected = adapter.select_agent(payload.prompt, preferred=preferred)
        if selected is None:
            raise HTTPException(
                status_code=503,
                detail="No coding CLI available in sidecar (codex/opencode/droid)",
            )

        cwd = payload.cwd or str(DEFAULT_WORKSPACE)
        cwd_path = Path(cwd)
        if not cwd_path.exists():
            raise HTTPException(status_code=400, detail=f"cwd does not exist: {cwd}")

        result = adapter.invoke(
            selected,
            payload.prompt,
            cwd=cwd_path,
            timeout=payload.timeout,
            model=payload.model,
        )
        return result.as_dict()

    return api


app = create_app()
