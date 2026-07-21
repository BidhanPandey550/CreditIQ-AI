"""Automatic, deterministic model comparison and champion selection."""

from __future__ import annotations

from creditiq_ai.core.base import BaseComponent
from creditiq_ai.credit_intelligence.evaluation.comparison_models import (
    LOSS_METRICS,
    ComparisonConfig,
    LeaderboardEntry,
    ModelComparisonReport,
)
from creditiq_ai.credit_intelligence.evaluation.models import CreditEvaluationReport
from creditiq_ai.exceptions import ValidationError


class ModelComparisonService(BaseComponent):
    """Rank evaluation reports using weighted metrics and hard policy gates."""

    def __init__(self, config: ComparisonConfig | None = None) -> None:
        super().__init__()
        self.comparison_config = config or ComparisonConfig()

    def compare(self, reports: list[CreditEvaluationReport]) -> ModelComparisonReport:
        if not reports:
            raise ValidationError("At least one evaluation report is required")
        identities = [(report.model_name, report.model_version) for report in reports]
        if len(set(identities)) != len(identities):
            raise ValidationError("Model name and version pairs must be unique")

        candidates = [self._candidate(report) for report in reports]
        eligible = [candidate for candidate in candidates if candidate[1]]
        if self.comparison_config.require_eligible_model and not eligible:
            raise ValidationError("No model satisfies the configured eligibility gates")

        candidates.sort(key=lambda item: (-int(item[1]), -item[0], item[2].model_name))
        leaderboard = [
            LeaderboardEntry(
                rank=index,
                model_name=report.model_name,
                model_version=report.model_version,
                composite_score=round(score, 8),
                eligible=is_eligible,
                failed_gates=failed_gates,
                metrics={
                    name: self._metric(report, name)
                    for name in self.comparison_config.metric_weights
                },
            )
            for index, (score, is_eligible, report, failed_gates) in enumerate(candidates, start=1)
        ]
        selected = next((entry for entry in leaderboard if entry.eligible), leaderboard[0])
        self.logger.info(
            "Compared {} models | selected={} version={} score={:.4f}",
            len(reports),
            selected.model_name,
            selected.model_version or "unversioned",
            selected.composite_score,
        )
        return ModelComparisonReport(
            leaderboard=leaderboard,
            selected_model=selected.model_name,
            selected_version=selected.model_version,
        )

    def _candidate(
        self, report: CreditEvaluationReport
    ) -> tuple[float, bool, CreditEvaluationReport, list[str]]:
        total_weight = sum(self.comparison_config.metric_weights.values())
        score = (
            sum(
                self._normalized(name, self._metric(report, name)) * weight
                for name, weight in self.comparison_config.metric_weights.items()
            )
            / total_weight
        )
        failed = [
            f"{name}<{minimum}"
            for name, minimum in self.comparison_config.minimum_metrics.items()
            if self._metric(report, name) < minimum
        ]
        failed.extend(
            f"{name}>{maximum}"
            for name, maximum in self.comparison_config.maximum_metrics.items()
            if self._metric(report, name) > maximum
        )
        return score, not failed, report, failed

    @staticmethod
    def _metric(report: CreditEvaluationReport, name: str) -> float:
        return float(getattr(report, name))

    @staticmethod
    def _normalized(name: str, value: float) -> float:
        if name in LOSS_METRICS:
            return 1.0 / (1.0 + max(0.0, value))
        if name == "matthews_correlation":
            return (value + 1.0) / 2.0
        return value
