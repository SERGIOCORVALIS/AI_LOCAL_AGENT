from __future__ import annotations

import json

import typer

from packages.config import load_settings
from packages.core import Action, Task
from services.orchestrator import OrchestratorRuntime
from services.quality import QualityEvaluator

app = typer.Typer(help="Local AI Agent operator CLI.")


@app.command()
def status() -> None:
    """Print current platform status."""
    settings = load_settings()
    payload = {
        "app_name": settings.app_name,
        "env": settings.env,
        "log_level": settings.log_level,
        "model_primary": settings.model_primary,
        "model_router": settings.model_router,
        "runtime_log_path": str(settings.runtime_log_path),
        "backup_dir": str(settings.backup_dir),
        "admin_ui_title": settings.admin_ui_title,
        "allowed_execute_actions": sorted(settings.allowed_execute_actions),
    }
    typer.echo(json.dumps(payload, indent=2))


@app.command()
def run(title: str, goal: str) -> None:
    """Run a minimal orchestrator task."""
    runtime = OrchestratorRuntime(load_settings())
    task = Task(
        title=title,
        goal=goal,
        actions=[
            Action(
                name="bootstrap",
                description="Foundational runtime bootstrap action.",
            )
        ],
    )
    result = runtime.run_task(task)
    typer.echo(result.model_dump_json(indent=2))


@app.command()
def doctor() -> None:
    """Print release-readiness health summary."""
    report = QualityEvaluator().evaluate()
    typer.echo(report.model_dump_json(indent=2))


if __name__ == "__main__":
    app()
