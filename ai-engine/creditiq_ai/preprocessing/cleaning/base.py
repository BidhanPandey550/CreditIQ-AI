"""Base cleaner (Strategy) + structured cleaning reports.

Purpose:  Define the independent-cleaner contract and the report objects the engine aggregates.
Inputs:   DataFrame.
Outputs:  cleaned DataFrame + CleaningStepReport.
Deps:     pandas, pydantic; core.base.BaseComponent.
Extend:   subclass BaseCleaner and implement _apply(); register it in the factory.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from creditiq_ai.core.base import BaseComponent


class CleaningStepReport(BaseModel):
    """What a single cleaner changed."""

    cleaner: str
    rows_before: int
    rows_after: int
    changes: dict[str, Any] = Field(default_factory=dict)


class CleaningReport(BaseModel):
    """Aggregate report across all cleaners in a run."""

    initial_rows: int
    final_rows: int
    steps: list[CleaningStepReport] = Field(default_factory=list)

    @property
    def rows_removed(self) -> int:
        return self.initial_rows - self.final_rows


class BaseCleaner(BaseComponent):
    """One independent cleaning operation (Strategy). Template method wraps reporting."""

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.params = params or {}

    def clean(self, df: pd.DataFrame, copy: bool = True) -> tuple[pd.DataFrame, CleaningStepReport]:
        """Clean `df`. Pass copy=False when the caller already owns a private copy (the engine
        copies once and reuses it across every step, avoiding N defensive copies)."""
        working = df.copy() if copy else df
        rows_before = len(working)
        cleaned, changes = self._apply(working)
        report = CleaningStepReport(
            cleaner=self.name, rows_before=rows_before, rows_after=len(cleaned), changes=changes
        )
        self.logger.info(f"{self.name} → {changes if changes else 'no changes'}")
        return cleaned, report

    @abstractmethod
    def _apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Return (cleaned_df, changes-summary). May mutate `df` in place — the caller decides
        whether a defensive copy was made (see `clean(copy=...)`)."""

    # --- shared helpers ---
    def _string_columns(self, df: pd.DataFrame) -> list[str]:
        configured = self.params.get("columns")
        if configured:
            return [c for c in configured if c in df.columns]
        return [c for c in df.columns if df[c].dtype == "object" or df[c].dtype == "string"]
