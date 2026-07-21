"""Priority-ordered, configuration-driven credit business-rule engine."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from creditiq_ai.config.models import CreditRuleSpec, CreditRulesConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.credit_intelligence.business_rules.models import RuleEvaluation, RuleResult
from creditiq_ai.exceptions import ConfigurationError


class CreditBusinessRuleEngine(BaseComponent):
    """Evaluate declarative rules without embedding lender thresholds in code."""

    _operators: dict[str, Callable[[Any, Any], bool]] = {
        "lt": lambda actual, expected: actual < expected,
        "lte": lambda actual, expected: actual <= expected,
        "gt": lambda actual, expected: actual > expected,
        "gte": lambda actual, expected: actual >= expected,
        "eq": lambda actual, expected: actual == expected,
        "neq": lambda actual, expected: actual != expected,
        "in": lambda actual, expected: actual in expected,
        "not_in": lambda actual, expected: actual not in expected,
    }

    def __init__(self, config: CreditRulesConfig) -> None:
        super().__init__()
        self.rules_config = config
        unknown = {rule.operator for rule in config.rules} - set(self._operators)
        if unknown:
            raise ConfigurationError(f"Unsupported credit rule operators: {sorted(unknown)}")

    def evaluate(self, applicant: Mapping[str, Any]) -> RuleEvaluation:
        results: list[RuleResult] = []
        warnings: list[str] = []
        stopped = False
        for rule in sorted(
            (item for item in self.rules_config.rules if item.enabled),
            key=lambda item: (item.priority, item.name),
        ):
            result = self._evaluate_rule(rule, applicant, warnings)
            results.append(result)
            if result.triggered and result.action in self.rules_config.stop_actions:
                stopped = True
                break
        triggered = [result for result in results if result.triggered]
        action = triggered[0].action if triggered else "proceed"
        return RuleEvaluation(
            results=results,
            triggered=triggered,
            recommended_action=action,
            stopped_early=stopped,
            warnings=warnings,
        )

    def _evaluate_rule(
        self, rule: CreditRuleSpec, applicant: Mapping[str, Any], warnings: list[str]
    ) -> RuleResult:
        if rule.field not in applicant or applicant[rule.field] is None:
            warnings.append(f"missing_rule_field:{rule.field}")
            return RuleResult(
                rule_name=rule.name,
                triggered=False,
                priority=rule.priority,
                severity=rule.severity,
                action=rule.action,
                explanation=rule.explanation,
            )
        actual = applicant[rule.field]
        try:
            triggered = self._operators[rule.operator](actual, rule.value)
        except (TypeError, ValueError) as exc:
            raise ConfigurationError(
                f"Rule '{rule.name}' could not compare field '{rule.field}'",
                context={"actual": actual, "expected": rule.value},
            ) from exc
        return RuleResult(
            rule_name=rule.name,
            triggered=triggered,
            priority=rule.priority,
            severity=rule.severity,
            action=rule.action,
            explanation=rule.explanation.format(
                field=rule.field, actual=actual, expected=rule.value
            ),
            observed_value=actual,
        )
