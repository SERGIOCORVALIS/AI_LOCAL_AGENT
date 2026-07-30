from __future__ import annotations

import logging
from enum import StrEnum

from packages.config import Settings
from packages.core import Action, ActionResult, Observation, Task
from packages.memory import MemoryKind
from packages.routing import TaskRouter
from packages.safety import AuditEvent, AuditLogger, PolicyEngine
from services.memory import build_memory_backend
from services.observability import configure_logging
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
    """Minimal runtime skeleton for the agent state machine."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        configure_logging(settings)
        settings.backup_dir.mkdir(parents=True, exist_ok=True)
        self._policy_engine = PolicyEngine(settings.allowed_execute_actions)
        self._audit_logger = AuditLogger(settings.audit_log_path)
        self._task_store = TaskStore(settings.task_store_path)
        self._registry = CapabilityRegistry()
        self._memory_store = build_memory_backend(settings)
        self._router = TaskRouter()
        self._swarm = SwarmCoordinator(self._router)
        self._registry.register("noop", self._execute_noop)

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def registry(self) -> CapabilityRegistry:
        return self._registry

    def resume_task(self, task_id: str) -> Task | None:
        return self._task_store.load(task_id)

    def run_task(self, task: Task) -> ActionResult:
        task.mark_running()
        action = task.actions[0] if task.actions else task_default_action()
        policy_decision = self._policy_engine.evaluate(action)
        phases = [phase.value for phase in RuntimePhase]
        route = self._router.route(task)
        memory_hits = self._memory_store.retrieve(task.goal)
        LOGGER.info(
            "Running task",
            extra={
                "task_id": str(task.id),
                "correlation_id": str(task.correlation_id),
                "goal": task.goal,
            },
        )
        self._audit_logger.write(
            AuditEvent(
                event_type="task.started",
                actor="orchestrator",
                summary=f"Task '{task.title}' entered runtime.",
                details={
                    "task_id": str(task.id),
                    "correlation_id": str(task.correlation_id),
                    "action": action.name,
                    "phases": phases,
                    "policy_verdict": policy_decision.verdict,
                    "route_target": route.target_model,
                    "memory_hits": len(memory_hits),
                },
            )
        )
        self._task_store.save(task)

        if policy_decision.required_approval:
            observation = Observation(
                source="policy",
                summary="Task paused pending human approval.",
                details={
                    "reason": policy_decision.reason,
                    "action": action.name,
                    "phase": "plan",
                },
            )
            task.observations.append(observation)
            task.mark_failed(observation)
            self._task_store.save(task)
            return ActionResult(
                action=action,
                success=False,
                message=policy_decision.reason,
                observations=[observation],
                policy_decision=policy_decision,
            )

        execution_result = self._execute_action(action)
        dispatch = self._swarm.dispatch(task)
        observation = Observation(
            source="orchestrator",
            summary="Task executed by runtime lifecycle.",
            details={
                "actions": len(task.actions),
                "env": self._settings.env,
                "phase": "observe",
                "execution_message": execution_result.message,
                "route": route.model_dump(mode="json"),
                "swarm_roles": dispatch.role_outputs,
                "memory": [
                    item.model_dump(mode="json")
                    for item in memory_hits
                ],
            },
        )
        task.observations.extend(
            [*dispatch.observations, *execution_result.observations, observation]
        )
        if execution_result.success:
            task.mark_succeeded()
            self._memory_store.remember(
                kind=MemoryKind.EPISODE,
                key=task.title,
                value=task.goal,
                tags=["runtime", route.tier.value],
            )
        else:
            task.mark_failed(observation)
        self._task_store.save(task)
        self._audit_logger.write(
            AuditEvent(
                event_type="task.finished",
                actor="orchestrator",
                summary=f"Task '{task.title}' finished runtime lifecycle.",
                details={
                    "task_id": str(task.id),
                    "success": execution_result.success,
                    "phase": "persist",
                },
            )
        )

        return ActionResult(
            action=action,
            success=execution_result.success,
            message=execution_result.message,
            artifacts=execution_result.artifacts,
            observations=[
                *dispatch.observations,
                *execution_result.observations,
                observation,
            ],
            policy_decision=policy_decision,
        )

    def _execute_action(self, action: Action) -> ActionResult:
        if self._registry.has(action.name):
            return self._registry.execute(action)
        return self._execute_noop(action)

    def _execute_noop(self, action: Action) -> ActionResult:
        observation = Observation(
            source="capability.noop",
            summary="No-op capability executed.",
            details={"action": action.name, "mode": action.mode},
        )
        return ActionResult(
            action=action,
            success=True,
            message=(
                f"Action '{action.name}' executed by runtime."
            ),
            observations=[observation],
        )


def task_default_action() -> Action:
    return Action(
        name="noop",
        description="Default action for foundational runtime.",
    )
