"""Typed generated-report artifact metadata."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ReportArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    format: str
    path: Path
    media_type: str
