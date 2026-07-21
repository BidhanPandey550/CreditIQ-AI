"""Training dataset abstraction.

Purpose:  A typed, immutable holder for a supervised training dataset (features + target +
          metadata) so trainers receive a consistent, self-describing object rather than loose
          arrays. Carries a version so a trained model can record what data it saw.
Inputs:   feature matrix (DataFrame) + target (Series/array) + names.
Outputs:  CreditDataset; optional train/test split.
Deps:     pandas, numpy, scikit-learn (split).
Extend:   add loaders (CSV/DB) that return CreditDataset — trainers stay unaware of the source.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CreditDataset:
    X: pd.DataFrame
    y: pd.Series
    feature_names: list[str] = field(default_factory=list)
    name: str = "credit_dataset"

    def __post_init__(self) -> None:
        if len(self.X) != len(self.y):
            raise ValueError("X and y must have the same number of rows")
        if not self.feature_names:
            object.__setattr__(self, "feature_names", list(self.X.columns))

    @property
    def n_rows(self) -> int:
        return len(self.X)

    @property
    def n_features(self) -> int:
        return len(self.feature_names)

    @property
    def version(self) -> str:
        """Deterministic content hash — identifies the exact data a model was trained on."""
        digest = hashlib.sha256(
            pd.util.hash_pandas_object(self.X, index=True).values.tobytes()
            + np.asarray(self.y).tobytes()
        )
        return digest.hexdigest()[:16]

    def split(self, test_size: float, random_seed: int) -> tuple["CreditDataset", "CreditDataset"]:
        """Stratified train/test split (used by holdout evaluation in later modules)."""
        from sklearn.model_selection import train_test_split

        X_tr, X_te, y_tr, y_te = train_test_split(
            self.X, self.y, test_size=test_size, random_state=random_seed, stratify=self.y
        )
        train = CreditDataset(
            X_tr.reset_index(drop=True),
            y_tr.reset_index(drop=True),
            self.feature_names,
            f"{self.name}:train",
        )
        test = CreditDataset(
            X_te.reset_index(drop=True),
            y_te.reset_index(drop=True),
            self.feature_names,
            f"{self.name}:test",
        )
        return train, test
