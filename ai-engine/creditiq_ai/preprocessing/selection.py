"""Supervised and unsupervised feature-selection strategies."""

from __future__ import annotations

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import RFE, SelectKBest, VarianceThreshold, chi2, mutual_info_classif
from sklearn.linear_model import LogisticRegression

from creditiq_ai.config.models import FeatureSelectionConfig
from creditiq_ai.exceptions import PreprocessingError


class FeatureSelectionReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    strategy: str
    selected: list[str]
    removed: list[str]
    scores: dict[str, float] = Field(default_factory=dict)


class FeatureSelectionEngine:
    """Learn a stable selected schema with configurable strategy implementations."""

    def __init__(self, config: FeatureSelectionConfig) -> None:
        self._config = config
        self._selected: list[str] = []
        self._scores: dict[str, float] = {}

    def fit(self, frame: pd.DataFrame, y: pd.Series | None = None) -> "FeatureSelectionEngine":
        if not all(pd.api.types.is_numeric_dtype(frame[column]) for column in frame.columns):
            raise PreprocessingError("Feature selection requires fully numeric input")
        strategy = self._config.strategy
        params = self._config.params
        if strategy == "correlation":
            threshold = float(params.get("threshold", 0.95))
            matrix = frame.corr().abs()
            upper = matrix.where(np.triu(np.ones(matrix.shape), k=1).astype(bool))
            removed = {column for column in upper.columns if (upper[column] > threshold).any()}
            self._selected = [column for column in frame.columns if column not in removed]
        elif strategy == "variance":
            selector = VarianceThreshold(float(params.get("threshold", 0.0))).fit(frame)
            self._selected = list(frame.columns[selector.get_support()])
            self._scores = dict(zip(frame.columns, selector.variances_, strict=True))
        else:
            if y is None:
                raise PreprocessingError(f"{strategy} feature selection requires labels")
            count = min(int(params.get("k", max(1, frame.shape[1] // 2))), frame.shape[1])
            if strategy in {"mutual_information", "chi_square"}:
                score_function = mutual_info_classif if strategy == "mutual_information" else chi2
                selector = SelectKBest(score_function, k=count).fit(frame, y)
                self._selected = list(frame.columns[selector.get_support()])
                self._scores = dict(
                    zip(frame.columns, np.nan_to_num(selector.scores_), strict=True)
                )
            elif strategy == "rfe":
                selector = RFE(LogisticRegression(max_iter=1000), n_features_to_select=count).fit(
                    frame, y
                )
                self._selected = list(frame.columns[selector.support_])
                self._scores = {
                    name: float(rank)
                    for name, rank in zip(frame.columns, selector.ranking_, strict=True)
                }
            elif strategy == "importance":
                estimator = RandomForestClassifier(
                    n_estimators=int(params.get("n_estimators", 100)),
                    random_state=int(params.get("random_state", 42)),
                ).fit(frame, y)
                ranked = sorted(
                    zip(frame.columns, estimator.feature_importances_, strict=True),
                    key=lambda item: item[1],
                    reverse=True,
                )
                self._selected = [name for name, _ in ranked[:count]]
                self._scores = {name: float(score) for name, score in ranked}
            else:
                raise PreprocessingError(
                    "Unknown feature selection strategy", context={"strategy": strategy}
                )
        if not self._selected:
            raise PreprocessingError("Feature selection removed every feature")
        return self

    def transform(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, FeatureSelectionReport]:
        if not self._selected:
            raise PreprocessingError("FeatureSelectionEngine must be fitted before transform")
        missing = sorted(set(self._selected) - set(frame.columns))
        if missing:
            raise PreprocessingError("Selected features are missing", context={"columns": missing})
        return frame[self._selected].copy(), FeatureSelectionReport(
            strategy=self._config.strategy,
            selected=self._selected,
            removed=[column for column in frame.columns if column not in self._selected],
            scores=self._scores,
        )

    def fit_transform(
        self, frame: pd.DataFrame, y: pd.Series | None = None
    ) -> tuple[pd.DataFrame, FeatureSelectionReport]:
        return self.fit(frame, y).transform(frame)
