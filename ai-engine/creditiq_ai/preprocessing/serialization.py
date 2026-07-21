"""Integrity-verified preprocessing pipeline serialization."""

from __future__ import annotations

import hashlib
import json
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
from pydantic import BaseModel, ConfigDict, Field

from creditiq_ai.exceptions import ArtifactIntegrityError


class PipelineArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: str
    format: str
    path: str
    checksum_sha256: str
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PipelineSerializer:
    """Persist Joblib or Pickle only behind mandatory SHA-256 verification."""

    def save(
        self,
        pipeline: Any,
        path: str | Path,
        *,
        version: str,
        format: str = "joblib",
        metadata: dict[str, str] | None = None,
    ) -> PipelineArtifact:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
        if format == "joblib":
            joblib.dump(pipeline, temporary)
        elif format == "pickle":
            temporary.write_bytes(pickle.dumps(pipeline, protocol=pickle.HIGHEST_PROTOCOL))
        else:
            raise ArtifactIntegrityError(
                "Unsupported pipeline serialization format", context={"format": format}
            )
        os.replace(temporary, destination)
        artifact = PipelineArtifact(
            version=version,
            format=format,
            path=str(destination),
            checksum_sha256=self._checksum(destination),
            metadata=metadata or {},
        )
        manifest = destination.with_suffix(destination.suffix + ".json")
        manifest.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
        return artifact

    def load(self, artifact: PipelineArtifact) -> Any:
        path = Path(artifact.path)
        if not path.exists() or self._checksum(path) != artifact.checksum_sha256:
            raise ArtifactIntegrityError(
                "Pipeline artifact checksum verification failed", context={"path": path.name}
            )
        if artifact.format == "joblib":
            return joblib.load(path)
        if artifact.format == "pickle":
            return pickle.loads(path.read_bytes())
        raise ArtifactIntegrityError(
            "Unsupported pipeline serialization format", context={"format": artifact.format}
        )

    @staticmethod
    def load_manifest(path: str | Path) -> PipelineArtifact:
        try:
            return PipelineArtifact.model_validate_json(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ArtifactIntegrityError("Pipeline artifact manifest is invalid") from exc

    @staticmethod
    def _checksum(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
