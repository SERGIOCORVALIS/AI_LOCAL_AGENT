from __future__ import annotations

import json
from pathlib import Path

import typer

from packages.config import Settings, load_settings
from packages.core import Task
from services.channels import ChannelGateway
from services.integrations.coding_agents import CodingAgentsAdapter
from services.integrations.playwright_adapter import PlaywrightAutomationAdapter
from services.llm import (
    AgentModelConfig,
    OllamaClient,
    agents_from_settings,
    ollama_agents_readiness,
    resolve_agents,
)
from services.memory import build_memory_backend
from services.orchestrator.capabilities import plan_actions_for_goal
from services.orchestrator.runtime import OrchestratorRuntime
from services.perception.readiness import perception_readiness
from services.quality import QualityEvaluator

app = typer.Typer(help="Local AI Agent operator CLI.")


def _agent_config(settings: Settings) -> AgentModelConfig:
    return agents_from_settings(
        primary=settings.model_primary,
        router=settings.model_router,
        vision=settings.model_vision,
        embed=settings.model_embed,
    )


@app.command()
def status() -> None:
    """Print current platform status including perception readiness."""
    settings = load_settings()
    memory = build_memory_backend(settings)
    embedder = getattr(memory, "embedder", None)
    ollama = OllamaClient(base_url=settings.ollama_url, timeout=3.0)
    agents = resolve_agents(ollama, _agent_config(settings))
    coding = CodingAgentsAdapter(
        default_agent=settings.coding_agent_default,
        model=(settings.coding_agent_model or agents.resolved.primary),
        timeout_seconds=settings.coding_agent_timeout_seconds,
        enabled=settings.coding_agents_enabled,
    )
    payload = {
        "app_name": settings.app_name,
        "env": settings.env,
        "log_level": settings.log_level,
        "model_primary": settings.model_primary,
        "model_router": settings.model_router,
        "model_vision": settings.model_vision,
        "model_embed": settings.model_embed,
        "models_resolved": agents.resolved.as_dict(),
        "ollama_url": settings.ollama_url,
        "ollama_online": agents.online,
        "embedding_dimensions": settings.embedding_dimensions,
        "embedding_prefer_native": settings.embedding_prefer_native,
        "runtime_log_path": str(settings.runtime_log_path),
        "backup_dir": str(settings.backup_dir),
        "admin_ui_title": settings.admin_ui_title,
        "allowed_execute_actions": sorted(settings.allowed_execute_actions),
        "coding_agents": coding.readiness(),
        "web_search": {"provider": "duckduckgo"},
        "perception": perception_readiness(
            embedder=embedder,
            ollama_client=ollama,
            vision_model=agents.resolved.vision,
            agents=agents.configured,
        ),
    }
    typer.echo(json.dumps(payload, indent=2))


@app.command()
def run(title: str, goal: str) -> None:
    """Plan and run a concrete orchestrator task from a goal."""
    runtime = OrchestratorRuntime(load_settings())
    task = Task(
        title=title,
        goal=goal,
        actions=plan_actions_for_goal(goal, title),
    )
    result = runtime.run_task(task)
    typer.echo(result.model_dump_json(indent=2))


@app.command()
def doctor() -> None:
    """Print release-readiness health summary + perception backends."""
    settings = load_settings()
    report = QualityEvaluator().evaluate()
    memory = build_memory_backend(settings)
    embedder = getattr(memory, "embedder", None)
    ollama = OllamaClient(base_url=settings.ollama_url, timeout=3.0)
    agents = resolve_agents(ollama, _agent_config(settings))
    coding = CodingAgentsAdapter(
        default_agent=settings.coding_agent_default,
        model=(settings.coding_agent_model or agents.resolved.primary),
        timeout_seconds=settings.coding_agent_timeout_seconds,
        enabled=settings.coding_agents_enabled,
    )
    payload = {
        "quality": json.loads(report.model_dump_json()),
        "models_resolved": agents.resolved.as_dict(),
        "ollama_agents": ollama_agents_readiness(ollama, agents.configured),
        "coding_agents": coding.readiness(),
        "web_search": {"provider": "duckduckgo"},
        "perception": perception_readiness(
            embedder=embedder,
            ollama_client=ollama,
            vision_model=agents.resolved.vision,
            agents=agents.configured,
        ),
    }
    typer.echo(json.dumps(payload, indent=2))


@app.command("ollama-check")
def ollama_check() -> None:
    """Verify Ollama daemon and all configured agent model slots."""
    settings = load_settings()
    ollama = OllamaClient(base_url=settings.ollama_url, timeout=5.0)
    configured = _agent_config(settings)
    agents = resolve_agents(ollama, configured)
    readiness = ollama_agents_readiness(ollama, configured)
    payload = {
        "ollama_url": settings.ollama_url,
        "online": agents.online,
        "installed": agents.installed,
        "configured": agents.configured.as_dict(),
        "resolved": agents.resolved.as_dict(),
        "slots": readiness["slots"],
        "roles": readiness["roles"],
        "all_required_available": readiness["all_required_available"],
        "hint": readiness["hint"],
    }
    typer.echo(json.dumps(payload, indent=2))
    if not readiness["all_required_available"]:
        raise typer.Exit(code=1)


@app.command("approve")
def approve_task(
    task_id: str,
    approved: bool = typer.Option(True, "--approved/--rejected"),
    reviewer: str = typer.Option("operator", "--reviewer"),
) -> None:
    """Continue a task paused for human approval."""
    runtime = OrchestratorRuntime(load_settings())
    result = runtime.continue_task(task_id, approved=approved, reviewer=reviewer)
    task = runtime.resume_task(task_id)
    payload = {
        "result": json.loads(result.model_dump_json()),
        "task": None if task is None else json.loads(task.model_dump_json()),
    }
    typer.echo(json.dumps(payload, indent=2))


@app.command("voice")
def voice_transcribe(
    audio_path: Path,
    channel: str = typer.Option("cli", "--channel"),
    language: str | None = typer.Option(None, "--language", help="STT language (default: auto)"),
) -> None:
    """Transcribe a local audio file via STT."""
    if not audio_path.exists():
        raise typer.BadParameter(f"Audio file not found: {audio_path}")
    payload = ChannelGateway().ingest_voice(
        channel,
        transcript="",
        duration_seconds=0.0,
        audio_path=audio_path,
        language=language,
    )
    typer.echo(payload.model_dump_json(indent=2))


@app.command("playwright-setup")
def playwright_setup() -> None:
    """Install Playwright Chromium browser for local automation."""
    result = PlaywrightAutomationAdapter().ensure_browsers()
    typer.echo(json.dumps(result, indent=2))
    if not result.get("success"):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
