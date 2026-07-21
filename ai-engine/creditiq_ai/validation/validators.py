"""Module 1 — Dataset validation.

Purpose:  Fail fast on bad data. Each validator checks one rule and returns a ValidationReport;
          DatasetValidator composes them.
Inputs:   DataFrame + DataConfig.
Outputs:  ValidationReport (issues with severity; `passed` is False if any ERROR present).
Deps:     pandas; config.models.DataConfig; core.schemas.
Extend:   implement a new BaseValidator and add it to DatasetValidator.validators.
"""

from __future__ import annotations

import pandas as pd

from creditiq_ai.config.models import DataConfig
from creditiq_ai.core.base import BaseValidator
from creditiq_ai.core.enums import ValidationSeverity
from creditiq_ai.core.schemas import ValidationIssue, ValidationReport


def _report(df: pd.DataFrame, issues: list[ValidationIssue]) -> ValidationReport:
    passed = not any(i.severity == ValidationSeverity.ERROR for i in issues)
    return ValidationReport(passed=passed, n_rows=len(df), n_columns=df.shape[1], issues=issues)


class SchemaValidator(BaseValidator):
    """Required columns present + declared value ranges respected."""

    def __init__(self, data_config: DataConfig) -> None:
        super().__init__(config=data_config.model_dump())
        self._cfg = data_config

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        issues: list[ValidationIssue] = []
        for spec in self._cfg.columns:
            if spec.name not in df.columns:
                sev = ValidationSeverity.ERROR if spec.required else ValidationSeverity.WARNING
                issues.append(
                    ValidationIssue(
                        severity=sev,
                        rule="schema.missing_column",
                        message=f"Column '{spec.name}' is absent",
                        column=spec.name,
                    )
                )
                continue
            series = pd.to_numeric(df[spec.name], errors="coerce")
            if spec.min is not None:
                n = int((series < spec.min).sum())
                if n:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            rule="schema.below_min",
                            message=f"{n} values below min {spec.min}",
                            column=spec.name,
                            count=n,
                        )
                    )
            if spec.max is not None:
                n = int((series > spec.max).sum())
                if n:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            rule="schema.above_max",
                            message=f"{n} values above max {spec.max}",
                            column=spec.name,
                            count=n,
                        )
                    )
        return _report(df, issues)


class MissingValueValidator(BaseValidator):
    """Flag columns whose missing fraction exceeds the configured threshold."""

    def __init__(self, data_config: DataConfig) -> None:
        super().__init__(config=data_config.model_dump())
        self._cfg = data_config

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        issues: list[ValidationIssue] = []
        n = len(df) or 1
        for column in df.columns:
            frac = float(df[column].isna().sum()) / n
            if frac > self._cfg.max_missing_fraction:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        rule="missing.exceeds_threshold",
                        message=f"{frac:.0%} missing (> {self._cfg.max_missing_fraction:.0%})",
                        column=column,
                        count=int(df[column].isna().sum()),
                    )
                )
            elif frac > 0:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        rule="missing.present",
                        message=f"{frac:.0%} missing",
                        column=column,
                        count=int(df[column].isna().sum()),
                    )
                )
        return _report(df, issues)


class DuplicateValidator(BaseValidator):
    """Detect duplicate rows and duplicate identifiers."""

    def __init__(self, data_config: DataConfig) -> None:
        super().__init__(config=data_config.model_dump())
        self._cfg = data_config

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        issues: list[ValidationIssue] = []
        dup_rows = int(df.duplicated().sum())
        if dup_rows:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    rule="duplicate.rows",
                    message=f"{dup_rows} duplicate rows",
                    count=dup_rows,
                )
            )
        id_col = self._cfg.id_column
        if id_col in df.columns:
            dup_ids = int(df[id_col].duplicated().sum())
            if dup_ids:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        rule="duplicate.ids",
                        message=f"{dup_ids} duplicate '{id_col}' values",
                        column=id_col,
                        count=dup_ids,
                    )
                )
        return _report(df, issues)


class DTypeValidator(BaseValidator):
    """Detect values that cannot be coerced to a column's declared numeric dtype."""

    def __init__(self, data_config: DataConfig) -> None:
        super().__init__(config=data_config.model_dump())
        self._cfg = data_config

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        issues: list[ValidationIssue] = []
        for spec in self._cfg.columns:
            if spec.name not in df.columns or spec.dtype not in {"int", "float"}:
                continue
            coerced = pd.to_numeric(df[spec.name], errors="coerce")
            newly_null = int(coerced.isna().sum() - df[spec.name].isna().sum())
            if newly_null > 0:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        rule="dtype.uncoercible",
                        message=f"{newly_null} values not coercible to {spec.dtype}",
                        column=spec.name,
                        count=newly_null,
                    )
                )
        return _report(df, issues)


class DatasetValidator(BaseValidator):
    """Compose all validators into a single report."""

    def __init__(self, data_config: DataConfig) -> None:
        super().__init__(config=data_config.model_dump())
        self.validators: list[BaseValidator] = [
            SchemaValidator(data_config),
            MissingValueValidator(data_config),
            DuplicateValidator(data_config),
            DTypeValidator(data_config),
        ]

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        issues: list[ValidationIssue] = []
        for validator in self.validators:
            issues.extend(validator.validate(df).issues)
        report = _report(df, issues)
        status = "PASSED" if report.passed else "FAILED"
        self.logger.info(
            f"Validation {status}: {len(report.issues)} issue(s), {len(report.errors)} error(s)"
        )
        return report
