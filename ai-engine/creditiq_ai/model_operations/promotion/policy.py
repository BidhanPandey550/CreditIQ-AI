"""Configuration-driven champion/challenger promotion policy."""

from creditiq_ai.config.models import MonitoringConfig
from creditiq_ai.model_operations.domain import ModelVersion
from creditiq_ai.model_operations.promotion.models import PromotionDecision


class PromotionPolicy:
    """Require absolute metric floors and bounded regression from the incumbent."""

    def __init__(self, config: MonitoringConfig) -> None:
        self._config = config

    def evaluate(
        self, candidate: ModelVersion, incumbent: ModelVersion | None = None
    ) -> PromotionDecision:
        reasons: list[str] = []
        metrics = candidate.metadata.metrics
        for metric, minimum in self._config.promotion_required_metrics.items():
            actual = metrics.get(metric)
            if actual is None or actual < minimum:
                reasons.append(f"{metric}_below_minimum")
        if incumbent is not None:
            for metric, allowed_drop in self._config.promotion_max_metric_drop.items():
                candidate_value = metrics.get(metric)
                incumbent_value = incumbent.metadata.metrics.get(metric)
                if (
                    candidate_value is not None
                    and incumbent_value is not None
                    and incumbent_value - candidate_value > allowed_drop
                ):
                    reasons.append(f"{metric}_regression")
        return PromotionDecision(
            approved=not reasons,
            reasons=reasons,
            candidate_version=candidate.version,
            incumbent_version=incumbent.version if incumbent else None,
        )
