"""Promotion policy evaluation result."""

from pydantic import BaseModel, ConfigDict, Field


class PromotionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    approved: bool
    reasons: list[str] = Field(default_factory=list)
    candidate_version: str
    incumbent_version: str | None = None
