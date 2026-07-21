"""Explainer factory — selects the best supported explainer for a model (graceful fallback).

Purpose:  Encapsulate "which explainer to use": try the highest-priority explainer whose
          `supports(ctx)` is True, guaranteeing a model-appropriate strategy every time.
Deps:     explainers.registry / .base; exceptions.
"""

from __future__ import annotations

from creditiq_ai.exceptions import ExplainabilityError
from creditiq_ai.explainability.explainers.base import (
    BaseLocalExplainer,
    ExplanationContext,
)
from creditiq_ai.explainability.explainers.registry import (
    available_explainers,
    registered_by_priority,
)


class ExplainerFactory:
    @staticmethod
    def select(ctx: ExplanationContext) -> BaseLocalExplainer:
        for _name, cls in registered_by_priority():
            explainer = cls()
            if explainer.supports(ctx):
                return explainer
        raise ExplainabilityError(
            "No explainer supports this context", context={"available": available_explainers()}
        )

    @staticmethod
    def available() -> list[str]:
        return available_explainers()
