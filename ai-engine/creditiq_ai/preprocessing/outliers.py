"""Configuration-driven outlier detection and treatment strategies."""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from sklearn.ensemble import IsolationForest

from creditiq_ai.config.models import OutlierConfig
from creditiq_ai.exceptions import PreprocessingError


class ColumnOutliers(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    column: str
    count: int = Field(ge=0)
    lower_bound: float | None = None
    upper_bound: float | None = None


class OutlierReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    strategy: str
    action: str
    rows_removed: int = Field(ge=0)
    columns: list[ColumnOutliers]


class OutlierEngine:
    """Fit statistical bounds or Isolation Forest and apply a configured treatment."""

    def __init__(self, config: OutlierConfig) -> None:
        self._config = config
        self._bounds: dict[str, tuple[float, float]] = {}
        self._detector: IsolationForest | None = None
        self._columns: list[str] = []

    def fit(self, frame: pd.DataFrame) -> "OutlierEngine":
        self._columns = self._config.columns or list(frame.select_dtypes(include="number").columns)
        if not self._columns:
            raise PreprocessingError("Outlier engine requires numeric columns")
        missing = sorted(set(self._columns) - set(frame.columns))
        if missing:
            raise PreprocessingError("Outlier columns are missing", context={"columns": missing})
        strategy = self._config.strategy
        if strategy == "isolation_forest":
            self._detector = IsolationForest(**self._config.params).fit(frame[self._columns])
        else:
            self._bounds = {
                column: self._calculate_bounds(frame[column].dropna()) for column in self._columns
            }
        return self

    def transform(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, OutlierReport]:
        if not self._columns:
            raise PreprocessingError("OutlierEngine must be fitted before transform")
        result = frame.copy()
        row_mask = pd.Series(False, index=result.index)
        reports: list[ColumnOutliers] = []
        if self._detector is not None:
            row_mask = pd.Series(
                self._detector.predict(result[self._columns]) == -1, index=result.index
            )
            reports.append(ColumnOutliers(column="__multivariate__", count=int(row_mask.sum())))
        else:
            for column, (lower, upper) in self._bounds.items():
                mask = (result[column] < lower) | (result[column] > upper)
                row_mask |= mask.fillna(False)
                reports.append(
                    ColumnOutliers(
                        column=column, count=int(mask.sum()), lower_bound=lower, upper_bound=upper
                    )
                )
                if self._config.action in {"clip", "winsorize"}:
                    result[column] = result[column].clip(lower, upper)
        removed = int(row_mask.sum()) if self._config.action == "remove" else 0
        if removed:
            result = result.loc[~row_mask].copy()
        return result, OutlierReport(
            strategy=self._config.strategy,
            action=self._config.action,
            rows_removed=removed,
            columns=reports,
        )

    def fit_transform(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, OutlierReport]:
        return self.fit(frame).transform(frame)

    def _calculate_bounds(self, values: pd.Series) -> tuple[float, float]:
        if values.empty:
            raise PreprocessingError("Cannot fit outlier bounds on an empty column")
        strategy = self._config.strategy
        if strategy in {"percentile", "winsorization"}:
            lower_q = float(self._config.params.get("lower", 0.01))
            upper_q = float(self._config.params.get("upper", 0.99))
            return float(values.quantile(lower_q)), float(values.quantile(upper_q))
        if strategy == "zscore":
            deviations = float(self._config.params.get("threshold", 3.0))
            mean, std = float(values.mean()), float(values.std(ddof=0))
            return mean - deviations * std, mean + deviations * std
        if strategy == "iqr":
            multiplier = float(self._config.params.get("multiplier", 1.5))
            first, third = values.quantile([0.25, 0.75])
            spread = float(third - first)
            return float(first - multiplier * spread), float(third + multiplier * spread)
        raise PreprocessingError("Unknown outlier strategy", context={"strategy": strategy})
