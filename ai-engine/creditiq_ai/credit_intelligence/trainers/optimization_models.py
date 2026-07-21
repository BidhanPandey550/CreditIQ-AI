"""Typed hyperparameter-optimization contracts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from creditiq_ai.config.models import ModelsConfig
from creditiq_ai.exceptions import ConfigurationError


class SearchDimensionType(StrEnum):
    INTEGER = "int"
    FLOAT = "float"
    CATEGORICAL = "categorical"


class SearchDimension(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: SearchDimensionType
    low: int | float | None = None
    high: int | float | None = None
    step: int | float | None = None
    log: bool = False
    choices: list[Any] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dimension(self) -> "SearchDimension":
        if self.type == SearchDimensionType.CATEGORICAL:
            if not self.choices:
                raise ValueError("Categorical dimensions require choices")
        elif self.low is None or self.high is None or self.low >= self.high:
            raise ValueError("Numeric dimensions require low < high")
        if self.log and self.step is not None:
            raise ValueError("Logarithmic dimensions cannot define a step")
        return self


class OptimizationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    algorithm: str
    fixed_params: dict[str, Any] = Field(default_factory=dict)
    search_space: dict[str, SearchDimension]
    trials: int = Field(default=30, ge=1)
    timeout_seconds: int | None = Field(default=None, ge=1)
    n_jobs: int = 1
    cv_folds: int = Field(default=5, ge=2)
    primary_metric: str = "roc_auc"
    random_seed: int = 42
    pruning_startup_trials: int = Field(default=5, ge=0)
    study_name: str | None = None
    storage_url: str | None = None

    @model_validator(mode="after")
    def validate_workers(self) -> "OptimizationConfig":
        if self.n_jobs == 0:
            raise ValueError("n_jobs cannot be zero")
        return self

    @classmethod
    def from_models(
        cls, models: ModelsConfig, algorithm: str, *, random_seed: int = 42
    ) -> "OptimizationConfig":
        spec = next((item for item in models.zoo if item.type.value == algorithm), None)
        if spec is None:
            raise ConfigurationError(f"No model configuration exists for '{algorithm}'")
        if not spec.search_space:
            raise ConfigurationError(f"No search space configured for '{algorithm}'")
        return cls(
            algorithm=algorithm,
            fixed_params=dict(spec.fixed_params),
            search_space={
                name: SearchDimension.model_validate(value)
                for name, value in spec.search_space.items()
            },
            trials=models.optuna_trials,
            timeout_seconds=models.optuna_timeout_seconds,
            n_jobs=models.optuna_n_jobs,
            cv_folds=models.cv_folds,
            primary_metric=models.primary_metric,
            random_seed=random_seed,
            pruning_startup_trials=models.optuna_pruning_startup_trials,
        )


class OptimizationTrial(BaseModel):
    number: int
    score: float | None
    state: str
    params: dict[str, Any] = Field(default_factory=dict)


class OptimizationResult(BaseModel):
    algorithm: str
    study_name: str
    best_score: float
    best_params: dict[str, Any]
    trials: list[OptimizationTrial]
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def save_json(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(f"{destination.suffix}.tmp")
        temporary.write_text(json.dumps(self.model_dump(mode="json"), indent=2), encoding="utf-8")
        temporary.replace(destination)
        return destination
