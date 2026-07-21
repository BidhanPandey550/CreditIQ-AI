"""FraudDetectionFactory — Factory pattern for building detectors from config.

Purpose:  Instantiate a detector by name + params so the pipeline stays config-driven and
          unaware of concrete detector classes.
Deps:     detectors.registry, detectors.base.
"""

from __future__ import annotations

from creditiq_ai.fraud.detectors.base import BaseFraudDetector
from creditiq_ai.fraud.detectors.registry import (
    available_detectors,
    get_detector_class,
    is_registered,
)


class FraudDetectionFactory:
    @staticmethod
    def create(name: str, params: dict | None = None) -> BaseFraudDetector:
        return get_detector_class(name)(params or {})

    @staticmethod
    def available() -> list[str]:
        return available_detectors()

    @staticmethod
    def supports(name: str) -> bool:
        return is_registered(name)
