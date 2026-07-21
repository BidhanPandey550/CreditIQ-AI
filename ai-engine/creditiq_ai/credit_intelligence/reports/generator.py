"""Atomic JSON and Markdown reporting for a completed credit training run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from creditiq_ai.core.base import BaseComponent
from creditiq_ai.credit_intelligence.evaluation.models import CreditEvaluationReport
from creditiq_ai.credit_intelligence.evaluation.comparison_models import ModelComparisonReport
from creditiq_ai.credit_intelligence.reports.models import ReportArtifact
from creditiq_ai.credit_intelligence.trainers.result import TrainingResult


class CreditReportGenerator(BaseComponent):
    """Render audit-friendly reports without coupling training to a presentation framework."""

    def generate(
        self,
        destination: str | Path,
        *,
        training: list[TrainingResult],
        evaluations: list[CreditEvaluationReport],
        comparison: ModelComparisonReport,
        formats: tuple[str, ...] = ("json", "markdown"),
    ) -> list[ReportArtifact]:
        output = Path(destination)
        output.mkdir(parents=True, exist_ok=True)
        payload = self._payload(training, evaluations, comparison)
        artifacts: list[ReportArtifact] = []
        for report_format in formats:
            if report_format == "json":
                path = self._atomic_write(
                    output / "credit-training-report.json", json.dumps(payload, indent=2)
                )
                artifacts.append(
                    ReportArtifact(format="json", path=path, media_type="application/json")
                )
            elif report_format == "markdown":
                path = self._atomic_write(
                    output / "credit-training-report.md", self._markdown(payload)
                )
                artifacts.append(
                    ReportArtifact(format="markdown", path=path, media_type="text/markdown")
                )
            else:
                raise ValueError(f"Unsupported report format '{report_format}'")
        self.logger.info("Generated {} credit training report artifact(s)", len(artifacts))
        return artifacts

    @staticmethod
    def _payload(
        training: list[TrainingResult],
        evaluations: list[CreditEvaluationReport],
        comparison: ModelComparisonReport,
    ) -> dict[str, Any]:
        return {
            "summary": {
                "models_trained": len(training),
                "models_evaluated": len(evaluations),
                "selected_model": comparison.selected_model,
                "selected_version": comparison.selected_version,
                "compared_at": comparison.compared_at.isoformat(),
            },
            "training": [item.model_dump(mode="json") for item in training],
            "evaluations": [item.model_dump(mode="json") for item in evaluations],
            "leaderboard": [item.model_dump(mode="json") for item in comparison.leaderboard],
        }

    @staticmethod
    def _markdown(payload: dict[str, Any]) -> str:
        summary = payload["summary"]
        lines = [
            "# Credit Intelligence Training Report",
            "",
            f"- Models trained: {summary['models_trained']}",
            f"- Models evaluated: {summary['models_evaluated']}",
            f"- Selected model: `{summary['selected_model']}`",
            f"- Selected version: `{summary['selected_version'] or 'unversioned'}`",
            f"- Compared at: {summary['compared_at']}",
            "",
            "## Leaderboard",
            "",
            "| Rank | Model | Version | Composite score | Eligible | Failed gates |",
            "|---:|---|---|---:|:---:|---|",
        ]
        for entry in payload["leaderboard"]:
            failed = ", ".join(entry["failed_gates"]) or "—"
            lines.append(
                f"| {entry['rank']} | {entry['model_name']} | {entry['model_version'] or '—'} | "
                f"{entry['composite_score']:.6f} | {entry['eligible']} | {failed} |"
            )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _atomic_write(path: Path, content: str) -> Path:
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
        return path
