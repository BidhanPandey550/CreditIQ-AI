"""Outcome-aware model performance monitor."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score

from creditiq_ai.config.models import MonitoringConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.exceptions import PerformanceMonitoringError
from creditiq_ai.model_operations.performance.models import PerformanceSnapshot


class PerformanceMonitor(BaseComponent):
    """Evaluate delayed labels against a configured production baseline."""

    def __init__(self, config: MonitoringConfig) -> None:
        super().__init__()
        self._config = config

    def evaluate(
        self, y_true: np.ndarray, probabilities: np.ndarray, *, baseline: float
    ) -> PerformanceSnapshot:
        if len(y_true) < self._config.minimum_performance_samples:
            raise PerformanceMonitoringError(
                "Insufficient labelled outcomes for performance monitoring",
                context={"minimum": self._config.minimum_performance_samples},
            )
        if len(y_true) != len(probabilities) or len(np.unique(y_true)) < 2:
            raise PerformanceMonitoringError("Performance inputs are incompatible")
        if self._config.performance_metric != "roc_auc":
            raise PerformanceMonitoringError(
                "Unsupported performance metric",
                context={"metric": self._config.performance_metric},
            )
        current = float(roc_auc_score(y_true, probabilities))
        drop = baseline - current
        status = (
            "critical"
            if drop >= self._config.performance_critical_drop
            else "warning"
            if drop >= self._config.performance_warning_drop
            else "healthy"
        )
        return PerformanceSnapshot(
            metric=self._config.performance_metric,
            baseline=baseline,
            current=round(current, 6),
            change=round(current - baseline, 6),
            status=status,
            sample_count=len(y_true),
        )
