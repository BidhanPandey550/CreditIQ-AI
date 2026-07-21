"""Privacy-safe aggregate dataset quality analysis."""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class ColumnQuality(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    column: str
    dtype: str
    missing_count: int = Field(ge=0)
    missing_fraction: float = Field(ge=0.0, le=1.0)
    unique_count: int = Field(ge=0)
    outlier_count: int = Field(ge=0)


class DataQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    duplicate_rows: int = Field(ge=0)
    health_score: float = Field(ge=0.0, le=100.0)
    columns: list[ColumnQuality]
    target_distribution: dict[str, float] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)


class DataQualityAnalyzer:
    """Measure completeness, cardinality, IQR outliers, duplicates and target balance."""

    def analyze(self, frame: pd.DataFrame, *, target: str | None = None) -> DataQualityReport:
        rows = len(frame)
        duplicates = int(frame.duplicated().sum())
        columns = [self._column(frame[name]) for name in frame.columns]
        missing = sum(item.missing_count for item in columns)
        outliers = sum(item.outlier_count for item in columns)
        penalty = (missing + outliers + duplicates * max(1, frame.shape[1])) / max(1, frame.size)
        recommendations = []
        if missing:
            recommendations.append("review_missing_values")
        if duplicates:
            recommendations.append("remove_duplicate_rows")
        if outliers:
            recommendations.append("review_numeric_outliers")
        distribution: dict[str, float] = {}
        if target and target in frame and rows:
            distribution = {
                str(key): round(float(value), 6)
                for key, value in frame[target].value_counts(normalize=True, dropna=False).items()
            }
            if distribution and min(distribution.values()) < 0.1:
                recommendations.append("review_target_imbalance")
        return DataQualityReport(
            row_count=rows,
            column_count=frame.shape[1],
            duplicate_rows=duplicates,
            health_score=round(max(0.0, 100.0 * (1.0 - penalty)), 2),
            columns=columns,
            target_distribution=distribution,
            recommendations=recommendations,
        )

    @staticmethod
    def _column(series: pd.Series) -> ColumnQuality:
        outliers = 0
        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            if not clean.empty:
                first, third = clean.quantile([0.25, 0.75])
                spread = third - first
                if spread > 0:
                    outliers = int(
                        ((clean < first - 1.5 * spread) | (clean > third + 1.5 * spread)).sum()
                    )
        missing = int(series.isna().sum())
        return ColumnQuality(
            column=str(series.name),
            dtype=str(series.dtype),
            missing_count=missing,
            missing_fraction=missing / max(1, len(series)),
            unique_count=int(series.nunique(dropna=False)),
            outlier_count=outliers,
        )
