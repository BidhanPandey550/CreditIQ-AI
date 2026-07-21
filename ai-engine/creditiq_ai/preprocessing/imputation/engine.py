"""Missing Value Engine — resolves a strategy per column and applies it (fit/transform).

Purpose:  Impute missing values reproducibly: statistics are learned at fit() and reused at
          transform() (inference-safe). Univariate strategies run per column; multivariate
          strategies (KNN / Iterative) run over the numeric block together.
Inputs:   DataFrame + ImputationConfig.
Outputs:  imputed DataFrame; ImputationReport (fit_transform).
Deps:     pandas; imputation.factory / .config / .base.
Extend:   change strategies in YAML; add strategies via the factory.
"""

from __future__ import annotations

from collections import defaultdict

import pandas as pd
from pandas.api.types import is_numeric_dtype

from creditiq_ai.core.base import BaseComponent
from creditiq_ai.exceptions import PreprocessingError
from creditiq_ai.config.models import ImputationConfig
from creditiq_ai.preprocessing.imputation.base import (
    BaseImputer,
    ColumnImputation,
    ImputationReport,
)
from creditiq_ai.preprocessing.imputation.factory import ImputerFactory


class MissingValueEngine(BaseComponent):
    """Applies configured imputation strategies with train-time fitted statistics."""

    def __init__(
        self, config: ImputationConfig | None = None, factory: type[ImputerFactory] = ImputerFactory
    ) -> None:
        super().__init__()
        self._config = config or ImputationConfig()
        self._factory = factory
        self._groups: list[tuple[BaseImputer, list[str]]] = []
        self._resolved: dict[str, str] = {}
        self._fitted = False

    def _resolve(self, df: pd.DataFrame) -> dict[str, tuple[str, dict]]:
        resolved: dict[str, tuple[str, dict]] = {}
        for col in df.columns:
            if col in self._config.columns:
                spec = self._config.columns[col]
                resolved[col] = (spec.strategy, spec.params)
            elif is_numeric_dtype(df[col]):
                resolved[col] = (self._config.default_numeric, self._config.numeric_params)
            else:
                resolved[col] = (self._config.default_categorical, self._config.categorical_params)
        return resolved

    def fit(self, df: pd.DataFrame) -> "MissingValueEngine":
        resolved = self._resolve(df)
        univariate: dict[tuple, list[str]] = defaultdict(list)
        multivariate: dict[tuple, list[str]] = defaultdict(list)

        for col, (strategy, params) in resolved.items():
            cls = self._factory.strategy_class(strategy)
            if cls.numeric_only and not is_numeric_dtype(df[col]):
                raise PreprocessingError(
                    f"Strategy '{strategy}' requires a numeric column",
                    context={"column": col, "dtype": str(df[col].dtype)},
                )
            key = (strategy, tuple(sorted(params.items())))
            if cls.supports_multivariate:
                multivariate[key].append(col)  # features + targets together
            elif df[col].isna().any():
                univariate[key].append(col)  # only impute columns that need it

        self._groups = []
        self._resolved = {}
        for (strategy, params_items), cols in {**univariate, **multivariate}.items():
            imputer = self._factory.create(strategy, dict(params_items))
            imputer.fit(df[cols])
            self._groups.append((imputer, cols))
            self._resolved.update({c: strategy for c in cols})

        self._fitted = True
        self.logger.info(
            f"Imputation fitted: {len(self._groups)} group(s), {len(self._resolved)} column(s)"
        )
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise PreprocessingError("MissingValueEngine must be fitted before transform().")
        out = df.copy()
        for imputer, cols in self._groups:
            present = [c for c in cols if c in out.columns]
            if present:
                out[present] = imputer.transform(out[present])[present]
        return out

    def fit_transform(self, df: pd.DataFrame) -> tuple[pd.DataFrame, ImputationReport]:
        before = {c: int(df[c].isna().sum()) for c in df.columns}
        self.fit(df)
        transformed = self.transform(df)
        report = ImputationReport(
            columns=[
                ColumnImputation(
                    column=col,
                    strategy=self._resolved[col],
                    missing_before=before.get(col, 0),
                    missing_after=int(transformed[col].isna().sum()),
                )
                for col in self._resolved
            ]
        )
        self.logger.info(f"Imputation complete: {report.total_imputed} value(s) imputed")
        return transformed, report
