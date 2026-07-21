"""DataFrame-preserving scaling strategy engine."""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, ConfigDict
from sklearn.preprocessing import (
    MaxAbsScaler,
    MinMaxScaler,
    Normalizer,
    RobustScaler,
    StandardScaler,
)

from creditiq_ai.config.models import ScalingConfig
from creditiq_ai.exceptions import PreprocessingError


class ScalingReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    strategy: str
    columns: list[str]


class ScalingEngine:
    """Fit a configured sklearn scaler while retaining names and unscaled columns."""

    _strategies = {
        "standard": StandardScaler,
        "minmax": MinMaxScaler,
        "robust": RobustScaler,
        "maxabs": MaxAbsScaler,
        "normalizer": Normalizer,
    }

    def __init__(self, config: ScalingConfig) -> None:
        self._config = config
        self._columns: list[str] = []
        self._scaler: object | None = None

    def fit(self, frame: pd.DataFrame) -> "ScalingEngine":
        self._columns = self._config.columns or list(frame.select_dtypes(include="number").columns)
        try:
            scaler_type = self._strategies[self._config.strategy]
        except KeyError as exc:
            raise PreprocessingError(
                "Unknown scaling strategy", context={"strategy": self._config.strategy}
            ) from exc
        self._scaler = scaler_type(**self._config.params).fit(frame[self._columns])
        return self

    def transform(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, ScalingReport]:
        if self._scaler is None:
            raise PreprocessingError("ScalingEngine must be fitted before transform")
        result = frame.copy()
        result[self._columns] = self._scaler.transform(result[self._columns])  # type: ignore[attr-defined]
        return result, ScalingReport(strategy=self._config.strategy, columns=self._columns)

    def fit_transform(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, ScalingReport]:
        return self.fit(frame).transform(frame)
