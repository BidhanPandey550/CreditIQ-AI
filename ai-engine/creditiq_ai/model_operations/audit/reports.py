"""Human- and machine-readable immutable model audit exports."""

from __future__ import annotations

import json
import os
from pathlib import Path

from creditiq_ai.model_operations.domain import AuditEvent


class AuditReportGenerator:
    def generate(self, events: list[AuditEvent], directory: str | Path) -> list[Path]:
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        json_path = destination / "model_audit.json"
        markdown_path = destination / "model_audit.md"
        self._atomic(
            json_path, json.dumps([event.model_dump(mode="json") for event in events], indent=2)
        )
        rows = [
            "# Model Operations Audit",
            "",
            "| Timestamp | Event | Model | Version | Previous | New | Actor |",
            "|---|---|---|---|---|---|---|",
            *[
                f"| {event.timestamp.isoformat()} | {event.event_type} | {event.model_name or '—'} | "
                f"{event.model_version or '—'} | {event.previous_state or '—'} | "
                f"{event.new_state or '—'} | {event.actor} |"
                for event in events
            ],
        ]
        self._atomic(markdown_path, "\n".join(rows) + "\n")
        return [json_path, markdown_path]

    @staticmethod
    def _atomic(path: Path, content: str) -> None:
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
