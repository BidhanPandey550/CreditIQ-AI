"""Compose local explanations and counterfactuals into a decision summary."""

from creditiq_ai.explainability.counterfactual.models import CounterfactualResult
from creditiq_ai.explainability.decision_summary.models import DecisionSummary
from creditiq_ai.explainability.explainers.result import LocalExplanation


class DecisionSummaryService:
    def create(
        self,
        *,
        credit_score: int,
        risk_level: str,
        recommendation: str,
        confidence: float,
        local: LocalExplanation,
        counterfactual: CounterfactualResult,
    ) -> DecisionSummary:
        explanation = local.explanation
        return DecisionSummary(
            credit_score=credit_score,
            probability_of_default=explanation.prediction,
            risk_level=risk_level,
            recommendation=recommendation,
            confidence=confidence,
            primary_factors=[item.feature for item in explanation.top_contributors],
            key_risks=[item.feature for item in explanation.positive_contributors],
            positive_strengths=[item.feature for item in explanation.negative_contributors],
            suggested_improvements=[item.guidance for item in counterfactual.suggestions],
            model_version=local.model_version,
            feature_version=local.feature_version,
        )
