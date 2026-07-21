"""Cleaner factory (Factory pattern).

Purpose:  Build cleaner strategies by name so the engine is config-driven and open/closed.
Inputs:   cleaner name + params.
Outputs:  BaseCleaner instances.
Deps:     cleaners module, exceptions.
Extend:   register("my_cleaner")(MyCleaner) — no change to the engine.
"""

from __future__ import annotations

from creditiq_ai.exceptions import PreprocessingError
from creditiq_ai.preprocessing.cleaning.base import BaseCleaner
from creditiq_ai.preprocessing.cleaning import cleaners as c

_REGISTRY: dict[str, type[BaseCleaner]] = {}


def register(name: str):
    def _wrap(cls: type[BaseCleaner]) -> type[BaseCleaner]:
        _REGISTRY[name] = cls
        return cls

    return _wrap


class CleanerFactory:
    """Creates cleaners registered by name."""

    @staticmethod
    def create(name: str, params: dict | None = None) -> BaseCleaner:
        if name not in _REGISTRY:
            raise PreprocessingError(
                f"Unknown cleaner '{name}'", context={"available": sorted(_REGISTRY)}
            )
        return _REGISTRY[name](params=params or {})

    @staticmethod
    def available() -> list[str]:
        return sorted(_REGISTRY)


# Register built-in cleaners (name used in YAML → strategy class).
register("whitespace")(c.WhitespaceCleaner)
register("standardize_missing")(c.MissingValueStandardizer)
register("drop_duplicates")(c.DuplicateRemover)
register("correct_dtypes")(c.DatatypeCorrector)
register("categorical_cleanup")(c.CategoricalCleanup)
register("currency")(c.CurrencyNormalizer)
register("percentage")(c.PercentageNormalizer)
register("boolean")(c.BooleanNormalizer)
register("date")(c.DateNormalizer)
register("invalid_values")(c.InvalidValueDetector)
register("consistency")(c.ConsistencyChecker)
