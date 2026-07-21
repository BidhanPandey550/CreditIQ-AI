"""Explainer registry (Registry pattern) with priority ordering.

Purpose:  Map explainer names → classes with a priority, so the factory can pick the highest-
          priority explainer that supports a given model (SHAP > model-specific > agnostic).
Deps:     explainers.base.
Extend:   @register("name", priority=N) on a BaseLocalExplainer subclass.
"""

from __future__ import annotations

from typing import Callable

from creditiq_ai.explainability.explainers.base import BaseLocalExplainer

_REGISTRY: dict[str, tuple[int, type[BaseLocalExplainer]]] = {}


def register(
    name: str, priority: int
) -> Callable[[type[BaseLocalExplainer]], type[BaseLocalExplainer]]:
    def _wrap(cls: type[BaseLocalExplainer]) -> type[BaseLocalExplainer]:
        _REGISTRY[name] = (priority, cls)
        return cls

    return _wrap


def registered_by_priority() -> list[tuple[str, type[BaseLocalExplainer]]]:
    """Highest priority first."""
    return [
        (name, cls)
        for name, (_, cls) in sorted(_REGISTRY.items(), key=lambda kv: kv[1][0], reverse=True)
    ]


def available_explainers() -> list[str]:
    return sorted(_REGISTRY)
