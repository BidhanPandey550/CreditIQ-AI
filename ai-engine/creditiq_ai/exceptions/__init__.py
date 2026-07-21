"""creditiq_ai.exceptions — canonical, structured exception hierarchy.

Import errors from here (e.g. ``from creditiq_ai.exceptions import ValidationError``).
"""

from creditiq_ai.exceptions.base import (
    AlertError,
    ArtifactIntegrityError,
    AuditError,
    ConfigurationError,
    CreditIQError,
    DataLoadingError,
    DriftDetectionError,
    ExplainabilityError,
    FeatureEngineeringError,
    FraudDetectionError,
    InvalidLifecycleTransitionError,
    LineageError,
    ModelNotFittedError,
    ModelNotFoundError,
    ModelRegistryError,
    ModelTrainingError,
    ModelVersionConflictError,
    MonitoringError,
    PerformanceMonitoringError,
    PipelineError,
    PredictionError,
    PreprocessingError,
    PromotionRejectedError,
    RegistryError,
    RollbackError,
    SchemaError,
    ValidationError,
)

# Backward-compatible aliases for earlier module names (single source of truth lives above).
DataLoadError = DataLoadingError
DataValidationError = ValidationError
SchemaValidationError = SchemaError
InferenceError = PredictionError
ModelError = ModelTrainingError

__all__ = [
    "CreditIQError",
    "ConfigurationError",
    "DataLoadingError",
    "ValidationError",
    "SchemaError",
    "PreprocessingError",
    "FeatureEngineeringError",
    "PipelineError",
    "ModelTrainingError",
    "PredictionError",
    "FraudDetectionError",
    "ExplainabilityError",
    "RegistryError",
    "ModelNotFittedError",
    # model operations (Sprint 8)
    "ModelRegistryError",
    "ModelNotFoundError",
    "ModelVersionConflictError",
    "ArtifactIntegrityError",
    "InvalidLifecycleTransitionError",
    "PromotionRejectedError",
    "RollbackError",
    "LineageError",
    "MonitoringError",
    "DriftDetectionError",
    "PerformanceMonitoringError",
    "AlertError",
    "AuditError",
    # aliases
    "DataLoadError",
    "DataValidationError",
    "SchemaValidationError",
    "InferenceError",
    "ModelError",
]
