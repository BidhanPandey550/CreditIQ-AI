"""Audited model promotion orchestration."""

from creditiq_ai.exceptions import ModelNotFoundError, PromotionRejectedError
from creditiq_ai.model_operations.domain import LifecycleStage, ModelIdentity, ModelVersion
from creditiq_ai.model_operations.promotion.models import PromotionDecision
from creditiq_ai.model_operations.promotion.policy import PromotionPolicy
from creditiq_ai.model_operations.registry import FileModelRegistry


class PromotionService:
    """Apply promotion policy before entering production."""

    def __init__(self, registry: FileModelRegistry, policy: PromotionPolicy) -> None:
        self._registry = registry
        self._policy = policy

    def promote(
        self, candidate_ref: str, *, actor: str = "system", reason: str | None = None
    ) -> tuple[ModelVersion, PromotionDecision]:
        candidate = self._registry.get(candidate_ref)
        if candidate.stage is not LifecycleStage.CHAMPION:
            raise PromotionRejectedError(
                "Only a champion model can be promoted to production",
                context={"ref": candidate_ref, "stage": candidate.stage.value},
            )
        incumbent = self._production_or_none(candidate.identity)
        decision = self._policy.evaluate(candidate, incumbent)
        if not decision.approved:
            raise PromotionRejectedError(
                "Candidate failed promotion policy",
                context={"ref": candidate_ref, "reasons": decision.reasons},
            )
        promoted = self._registry.promote_to_production(candidate_ref, actor=actor, reason=reason)
        return promoted, decision

    def _production_or_none(self, identity: ModelIdentity) -> ModelVersion | None:
        try:
            return self._registry.production(identity)
        except ModelNotFoundError:
            return None
