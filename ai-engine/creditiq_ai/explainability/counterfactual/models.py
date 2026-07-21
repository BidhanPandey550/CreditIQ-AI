"""Typed counterfactual guidance result."""

from pydantic import BaseModel, ConfigDict, Field


class CounterfactualSuggestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    feature: str
    current_value: float
    suggested_value: float
    resulting_probability: float = Field(ge=0.0, le=1.0)
    target_reached: bool
    guidance: str


class CounterfactualResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    original_probability: float = Field(ge=0.0, le=1.0)
    target_probability: float = Field(ge=0.0, le=1.0)
    suggestions: list[CounterfactualSuggestion]
