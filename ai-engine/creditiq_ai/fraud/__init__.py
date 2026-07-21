"""creditiq_ai.fraud — the Fraud Intelligence Engine (Sprint 5).

Module 1 (Detection Framework) public API. Importing this package registers built-in detectors.

    from creditiq_ai.config import load_config
    from creditiq_ai.fraud import FraudDetectionPipeline
    cfg = load_config()
    pipeline = FraudDetectionPipeline(cfg.fraud).fit(reference_X)
    results = pipeline.analyze(new_X)          # list[FraudDetectionResult]
"""

from creditiq_ai.fraud import algorithms  # noqa: F401  (registers detectors)
from creditiq_ai.fraud.detectors.base import BaseFraudDetector
from creditiq_ai.fraud.detectors.config import FraudDetectionConfig
from creditiq_ai.fraud.detectors.factory import FraudDetectionFactory
from creditiq_ai.fraud.detectors.registry import available_detectors, register
from creditiq_ai.fraud.detectors.result import FraudDetectionResult
from creditiq_ai.fraud.pipelines.pipeline import FraudDetectionPipeline

__all__ = [
    "BaseFraudDetector",
    "FraudDetectionConfig",
    "FraudDetectionResult",
    "FraudDetectionFactory",
    "FraudDetectionPipeline",
    "register",
    "available_detectors",
]
