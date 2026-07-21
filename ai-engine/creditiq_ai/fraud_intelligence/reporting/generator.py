"""Atomic JSON and Markdown fraud report generation."""

import json
from pathlib import Path

from creditiq_ai.fraud_intelligence.models.results import FraudAssessment


class FraudReportGenerator:
    def generate(self, assessment: FraudAssessment, destination: str | Path) -> list[Path]:
        output = Path(destination)
        output.mkdir(parents=True, exist_ok=True)
        payload = assessment.model_dump(mode="json")
        json_path = self._write(output / "fraud-assessment.json", json.dumps(payload, indent=2))
        flags = "\n".join(f"- {flag}" for flag in assessment.risk_flags) or "- None"
        markdown = (
            "# Fraud Assessment\n\n"
            f"- Fraud score: {assessment.fraud_score}\n"
            f"- Risk level: {assessment.fraud_level.value}\n"
            f"- Confidence: {assessment.confidence_score} ({assessment.confidence_level})\n"
            f"- Recommended action: {assessment.recommended_action}\n"
            f"- Model version: {assessment.model_version}\n\n"
            f"## Risk flags\n\n{flags}\n"
        )
        markdown_path = self._write(output / "fraud-assessment.md", markdown)
        return [json_path, markdown_path]

    @staticmethod
    def _write(path: Path, content: str) -> Path:
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
        return path
