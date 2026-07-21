"""Aggregate operational, drift and performance state into model health."""

from creditiq_ai.model_operations.drift import DriftReport
from creditiq_ai.model_operations.health.models import ModelHealthReport
from creditiq_ai.model_operations.monitoring import MonitoringSnapshot
from creditiq_ai.model_operations.performance import PerformanceSnapshot


class ModelHealthService:
    """Deterministically combine independent monitoring signals."""

    def evaluate(
        self,
        operational: MonitoringSnapshot,
        *,
        drift: DriftReport | None = None,
        performance: PerformanceSnapshot | None = None,
    ) -> ModelHealthReport:
        statuses = [operational.status]
        reasons = list(operational.reasons)
        if drift is not None:
            statuses.append(drift.status)
            reasons.extend(f"drift:{feature}" for feature in drift.drifted_features)
        if performance is not None:
            statuses.append(performance.status)
            if performance.status != "healthy":
                reasons.append(f"performance:{performance.metric}")
        status = self._worst(statuses)
        return ModelHealthReport(
            status=status,
            operational_status=operational.status,
            drift_status=drift.status if drift else None,
            performance_status=performance.status if performance else None,
            reasons=list(dict.fromkeys(reasons)),
        )

    @staticmethod
    def _worst(statuses: list[str]) -> str:
        rank = {
            "unknown": 0,
            "healthy": 1,
            "stable": 1,
            "degraded": 2,
            "warning": 2,
            "unhealthy": 3,
            "critical": 3,
        }
        return max(statuses, key=lambda status: rank.get(status, 3))
