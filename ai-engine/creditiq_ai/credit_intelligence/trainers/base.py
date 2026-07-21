"""BaseTrainer — Template Method for every credit-risk algorithm.

Purpose:  Define the invariant training workflow once (validate → cross-validate → fit → package
          result → log) while each algorithm supplies only its estimator via `_build_estimator`.
          Guarantees consistent CV, metrics, persistence, and logging across all models.
Inputs:   TrainingContext (dataset + config).
Outputs:  TrainingResult; a fitted estimator retained on the trainer.
Deps:     scikit-learn, joblib, numpy; core.base.BaseComponent; exceptions.
Extend:   subclass, set `algorithm`, implement `_build_estimator(params)`, register in the factory.
"""

from __future__ import annotations

import time
import warnings
from abc import abstractmethod
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import StratifiedKFold, cross_val_score

from creditiq_ai.core.base import BaseComponent
from creditiq_ai.core.types import NDArray, PathLike
from creditiq_ai.credit_intelligence.trainers.config import TrainingConfig
from creditiq_ai.credit_intelligence.trainers.context import TrainingContext
from creditiq_ai.credit_intelligence.trainers.result import (
    CrossValidationScore,
    TrainingResult,
)
from creditiq_ai.exceptions import ModelNotFittedError, ModelTrainingError
from creditiq_ai.model_operations.domain import ModelArtifact
from creditiq_ai.model_operations.storage.artifacts import ArtifactStore


class BaseTrainer(BaseComponent):
    """Template Method base for all trainers. Subclasses only build the estimator."""

    algorithm: str = "base"

    @classmethod
    def dependency_available(cls) -> bool:
        """Whether optional runtime dependencies required by this trainer are installed."""
        return True

    def __init__(self, config: TrainingConfig) -> None:
        super().__init__(name=self.algorithm)
        self.train_config = config
        self._estimator: Any = None
        self._fitted = False

    # ---- Template Method (do not override) ----
    def train(self, context: TrainingContext) -> TrainingResult:
        self._validate(context)
        started = time.perf_counter()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            cv = self._cross_validate(context)
            estimator = self._build_estimator(self.train_config.params)
            estimator.fit(context.X, context.y)
            captured = [str(w.message) for w in caught]

        self._estimator = estimator
        self._fitted = True
        duration = time.perf_counter() - started

        result = TrainingResult(
            algorithm=self.algorithm,
            params=dict(self.train_config.params),
            primary_metric=self.train_config.primary_metric,
            primary_score=cv.mean,
            cv=cv,
            n_train=context.dataset.n_rows,
            n_features=context.dataset.n_features,
            dataset_version=context.dataset.version,
            duration_seconds=round(duration, 4),
            feature_names=context.feature_names,
            warnings=captured,
        )
        self.logger.info(
            f"Trained {self.algorithm} | {cv.metric}={cv.mean:.4f}±{cv.std:.4f} "
            f"| {context.dataset.n_rows} rows | {duration:.2f}s"
            + (f" | {len(captured)} warning(s)" if captured else "")
        )
        return result

    # ---- Hook every subclass implements ----
    @abstractmethod
    def _build_estimator(self, params: dict[str, Any]) -> Any:
        """Return an unfitted scikit-learn-compatible estimator configured with `params`."""

    # ---- Shared behaviour ----
    def _validate(self, context: TrainingContext) -> None:
        y = np.asarray(context.y)
        if len(y) == 0:
            raise ModelTrainingError("Cannot train on an empty dataset")
        if pd.isna(y).any():
            raise ModelTrainingError("Target contains missing labels")
        if np.unique(y[~pd.isna(y)]).size < 2:
            raise ModelTrainingError("Target must contain at least two classes")

    def _cross_validate(self, context: TrainingContext) -> CrossValidationScore:
        cfg = self.train_config
        splitter = StratifiedKFold(
            n_splits=cfg.cv_folds, shuffle=True, random_state=cfg.random_seed
        )
        estimator = self._build_estimator(cfg.params)
        try:
            scores = cross_val_score(
                clone(estimator), context.X, context.y, cv=splitter, scoring=cfg.primary_metric
            )
        except Exception as exc:  # noqa: BLE001
            raise ModelTrainingError(
                f"Cross-validation failed for {self.algorithm}", context={"error": str(exc)}
            ) from exc
        return CrossValidationScore(
            metric=cfg.primary_metric,
            mean=float(scores.mean()),
            std=float(scores.std()),
            folds=[float(s) for s in scores],
        )

    def predict(self, X: pd.DataFrame) -> NDArray:
        self._check_fitted()
        return self._estimator.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> NDArray:
        """Probability of the positive (default) class."""
        self._check_fitted()
        return self._estimator.predict_proba(X)[:, 1]

    def save(self, path: PathLike) -> ModelArtifact:
        """Persist this trainer and return integrity metadata required for safe loading."""
        self._check_fitted()
        payload = {
            "algorithm": self.algorithm,
            "config": self.train_config,
            "estimator": self._estimator,
        }
        return ArtifactStore().save(payload, path)

    @classmethod
    def load(cls, path: PathLike, expected_sha256: str | None = None) -> "BaseTrainer":
        """Load only after verifying the caller-supplied trusted SHA-256 checksum."""
        payload = ArtifactStore().load(path, expected_sha256 or "")
        trainer = cls(payload["config"])
        trainer._estimator = payload["estimator"]
        trainer._fitted = True
        return trainer

    @classmethod
    def load_artifact(cls, artifact: ModelArtifact) -> "BaseTrainer":
        """Load from a registry artifact record carrying trusted integrity metadata."""
        return cls.load(artifact.path, artifact.checksum_sha256)

    def _check_fitted(self) -> None:
        if not self._fitted:
            raise ModelNotFittedError(f"{self.algorithm} trainer is not fitted")
