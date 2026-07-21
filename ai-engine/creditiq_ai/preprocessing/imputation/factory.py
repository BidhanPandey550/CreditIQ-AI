"""Imputer factory (Factory pattern).

Purpose:  Build imputation strategies by name so the engine is fully config-driven.
Inputs:   strategy name + params.
Outputs:  BaseImputer instances.
Deps:     imputers module, exceptions.
Extend:   register("my_strategy")(MyImputer).
"""

from __future__ import annotations

from creditiq_ai.exceptions import PreprocessingError
from creditiq_ai.preprocessing.imputation import imputers as im
from creditiq_ai.preprocessing.imputation.base import BaseImputer

_REGISTRY: dict[str, type[BaseImputer]] = {}


def register(name: str):
    def _wrap(cls: type[BaseImputer]) -> type[BaseImputer]:
        _REGISTRY[name] = cls
        return cls

    return _wrap


class ImputerFactory:
    @staticmethod
    def create(name: str, params: dict | None = None) -> BaseImputer:
        if name not in _REGISTRY:
            raise PreprocessingError(
                f"Unknown imputation strategy '{name}'", context={"available": sorted(_REGISTRY)}
            )
        return _REGISTRY[name](params=params or {})

    @staticmethod
    def strategy_class(name: str) -> type[BaseImputer]:
        if name not in _REGISTRY:
            raise PreprocessingError(
                f"Unknown imputation strategy '{name}'", context={"available": sorted(_REGISTRY)}
            )
        return _REGISTRY[name]

    @staticmethod
    def available() -> list[str]:
        return sorted(_REGISTRY)


register("mean")(im.MeanImputer)
register("median")(im.MedianImputer)
register("mode")(im.ModeImputer)
register("constant")(im.ConstantImputer)
register("ffill")(im.ForwardFillImputer)
register("bfill")(im.BackwardFillImputer)
register("knn")(im.KNNImputerStrategy)
register("iterative")(im.IterativeImputerStrategy)
