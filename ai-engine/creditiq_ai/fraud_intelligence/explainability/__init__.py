"""Business-friendly fraud explanation generation."""

from creditiq_ai.fraud_intelligence.explainability.service import FraudExplanationService
from creditiq_ai.fraud_intelligence.explainability.models import FraudExplanation

__all__ = ["FraudExplanation", "FraudExplanationService"]
