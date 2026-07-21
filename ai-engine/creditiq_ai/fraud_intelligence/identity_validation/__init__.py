"""Applicant identity-consistency validation."""

from creditiq_ai.fraud_intelligence.identity_validation.validator import (
    DuplicateCheck,
    IdentityValidator,
)
from creditiq_ai.fraud_intelligence.identity_validation.models import IdentityValidationResult

__all__ = ["DuplicateCheck", "IdentityValidationResult", "IdentityValidator"]
