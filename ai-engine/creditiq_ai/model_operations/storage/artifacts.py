"""Artifact store — the authoritative, integrity-verified model (de)serialization path (fix D1).

Purpose:  Never deserialize a model artifact without verifying its SHA-256 checksum first. Loading
          goes through `ArtifactStore.load(path, expected_sha256)`, which raises
          `ArtifactIntegrityError` on a missing / unsupported / corrupted / tampered artifact —
          closing the "unsafe model loading" finding (D1).
Inputs:   an object to persist, or a path + expected checksum to load.
Outputs:  ModelArtifact (on save) / the deserialized object (on verified load).
Deps:     joblib (existing serializer — no new/unsafe deserialization); exceptions; domain.ModelArtifact.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import joblib

from creditiq_ai.core.base import BaseComponent
from creditiq_ai.core.types import PathLike
from creditiq_ai.exceptions import ArtifactIntegrityError
from creditiq_ai.model_operations.domain import ArtifactKind, ModelArtifact

_SUPPORTED_FORMATS = {".joblib"}
_CHUNK = 1 << 20  # 1 MiB


def compute_sha256(path: PathLike) -> str:
    """Streaming SHA-256 of a file's bytes."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ArtifactStore(BaseComponent):
    """Persist and load model artifacts with mandatory integrity verification on load."""

    def save(
        self, obj: Any, path: PathLike, *, kind: ArtifactKind = ArtifactKind.MODEL
    ) -> ModelArtifact:
        target = Path(path)
        if target.suffix not in _SUPPORTED_FORMATS:
            raise ArtifactIntegrityError(
                f"Unsupported serialization format '{target.suffix}'",
                context={"supported": sorted(_SUPPORTED_FORMATS)},
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(obj, target)
        checksum = compute_sha256(target)
        size = target.stat().st_size
        self.logger.info(f"Saved artifact {target.name} ({size} bytes) sha256={checksum[:12]}…")
        return ModelArtifact(
            kind=kind,
            path=str(target),
            checksum_sha256=checksum,
            serialization_format="joblib",
            size_bytes=size,
        )

    def verify(self, path: PathLike, expected_sha256: str) -> None:
        """Raise ArtifactIntegrityError unless the file exists and matches the expected checksum."""
        target = Path(path)
        if not target.exists():
            raise ArtifactIntegrityError("Artifact file is missing", context={"path": str(target)})
        if target.suffix not in _SUPPORTED_FORMATS:
            raise ArtifactIntegrityError(
                f"Unsupported serialization format '{target.suffix}'",
                context={"supported": sorted(_SUPPORTED_FORMATS)},
            )
        if not expected_sha256:
            raise ArtifactIntegrityError(
                "No expected checksum supplied; refusing to load", context={"path": str(target)}
            )
        actual = compute_sha256(target)
        if actual != expected_sha256:
            # Do not leak the full path; report only the file name.
            raise ArtifactIntegrityError(
                "Artifact checksum mismatch — possible corruption or tampering",
                context={
                    "artifact": target.name,
                    "expected": expected_sha256[:12] + "…",
                    "actual": actual[:12] + "…",
                },
            )

    def load(self, path: PathLike, expected_sha256: str) -> Any:
        """Verify integrity, THEN deserialize. Never loads an unverified artifact."""
        self.verify(path, expected_sha256)
        obj = joblib.load(path)
        self.logger.info(f"Loaded artifact {Path(path).name} after integrity check")
        return obj

    def load_artifact(self, artifact: ModelArtifact) -> Any:
        """Load using a ModelArtifact record (carries its own checksum)."""
        if not artifact.checksum_sha256:
            raise ArtifactIntegrityError(
                "ModelArtifact has no checksum; refusing to load",
                context={"artifact": Path(artifact.path).name},
            )
        return self.load(artifact.path, artifact.checksum_sha256)
