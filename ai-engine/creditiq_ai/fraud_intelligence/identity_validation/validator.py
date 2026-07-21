"""Extensible local identity consistency checks with a duplicate-detection hook."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from creditiq_ai.config.models import IdentityConsistencyConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.exceptions import ConfigurationError
from creditiq_ai.fraud_intelligence.identity_validation.models import IdentityValidationResult

DuplicateCheck = Callable[[Mapping[str, Any]], bool]


class IdentityValidator(BaseComponent):
    def __init__(
        self,
        config: IdentityConsistencyConfig,
        *,
        duplicate_check: DuplicateCheck | None = None,
    ) -> None:
        super().__init__()
        self.identity_config = config
        self.duplicate_check = duplicate_check
        if any(len(pair) != 2 for pair in config.matching_field_pairs):
            raise ConfigurationError(
                "Identity matching_field_pairs must contain exactly two fields"
            )

    def validate(self, identity: Mapping[str, Any]) -> IdentityValidationResult:
        config = self.identity_config
        missing = sorted(
            field
            for field in config.required_fields
            if field not in identity or identity[field] in (None, "")
        )
        mismatches = [
            f"{left}!={right}"
            for left, right in config.matching_field_pairs
            if identity.get(left) not in (None, "")
            and identity.get(right) not in (None, "")
            and identity[left] != identity[right]
        ]
        duplicate = bool(self.duplicate_check(identity)) if self.duplicate_check else False
        risk = min(
            1.0,
            len(missing) * config.missing_field_penalty
            + len(mismatches) * config.mismatch_penalty
            + (config.duplicate_penalty if duplicate else 0.0),
        )
        flags = [
            *(f"missing_identity:{field}" for field in missing),
            *(f"identity_mismatch:{pair}" for pair in mismatches),
        ]
        if duplicate:
            flags.append("duplicate_identity_suspected")
        return IdentityValidationResult(
            risk_score=round(risk, 4),
            missing_fields=missing,
            mismatches=mismatches,
            duplicate_suspected=duplicate,
            flags=flags,
        )
