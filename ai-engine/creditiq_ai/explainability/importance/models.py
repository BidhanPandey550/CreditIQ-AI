"""Typed global importance report."""

from pydantic import BaseModel, ConfigDict, Field


class ImportanceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    feature: str
    rank: int = Field(ge=1)
    importance: float = Field(ge=0.0)
    standard_deviation: float = Field(ge=0.0)
    stability: float = Field(ge=0.0, le=1.0)


class GlobalImportanceReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: str
    features: list[ImportanceItem]
    sample_count: int
    model_version: str | None = None
    feature_version: str | None = None
