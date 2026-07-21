"""Inference boundary validation without business-rule duplication."""

from __future__ import annotations

from typing import Any

import pandas as pd

from creditiq_ai.exceptions import ValidationError


class InferenceValidator:
    """Validate shape, required keys, finite values and expected input schema."""

    def __init__(
        self, *, required: list[str] | None = None, expected: list[str] | None = None
    ) -> None:
        self._required = required or []
        self._expected = expected

    def validate(self, features: dict[str, Any]) -> pd.DataFrame:
        if not features:
            raise ValidationError("Inference features cannot be empty")
        missing = sorted(set(self._required) - set(features))
        if missing:
            raise ValidationError(
                "Required inference features are missing", context={"columns": missing}
            )
        if self._expected is not None:
            unknown = sorted(set(features) - set(self._expected))
            if unknown:
                raise ValidationError("Unexpected inference features", context={"columns": unknown})
        frame = pd.DataFrame([features])
        if len(frame) != 1:
            raise ValidationError("Inference request must contain exactly one row")
        return frame
