"""TrainingRegistry — Registry pattern for algorithm trainer types.

Purpose:  Map an algorithm name to its BaseTrainer subclass so new algorithms are added by
          registration only (open/closed). The TrainingFactory reads this registry.
Inputs:   register() decorator calls (from algorithm modules).
Outputs:  trainer classes by name.
Deps:     trainers.base.BaseTrainer; exceptions.
Extend:   @register("my_algo") on a BaseTrainer subclass.
"""

from __future__ import annotations

from typing import Callable

from creditiq_ai.credit_intelligence.trainers.base import BaseTrainer
from creditiq_ai.exceptions import ModelTrainingError

_REGISTRY: dict[str, type[BaseTrainer]] = {}


def register(name: str) -> Callable[[type[BaseTrainer]], type[BaseTrainer]]:
    def _wrap(cls: type[BaseTrainer]) -> type[BaseTrainer]:
        _REGISTRY[name] = cls
        return cls

    return _wrap


def get_trainer_class(name: str) -> type[BaseTrainer]:
    if name not in _REGISTRY:
        raise ModelTrainingError(
            f"No trainer registered for '{name}'", context={"available": sorted(_REGISTRY)}
        )
    return _REGISTRY[name]


def available_algorithms() -> list[str]:
    return sorted(_REGISTRY)


def is_registered(name: str) -> bool:
    return name in _REGISTRY
