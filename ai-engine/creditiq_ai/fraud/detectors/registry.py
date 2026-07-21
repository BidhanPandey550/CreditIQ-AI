"""FraudDetectionRegistry — Registry pattern for detector types.

Purpose:  Map a detector name to its BaseFraudDetector subclass so new detectors are added by
          registration only (open/closed). The factory reads this registry.
Deps:     detectors.base; exceptions.
Extend:   @register("my_detector") on a BaseFraudDetector subclass.
"""

from __future__ import annotations

from creditiq_ai.exceptions import FraudDetectionError
from creditiq_ai.fraud.detectors.base import BaseFraudDetector

_REGISTRY: dict[str, type[BaseFraudDetector]] = {}


def register(name: str):
    def _wrap(cls: type[BaseFraudDetector]) -> type[BaseFraudDetector]:
        _REGISTRY[name] = cls
        return cls

    return _wrap


def get_detector_class(name: str) -> type[BaseFraudDetector]:
    if name not in _REGISTRY:
        raise FraudDetectionError(
            f"No detector registered for '{name}'", context={"available": sorted(_REGISTRY)}
        )
    return _REGISTRY[name]


def available_detectors() -> list[str]:
    return sorted(_REGISTRY)


def is_registered(name: str) -> bool:
    return name in _REGISTRY
