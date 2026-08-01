from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


class CodingAgentName(StrEnum):
    CLAUDE = "claude"
    OPENCODE = "opencode"
    CODEX = "codex"
    DROID = "droid"


# Preference order when default is "auto".
DEFAULT_AGENT_ORDER: tuple[CodingAgentName, ...] = (
    CodingAgentName.CODEX,
    CodingAgentName.OPENCODE,
    CodingAgentName.DROID,
    CodingAgentName.CLAUDE,
)

LAUNCH_HINTS: dict[CodingAgentName, str] = {
    CodingAgentName.CLAUDE: "ollama launch claude --model <model>",
    CodingAgentName.OPENCODE: "ollama launch opencode --model <model>",
    CodingAgentName.CODEX: "ollama launch codex --model <model>",
    CodingAgentName.DROID: "ollama launch droid --model <model>",
}

CODING_GOAL_KEYWORDS: tuple[str, ...] = (
    "implement",
    "refactor",
    "fix bug",
    "fix the",
    "patch",
    "write tests",
    "unit test",
    "write a script",
    "create a script",
    "create file",
    "create a file",
    "write a file",
    "код",
    "исправ",
    "рефактор",
    "скрипт",
    "создай файл",
    "создать файл",
    "создай скрипт",
    "создать скрипт",
    "напиши код",
    "напиши скрипт",
    "напиши файл",
    "сделай файл",
    "сделай скрипт",
    "review code",
    "code review",
    "pull request",
    " create pr",
    "open pr",
)


@dataclass(frozen=True)
class CodingAgentInvokeResult:
    agent: str
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    success: bool
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "success": self.success,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CodingAgentInvokeResult:
        return cls(
            agent=str(payload.get("agent") or ""),
            command=[str(item) for item in (payload.get("command") or [])],
            exit_code=int(payload.get("exit_code") or 1),
            stdout=str(payload.get("stdout") or ""),
            stderr=str(payload.get("stderr") or ""),
            success=bool(payload.get("success")),
            error=None if payload.get("error") in (None, "") else str(payload.get("error")),
        )


class CodingAgentsAdapter:
    """Discover and invoke coding CLIs locally or via the Docker coding sidecar."""

    def __init__(
        self,
        *,
        default_agent: str = "auto",
        model: str = "gemma4",
        timeout_seconds: float = 300.0,
        enabled: bool = True,
        which: Any | None = None,
        runner: Any | None = None,
        remote_url: str | None = None,
        http_client: Any | None = None,
    ) -> None:
        self._default_agent = (default_agent or "auto").strip().lower()
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._enabled = enabled
        self._which = which or shutil.which
        self._runner = runner or subprocess.run
        cleaned = (remote_url or "").strip().rstrip("/")
        self._remote_url = cleaned or None
        self._http_client = http_client
        self._remote_agents_cache: dict[str, Any] | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def remote_url(self) -> str | None:
        return self._remote_url

    def _http(self) -> Any:
        if self._http_client is not None:
            return self._http_client
        import httpx

        self._http_client = httpx.Client(timeout=self._timeout_seconds + 30.0)
        return self._http_client

    def _fetch_remote_agents(self, *, force: bool = False) -> dict[str, Any]:
        if self._remote_url is None:
            return {}
        if self._remote_agents_cache is not None and not force:
            return self._remote_agents_cache
        response = self._http().get(f"{self._remote_url}/agents")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Coding sidecar /agents returned non-object JSON")
        self._remote_agents_cache = payload
        return payload

    def resolve_binary(self, agent: CodingAgentName | str) -> str | None:
        if self._remote_url is not None:
            name = CodingAgentName(agent).value
            try:
                remote = self._fetch_remote_agents()
            except Exception:  # noqa: BLE001 - treat remote errors as unavailable
                LOGGER.debug("Coding sidecar agents lookup failed", exc_info=True)
                return None
            info = (remote.get("agents") or {}).get(name) or {}
            path = info.get("path")
            if info.get("installed") and path:
                return str(path)
            return None
        name = CodingAgentName(agent)
        return self._which(name.value)

    def is_available(self, agent: CodingAgentName | str) -> bool:
        return self.resolve_binary(agent) is not None

    def available_agents(self) -> list[CodingAgentName]:
        return [agent for agent in DEFAULT_AGENT_ORDER if self.is_available(agent)]

    def hint_from_text(self, text: str) -> CodingAgentName | None:
        lowered = text.lower()
        # Longer / more specific aliases first.
        aliases: list[tuple[str, CodingAgentName]] = [
            ("openaicodex", CodingAgentName.CODEX),
            ("openai-codex", CodingAgentName.CODEX),
            ("claude-code", CodingAgentName.CLAUDE),
            ("clodcod", CodingAgentName.CLAUDE),
            ("cloudcod", CodingAgentName.CLAUDE),
            ("opencod", CodingAgentName.OPENCODE),
            ("opencode", CodingAgentName.OPENCODE),
            ("codex", CodingAgentName.CODEX),
            ("droid", CodingAgentName.DROID),
            ("droip", CodingAgentName.DROID),
            ("claude", CodingAgentName.CLAUDE),
        ]
        for alias, agent in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", lowered):
                return agent
        return None

    def select_agent(self, text: str = "", preferred: str | None = None) -> CodingAgentName | None:
        if not self._enabled:
            return None

        candidates: list[CodingAgentName] = []
        if preferred:
            try:
                candidates.append(CodingAgentName(preferred.strip().lower()))
            except ValueError:
                pass
        hinted = self.hint_from_text(text)
        if hinted is not None and hinted not in candidates:
            candidates.append(hinted)
        default = (self._default_agent or "auto").strip().lower()
        if default not in {"", "auto"}:
            try:
                agent = CodingAgentName(default)
            except ValueError:
                agent = None
            if agent is not None and agent not in candidates:
                candidates.append(agent)

        for agent in candidates:
            if self.is_available(agent):
                return agent

        available = self.available_agents()
        return available[0] if available else None

    def build_command(
        self,
        agent: CodingAgentName | str,
        prompt: str,
        *,
        model: str | None = None,
    ) -> list[str]:
        name = CodingAgentName(agent)
        binary = self.resolve_binary(name)
        if binary is None:
            raise FileNotFoundError(
                f"Coding agent '{name.value}' is not installed. "
                f"Hint: {LAUNCH_HINTS[name]}"
            )
        model_id = model or self._model
        if name == CodingAgentName.CODEX:
            return [
                binary,
                "exec",
                "--oss",
                "--local-provider",
                "ollama",
                "-m",
                model_id,
                prompt,
            ]
        if name == CodingAgentName.OPENCODE:
            return [binary, "run", "-m", f"ollama/{model_id}", prompt]
        if name == CodingAgentName.DROID:
            return [binary, "exec", "--auto", "low", "-m", model_id, prompt]
        # Claude Code print/non-interactive mode.
        return [binary, "-p", prompt]

    def invoke(
        self,
        agent: CodingAgentName | str,
        prompt: str,
        *,
        cwd: str | Path | None = None,
        timeout: float | None = None,
        model: str | None = None,
    ) -> CodingAgentInvokeResult:
        name = CodingAgentName(agent)
        if self._remote_url is not None:
            return self._invoke_remote(
                name,
                prompt,
                cwd=cwd,
                timeout=timeout,
                model=model,
            )

        try:
            command = self.build_command(name, prompt, model=model)
        except FileNotFoundError as exc:
            return CodingAgentInvokeResult(
                agent=name.value,
                command=[],
                exit_code=127,
                stdout="",
                stderr=str(exc),
                success=False,
                error=str(exc),
            )

        workdir = str(cwd) if cwd is not None else None
        try:
            completed = self._runner(
                command,
                capture_output=True,
                text=True,
                cwd=workdir,
                timeout=timeout if timeout is not None else self._timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else str(exc)
            return CodingAgentInvokeResult(
                agent=name.value,
                command=command,
                exit_code=124,
                stdout=stdout,
                stderr=stderr,
                success=False,
                error=f"Timed out after {timeout or self._timeout_seconds}s",
            )
        except OSError as exc:
            return CodingAgentInvokeResult(
                agent=name.value,
                command=command,
                exit_code=1,
                stdout="",
                stderr=str(exc),
                success=False,
                error=str(exc),
            )

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        return CodingAgentInvokeResult(
            agent=name.value,
            command=command,
            exit_code=int(completed.returncode),
            stdout=stdout,
            stderr=stderr,
            success=completed.returncode == 0,
            error=None if completed.returncode == 0 else (stderr.strip() or "non-zero exit"),
        )

    def _invoke_remote(
        self,
        agent: CodingAgentName,
        prompt: str,
        *,
        cwd: str | Path | None,
        timeout: float | None,
        model: str | None,
    ) -> CodingAgentInvokeResult:
        assert self._remote_url is not None
        body: dict[str, Any] = {
            "prompt": prompt,
            "agent": agent.value,
            "model": model or self._model,
        }
        if cwd is not None:
            body["cwd"] = str(cwd)
        if timeout is not None:
            body["timeout"] = timeout
        try:
            response = self._http().post(
                f"{self._remote_url}/run",
                json=body,
                timeout=(timeout if timeout is not None else self._timeout_seconds) + 30.0,
            )
            if response.status_code >= 400:
                detail = response.text
                try:
                    payload = response.json()
                    detail = str(payload.get("detail") or payload)
                except Exception:  # noqa: BLE001
                    pass
                return CodingAgentInvokeResult(
                    agent=agent.value,
                    command=[],
                    exit_code=response.status_code,
                    stdout="",
                    stderr=detail,
                    success=False,
                    error=detail,
                )
            payload = response.json()
            if not isinstance(payload, dict):
                raise RuntimeError("Coding sidecar /run returned non-object JSON")
            return CodingAgentInvokeResult.from_dict(payload)
        except Exception as exc:  # noqa: BLE001 - surface transport failures
            LOGGER.exception("Coding sidecar invoke failed")
            return CodingAgentInvokeResult(
                agent=agent.value,
                command=[],
                exit_code=1,
                stdout="",
                stderr=str(exc),
                success=False,
                error=f"Coding sidecar error: {exc}",
            )

    def readiness(self) -> dict[str, Any]:
        if self._remote_url is not None:
            try:
                payload = dict(self._fetch_remote_agents(force=True))
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Coding sidecar readiness failed")
                return {
                    "enabled": self._enabled,
                    "default": self._default_agent,
                    "model": self._model,
                    "timeout_seconds": self._timeout_seconds,
                    "selected": None,
                    "available": [],
                    "agents": {},
                    "provider": "docker-sidecar",
                    "runtime": "docker-sidecar",
                    "remote_url": self._remote_url,
                    "error": str(exc),
                }
            payload.setdefault("provider", "docker-sidecar")
            payload["runtime"] = "docker-sidecar"
            payload["remote_url"] = self._remote_url
            payload["enabled"] = self._enabled and bool(payload.get("enabled", True))
            return payload

        agents: dict[str, Any] = {}
        for agent in CodingAgentName:
            path = self.resolve_binary(agent)
            agents[agent.value] = {
                "installed": path is not None,
                "path": path,
                "launch_hint": LAUNCH_HINTS[agent],
            }
        selected = self.select_agent()
        return {
            "enabled": self._enabled,
            "default": self._default_agent,
            "model": self._model,
            "timeout_seconds": self._timeout_seconds,
            "selected": selected.value if selected else None,
            "available": [agent.value for agent in self.available_agents()],
            "agents": agents,
            "provider": "ollama-launch",
            "runtime": "local",
        }


def goal_requests_coding_agent(text: str) -> bool:
    lowered = text.lower()
    if any(token in lowered for token in CODING_GOAL_KEYWORDS):
        return True
    adapter = CodingAgentsAdapter(enabled=True)
    return adapter.hint_from_text(lowered) is not None
