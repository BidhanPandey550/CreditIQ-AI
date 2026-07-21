"""Training context — the dependency-injection container for one training run.

Purpose:  Bundle everything a trainer needs (dataset + run config) into one object so trainers
          depend on an abstraction, not on globals. One context per (dataset, config) pair.
Inputs:   CreditDataset + TrainingConfig.
Outputs:  TrainingContext.
Deps:     datasets.CreditDataset, trainers.config.TrainingConfig.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from creditiq_ai.credit_intelligence.datasets.dataset import CreditDataset
from creditiq_ai.credit_intelligence.trainers.config import TrainingConfig


@dataclass(frozen=True)
class TrainingContext:
    dataset: CreditDataset
    config: TrainingConfig

    @property
    def X(self) -> pd.DataFrame:
        return self.dataset.X

    @property
    def y(self) -> pd.Series:
        return self.dataset.y

    @property
    def feature_names(self) -> list[str]:
        return self.dataset.feature_names
