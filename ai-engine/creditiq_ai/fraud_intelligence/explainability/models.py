"""Structured fraud explanation item."""

from pydantic import BaseModel, ConfigDict


class FraudExplanation(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str
    code: str
    severity: str
    message: str
