from __future__ import annotations

import re
import shlex
from pathlib import Path
from urllib.parse import urlparse

from packages.core import Action, ActionMode, ActionResult, Artifact, ArtifactKind, Observation
from packages.sandbox import SandboxRequest
from services.fs_daemon import FileSystemDaemon
from services.integrations.coding_agents import (
    CodingAgentsAdapter,
    goal_requests_coding_agent,
)
from services.integrations.watchdog_adapter import WatchdogAdapter
from services.llm import OLLAMA_UNAVAILABLE, OllamaClient
from services.perception import CodeIntelligence, VisionAnalyzer, WebParser
from services.sandbox import SandboxExecutor

_SEARCH_KEYWORDS: tuple[str, ...] = (
    "search",
    "найди",
    "найти",
    "research",
    "look up",
    "lookup",
    "what is",
    "who is",
    "web search",
    "поиск",
    "гугл",
    "duckduckgo",
    "интернет",
    "в сети",
    "в интернете",
    "online",
    "google",
    "узнай",
    "поищи",
)


def plan_actions_for_goal(goal: str, title: str = "") -> list[Action]:
    """Derive concrete capability actions from a free-form goal."""
    text = f"{title} {goal}".lower()
    actions: list[Action] = []
    write_spec = _extract_write_file(goal)

    urls = _extract_urls(goal)
    for url in urls:
        actions.append(
            Action(
                name="web_fetch",
                description=f"Fetch and parse web page {url}",
                mode=ActionMode.EXECUTE,
                payload={"url": url},
                side_effects=["network"],
            )
        )

    if not urls and any(token in text for token in _SEARCH_KEYWORDS):
        actions.append(
            Action(
                name="web_search",
                description="Search the web via DuckDuckGo",
                mode=ActionMode.EXECUTE,
                payload={"query": goal.strip() or title.strip()},
                side_effects=["network"],
            )
        )

    sandbox_command = _extract_sandbox_command(goal)
    if sandbox_command is not None:
        actions.append(
            Action(
                name="sandbox_run",
                description="Execute command inside sandbox",
                mode=ActionMode.EXECUTE,
                payload={"command": sandbox_command, "language": "python"},
                side_effects=["execute"],
            )
        )

    if write_spec is not None:
        actions.append(
            Action(
                name="write_file",
                description=f"Create file {write_spec['path']}",
                mode=ActionMode.EXECUTE,
                payload=write_spec,
                side_effects=["write"],
            )
        )

    if any(token in text for token in ("code", "import", "ast", "index", "workspace", "repo")):
        actions.append(
            Action(
                name="code_intel",
                description="Index Python workspace",
                mode=ActionMode.OBSERVE,
                payload={"root": "."},
            )
        )

    if goal_requests_coding_agent(text) and write_spec is None:
        hinted = CodingAgentsAdapter().hint_from_text(text)
        payload: dict[str, object] = {"prompt": goal.strip() or title.strip(), "cwd": "."}
        if hinted is not None:
            payload["agent"] = hinted.value
        actions.append(
            Action(
                name="coding_agent",
                description="Run local Ollama coding agent",
                mode=ActionMode.EXECUTE,
                payload=payload,
                side_effects=["execute", "write", "network"],
            )
        )

    create_file_intent = write_spec is not None or any(
        token in text
        for token in (
            "создай файл",
            "создать файл",
            "create file",
            "write a file",
            "напиши файл",
            "сделай файл",
        )
    )
    if (
        any(token in text for token in ("download", "organize", "filesystem", "scan"))
        or ("file" in text and not create_file_intent)
    ):
        actions.append(
            Action(
                name="fs_scan",
                description="Scan and propose file routes",
                mode=ActionMode.DRY_RUN,
                payload={},
                side_effects=["read"],
            )
        )

    if any(token in text for token in ("watch", "monitor downloads", "filesystem watch")):
        actions.append(
            Action(
                name="fs_watch",
                description="Start filesystem watch and collect events",
                mode=ActionMode.OBSERVE,
                payload={"seconds": 0.5},
                side_effects=["read"],
            )
        )

    if any(token in text for token in ("screenshot", "image", "vision", "ocr", "ui")):
        image_path = _extract_image_path(goal)
        if image_path is not None:
            actions.append(
                Action(
                    name="vision_inspect",
                    description="Inspect an image artifact",
                    mode=ActionMode.OBSERVE,
                    payload={"path": image_path},
                )
            )

    if any(token in text for token in ("browser", "playwright", "navigate", "webpage")) and urls:
        target = urls[0]
        actions.append(
            Action(
                name="browser_open",
                description=f"Open page with Playwright: {target}",
                mode=ActionMode.EXECUTE,
                payload={"url": target},
                side_effects=["network", "browser"],
            )
        )

    if not actions:
        actions.append(
            Action(
                name="reflect",
                description="Reflect on goal using memory and local analysis",
                mode=ActionMode.OBSERVE,
                payload={"goal": goal, "title": title},
            )
        )
    return actions


def _extract_urls(text: str) -> list[str]:
    candidates = []
    for token in text.split():
        parsed = urlparse(token)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            candidates.append(token.rstrip(".,)"))
    return candidates


def _extract_write_file(goal: str) -> dict[str, str] | None:
    """Extract a simple create-file request with optional script/content body."""
    match = re.search(
        r"(?:создай|создать|сделай|напиши|create|write)\s+"
        r"(?:файл|file|скрипт|script)\s+"
        r"[\"'`]?([A-Za-z0-9_.\\/-]+\.[A-Za-z0-9]+)[\"'`]?"
        r"(?:\s+(?:со?\s+скриптом|with(?:\s+(?:content|script))?|содержим(?:ое|ым)?|:)\s+(.+))?",
        goal,
        re.I | re.S,
    )
    if not match:
        # "hello.py со скриптом print(1)" / "файл hello.py: print(1)"
        match = re.search(
            r"(?:файл|file)\s+[\"'`]?([A-Za-z0-9_.\\/-]+\.[A-Za-z0-9]+)[\"'`]?"
            r"(?:\s*(?::|со?\s+скриптом|with)\s*(.+))?",
            goal,
            re.I | re.S,
        )
    if not match:
        return None
    path = match.group(1).strip()
    body = (match.group(2) or "").strip().strip("\"'`")
    if not body:
        suffix = Path(path).suffix.lower()
        if suffix == ".py":
            body = 'print("hello")\n'
        elif suffix in {".ps1", ".bat", ".cmd"}:
            body = "Write-Host 'hello'\n"
        elif suffix in {".js", ".ts"}:
            body = 'console.log("hello");\n'
        else:
            body = "hello\n"
    if body.startswith("print ") and "(" not in body:
        body = f'print("{body[6:].strip()}")\n'
    if not body.endswith("\n"):
        body += "\n"
    return {"path": path, "content": body}


def _extract_sandbox_command(goal: str) -> list[str] | None:
    fenced = re.search(r"```(?:bash|shell|sh|powershell|python)?\s*\n(.*?)```", goal, re.S | re.I)
    if fenced:
        line = fenced.group(1).strip().splitlines()[0].strip()
        if line:
            return shlex.split(line, posix=False)

    python_c = re.search(r"python\s+-c\s+([\"'])(.*?)\1", goal, re.I | re.S)
    if python_c:
        return ["python", "-c", python_c.group(2)]

    python_file = re.search(r"python\s+([^\s]+\.py)\b", goal, re.I)
    if python_file:
        return ["python", python_file.group(1)]

    run_match = re.search(
        r"(?:run|execute)\s+((?:python|[A-Za-z0-9_./\\-]+)(?:\s+[^\n]+)?)",
        goal,
        re.I,
    )
    if run_match:
        candidate = run_match.group(1).strip()
        if candidate:
            return shlex.split(candidate, posix=False)
    return None


def _default_screenshot_path() -> str:
    return str(Path("runtime/screenshots/latest.png"))


def _extract_image_path(goal: str) -> str | None:
    match = re.search(
        r"([A-Za-z]:\\[^\s\"']+\.(?:png|jpe?g|gif|webp)|/[^\s\"']+\.(?:png|jpe?g|gif|webp)|"
        r"[^\s\"']+\.(?:png|jpe?g|gif|webp))",
        goal,
        re.I,
    )
    if match:
        return match.group(1)
    default = Path(_default_screenshot_path())
    if default.exists():
        return str(default)
    screenshots = Path("runtime/screenshots")
    if screenshots.exists():
        candidates = sorted(
            [
                path
                for path in screenshots.iterdir()
                if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}
            ],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return str(candidates[0])
    return None


def _resolve_existing_image_path(raw_path: str | None) -> Path | None:
    """Resolve an existing image path; never synthesizes placeholder files."""
    if raw_path:
        path = Path(str(raw_path))
        if path.exists() and path.is_file():
            return path
    discovered = _extract_image_path("")
    if discovered:
        candidate = Path(discovered)
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


class CapabilityHandlers:
    """Concrete capability implementations bound into the registry."""

    def __init__(
        self,
        downloads_watch_path: Path,
        *,
        prefer_docker: bool = True,
        ollama_client: OllamaClient | None = None,
        vision_model: str = "gemma4",
        chat_model: str = "gemma4",
        watchdog: WatchdogAdapter | None = None,
        coding_agents: CodingAgentsAdapter | None = None,
    ) -> None:
        self._downloads_watch_path = downloads_watch_path
        self._sandbox = SandboxExecutor(prefer_docker=prefer_docker)
        self._prefer_docker = prefer_docker
        self._web = WebParser()
        self._vision = VisionAnalyzer(ollama_client=ollama_client, vision_model=vision_model)
        self._code = CodeIntelligence()
        self._fs = FileSystemDaemon()
        self._watchdog = watchdog or WatchdogAdapter(downloads_watch_path)
        self._ollama = ollama_client
        self._chat_model = chat_model
        self._coding_agents = coding_agents or CodingAgentsAdapter(enabled=False)

    @property
    def watchdog(self) -> WatchdogAdapter:
        return self._watchdog

    @property
    def coding_agents(self) -> CodingAgentsAdapter:
        return self._coding_agents

    def sandbox_run(self, action: Action) -> ActionResult:
        command = action.payload.get("command")
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            return _failed(action, "sandbox_run requires payload.command as list[str]")
        language = str(action.payload.get("language", "shell"))
        allow_network = bool(action.payload.get("allow_network", False))
        result = self._sandbox.execute(
            SandboxRequest(
                command=command,
                language=language,
                allow_network=allow_network,
                prefer_docker=self._prefer_docker,
            )
        )
        observation = Observation(
            source="capability.sandbox",
            summary=(
                f"Sandbox finished mode={result.mode} "
                f"isolated={result.isolated} degraded={result.degraded}."
            ),
            details=result.model_dump(mode="json"),
        )
        output = result.stdout.strip() or result.stderr.strip() or "sandbox finished"
        if result.degraded:
            output = f"{output} [sandbox_degraded:mode={result.mode}]"
        return ActionResult(
            action=action,
            success=result.success,
            message=output,
            observations=[observation],
            artifacts=[
                Artifact(
                    kind=ArtifactKind.LOG,
                    name="sandbox-output",
                    metadata={
                        "exit_code": result.exit_code,
                        "mode": result.mode,
                        "isolated": result.isolated,
                        "degraded": result.degraded,
                    },
                )
            ],
        )

    def web_fetch(self, action: Action) -> ActionResult:
        url = str(action.payload.get("url", "")).strip()
        if not url:
            return _failed(action, "web_fetch requires payload.url")
        document = self._web.fetch_url(url)
        observation = Observation(
            source="capability.web",
            summary=f"Fetched {document.title}",
            details=document.model_dump(mode="json"),
        )
        return ActionResult(
            action=action,
            success=True,
            message=f"Fetched '{document.title}' from {url}",
            observations=[observation],
            artifacts=[
                Artifact(
                    kind=ArtifactKind.REPORT,
                    name="web-document",
                    uri=url,
                    metadata={"title": document.title},
                )
            ],
        )

    def web_search(self, action: Action) -> ActionResult:
        query = str(action.payload.get("query", "")).strip()
        if not query:
            return _failed(action, "web_search requires payload.query")
        max_results = int(action.payload.get("max_results", 5))
        response = self._web.search(query, max_results=max_results)
        observation = Observation(
            source="capability.web_search",
            summary=f"DuckDuckGo search returned {len(response.results)} results",
            details=response.model_dump(mode="json"),
        )
        if response.results:
            lines = [
                f"{idx}. {item.title} — {item.url}"
                for idx, item in enumerate(response.results, start=1)
            ]
            message = (
                f"Интернет-поиск (DuckDuckGo) по запросу '{query}': "
                f"{len(response.results)} результатов\n" + "\n".join(lines)
            )
        else:
            message = (
                f"Интернет-поиск (DuckDuckGo) по запросу '{query}': "
                "результатов нет (проверьте сеть/фильтры)."
            )
        return ActionResult(
            action=action,
            success=True,
            message=message,
            observations=[observation],
            artifacts=[
                Artifact(
                    kind=ArtifactKind.REPORT,
                    name="web-search",
                    metadata={
                        "provider": response.provider,
                        "query": response.query,
                        "count": len(response.results),
                    },
                )
            ],
        )

    def write_file(self, action: Action) -> ActionResult:
        raw_path = str(action.payload.get("path", "")).strip()
        content = action.payload.get("content")
        if not raw_path:
            return _failed(action, "write_file requires payload.path")
        if not isinstance(content, str):
            return _failed(action, "write_file requires payload.content as str")
        path = Path(raw_path)
        if path.is_absolute():
            return _failed(action, "write_file rejects absolute paths; use a relative path")
        if ".." in path.parts:
            return _failed(action, "write_file rejects parent-directory traversal")
        cwd = Path.cwd().resolve()
        target = (cwd / path).resolve()
        try:
            target.relative_to(cwd)
        except ValueError:
            return _failed(action, "write_file path must stay inside the workspace")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        observation = Observation(
            source="capability.write_file",
            summary=f"Wrote {len(content)} chars to {target}",
            details={"path": str(target), "bytes": len(content.encode("utf-8"))},
        )
        return ActionResult(
            action=action,
            success=True,
            message=f"Файл создан: {target}",
            observations=[observation],
            artifacts=[
                Artifact(
                    kind=ArtifactKind.FILE,
                    name=target.name,
                    uri=str(target),
                    metadata={"bytes": len(content.encode("utf-8"))},
                )
            ],
        )
    def coding_agent(self, action: Action) -> ActionResult:
        if not self._coding_agents.enabled:
            return _failed(action, "coding agents are disabled in settings")
        prompt = str(action.payload.get("prompt", "")).strip()
        if not prompt:
            return _failed(action, "coding_agent requires payload.prompt")
        preferred = action.payload.get("agent")
        preferred_str = str(preferred).strip() if preferred else None
        selected = self._coding_agents.select_agent(prompt, preferred=preferred_str)
        if selected is None:
            readiness = self._coding_agents.readiness()
            hints = [
                info["launch_hint"]
                for info in readiness["agents"].values()
                if not info["installed"]
            ]
            return _failed(
                action,
                "No local coding agent CLI found. Install via: "
                + "; ".join(hints[:3]),
            )
        cwd_raw = action.payload.get("cwd", ".")
        cwd = Path(str(cwd_raw)) if cwd_raw else Path(".")
        result = self._coding_agents.invoke(selected, prompt, cwd=cwd)
        observation = Observation(
            source="capability.coding_agent",
            summary=(
                f"Coding agent '{result.agent}' "
                f"{'succeeded' if result.success else 'failed'} "
                f"(exit={result.exit_code})"
            ),
            details=result.as_dict(),
        )
        message = (
            result.stdout.strip()
            or result.stderr.strip()
            or result.error
            or f"coding agent {result.agent} finished"
        )
        return ActionResult(
            action=action,
            success=result.success,
            message=message[:4000],
            observations=[observation],
            artifacts=[
                Artifact(
                    kind=ArtifactKind.LOG,
                    name="coding-agent-output",
                    metadata={
                        "agent": result.agent,
                        "exit_code": result.exit_code,
                        "success": result.success,
                    },
                )
            ],
        )

    def code_intel(self, action: Action) -> ActionResult:
        root = Path(str(action.payload.get("root", ".")))
        summary = self._code.index_python_tree(root)
        observation = Observation(
            source="capability.code_intel",
            summary=f"Indexed {len(summary.python_files)} Python files",
            details=summary.model_dump(mode="json"),
        )
        return ActionResult(
            action=action,
            success=True,
            message=f"Indexed {len(summary.python_files)} files under {root}",
            observations=[observation],
        )

    def fs_scan(self, action: Action) -> ActionResult:
        root = Path(str(action.payload.get("root", self._downloads_watch_path)))
        if not root.exists():
            root.mkdir(parents=True, exist_ok=True)
        records = self._fs.scan_directory(root)
        proposals = self._fs.propose_routes(records)
        apply = bool(action.payload.get("apply", False))
        applied: list[str] = []
        if apply:
            applied = [str(path) for path in self._fs.apply_routes(proposals, root)]
        observation = Observation(
            source="capability.fs",
            summary=f"Scanned {len(records)} files",
            details={
                "records": [record.model_dump(mode="json") for record in records],
                "proposals": [item.model_dump(mode="json") for item in proposals],
                "applied": applied,
            },
        )
        return ActionResult(
            action=action,
            success=True,
            message=f"FS scan complete: {len(records)} files, {len(proposals)} proposals",
            observations=[observation],
        )

    def fs_watch(self, action: Action) -> ActionResult:
        seconds = float(action.payload.get("seconds", 0.5))
        started = self._watchdog.start()
        events = self._watchdog.poll_once(timeout_seconds=seconds) if started else []
        observation = Observation(
            source="capability.fs_watch",
            summary=f"Watchdog started={started}, events={len(events)}",
            details={
                "started": started,
                "watch_path": str(self._watchdog.watch_path),
                "events": events,
            },
        )
        return ActionResult(
            action=action,
            success=started,
            message=observation.summary,
            observations=[observation],
        )

    def vision_inspect(self, action: Action) -> ActionResult:
        raw_path = action.payload.get("path")
        path = _resolve_existing_image_path(str(raw_path) if raw_path else None)
        if path is None:
            return _failed(
                action,
                "vision_inspect requires an existing image file "
                "(payload.path or runtime/screenshots/*)",
            )
        analysis = self._vision.inspect_image(path)
        ocr_used = "ocr=" in analysis.summary
        vlm_used = "vlm=" in analysis.summary and OLLAMA_UNAVAILABLE not in analysis.summary
        observation = Observation(
            source="capability.vision",
            summary=analysis.summary,
            details={
                **analysis.model_dump(mode="json"),
                "ocr_used": ocr_used,
                "vlm_used": vlm_used,
            },
        )
        return ActionResult(
            action=action,
            success=True,
            message=analysis.summary,
            observations=[observation],
        )

    def browser_open(self, action: Action) -> ActionResult:
        from services.integrations.playwright_adapter import PlaywrightAutomationAdapter

        url = str(action.payload.get("url", "")).strip()
        if not url:
            return _failed(action, "browser_open requires payload.url")
        adapter = PlaywrightAutomationAdapter()
        result = adapter.open_page(url)
        observation = Observation(
            source="capability.browser",
            summary=result.get("summary", "browser action finished"),
            details=result,
        )
        return ActionResult(
            action=action,
            success=bool(result.get("success")),
            message=str(result.get("summary", "browser action finished")),
            observations=[observation],
        )

    def reflect(self, action: Action, memory_snippets: list[str] | None = None) -> ActionResult:
        goal = str(action.payload.get("goal", action.description))
        snippets = memory_snippets or []
        model = str(action.payload.get("model") or self._chat_model)
        memory_block = "\n- ".join(snippets[:5] or ["none"])
        if self._ollama is None:
            llm_text = OLLAMA_UNAVAILABLE
        else:
            llm_text = self._ollama.chat(
                model,
                [
                    {
                        "role": "system",
                        "content": (
                            "You are Local AI Agent, a helpful local assistant. "
                            "Reply briefly and naturally in the user's language. "
                            "Do not invent tool results. If you need a concrete action "
                            "(URL, file path, or command), ask for it clearly."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"User message: {goal}\n"
                            f"Relevant memory:\n- {memory_block}"
                        ),
                    },
                ],
            )
        if llm_text == OLLAMA_UNAVAILABLE:
            keywords = sorted(
                {token for token in goal.lower().replace(",", " ").split() if len(token) > 3}
            )[:8]
            summary = (
                f"Ollama недоступен, поэтому это локальный stub-ответ. "
                f"Сообщение: '{goal}'. Memory={len(snippets)}. "
                f"Keywords={','.join(keywords) or 'none'}. "
                "Запусти Ollama и модель из LOCAL_AI_AGENT_MODEL_PRIMARY."
            )
            backend = "local"
            degraded = True
        else:
            summary = llm_text
            backend = "ollama"
            degraded = False
        observation = Observation(
            source="capability.reflect",
            summary=summary[:500],
            details={
                "goal": goal,
                "memory": snippets[:5],
                "llm": llm_text[:1000],
                "backend": backend,
                "degraded": degraded,
                "model": model,
            },
        )
        return ActionResult(
            action=action,
            success=True,
            message=summary[:4000],
            observations=[observation],
        )


def _failed(action: Action, message: str) -> ActionResult:
    observation = Observation(
        source="capability.error",
        summary=message,
        details={"action": action.name},
    )
    return ActionResult(
        action=action,
        success=False,
        message=message,
        observations=[observation],
    )
