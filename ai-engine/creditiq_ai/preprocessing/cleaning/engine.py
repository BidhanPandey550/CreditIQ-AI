"""Data cleaning engine — orchestrates independent cleaners from injected configuration.

Purpose:  Run a configured, ordered sequence of cleaning strategies and produce an aggregate
          CleaningReport. The config is injected (from the unified EngineConfig.cleaning) — the
          engine never loads YAML itself.
Inputs:   DataFrame + CleaningConfig.
Outputs:  (cleaned DataFrame, CleaningReport).
Deps:     config.models.CleaningConfig; cleaning.factory / .base.
Extend:   reorder/toggle steps in config/base.yaml; add cleaners via the factory.
"""

from __future__ import annotations

import pandas as pd

from creditiq_ai.config.models import CleaningConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.preprocessing.cleaning.base import CleaningReport
from creditiq_ai.preprocessing.cleaning.factory import CleanerFactory


class DataCleaningEngine(BaseComponent):
    """Applies configured cleaners in order and reports what changed."""

    def __init__(
        self, config: CleaningConfig | None = None, factory: type[CleanerFactory] = CleanerFactory
    ) -> None:
        super().__init__()
        self._config = config or CleaningConfig()
        self._cleaners = [
            factory.create(step.name, step.params) for step in self._config.steps if step.enabled
        ]

    def clean(self, df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
        initial_rows = len(df)
        current = df.copy()  # single defensive copy reused by every step (perf)
        steps = []
        for cleaner in self._cleaners:
            current, step_report = cleaner.clean(current, copy=False)
            steps.append(step_report)
        report = CleaningReport(initial_rows=initial_rows, final_rows=len(current), steps=steps)
        self.logger.info(
            f"Cleaning complete: {len(steps)} step(s), {report.rows_removed} row(s) removed"
        )
        return current, report
