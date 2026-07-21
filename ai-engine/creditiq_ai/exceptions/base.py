"""Custom exception hierarchy for the CreditIQ AI engine.

Purpose:  Typed, structured errors so callers can distinguish failure modes and surface
          machine-readable diagnostics. Every module raises from this hierarchy — never bare
          Exception.
Inputs:   a human message + optional structured context + optional error code.
Outputs:  exception instances with `.to_dict()` for logging / API surfaces.
Deps:     stdlib only.
Extend:   subclass CreditIQError (or a category base) for a new failure type.
"""

from __future__ import annotations

from typing import Any


class CreditIQError(Exception):
    """Root of all engine exceptions.

    Carries an optional ``context`` mapping (structured diagnostic data) and a stable
    ``error_code`` (defaults to the class name) suitable for logs and future API responses.
    """

    default_code: str = "creditiq_error"

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.error_code = error_code or self.default_code

    def to_dict(self) -> dict[str, Any]:
        """Machine-readable representation for structured logging / responses."""
        return {
            "error_code": self.error_code,
            "type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
        }

    def __str__(self) -> str:
        if self.context:
            return f"[{self.error_code}] {self.message} | context={self.context}"
        return f"[{self.error_code}] {self.message}"


# --------------------------------------------------------------------------- configuration
class ConfigurationError(CreditIQError):
    """Invalid, missing, or contradictory configuration."""

    default_code = "configuration_error"


# --------------------------------------------------------------------------- data
class DataLoadingError(CreditIQError):
    """A data source could not be read or produced a malformed frame."""

    default_code = "data_loading_error"


class ValidationError(CreditIQError):
    """A data validation rule failed (schema, nulls, duplicates, dtypes, outliers)."""

    default_code = "validation_error"


class SchemaError(ValidationError):
    """Dataset does not conform to its declared schema."""

    default_code = "schema_error"


# --------------------------------------------------------------------------- pipeline stages
class PreprocessingError(CreditIQError):
    """A preprocessing transformer failed."""

    default_code = "preprocessing_error"


class FeatureEngineeringError(CreditIQError):
    """A feature generator failed or a required input was missing."""

    default_code = "feature_engineering_error"


class PipelineError(CreditIQError):
    """A pipeline stage failed or stages were wired incorrectly."""

    default_code = "pipeline_error"


# --------------------------------------------------------------------------- modelling (future)
class ModelTrainingError(CreditIQError):
    """Model training / tuning failed."""

    default_code = "model_training_error"


class PredictionError(CreditIQError):
    """Inference / prediction failed."""

    default_code = "prediction_error"


class FraudDetectionError(CreditIQError):
    """A fraud / anomaly detector failed."""

    default_code = "fraud_detection_error"


class ExplainabilityError(CreditIQError):
    """Explanation generation failed."""

    default_code = "explainability_error"


class RegistryError(CreditIQError):
    """A model could not be saved to or loaded from the registry."""

    default_code = "registry_error"


class ModelNotFittedError(CreditIQError):
    """An operation requiring a fitted component was attempted before fit()."""

    default_code = "model_not_fitted_error"


# --------------------------------------------------------------------------- model operations
class ModelRegistryError(CreditIQError):
    """Base for model-registry operation failures (Sprint 8)."""

    default_code = "model_registry_error"


class ModelNotFoundError(ModelRegistryError):
    """Requested model or model version does not exist."""

    default_code = "model_not_found_error"


class ModelVersionConflictError(ModelRegistryError):
    """A model version already exists / violates uniqueness."""

    default_code = "model_version_conflict_error"


class ArtifactIntegrityError(ModelRegistryError):
    """An artifact is missing, corrupted, checksum-mismatched, or an unsupported format."""

    default_code = "artifact_integrity_error"


class InvalidLifecycleTransitionError(ModelRegistryError):
    """An illegal model lifecycle state transition was requested."""

    default_code = "invalid_lifecycle_transition_error"


class PromotionRejectedError(ModelRegistryError):
    """A model failed its configured promotion policy."""

    default_code = "promotion_rejected_error"


class RollbackError(ModelRegistryError):
    """A rollback could not be completed safely."""

    default_code = "rollback_error"


class LineageError(ModelRegistryError):
    """Invalid or circular model lineage."""

    default_code = "lineage_error"


class MonitoringError(CreditIQError):
    """Base for monitoring-subsystem failures."""

    default_code = "monitoring_error"


class DriftDetectionError(MonitoringError):
    """A drift detector failed or received incompatible data."""

    default_code = "drift_detection_error"


class PerformanceMonitoringError(MonitoringError):
    """Performance monitoring failed."""

    default_code = "performance_monitoring_error"


class AlertError(MonitoringError):
    """An alert could not be created / updated."""

    default_code = "alert_error"


class AuditError(CreditIQError):
    """An audit record could not be written or was tampered with."""

    default_code = "audit_error"
