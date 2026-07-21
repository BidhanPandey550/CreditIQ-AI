"""LocalExplanation — the audit-ready wrapper around the frozen core Explanation contract.

Purpose:  Enrich `core.schemas.Explanation` (contribution-level detail) with XAI metadata (method,
          confidence text, model/feature versions, completeness) for APIs, UIs, and audit reports —
          without modifying the frozen Sprint-1 schema.
Deps:     pydantic v2; core.schemas.Explanation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from creditiq_ai.core.schemas import Explanation


class LocalExplanation(BaseModel):
    explanation: Explanation
    method: str
    confidence_explanation: str | None = None
    complete: bool = True
    issues: list[str] = Field(default_factory=list)
    model_version: str | None = None
    feature_version: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
