"""Population Stability Index drift detector for numeric lending features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from creditiq_ai.config.models import MonitoringConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.exceptions import DriftDetectionError
from creditiq_ai.model_operations.drift.models import DriftReport, FeatureDrift


class PopulationStabilityDetector(BaseComponent):
    """Compare reference and current numeric distributions using robust PSI bins."""

    def __init__(self, config: MonitoringConfig) -> None:
        super().__init__()
        self._config = config

    def analyze(self, reference: pd.DataFrame, current: pd.DataFrame) -> DriftReport:
        common = sorted(set(reference.select_dtypes(include="number")) & set(current.columns))
        if not common:
            raise DriftDetectionError("No common numeric features are available for drift analysis")
        if min(len(reference), len(current)) < self._config.minimum_drift_samples:
            raise DriftDetectionError(
                "Insufficient samples for drift analysis",
                context={"minimum": self._config.minimum_drift_samples},
            )
        results = [
            self._feature(feature, reference[feature], current[feature]) for feature in common
        ]
        status = self._overall_status(results)
        return DriftReport(
            status=status,
            features=results,
            drifted_features=[item.feature for item in results if item.status != "stable"],
        )

    def _feature(self, name: str, reference: pd.Series, current: pd.Series) -> FeatureDrift:
        ref = reference.dropna().to_numpy(dtype=float)
        cur = current.dropna().to_numpy(dtype=float)
        if len(ref) == 0 or len(cur) == 0:
            raise DriftDetectionError("Feature has no comparable values", context={"feature": name})
        quantiles = np.linspace(0.0, 1.0, self._config.drift_bins + 1)
        edges = np.unique(np.quantile(ref, quantiles))
        if len(edges) < 2:
            edges = np.array([-np.inf, np.inf])
        else:
            edges[0], edges[-1] = -np.inf, np.inf
        ref_counts, _ = np.histogram(ref, bins=edges)
        cur_counts, _ = np.histogram(cur, bins=edges)
        epsilon = np.finfo(float).eps
        expected = np.clip(ref_counts / len(ref), epsilon, None)
        actual = np.clip(cur_counts / len(cur), epsilon, None)
        psi = float(np.sum((actual - expected) * np.log(actual / expected)))
        status = (
            "critical"
            if psi >= self._config.drift_critical_psi
            else "warning"
            if psi >= self._config.drift_warning_psi
            else "stable"
        )
        return FeatureDrift(
            feature=name,
            psi=round(psi, 6),
            status=status,
            reference_count=len(ref),
            current_count=len(cur),
        )

    @staticmethod
    def _overall_status(features: list[FeatureDrift]) -> str:
        statuses = {item.status for item in features}
        return (
            "critical"
            if "critical" in statuses
            else "warning"
            if "warning" in statuses
            else "stable"
        )
