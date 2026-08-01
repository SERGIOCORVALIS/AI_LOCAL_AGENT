from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from enum import StrEnum

from packages.config import Settings
from packages.core import Action, ActionResult, Observation, PolicyVerdict, Task, TaskState
from packages.memory import MemoryItem, MemoryKind
from packages.routing import TaskRouter
from packages.safety import AuditEvent, AuditLogger, PolicyEngine
from services.channels import ChannelGateway
from services.integrations.coding_agents import CodingAgentsAdapter
from services.llm import (
    AgentModelConfig,
    OllamaClient,
    ResolvedAgents,
    agents_from_settings,
    resolve_agents,
)
from services.memory import build_memory_backend
from services.memory.protocol import MemoryBackend
from services.observability import configure_logging
from services.orchestrator.capabilities import CapabilityHandlers, plan_actions_for_goal
from services.orchestrator.registry import CapabilityRegistry
from services.orchestrator.store import TaskStore
from services.swarm import SwarmCoordinator

LOGGER = logging.getLogger(__name__)


class RuntimePhase(StrEnum):
    INGEST = "ingest"
    PLAN = "plan"
    ACT = "act"
    OBSERVE = "observe"
    REFLECT = "reflect"
    PERSIST = "persist"


class OrchestratorRuntime:
    """Full local runtime lifecycle with concrete capability execution."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        configure_logging(settings)
        settings.backup_dir.mkdir(parents=True, exist_ok=True)
        self._policy_engine = PolicyEngine(
            settings.allowed_execute_actions,
            denied_execute_actions=settings.denied_execute_actions,
        )
        self._audit_logger = AuditLogger(settings.audit_log_path)
        self._task_store = TaskStore(settings.task_store_path)
        self._registry = CapabilityRegistry()
        self._approval_gateway = ChannelGateway(
            approval_log_path=settings.backup_dir / "approvals" / "events.jsonl"
        )
        self._memory_store = build_memory_backend(settings)
        # Keep unit tests offline even when a local Ollama daemon is running.
        if "pytest" in sys.modules:
            self._ollama = OllamaClient(base_url="http://127.0.0.1:9", timeout=0.5)
        else:
            self._ollama = OllamaClient(base_url=settings.ollama_url, timeout=300.0)
        configured = agents_from_settings(
            primary=settings.model_primary,
            router=settings.model_router,
            vision=settings.model_vision,
            embed=settings.model_embed,
        )
        self._agents = resolve_agents(self._ollama, configured)
        models = self._agents.resolved
        if self._agents.online and models != configured:
            LOGGER.info(
                "Resolved Ollama agent models: %s -> %s",
                configured.as_dict(),
                models.as_dict(),
            )
        self._router = TaskRouter(
            primary_model=models.primary,
            router_model=models.router,
            ollama_client=self._ollama,
        )
        self._swarm = SwarmCoordinator(
            self._router,
            ollama_client=self._ollama,
            model=models.primary,
            router_model=models.router,
            agents=models,
        )
        # Keep unit tests on the local scrubbed path even if Docker is installed.
        prefer_docker = False if "pytest" in sys.modules else settings.sandbox_prefer_docker
        coding_model = (settings.coding_agent_model or models.primary).strip() or models.primary
        self._coding_agents = CodingAgentsAdapter(
            default_agent=settings.coding_agent_default,
            model=coding_model,
            timeout_seconds=settings.coding_agent_timeout_seconds,
            enabled=settings.coding_agents_enabled and "pytest" not in sys.modules,
        )
        self._capabilities = CapabilityHandlers(
            settings.downloads_watch_path,
            prefer_docker=prefer_docker,
            ollama_client=self._ollama,
            vision_model=models.vision,
            chat_model=models.primary,
            coding_agents=self._coding_agents,
        )
        self._register_capabilities()

    def _register_capabilities(self) -> None:
        self._registry.register("noop", self._execute_noop)
        self._registry.register("bootstrap", self._execute_bootstrap)
        self._registry.register("sandbox_run", self._capabilities.sandbox_run)
        self._registry.register("web_fetch", self._capabilities.web_fetch)
        self._registry.register("web_search", self._capabilities.web_search)
        self._registry.register("write_file", self._capabilities.write_file)
        self._registry.register("coding_agent", self._capabilities.coding_agent)
        self._registry.register("code_intel", self._capabilities.code_intel)
        self._registry.register("fs_scan", self._capabilities.fs_scan)
        self._registry.register("fs_watch", self._capabilities.fs_watch)
        self._registry.register("vision_inspect", self._capabilities.vision_inspect)
        self._registry.register("browser_open", self._capabilities.browser_open)
        self._registry.register("reflect", self._execute_reflect)

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def registry(self) -> CapabilityRegistry:
        return self._registry

    @property
    def capabilities(self) -> CapabilityHandlers:
        return self._capabilities

    @property
    def ollama(self) -> OllamaClient:
        return self._ollama

    @property
    def agents(self) -> ResolvedAgents:
        return self._agents

    @property
    def agent_models(self) -> AgentModelConfig:
        return self._agents.resolved

    @property
    def memory_store(self) -> MemoryBackend:
        return self._memory_store

    def refresh_agents(self) -> ResolvedAgents:
        """Re-probe Ollama so status/chat recover after daemon restarts."""
        self._ollama.invalidate_ping()
        configured = agents_from_settings(
            primary=self._settings.model_primary,
            router=self._settings.model_router,
            vision=self._settings.model_vision,
            embed=self._settings.model_embed,
        )
        self._agents = resolve_agents(self._ollama, configured)
        models = self._agents.resolved
        self._router._primary_model = models.primary
        self._router._router_model = models.router
        self._swarm._agents = models
        self._capabilities._chat_model = models.primary
        return self._agents

    def resume_task(self, task_id: str) -> Task | None:
        return self._task_store.load(task_id)

    def continue_task(
        self,
        task_id: str,
        *,
        approved: bool,
        reviewer: str = "operator",
    ) -> ActionResult:
        task = self._task_store.load(task_id)
        if task is None:
            missing = Action(name="noop", description="missing task")
            return ActionResult(
                action=missing,
                success=False,
                message=f"Task '{task_id}' was not found.",
            )
        if task.state != TaskState.AWAITING_APPROVAL:
            action = task.actions[0] if task.actions else Action(name="noop", description="idle")
            return ActionResult(
                action=action,
                success=False,
                message=(
                    f"Task '{task_id}' is not awaiting approval "
                    f"(state={task.state.value})."
                ),
            )

        self._approval_gateway.record_approval(str(task.id), reviewer, approved)
        pending_index = task.resume_from_index
        if pending_index is None or pending_index < 0 or pending_index >= len(task.actions):
            observation = Observation(
                source="policy",
                summary="Approval resume failed: missing pending action index.",
                details={"task_id": task_id},
            )
            task.mark_failed(observation)
            self._task_store.save(task)
            return ActionResult(
                action=Action(name="noop", description="invalid resume"),
                success=False,
                message=observation.summary,
                observations=[observation],
            )

        pending_action = task.actions[pending_index]
        if not approved:
            observation = Observation(
                source="policy",
                summary="Human rejected pending action; task cancelled.",
                details={
                    "task_id": task_id,
                    "action": pending_action.name,
                    "reviewer": reviewer,
                },
            )
            task.mark_cancelled(observation)
            self._task_store.save(task)
            self._audit_logger.write(
                AuditEvent(
                    event_type="task.cancelled",
                    actor=reviewer,
                    summary=observation.summary,
                    details={"task_id": task_id, "action": pending_action.name},
                )
            )
            return ActionResult(
                action=pending_action,
                success=False,
                message=observation.summary,
                observations=[observation],
            )

        if pending_index not in task.approved_action_indexes:
            task.approved_action_indexes.append(pending_index)
        task.resume_from_index = None
        self._audit_logger.write(
            AuditEvent(
                event_type="task.approved",
                actor=reviewer,
                summary=f"Action '{pending_action.name}' approved for resume.",
                details={"task_id": task_id, "action_index": pending_index},
            )
        )
        return self.run_task(task, start_index=pending_index, replan=False)

    def run_task(
        self,
        task: Task,
        *,
        start_index: int = 0,
        replan: bool = True,
    ) -> ActionResult:
        from services.observability import clear_correlation_id, set_correlation_id

        set_correlation_id(str(task.correlation_id))
        try:
            return self._run_task_body(task, start_index=start_index, replan=replan)
        finally:
            clear_correlation_id()

    def _run_task_body(
        self,
        task: Task,
        *,
        start_index: int = 0,
        replan: bool = True,
    ) -> ActionResult:
        if not self._agents.online:
            self.refresh_agents()
        task.mark_running()
        memory_hits = self._memory_store.retrieve(task.goal, limit=5)
        if replan and start_index <= 0:
            planned = self._ensure_actions(task, memory_hits)
            task.actions = planned
        route = self._router.route(task)

        self._audit_logger.write(
            AuditEvent(
                event_type="task.started" if start_index <= 0 else "task.resumed",
                actor="orchestrator",
                summary=f"Task '{task.title}' entered runtime.",
                details={
                    "task_id": str(task.id),
                    "correlation_id": str(task.correlation_id),
                    "actions": [action.name for action in task.actions],
                    "phases": [phase.value for phase in RuntimePhase],
                    "route_target": route.target_model,
                    "memory_hits": len(memory_hits),
                    "start_index": start_index,
                    "memory_context": [
                        f"{item.key}:{item.value}" for item in memory_hits[:3]
                    ],
                },
            )
        )
        self._task_store.save(task)

        results: list[ActionResult] = []
        for index, action in enumerate(task.actions):
            if index < start_index:
                continue
            policy_decision = self._policy_engine.evaluate(action)
            if policy_decision.verdict == PolicyVerdict.DENY:
                observation = Observation(
                    source="policy",
                    summary="Action denied by policy.",
                    details={
                        "reason": policy_decision.reason,
                        "action": action.name,
                        "phase": RuntimePhase.PLAN.value,
                    },
                )
                task.mark_failed(observation)
                self._task_store.save(task)
                return ActionResult(
                    action=action,
                    success=False,
                    message=policy_decision.reason,
                    observations=[observation],
                    policy_decision=policy_decision,
                )

            approved_once = index in task.approved_action_indexes
            if policy_decision.required_approval and not approved_once:
                observation = Observation(
                    source="policy",
                    summary="Task paused pending human approval.",
                    details={
                        "reason": policy_decision.reason,
                        "action": action.name,
                        "action_index": index,
                        "phase": RuntimePhase.PLAN.value,
                    },
                )
                task.mark_awaiting_approval(observation, index)
                self._task_store.save(task)
                return ActionResult(
                    action=action,
                    success=False,
                    message=policy_decision.reason,
                    observations=[observation],
                    policy_decision=policy_decision,
                )

            result = self._execute_action(action, memory_hits)
            results.append(result)
            task.observations.extend(result.observations)
            if not result.success:
                task.mark_failed(
                    Observation(
                        source="orchestrator",
                        summary="Action failed during ACT phase.",
                        details={"action": action.name, "message": result.message},
                    )
                )
                self._task_store.save(task)
                return result

        dispatch = self._swarm.dispatch(task)
        final = results[-1] if results else self._execute_noop(task_default_action())
        observation = Observation(
            source="orchestrator",
            summary="Task executed by runtime lifecycle.",
            details={
                "actions": [action.name for action in task.actions],
                "env": self._settings.env,
                "phase": RuntimePhase.OBSERVE.value,
                "execution_message": final.message,
                "route": route.model_dump(mode="json"),
                "swarm_roles": dispatch.role_outputs,
                "memory": [item.model_dump(mode="json") for item in memory_hits],
            },
        )
        task.observations.extend([*dispatch.observations, observation])
        task.mark_succeeded()
        self._memory_store.remember(
            kind=MemoryKind.EPISODE,
            key=task.title,
            value=task.goal,
            tags=["runtime", route.tier.value, *{action.name for action in task.actions}],
        )
        self._task_store.save(task)
        self._audit_logger.write(
            AuditEvent(
                event_type="task.finished",
                actor="orchestrator",
                summary=f"Task '{task.title}' finished runtime lifecycle.",
                details={
                    "task_id": str(task.id),
                    "success": True,
                    "phase": RuntimePhase.PERSIST.value,
                    "actions": [action.name for action in task.actions],
                },
            )
        )
        return ActionResult(
            action=final.action,
            success=True,
            message=final.message,
            artifacts=final.artifacts,
            observations=[
                *dispatch.observations,
                *final.observations,
                observation,
            ],
            policy_decision=None,
        )

    def _ensure_actions(
        self,
        task: Task,
        memory_hits: Sequence[MemoryItem],
    ) -> list[Action]:
        del memory_hits
        if not task.actions:
            return plan_actions_for_goal(task.goal, task.title)
        if len(task.actions) == 1 and task.actions[0].name in {"bootstrap", "noop"}:
            # Preserve explicitly supplied side-effectful stubs (approval tests, etc.).
            if task.actions[0].side_effects:
                return task.actions
            planned = plan_actions_for_goal(task.goal, task.title)
            return planned or task.actions
        return task.actions

    def _execute_action(
        self,
        action: Action,
        memory_hits: Sequence[MemoryItem],
    ) -> ActionResult:
        if action.name == "reflect":
            return self._execute_reflect(action, memory_hits)
        if self._registry.has(action.name):
            return self._registry.execute(action)
        observation = Observation(
            source="capability.missing",
            summary=f"No capability registered for '{action.name}'.",
            details={"action": action.name},
        )
        return ActionResult(
            action=action,
            success=False,
            message=f"Unknown capability '{action.name}'",
            observations=[observation],
        )

    def _execute_bootstrap(self, action: Action) -> ActionResult:
        planned = plan_actions_for_goal(
            str(action.payload.get("goal", action.description)),
            str(action.payload.get("title", "")),
        )
        observation = Observation(
            source="capability.bootstrap",
            summary="Bootstrap planned concrete actions.",
            details={"planned": [item.name for item in planned]},
        )
        return ActionResult(
            action=action,
            success=True,
            message=f"Bootstrap planned: {', '.join(item.name for item in planned)}",
            observations=[observation],
        )

    def _execute_reflect(
        self,
        action: Action,
        memory_hits: Sequence[MemoryItem] | None = None,
    ) -> ActionResult:
        snippets = [
            f"{item.key}:{item.value}"
            for item in (memory_hits or [])
        ]
        payload = dict(action.payload)
        payload.setdefault("model", self._agents.resolved.primary)
        mirrored = action.model_copy(update={"payload": payload})
        return self._capabilities.reflect(mirrored, snippets)

    def _execute_noop(self, action: Action) -> ActionResult:
        observation = Observation(
            source="capability.noop",
            summary="No-op capability executed.",
            details={"action": action.name, "mode": action.mode},
        )
        return ActionResult(
            action=action,
            success=True,
            message=f"Action '{action.name}' executed by runtime.",
            observations=[observation],
        )


def task_default_action() -> Action:
    return Action(
        name="noop",
        description="Default action for foundational runtime.",
    )
