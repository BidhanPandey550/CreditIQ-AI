"""Composable enterprise preprocessing orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from creditiq_ai.preprocessing.cleaning import DataCleaningEngine
from creditiq_ai.preprocessing.encoding import EncodingEngine
from creditiq_ai.preprocessing.imputation import MissingValueEngine
from creditiq_ai.preprocessing.outliers import OutlierEngine
from creditiq_ai.preprocessing.scaling import ScalingEngine
from creditiq_ai.preprocessing.selection import FeatureSelectionEngine


class PreprocessingReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    input_rows: int
    output_rows: int
    input_columns: list[str]
    output_columns: list[str]
    stages: dict[str, dict[str, Any]] = Field(default_factory=dict)


@dataclass
class PreprocessingPipeline:
    """Orchestrate injected stages while keeping each implementation independently replaceable."""

    cleaning: DataCleaningEngine | None = None
    imputation: MissingValueEngine | None = None
    outliers: OutlierEngine | None = None
    encoding: EncodingEngine | None = None
    scaling: ScalingEngine | None = None
    selection: FeatureSelectionEngine | None = None

    def fit_transform(
        self, frame: pd.DataFrame, y: pd.Series | None = None
    ) -> tuple[pd.DataFrame, PreprocessingReport]:
        result = frame
        stages: dict[str, dict[str, Any]] = {}
        if self.cleaning:
            result, cleaning_report = self.cleaning.clean(result)
            stages["clean"] = cleaning_report.model_dump(mode="json")
        if self.imputation:
            result, imputation_report = self.imputation.fit_transform(result)
            stages["impute"] = imputation_report.model_dump(mode="json")
        if self.outliers:
            result, outlier_report = self.outliers.fit_transform(result)
            stages["outliers"] = outlier_report.model_dump(mode="json")
        if self.encoding:
            result, encoding_report = self.encoding.fit_transform(result, y)
            stages["encode"] = encoding_report.model_dump(mode="json")
        if self.scaling:
            result, scaling_report = self.scaling.fit_transform(result)
            stages["scale"] = scaling_report.model_dump(mode="json")
        if self.selection:
            labels = y.loc[result.index] if y is not None else None
            result, selection_report = self.selection.fit_transform(result, labels)
            stages["select"] = selection_report.model_dump(mode="json")
        return result, PreprocessingReport(
            input_rows=len(frame),
            output_rows=len(result),
            input_columns=list(frame.columns),
            output_columns=list(result.columns),
            stages=stages,
        )

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        result = frame
        if self.cleaning:
            result, _ = self.cleaning.clean(result)
        if self.imputation:
            result = self.imputation.transform(result)
        if self.outliers:
            result, _ = self.outliers.transform(result)
        if self.encoding:
            result, _ = self.encoding.transform(result)
        if self.scaling:
            result, _ = self.scaling.transform(result)
        if self.selection:
            result, _ = self.selection.transform(result)
        return result
