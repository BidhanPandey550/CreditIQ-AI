"""Leakage-safe categorical encoding engine."""

from __future__ import annotations

import hashlib

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from creditiq_ai.config.models import EncodingConfig
from creditiq_ai.exceptions import PreprocessingError


class EncodingReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    input_columns: list[str]
    output_columns: list[str]
    unknown_values: dict[str, int] = Field(default_factory=dict)


class EncodingEngine:
    """Fit independent categorical strategies and preserve a stable inference schema."""

    def __init__(self, config: EncodingConfig) -> None:
        self._config = config
        self._maps: dict[str, dict[object, float]] = {}
        self._categories: dict[str, list[object]] = {}
        self._global_target: float = 0.0
        self._fitted = False

    def fit(self, frame: pd.DataFrame, y: pd.Series | None = None) -> "EncodingEngine":
        missing = sorted(set(self._config.columns) - set(frame.columns))
        if missing:
            raise PreprocessingError("Encoding columns are missing", context={"columns": missing})
        self._global_target = float(y.mean()) if y is not None else 0.0
        for column, spec in self._config.columns.items():
            values = frame[column].astype("object")
            self._categories[column] = sorted(values.dropna().unique().tolist(), key=str)
            if spec.strategy == "frequency":
                self._maps[column] = values.value_counts(normalize=True).to_dict()
            elif spec.strategy == "target":
                if y is None:
                    raise PreprocessingError("Target encoding requires training labels")
                smoothing = float(spec.params.get("smoothing", 10.0))
                stats = (
                    pd.DataFrame({"value": values, "target": y.to_numpy()})
                    .groupby("value")["target"]
                    .agg(["mean", "count"])
                )
                encoded = (stats["mean"] * stats["count"] + self._global_target * smoothing) / (
                    stats["count"] + smoothing
                )
                self._maps[column] = encoded.to_dict()
            elif spec.strategy in {"label", "ordinal"}:
                order = spec.params.get("categories") or self._categories[column]
                self._maps[column] = {value: float(index) for index, value in enumerate(order)}
            elif spec.strategy not in {"one_hot", "hash"}:
                raise PreprocessingError(
                    "Unknown encoding strategy", context={"strategy": spec.strategy}
                )
        self._fitted = True
        return self

    def transform(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, EncodingReport]:
        if not self._fitted:
            raise PreprocessingError("EncodingEngine must be fitted before transform")
        result = frame.drop(columns=list(self._config.columns)).copy()
        unknown: dict[str, int] = {}
        for column, spec in self._config.columns.items():
            values = frame[column].astype("object")
            known = set(self._categories[column])
            unknown[column] = int((~values.isin(known) & values.notna()).sum())
            if spec.strategy == "one_hot":
                for category in self._categories[column]:
                    name = f"{column}__{self._safe_name(category)}"
                    result[name] = (values == category).astype("int8")
            elif spec.strategy == "hash":
                dimensions = int(spec.params.get("dimensions", 8))
                if dimensions < 1:
                    raise PreprocessingError("Hash encoding dimensions must be positive")
                for index in range(dimensions):
                    result[f"{column}__hash_{index}"] = 0
                for row_index, value in values.items():
                    bucket = int(hashlib.sha256(str(value).encode()).hexdigest(), 16) % dimensions
                    result.at[row_index, f"{column}__hash_{bucket}"] = 1
            else:
                fallback = self._global_target if spec.strategy == "target" else -1.0
                result[column] = values.map(self._maps[column]).fillna(fallback).astype(float)
        return result, EncodingReport(
            input_columns=list(self._config.columns),
            output_columns=list(result.columns),
            unknown_values=unknown,
        )

    def fit_transform(
        self, frame: pd.DataFrame, y: pd.Series | None = None
    ) -> tuple[pd.DataFrame, EncodingReport]:
        return self.fit(frame, y).transform(frame)

    @staticmethod
    def _safe_name(value: object) -> str:
        return (
            "".join(character if character.isalnum() else "_" for character in str(value)).strip(
                "_"
            )
            or "empty"
        )
