"""Typed financial-behaviour inputs and outputs."""

from pydantic import BaseModel, ConfigDict, Field


class BehaviourInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    monthly_income: list[float] = Field(default_factory=list)
    monthly_expenses: list[float] = Field(default_factory=list)
    monthly_savings: list[float] = Field(default_factory=list)
    monthly_debt_payments: list[float] = Field(default_factory=list)
    transaction_counts: list[int] = Field(default_factory=list)


class BehaviourRiskProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    risk_score: float = Field(ge=0.0, le=1.0)
    indicators: dict[str, float]
    data_completeness: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
