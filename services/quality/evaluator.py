from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, Field

CommandRunner = Callable[[list[str], Path, float], tuple[int, str, str]]


class QualityReport(BaseModel):
    lint_ready: bool
    typed_contracts_ready: bool
    tests_ready: bool
    audit_ready: bool
    details: dict[str, bool | str | int] = Field(default_factory=dict)


def _default_runner(command: list[str], cwd: Path, timeout: float) -> tuple[int, str, str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


class QualityEvaluator:
    """Runs local quality gates and reports readiness from real exit codes."""

    def __init__(self, runner: CommandRunner | None = None) -> None:
        self._runner = runner or _default_runner

    def evaluate(
        self,
        project_root: Path | None = None,
        *,
        run_tools: bool = True,
        timeout_seconds: float = 120.0,
    ) -> QualityReport:
        root = project_root or Path.cwd()
        audit_ready = (root / "packages" / "safety" / "audit.py").exists()
        details: dict[str, bool | str | int] = {
            "core_models_present": (root / "packages" / "core" / "models.py").exists(),
            "tests_dir_present": (root / "tests").exists(),
            "audit_module_present": audit_ready,
        }

        if not run_tools:
            return QualityReport(
                lint_ready=False,
                typed_contracts_ready=False,
                tests_ready=False,
                audit_ready=audit_ready,
                details=details,
            )

        lint_code, lint_out, lint_err = self._runner(
            [sys.executable, "-m", "ruff", "check", "."],
            root,
            timeout_seconds,
        )
        mypy_code, mypy_out, mypy_err = self._runner(
            [sys.executable, "-m", "mypy", "."],
            root,
            timeout_seconds,
        )
        pytest_code, pytest_out, pytest_err = self._runner(
            [sys.executable, "-m", "pytest", "-q"],
            root,
            timeout_seconds,
        )

        details.update(
            {
                "ruff_exit_code": lint_code,
                "mypy_exit_code": mypy_code,
                "pytest_exit_code": pytest_code,
                "ruff_output": (lint_out or lint_err)[:500],
                "mypy_output": (mypy_out or mypy_err)[:500],
                "pytest_output": (pytest_out or pytest_err)[:500],
            }
        )
        return QualityReport(
            lint_ready=lint_code == 0,
            typed_contracts_ready=mypy_code == 0,
            tests_ready=pytest_code == 0,
            audit_ready=audit_ready,
            details=details,
        )
