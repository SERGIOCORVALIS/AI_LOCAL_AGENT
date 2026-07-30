from __future__ import annotations

from enum import StrEnum

from packages.core import Action, ActionMode, PolicyDecision, PolicyVerdict


class ActionSensitivity(StrEnum):
    SAFE = "safe"
    SENSITIVE = "sensitive"
    DESTRUCTIVE = "destructive"
    PRIVILEGED = "privileged"


class PolicyEngine:
    """Policy layer for guarding side-effectful actions."""

    def __init__(
        self,
        allowed_execute_actions: set[str] | None = None,
    ) -> None:
        self._allowed_execute_actions = {
            action_name.lower()
            for action_name in (allowed_execute_actions or set())
        }

    def classify(self, action: Action) -> ActionSensitivity:
        side_effects = {effect.lower() for effect in action.side_effects}
        if {"admin", "privileged", "elevated"} & side_effects:
            return ActionSensitivity.PRIVILEGED
        if {"delete", "overwrite", "move", "write"} & side_effects:
            return ActionSensitivity.DESTRUCTIVE
        if side_effects:
            return ActionSensitivity.SENSITIVE
        return ActionSensitivity.SAFE

    def evaluate(self, action: Action) -> PolicyDecision:
        sensitivity = self.classify(action)
        normalized_name = action.name.lower()

        if action.mode == ActionMode.OBSERVE:
            return PolicyDecision(
                verdict=PolicyVerdict.ALLOW,
                reason="Observe mode does not permit side effects.",
                tags=[sensitivity.value, action.mode.value],
            )

        if action.mode == ActionMode.SUGGEST:
            return PolicyDecision(
                verdict=PolicyVerdict.ALLOW,
                reason="Suggest mode only proposes work.",
                tags=[sensitivity.value, action.mode.value],
            )

        if action.mode == ActionMode.DRY_RUN:
            return PolicyDecision(
                verdict=PolicyVerdict.ALLOW,
                reason="Dry-run mode is allowed with reporting only.",
                tags=[sensitivity.value, action.mode.value],
            )

        if (
            self._allowed_execute_actions
            and normalized_name not in self._allowed_execute_actions
        ):
            return PolicyDecision(
                verdict=PolicyVerdict.REQUIRE_APPROVAL,
                reason=(
                    "Execute mode requires approval for actions outside "
                    "the local allowlist."
                ),
                required_approval=True,
                tags=[sensitivity.value, action.mode.value, "allowlist"],
            )

        if sensitivity in {
            ActionSensitivity.DESTRUCTIVE,
            ActionSensitivity.PRIVILEGED,
        }:
            return PolicyDecision(
                verdict=PolicyVerdict.REQUIRE_APPROVAL,
                reason=(
                    "Execute mode requires approval for destructive or "
                    "privileged actions."
                ),
                required_approval=True,
                tags=[sensitivity.value, action.mode.value],
            )

        if sensitivity == ActionSensitivity.SENSITIVE:
            return PolicyDecision(
                verdict=PolicyVerdict.REQUIRE_APPROVAL,
                reason="Execute mode requires approval for sensitive actions.",
                required_approval=True,
                tags=[sensitivity.value, action.mode.value],
            )

        return PolicyDecision(
            verdict=PolicyVerdict.ALLOW,
            reason="Safe execute action permitted.",
            tags=[sensitivity.value, action.mode.value],
        )
