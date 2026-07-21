"""Base imputer (Strategy) + imputation report contracts.

Purpose:  Define the fit/transform imputer contract so statistics learned on training data are
          reused verbatim at inference (no leakage), and every strategy is interchangeable.
Inputs:   DataFrame subset (the columns the strategy owns).
Outputs:  imputed DataFrame subset; an ImputationReport from the engine.
Deps:     pandas, pydantic; core.base.BaseComponent.
Extend:   subclass BaseImputer, implement fit/transform, register it in factory.py.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from creditiq_ai.core.base import BaseComponent
from creditiq_ai.exceptions import ModelNotFittedError


class ColumnImputation(BaseModel):
    column: str
    strategy: str
    missing_before: int
    missing_after: int


class ImputationReport(BaseModel):
    columns: list[ColumnImputation] = Field(default_factory=list)

    @property
    def total_imputed(self) -> int:
        return sum(c.missing_before - c.missing_after for c in self.columns)


class BaseImputer(BaseComponent):
    """One imputation strategy. Univariate strategies store per-column statistics; multivariate
    strategies (KNN / Iterative) learn from the whole numeric block."""

    supports_multivariate: bool = False
    numeric_only: bool = False

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.params = params or {}
        self._fitted = False

    @abstractmethod
    def fit(self, df: pd.DataFrame) -> "BaseImputer": ...

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame: ...

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

    def _check_fitted(self) -> None:
        if not self._fitted:
            raise ModelNotFittedError(f"{self.name} must be fitted before transform().")
