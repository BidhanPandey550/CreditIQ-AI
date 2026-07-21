"""Module 3 — Feature engineering pipeline.

Purpose:  Instantiate the enabled feature generators from config and apply them in
          dependency order (a generator runs once all its inputs exist), so composite features
          like financial_behaviour_index resolve automatically.
Inputs:   DataFrame + FeaturesConfig.
Outputs:  DataFrame with engineered features; list of produced feature names.
Deps:     pandas; feature_engineering.registry; config.
Extend:   add a FeatureSpec to features.yaml — no code change needed.
"""

from __future__ import annotations

import pandas as pd

from creditiq_ai.config.models import FeaturesConfig
from creditiq_ai.core.base import BaseComponent, BaseFeatureGenerator
from creditiq_ai.core.exceptions import FeatureEngineeringError
from creditiq_ai.feature_engineering.registry import get_generator_class


class FeatureEngineeringPipeline(BaseComponent):
    """Applies configured feature generators with automatic dependency resolution."""

    def __init__(self, config: FeaturesConfig) -> None:
        super().__init__()
        self._generators: list[BaseFeatureGenerator] = [
            get_generator_class(spec.name)(params=spec.params)
            for spec in config.generators
            if spec.enabled
        ]
        self.produced_features: list[str] = []

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        pending = list(self._generators)
        out = df
        produced: list[str] = []

        # Iteratively run any generator whose input columns are all present.
        progress = True
        while pending and progress:
            progress = False
            still_pending: list[BaseFeatureGenerator] = []
            for gen in pending:
                if all(dep in out.columns for dep in gen.dependencies):
                    out = gen.generate(out)
                    produced.extend(gen.feature_names)
                    progress = True
                else:
                    still_pending.append(gen)
            pending = still_pending

        if pending:
            unresolved = {
                g.name: [d for d in g.dependencies if d not in out.columns] for g in pending
            }
            raise FeatureEngineeringError(
                "Unresolved feature dependencies", context={"unresolved": unresolved}
            )

        self.produced_features = produced
        self.logger.info(f"Generated {len(produced)} features: {produced}")
        return out

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        # Stateless (features are deterministic functions of inputs); provided for API symmetry.
        return self.transform(df)
