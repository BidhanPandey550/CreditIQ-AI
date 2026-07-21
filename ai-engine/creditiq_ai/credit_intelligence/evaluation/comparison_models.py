"""Typed contracts for automatic multi-metric model comparison."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

SUPPORTED_COMPARISON_METRICS = frozenset(
    {
        "accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "pr_auc",
        "log_loss",
        "brier_score",
        "matthews_correlation",
        "balanced_accuracy",
    }
)
LOSS_METRICS = frozenset({"log_loss", "brier_score"})


class ComparisonConfig(BaseModel):
    """Metric weights and hard eligibility gates for champion selection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric_weights: dict[str, float] = Field(
        default_factory=lambda: {"roc_auc": 0.4, "pr_auc": 0.3, "brier_score": 0.3}
    )
    minimum_metrics: dict[str, float] = Field(default_factory=dict)
    maximum_metrics: dict[str, float] = Field(default_factory=dict)
    require_eligible_model: bool = True

    @model_validator(mode="after")
    def validate_metrics(self) -> "ComparisonConfig":
        configured = (
            set(self.metric_weights) | set(self.minimum_metrics) | set(self.maximum_metrics)
        )
        unsupported = configured - SUPPORTED_COMPARISON_METRICS
        if unsupported:
            raise ValueError(f"Unsupported comparison metrics: {sorted(unsupported)}")
        if not self.metric_weights or any(weight <= 0.0 for weight in self.metric_weights.values()):
            raise ValueError("metric_weights must contain positive weights")
        if set(self.minimum_metrics) & LOSS_METRICS:
            raise ValueError("Loss metrics must use maximum_metrics eligibility gates")
        if set(self.maximum_metrics) - LOSS_METRICS:
            raise ValueError("Only loss metrics may use maximum_metrics eligibility gates")
        return self


class LeaderboardEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    rank: int = Field(ge=1)
    model_name: str
    model_version: str | None
    composite_score: float
    eligible: bool
    failed_gates: list[str] = Field(default_factory=list)
    metrics: dict[str, float]


class ModelComparisonReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    leaderboard: list[LeaderboardEntry]
    selected_model: str
    selected_version: str | None
    compared_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
