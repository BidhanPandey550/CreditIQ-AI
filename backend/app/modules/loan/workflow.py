"""Tenant-configurable workflow policy constrained by the mandatory lending safety graph."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.shared.enums import LOAN_TRANSITIONS, LoanStatus


class LoanWorkflowSettings(BaseModel):
    """Governed tenant choices that cannot bypass AI or fraud screening stages."""

    analyst_review_policy: Literal["optional", "required", "amount_threshold"] = "optional"
    analyst_review_amount_threshold: float | None = Field(default=None, gt=0)
    allow_needs_more_information: bool = True
    allow_default_classification: bool = True

    @model_validator(mode="after")
    def validate_threshold_policy(self) -> "LoanWorkflowSettings":
        if self.analyst_review_policy == "amount_threshold":
            if self.analyst_review_amount_threshold is None:
                raise ValueError("Analyst review amount threshold is required for threshold policy")
        elif self.analyst_review_amount_threshold is not None:
            raise ValueError("Analyst review amount threshold is valid only for threshold policy")
        return self


class LoanWorkflowPolicy:
    """Resolve allowed transitions from immutable safety rules and tenant configuration."""

    def __init__(self, settings: LoanWorkflowSettings) -> None:
        self.settings = settings

    def allowed(self, current: LoanStatus, *, amount: Decimal | float) -> set[LoanStatus]:
        allowed = set(LOAN_TRANSITIONS.get(current, set()))
        if not self.settings.allow_needs_more_information:
            allowed.discard(LoanStatus.needs_more_info)
        if not self.settings.allow_default_classification:
            allowed.discard(LoanStatus.defaulted)
        if current is LoanStatus.officer_review and self._analyst_required(amount):
            allowed.discard(LoanStatus.approved)
            allowed.discard(LoanStatus.rejected)
        return allowed

    def _analyst_required(self, amount: Decimal | float) -> bool:
        policy = self.settings.analyst_review_policy
        if policy == "required":
            return True
        if policy == "amount_threshold":
            threshold = self.settings.analyst_review_amount_threshold
            return threshold is not None and float(amount) >= threshold
        return False
