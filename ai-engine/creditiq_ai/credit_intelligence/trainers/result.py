"""Training result — the serialisable outcome of one training run.

Purpose:  A typed, JSON-serialisable record of a training run (algorithm, params, CV scores,
          timing, data provenance) used for leaderboards, reports, and the model registry.
Inputs:   populated by BaseTrainer.train().
Outputs:  TrainingResult (Pydantic).
Deps:     pydantic v2.
Note:     the fitted estimator is NOT stored here (kept on the trainer / persisted separately)
          so results stay lightweight and serialisable.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class CrossValidationScore(BaseModel):
    metric: str
    mean: float
    std: float
    folds: list[float] = Field(default_factory=list)


class TrainingResult(BaseModel):
    algorithm: str
    params: dict = Field(default_factory=dict)
    primary_metric: str
    primary_score: float
    cv: CrossValidationScore
    n_train: int
    n_features: int
    dataset_version: str
    duration_seconds: float
    feature_names: list[str] = Field(default_factory=list)
    trained_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    warnings: list[str] = Field(default_factory=list)
