"""Model lifecycle state machine.

Purpose:  Enforce the legal model lifecycle transitions (State Machine principles). Every promotion,
          demotion, archival, rejection, or retirement goes through here, guaranteeing invalid
          transitions raise a domain-specific error rather than silently corrupting state.
Inputs:   current stage + target stage.
Outputs:  validated transition (or raises InvalidLifecycleTransitionError).
Deps:     model_operations.domain (LIFECYCLE_TRANSITIONS); exceptions.
"""

from __future__ import annotations

from creditiq_ai.core.base import BaseComponent
from creditiq_ai.exceptions import InvalidLifecycleTransitionError
from creditiq_ai.model_operations.domain import LIFECYCLE_TRANSITIONS, LifecycleStage


class LifecycleStateMachine(BaseComponent):
    """Validates model lifecycle stage transitions against the legal transition graph."""

    def allowed_transitions(self, stage: LifecycleStage) -> set[LifecycleStage]:
        return LIFECYCLE_TRANSITIONS.get(stage, set())

    def can_transition(self, current: LifecycleStage, target: LifecycleStage) -> bool:
        return target in self.allowed_transitions(current)

    def is_terminal(self, stage: LifecycleStage) -> bool:
        return len(self.allowed_transitions(stage)) == 0

    def validate_transition(self, current: LifecycleStage, target: LifecycleStage) -> None:
        """Raise if the transition is illegal; otherwise return None."""
        if current == target:
            raise InvalidLifecycleTransitionError(
                f"No-op transition: already in '{current.value}'",
                context={"current": current.value, "target": target.value},
            )
        if not self.can_transition(current, target):
            allowed = sorted(s.value for s in self.allowed_transitions(current))
            raise InvalidLifecycleTransitionError(
                f"Illegal lifecycle transition '{current.value}' → '{target.value}'",
                context={"current": current.value, "target": target.value, "allowed": allowed},
            )
        self.logger.info(f"Lifecycle transition validated: {current.value} → {target.value}")
