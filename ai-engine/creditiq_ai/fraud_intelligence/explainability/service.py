"""Configuration-template-based fraud explanations."""

from creditiq_ai.config.models import FraudExplanationConfig
from creditiq_ai.credit_intelligence.business_rules import RuleEvaluation
from creditiq_ai.fraud.detectors.result import FraudDetectionResult
from creditiq_ai.fraud_intelligence.behaviour_analysis import BehaviourRiskProfile
from creditiq_ai.fraud_intelligence.explainability.models import FraudExplanation
from creditiq_ai.fraud_intelligence.identity_validation import IdentityValidationResult
from creditiq_ai.fraud_intelligence.models.results import FraudScore


class FraudExplanationService:
    def __init__(self, config: FraudExplanationConfig) -> None:
        self.templates = config.templates

    def explain(
        self,
        *,
        anomaly: FraudDetectionResult,
        behaviour: BehaviourRiskProfile,
        identity: IdentityValidationResult,
        rules: RuleEvaluation,
        score: FraudScore,
        confidence: float,
    ) -> list[FraudExplanation]:
        explanations = [
            FraudExplanation(
                category="anomaly",
                code="detector_ensemble",
                severity="high" if anomaly.anomaly_detected else "informational",
                message=self.templates["anomaly"].format(
                    probability=anomaly.fraud_probability, agreement=anomaly.detector_agreement
                ),
            ),
            FraudExplanation(
                category="behaviour",
                code="behaviour_profile",
                severity="medium" if behaviour.risk_score >= 0.5 else "informational",
                message=self.templates["behaviour"].format(risk=behaviour.risk_score),
            ),
            FraudExplanation(
                category="identity",
                code="identity_consistency",
                severity="high" if identity.risk_score >= 0.5 else "informational",
                message=self.templates["identity"].format(risk=identity.risk_score),
            ),
        ]
        explanations.extend(
            FraudExplanation(
                category="rule",
                code=result.rule_name,
                severity=result.severity,
                message=result.explanation,
            )
            for result in rules.triggered
        )
        explanations.append(
            FraudExplanation(
                category="summary",
                code="fraud_summary",
                severity=score.fraud_risk_level.value,
                message=self.templates["summary"].format(
                    level=score.fraud_risk_level.value,
                    score=score.fraud_score,
                    confidence=confidence,
                ),
            )
        )
        return explanations
