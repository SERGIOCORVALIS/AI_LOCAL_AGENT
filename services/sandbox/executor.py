from __future__ import annotations

import subprocess

from packages.sandbox import SandboxExecution, SandboxRequest


class SandboxExecutor:
    """Execution abstraction ready for Docker-backed isolation."""

    def execute(self, request: SandboxRequest) -> SandboxExecution:
        completed = subprocess.run(
            request.command,
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
        )

    def execute_with_retries(self, request: SandboxRequest, retries: int = 1) -> SandboxExecution:
        attempt = 0
        last_result = self.execute(request)
        while attempt < retries and not last_result.success:
            attempt += 1
            last_result = self.execute(request)
            last_result.retries = attempt
        return last_result
