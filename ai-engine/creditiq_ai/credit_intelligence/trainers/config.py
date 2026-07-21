"""Training configuration — a single, immutable training-run spec.

Purpose:  Describe ONE training run (algorithm + hyperparameters + CV + metric + seed) with no
          hardcoded values. Built from the unified EngineConfig.models so config stays in one
          place (Sprint 3.5 rule).
Inputs:   algorithm name + params, or an EngineConfig ModelsConfig.
Outputs:  TrainingConfig (frozen dataclass) / a list of them.
Deps:     config.models.ModelsConfig.
Extend:   add fields here + a matching key under `models:` in config/base.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from creditiq_ai.config.models import ModelsConfig

# Valid primary metrics = scikit-learn scorer names (no custom magic strings).
ALLOWED_METRICS: frozenset[str] = frozenset(
    {
        "roc_auc",
        "average_precision",
        "accuracy",
        "balanced_accuracy",
        "f1",
        "precision",
        "recall",
        "neg_log_loss",
    }
)


@dataclass(frozen=True)
class TrainingConfig:
    algorithm: str
    params: dict[str, Any] = field(default_factory=dict)
    cv_folds: int = 5
    primary_metric: str = "roc_auc"
    random_seed: int = 42

    def __post_init__(self) -> None:
        if self.primary_metric not in ALLOWED_METRICS:
            raise ValueError(
                f"Unsupported primary_metric '{self.primary_metric}'; "
                f"allowed: {sorted(ALLOWED_METRICS)}"
            )
        if self.cv_folds < 2:
            raise ValueError("cv_folds must be >= 2")


def training_configs_from_models(
    models: ModelsConfig, random_seed: int = 42
) -> list[TrainingConfig]:
    """Build one TrainingConfig per enabled model in the unified config's model zoo."""
    return [
        TrainingConfig(
            algorithm=spec.type.value,
            params=dict(spec.fixed_params),
            cv_folds=models.cv_folds,
            primary_metric=models.primary_metric,
            random_seed=random_seed,
        )
        for spec in models.zoo
        if spec.enabled
    ]
