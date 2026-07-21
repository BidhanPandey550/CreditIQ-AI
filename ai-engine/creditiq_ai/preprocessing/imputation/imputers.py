"""Imputation strategies.

Purpose:  Concrete, interchangeable missing-value strategies (SRP). Univariate ones store
          per-column statistics; multivariate ones wrap scikit-learn imputers.
Inputs:   DataFrame subset + params (from YAML).
Outputs:  imputed DataFrame subset.
Deps:     pandas, numpy, scikit-learn.
Extend:   add a class here + register it in factory.py.
"""

from __future__ import annotations

import pandas as pd

from creditiq_ai.preprocessing.imputation.base import BaseImputer


class _UnivariateStatImputer(BaseImputer):
    """Shared machinery for per-column constant/statistic imputers."""

    def _statistic(self, series: pd.Series):  # pragma: no cover - overridden
        raise NotImplementedError

    def fit(self, df: pd.DataFrame) -> "BaseImputer":
        self._fills = {col: self._statistic(df[col]) for col in df.columns}
        self._fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        self._check_fitted()
        out = df.copy()
        for col, value in self._fills.items():
            if col in out.columns and value is not None:
                out[col] = out[col].fillna(value)
        return out


class MeanImputer(_UnivariateStatImputer):
    numeric_only = True

    def _statistic(self, series: pd.Series):
        return float(pd.to_numeric(series, errors="coerce").mean())


class MedianImputer(_UnivariateStatImputer):
    numeric_only = True

    def _statistic(self, series: pd.Series):
        return float(pd.to_numeric(series, errors="coerce").median())


class ModeImputer(_UnivariateStatImputer):
    """Most-frequent value; works for numeric and categorical columns."""

    def _statistic(self, series: pd.Series):
        mode = series.mode(dropna=True)
        return mode.iloc[0] if not mode.empty else None


class ConstantImputer(_UnivariateStatImputer):
    """Fill with a configured constant (``fill_value``)."""

    def _statistic(self, series: pd.Series):
        return self.params.get("fill_value", 0)


class ForwardFillImputer(BaseImputer):
    def fit(self, df: pd.DataFrame) -> "BaseImputer":
        self._fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        self._check_fitted()
        return df.ffill(limit=self.params.get("limit"))


class BackwardFillImputer(BaseImputer):
    def fit(self, df: pd.DataFrame) -> "BaseImputer":
        self._fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        self._check_fitted()
        return df.bfill(limit=self.params.get("limit"))


class KNNImputerStrategy(BaseImputer):
    """Multivariate KNN imputation over the numeric block (scikit-learn)."""

    supports_multivariate = True
    numeric_only = True

    def fit(self, df: pd.DataFrame) -> "BaseImputer":
        from sklearn.impute import KNNImputer

        self._columns = list(df.columns)
        self._imputer = KNNImputer(n_neighbors=int(self.params.get("n_neighbors", 5)))
        self._imputer.fit(df[self._columns].to_numpy(dtype=float))
        self._fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        self._check_fitted()
        out = df.copy()
        values = self._imputer.transform(out[self._columns].to_numpy(dtype=float))
        out[self._columns] = pd.DataFrame(values, columns=self._columns, index=out.index)
        return out


class IterativeImputerStrategy(BaseImputer):
    """Multivariate iterative (MICE-style) imputation over the numeric block (scikit-learn)."""

    supports_multivariate = True
    numeric_only = True

    def fit(self, df: pd.DataFrame) -> "BaseImputer":
        from sklearn.experimental import enable_iterative_imputer  # noqa: F401
        from sklearn.impute import IterativeImputer

        self._columns = list(df.columns)
        self._imputer = IterativeImputer(
            max_iter=int(self.params.get("max_iter", 10)),
            random_state=int(self.params.get("random_state", 42)),
        )
        self._imputer.fit(df[self._columns].to_numpy(dtype=float))
        self._fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        self._check_fitted()
        out = df.copy()
        values = self._imputer.transform(out[self._columns].to_numpy(dtype=float))
        out[self._columns] = pd.DataFrame(values, columns=self._columns, index=out.index)
        return out
