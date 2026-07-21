"""Typed identity validation result."""

from pydantic import BaseModel, ConfigDict, Field


class IdentityValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    risk_score: float = Field(ge=0.0, le=1.0)
    missing_fields: list[str] = Field(default_factory=list)
    mismatches: list[str] = Field(default_factory=list)
    duplicate_suspected: bool = False
    flags: list[str] = Field(default_factory=list)
