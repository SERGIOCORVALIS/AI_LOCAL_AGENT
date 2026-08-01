from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from packages.sandbox import SandboxExecution, SandboxRequest


class SandboxExecutor:
    """Command runner with Docker isolation when available, scrubbed local fallback."""

    def __init__(self, prefer_docker: bool = True) -> None:
        self._prefer_docker = prefer_docker

    def execute(self, request: SandboxRequest) -> SandboxExecution:
        use_docker = self._prefer_docker or request.prefer_docker
        if use_docker and self._docker_available():
            return self._execute_docker(request)
        result = self._execute_local(request)
        if use_docker:
            result.degraded = True
            note = "docker_unavailable; ran in scrubbed local tempdir (not container-isolated)"
            result.stderr = f"{result.stderr}\n{note}".strip()
        return result

    def execute_with_retries(self, request: SandboxRequest, retries: int = 1) -> SandboxExecution:
        attempt = 0
        last_result = self.execute(request)
        while attempt < retries and not last_result.success:
            attempt += 1
            last_result = self.execute(request)
            last_result.retries = attempt
        return last_result

    def _docker_available(self) -> bool:
        if shutil.which("docker") is None:
            return False
        probe = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            check=False,
            timeout=8,
        )
        return probe.returncode == 0

    def _execute_docker(self, request: SandboxRequest) -> SandboxExecution:
        network = "bridge" if request.allow_network else "none"
        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            network,
            "--cpus",
            "1",
            "--memory",
            "512m",
            "python:3.12-slim",
            *request.command,
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=request.timeout_seconds,
            check=False,
        )
        return SandboxExecution(
            success=completed.returncode == 0,
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
            mode="docker",
            degraded=False,
            isolated=True,
        )

    def _execute_local(self, request: SandboxRequest) -> SandboxExecution:
        with tempfile.TemporaryDirectory(prefix="local-ai-agent-sandbox-") as temp_dir:
            env = self._scrubbed_env(allow_network=request.allow_network)
            completed = subprocess.run(
                request.command,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                check=False,
                cwd=temp_dir,
                env=env,
            )
            marker = Path(temp_dir) / "sandbox-meta.json"
            marker.write_text(
                json.dumps(
                    {
                        "command": request.command,
                        "language": request.language,
                        "allow_network": request.allow_network,
                        "exit_code": completed.returncode,
                        "mode": "local",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            return SandboxExecution(
                success=completed.returncode == 0,
                stdout=completed.stdout,
                stderr=completed.stderr,
                exit_code=completed.returncode,
                mode="local",
                degraded=False,
                isolated=False,
            )

    def _scrubbed_env(self, *, allow_network: bool) -> dict[str, str]:
        allowed_keys = {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "HOME",
            "USERPROFILE",
            "LANG",
            "LC_ALL",
            "PYTHONUTF8",
            "PYTHONIOENCODING",
        }
        env = {key: value for key, value in os.environ.items() if key in allowed_keys}
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        if not allow_network:
            env["NO_PROXY"] = "*"
            env["HTTP_PROXY"] = ""
            env["HTTPS_PROXY"] = ""
            env["ALL_PROXY"] = ""
        return env
