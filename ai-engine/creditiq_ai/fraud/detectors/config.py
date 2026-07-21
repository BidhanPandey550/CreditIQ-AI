"""Fraud detection configuration.

Purpose:  Keep configuration on the single unified surface (Sprint 3.5 rule). The fraud framework
          is configured by `EngineConfig.fraud` (detectors + params + vote_threshold); this module
          exposes it under the framework's expected name via a type alias — no duplicate config.
Deps:     config.models.FraudConfig.
"""

from __future__ import annotations

from creditiq_ai.config.models import DetectorSpec, FraudConfig

# The framework's config IS the unified EngineConfig.fraud slice.
FraudDetectionConfig = FraudConfig

__all__ = ["FraudDetectionConfig", "FraudConfig", "DetectorSpec"]
