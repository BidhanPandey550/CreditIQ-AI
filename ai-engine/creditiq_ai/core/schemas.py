"""Domain contracts (Pydantic v2).

Purpose:  Typed, validated I/O objects exchanged between engine stages. These are the stable
          contracts that make stages independently testable and replaceable.
Inputs:   plain dicts / kwargs.
Outputs:  validated model instances.
Deps:     pydantic v2.
Extend:   add fields with defaults to stay backward compatible; add new result models here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from creditiq_ai.core.enums import (
    ModelType,
    ProblemType,
    RiskCategory,
    ValidationSeverity,
)


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


# --------------------------------------------------------------------------- inputs
class ApplicantRecord(_Base):
    """A single applicant's raw structured data presented to the engine.

    Deliberately permissive: unknown financial attributes ride in `attributes` so the schema
    does not need to change every time a new upstream field appears.
    """

    applicant_id: str
    monthly_income: float | None = None
    monthly_expenses: float | None = None
    monthly_debt_payments: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    savings_balance: float | None = None
    employment_months: int | None = None
    num_existing_loans: int | None = None
    has_delinquency: bool | None = None
    # Time-series style inputs (e.g. last N months of income / transactions).
    monthly_income_series: list[float] = Field(default_factory=list)
    monthly_transaction_counts: list[int] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


class FeatureVector(_Base):
    """Engineered features for one applicant, ready for a model."""

    applicant_id: str
    features: dict[str, float]


# --------------------------------------------------------------------------- outputs
class RiskAssessment(_Base):
    band: RiskCategory
    probability: float = Field(ge=0.0, le=1.0, description="Model probability of the adverse class")
    model_type: ModelType | None = None
    model_version: str | None = None


class CreditScoreResult(_Base):
    """Alternative credit score on the configurable 300–850 scale."""

    score: int = Field(ge=300, le=850)
    band: RiskCategory
    subscores: dict[str, float] = Field(default_factory=dict)
    strategy: str
    assumptions: list[str] = Field(default_factory=list)


class DefaultProbabilityResult(_Base):
    probability: float = Field(ge=0.0, le=1.0)
    risk_category: RiskCategory
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence in this estimate")
    horizon_months: int = 12


class FeatureContribution(_Base):
    feature: str
    value: float
    contribution: float = Field(description="Signed effect on the prediction (SHAP value)")


class Explanation(_Base):
    """Machine-readable local explanation for a single prediction."""

    base_value: float
    prediction: float
    top_contributors: list[FeatureContribution] = Field(default_factory=list)
    positive_contributors: list[FeatureContribution] = Field(default_factory=list)
    negative_contributors: list[FeatureContribution] = Field(default_factory=list)
    narrative: str | None = None


class GlobalImportance(_Base):
    importances: dict[str, float]
    method: str = "shap_mean_abs"


class FraudResult(_Base):
    is_flagged: bool
    severity: str
    anomaly_score: float = Field(description="Lower = more anomalous")
    reasons: list[str] = Field(default_factory=list)
    detector_votes: dict[str, bool] = Field(default_factory=dict)


class PredictionResult(_Base):
    """The single structured object returned by the InferenceEngine."""

    applicant_id: str
    risk: RiskAssessment
    credit_score: CreditScoreResult
    default: DefaultProbabilityResult
    fraud: FraudResult
    explanation: Explanation
    model_version: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --------------------------------------------------------------------------- validation
class ValidationIssue(_Base):
    severity: ValidationSeverity
    rule: str
    message: str
    column: str | None = None
    count: int | None = None


class ValidationReport(_Base):
    passed: bool
    n_rows: int
    n_columns: int
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]


# --------------------------------------------------------------------------- ml metadata
class EvaluationReport(_Base):
    model_type: ModelType | None = None
    problem_type: ProblemType = ProblemType.BINARY_CLASSIFICATION
    metrics: dict[str, float] = Field(default_factory=dict)
    confusion_matrix: list[list[int]] | None = None
    primary_metric: str = "roc_auc"

    @property
    def primary_score(self) -> float | None:
        return self.metrics.get(self.primary_metric)


class ModelMetadata(_Base):
    """Registry record for one trained model version."""

    name: str
    version: str
    model_type: ModelType
    problem_type: ProblemType = ProblemType.BINARY_CLASSIFICATION
    trained_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    features: list[str] = Field(default_factory=list)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    config_hash: str | None = None
    artifact_path: str | None = None


# --------------------------------------------------------------------------- monitoring
class PredictionEvent(_Base):
    applicant_id: str
    model_version: str
    latency_ms: float
    risk_band: RiskCategory
    default_probability: float
    fraud_flagged: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
