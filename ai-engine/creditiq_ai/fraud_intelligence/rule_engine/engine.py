"""Fraud-specific façade over the canonical declarative rule evaluator."""

from collections.abc import Mapping
from typing import Any

from creditiq_ai.config.models import CreditRulesConfig
from creditiq_ai.credit_intelligence.business_rules import CreditBusinessRuleEngine, RuleEvaluation


class FraudRuleEngine:
    """Expose fraud semantics without duplicating rule comparison and priority logic."""

    def __init__(self, config: CreditRulesConfig) -> None:
        self._engine = CreditBusinessRuleEngine(config)

    def evaluate(self, application: Mapping[str, Any]) -> RuleEvaluation:
        return self._engine.evaluate(application)
