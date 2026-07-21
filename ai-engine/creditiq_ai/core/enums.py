"""Controlled vocabularies used across the engine.

Purpose:  Single source of truth for categorical constants (no magic strings).
Inputs:   n/a
Outputs:  Enum types.
Deps:     stdlib enum.
Extend:   Add members here; never inline string literals elsewhere.
"""

from __future__ import annotations

from enum import Enum


class Environment(str, Enum):
    """Deployment environment, detected from CREDITIQ_ENV."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class ProblemType(str, Enum):
    """The supervised-learning task a model addresses."""

    BINARY_CLASSIFICATION = "binary_classification"
    MULTICLASS_CLASSIFICATION = "multiclass_classification"
    REGRESSION = "regression"


class ModelType(str, Enum):
    """Supported estimator families (the model zoo keys)."""

    LOGISTIC_REGRESSION = "logistic_regression"
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    CATBOOST = "catboost"


class RiskCategory(str, Enum):
    """Ordinal risk bands. Thresholds are configuration, not code."""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class AnomalyDetectorType(str, Enum):
    ISOLATION_FOREST = "isolation_forest"
    LOCAL_OUTLIER_FACTOR = "local_outlier_factor"
    ONE_CLASS_SVM = "one_class_svm"


class ScoringStrategy(str, Enum):
    """How the 300–850 alternative credit score is derived."""

    PROBABILITY_TO_SCORE = "probability_to_score"
    WEIGHTED_FEATURES = "weighted_features"


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ImputationStrategy(str, Enum):
    MEAN = "mean"
    MEDIAN = "median"
    MOST_FREQUENT = "most_frequent"
    CONSTANT = "constant"


class ScalingStrategy(str, Enum):
    STANDARD = "standard"
    MINMAX = "minmax"
    ROBUST = "robust"
    NONE = "none"


class EncodingStrategy(str, Enum):
    ONE_HOT = "one_hot"
    ORDINAL = "ordinal"
    TARGET = "target"
