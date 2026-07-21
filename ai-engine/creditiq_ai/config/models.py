"""Typed configuration schema.

Purpose:  Validate and expose ALL engine configuration as immutable, typed objects so nothing is
          hardcoded and every run is reproducible. This is the single configuration surface —
          per-component configs (cleaning, imputation) are fields here, never loaded separately.
Inputs:   merged dict from base.yaml + environment YAML + env vars (see loader.py).
Outputs:  EngineConfig instance.
Deps:     pydantic v2.
Extend:   add a sub-config model + a field on EngineConfig, and a section in config/base.yaml.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from creditiq_ai.core.enums import Environment, ModelType, ScoringStrategy


class _Cfg(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RuntimeConfig(_Cfg):
    random_seed: int = 42
    n_jobs: int = -1
    artifacts_dir: str = "artifacts"
    log_level: str = "INFO"
    log_json: bool = False


class ColumnSpec(_Cfg):
    name: str
    dtype: str = "float"
    required: bool = True
    min: float | None = None
    max: float | None = None


class DataConfig(_Cfg):
    id_column: str = "applicant_id"
    target_column: str = "default"
    columns: list[ColumnSpec] = Field(default_factory=list)
    drop_duplicates: bool = True
    max_missing_fraction: float = 0.4  # column-level error threshold


# --- Cleaning (Data Cleaning Engine) — moved here in Sprint 3.5 so config lives in one place ---
class CleanerStep(_Cfg):
    name: str
    enabled: bool = True
    params: dict[str, Any] = Field(default_factory=dict)


class CleaningConfig(_Cfg):
    steps: list[CleanerStep] = Field(default_factory=list)


# --- Imputation (Missing Value Engine) ---
class ColumnStrategy(_Cfg):
    strategy: str
    params: dict[str, Any] = Field(default_factory=dict)


class ImputationConfig(_Cfg):
    default_numeric: str = "median"
    default_categorical: str = "mode"
    numeric_params: dict[str, Any] = Field(default_factory=dict)
    categorical_params: dict[str, Any] = Field(default_factory=dict)
    columns: dict[str, ColumnStrategy] = Field(default_factory=dict)


class FeatureSpec(_Cfg):
    name: str
    enabled: bool = True
    params: dict[str, Any] = Field(default_factory=dict)


class FeaturesConfig(_Cfg):
    generators: list[FeatureSpec] = Field(default_factory=list)


class ModelSpec(_Cfg):
    type: ModelType
    enabled: bool = True
    fixed_params: dict[str, Any] = Field(default_factory=dict)
    search_space: dict[str, Any] = Field(default_factory=dict)


class ModelsConfig(_Cfg):
    zoo: list[ModelSpec] = Field(default_factory=list)
    cv_folds: int = 5
    primary_metric: str = "roc_auc"
    tuning_enabled: bool = True
    optuna_trials: int = 30
    optuna_timeout_seconds: int | None = None
    optuna_n_jobs: int = 1
    optuna_pruning_startup_trials: int = 5


class CreditRuleSpec(_Cfg):
    name: str
    field: str
    operator: str
    value: Any
    enabled: bool = True
    priority: int = 100
    severity: str = "medium"
    action: str = "review"
    explanation: str


class CreditRulesConfig(_Cfg):
    rules: list[CreditRuleSpec] = Field(default_factory=list)
    stop_actions: list[str] = Field(default_factory=lambda: ["reject"])


class CreditConfidenceConfig(_Cfg):
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "probability": 0.35,
            "calibration": 0.25,
            "completeness": 0.25,
            "stability": 0.15,
        }
    )
    levels: dict[str, float] = Field(
        default_factory=lambda: {"low": 0.0, "medium": 0.5, "high": 0.75}
    )


class CreditIntelligenceConfig(_Cfg):
    business_rules: CreditRulesConfig = Field(default_factory=CreditRulesConfig)
    confidence: CreditConfidenceConfig = Field(default_factory=CreditConfidenceConfig)


class ScoreBand(_Cfg):
    band: str
    min_score: int


class ScoringConfig(_Cfg):
    strategy: ScoringStrategy = ScoringStrategy.PROBABILITY_TO_SCORE
    min_score: int = 300
    max_score: int = 850
    # Log-odds → points mapping (industry-style scorecard parameters).
    base_score: int = 600
    base_odds: float = 50.0
    pdo: float = 20.0  # points to double the odds
    feature_weights: dict[str, float] = Field(default_factory=dict)
    bands: list[ScoreBand] = Field(default_factory=list)


class DetectorSpec(_Cfg):
    type: str
    enabled: bool = True
    params: dict[str, Any] = Field(default_factory=dict)


class FraudConfig(_Cfg):
    detectors: list[DetectorSpec] = Field(default_factory=list)
    vote_threshold: int = 1  # #detectors that must flag to raise an alert


class ExplainabilityConfig(_Cfg):
    """XAI settings — narrative templates + labels are config, never hardcoded in code."""

    top_k: int = 5
    consistency_tolerance: float = 0.05  # |Σcontrib + base − prediction| tolerance
    feature_labels: dict[str, str] = Field(default_factory=dict)
    templates: dict[str, str] = Field(default_factory=dict)


# --- Fraud Intelligence (Sprint 7) ---
class FraudScoreBand(_Cfg):
    level: str
    min_score: int


class FraudScoringConfig(_Cfg):
    """Fraud score is 0–1000; weights, bands, and actions are all configurable."""

    score_min: int = 0
    score_max: int = 1000
    weights: dict[str, float] = Field(
        default_factory=dict
    )  # signal → weight (anomaly/rules/behaviour)
    bands: list[FraudScoreBand] = Field(default_factory=list)
    actions: dict[str, str] = Field(default_factory=dict)  # risk level → recommended action


class FraudBehaviourConfig(_Cfg):
    weights: dict[str, float] = Field(default_factory=dict)
    volatility_cap: float = Field(default=2.0, gt=0.0)
    transaction_frequency_cap: float = Field(default=100.0, gt=0.0)


class IdentityConsistencyConfig(_Cfg):
    required_fields: list[str] = Field(default_factory=list)
    matching_field_pairs: list[list[str]] = Field(default_factory=list)
    missing_field_penalty: float = Field(default=0.15, ge=0.0, le=1.0)
    mismatch_penalty: float = Field(default=0.25, ge=0.0, le=1.0)
    duplicate_penalty: float = Field(default=0.5, ge=0.0, le=1.0)


class FraudConfidenceConfig(_Cfg):
    weights: dict[str, float] = Field(default_factory=dict)
    levels: dict[str, float] = Field(default_factory=dict)


class FraudExplanationConfig(_Cfg):
    templates: dict[str, str] = Field(default_factory=dict)


class FraudIntelligenceConfig(_Cfg):
    scoring: FraudScoringConfig = Field(default_factory=FraudScoringConfig)
    behaviour: FraudBehaviourConfig = Field(default_factory=FraudBehaviourConfig)
    identity: IdentityConsistencyConfig = Field(default_factory=IdentityConsistencyConfig)
    rules: CreditRulesConfig = Field(default_factory=CreditRulesConfig)
    confidence: FraudConfidenceConfig = Field(default_factory=FraudConfidenceConfig)
    explainability: FraudExplanationConfig = Field(default_factory=FraudExplanationConfig)
    action_priority: list[str] = Field(
        default_factory=lambda: ["approve", "review", "manual_review", "reject"]
    )


# --- Unified Decision Engine (fix D2) ---
class DecisionConfidenceWeights(_Cfg):
    credit_weight: float = 0.6
    fraud_weight: float = 0.4


class DecisionConfig(_Cfg):
    """Policy for combining credit + fraud into a lending recommendation. No hardcoded thresholds."""

    credit_recommendation: dict[str, str] = Field(default_factory=dict)  # credit risk band → action
    fraud_reject_levels: list[str] = Field(default_factory=list)  # force reject
    fraud_block_levels: list[str] = Field(default_factory=list)  # block auto-approval
    fraud_block_action: str = "manual_review"
    on_fraud_failure: str = "manual_review"  # if would-approve but fraud unavailable
    on_credit_failure: str = "manual_review"
    on_incomplete_data: str = "manual_review"
    required_features: list[str] = Field(default_factory=list)
    confidence: DecisionConfidenceWeights = Field(default_factory=DecisionConfidenceWeights)


class MonitoringConfig(_Cfg):
    """Operational thresholds for inference monitoring and health evaluation."""

    enabled: bool = True
    retention_events: int = Field(default=10_000, ge=1)
    warning_failure_rate: float = Field(default=0.02, ge=0.0, le=1.0)
    critical_failure_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    warning_average_latency_ms: float = Field(default=250.0, gt=0.0)
    critical_average_latency_ms: float = Field(default=500.0, gt=0.0)


class EngineConfig(_Cfg):
    """Root configuration object injected across the engine (single source of truth)."""

    environment: Environment = Environment.DEVELOPMENT
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    cleaning: CleaningConfig = Field(default_factory=CleaningConfig)
    imputation: ImputationConfig = Field(default_factory=ImputationConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    credit_intelligence: CreditIntelligenceConfig = Field(default_factory=CreditIntelligenceConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    fraud: FraudConfig = Field(default_factory=FraudConfig)
    explainability: ExplainabilityConfig = Field(default_factory=ExplainabilityConfig)
    fraud_intelligence: FraudIntelligenceConfig = Field(default_factory=FraudIntelligenceConfig)
    decision: DecisionConfig = Field(default_factory=DecisionConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
