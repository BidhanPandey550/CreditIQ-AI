"""Atomic machine-readable and human-readable XAI audit reports."""

import json
from pathlib import Path

from creditiq_ai.explainability.decision_summary.models import DecisionSummary
from creditiq_ai.explainability.explainers.result import LocalExplanation
from creditiq_ai.explainability.importance.models import GlobalImportanceReport


class XAIAuditReportGenerator:
    def generate(
        self,
        destination: str | Path,
        *,
        summary: DecisionSummary,
        local: LocalExplanation,
        global_importance: GlobalImportanceReport,
    ) -> list[Path]:
        output = Path(destination)
        output.mkdir(parents=True, exist_ok=True)
        payload = {
            "decision_summary": summary.model_dump(mode="json"),
            "local_explanation": local.model_dump(mode="json"),
            "global_importance": global_importance.model_dump(mode="json"),
            "metadata": {
                "model_version": summary.model_version,
                "feature_version": summary.feature_version,
                "generated_at": local.generated_at.isoformat(),
                "explanation_method": local.method,
                "complete": local.complete,
                "issues": local.issues,
            },
        }
        json_path = self._write(output / "xai-audit-report.json", json.dumps(payload, indent=2))
        improvements = "\n".join(f"- {item}" for item in summary.suggested_improvements) or "- None"
        markdown = (
            "# Explainable Lending Decision\n\n"
            f"- Credit score: {summary.credit_score}\n"
            f"- Probability of default: {summary.probability_of_default}\n"
            f"- Risk level: {summary.risk_level}\n"
            f"- Recommendation: {summary.recommendation}\n"
            f"- Confidence: {summary.confidence}\n"
            f"- Model version: {summary.model_version or 'unversioned'}\n"
            f"- Feature version: {summary.feature_version or 'unversioned'}\n\n"
            f"## Decision narrative\n\n{local.explanation.narrative}\n\n"
            f"## Suggested improvements\n\n{improvements}\n"
        )
        markdown_path = self._write(output / "xai-audit-report.md", markdown)
        return [json_path, markdown_path]

    @staticmethod
    def _write(path: Path, content: str) -> Path:
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
        return path
