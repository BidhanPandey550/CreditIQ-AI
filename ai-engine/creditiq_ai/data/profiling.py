"""Bounded dataset profiling without retaining raw customer values."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class DatasetProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    rows: int = Field(ge=0)
    columns: int = Field(ge=0)
    memory_bytes: int = Field(ge=0)
    column_types: dict[str, str]
    numerical: dict[str, dict[str, float | None]]
    categorical: dict[str, dict[str, int | float]]
    recommendations: list[str] = Field(default_factory=list)


class DatasetProfiler:
    def profile(self, frame: pd.DataFrame) -> DatasetProfile:
        numerical: dict[str, dict[str, float | None]] = {}
        categorical: dict[str, dict[str, int | float]] = {}
        recommendations: list[str] = []
        for name in frame.columns:
            series = frame[name]
            if pd.api.types.is_numeric_dtype(series):
                numerical[name] = {
                    key: self._number(value)
                    for key, value in {
                        "mean": series.mean(),
                        "std": series.std(),
                        "min": series.min(),
                        "max": series.max(),
                    }.items()
                }
            else:
                cardinality = int(series.nunique(dropna=False))
                categorical[name] = {
                    "cardinality": cardinality,
                    "cardinality_ratio": round(cardinality / max(1, len(series)), 6),
                }
                if cardinality > max(50, len(series) // 2):
                    recommendations.append(f"review_high_cardinality:{name}")
        return DatasetProfile(
            rows=len(frame),
            columns=frame.shape[1],
            memory_bytes=int(frame.memory_usage(index=True, deep=True).sum()),
            column_types={name: str(dtype) for name, dtype in frame.dtypes.items()},
            numerical=numerical,
            categorical=categorical,
            recommendations=recommendations,
        )

    @staticmethod
    def _number(value: Any) -> float | None:
        return None if pd.isna(value) else float(value)
