"""Typed business-rule evaluation results."""

from pydantic import BaseModel, ConfigDict, Field


class RuleResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_name: str
    triggered: bool
    priority: int
    severity: str
    action: str
    explanation: str
    observed_value: object | None = None


class RuleEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True)

    results: list[RuleResult]
    triggered: list[RuleResult]
    recommended_action: str
    stopped_early: bool = False
    warnings: list[str] = Field(default_factory=list)
