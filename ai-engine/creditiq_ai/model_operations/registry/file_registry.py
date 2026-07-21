"""Durable, atomic model registry for local and single-node deployments.

The registry persists model metadata and audit events in one versioned JSON document. Writes use a
temporary file followed by ``os.replace`` so readers never observe a partially written registry.
Lifecycle changes are delegated to ``LifecycleStateMachine`` and production selection is unique per
model identity.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from creditiq_ai.core.base import BaseComponent
from creditiq_ai.exceptions import (
    ArtifactIntegrityError,
    ModelNotFoundError,
    ModelRegistryError,
    ModelVersionConflictError,
    RollbackError,
)
from creditiq_ai.model_operations.domain import (
    AuditEvent,
    LifecycleStage,
    ModelIdentity,
    ModelVersion,
)
from creditiq_ai.model_operations.lifecycle.state_machine import LifecycleStateMachine

_SCHEMA_VERSION = 1


class FileModelRegistry(BaseComponent):
    """JSON-backed model registry with atomic writes and auditable lifecycle operations."""

    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self._path = Path(path)
        self._lock = threading.RLock()
        self._lifecycle = LifecycleStateMachine()

    def register(self, model: ModelVersion, *, actor: str = "system") -> ModelVersion:
        """Register a unique model version after validating artifact integrity metadata."""
        self._validate_artifacts(model)
        with self._lock:
            state = self._read()
            if self._find(state, model.ref) is not None:
                raise ModelVersionConflictError(
                    "Model version is already registered", context={"ref": model.ref}
                )
            registered = model.model_copy(update={"stage": LifecycleStage.REGISTERED})
            state["models"].append(registered.model_dump(mode="json"))
            self._audit(
                state,
                event_type="model_registered",
                model=registered,
                actor=actor,
                previous=LifecycleStage.CREATED,
                new=LifecycleStage.REGISTERED,
            )
            self._write(state)
            return registered

    def get(self, ref: str) -> ModelVersion:
        """Return one exact model reference or raise ``ModelNotFoundError``."""
        with self._lock:
            raw = self._find(self._read(), ref)
            if raw is None:
                raise ModelNotFoundError("Model version was not found", context={"ref": ref})
            return ModelVersion.model_validate(raw)

    def list_versions(self, identity: ModelIdentity | None = None) -> list[ModelVersion]:
        """List versions, optionally restricted to one model identity."""
        with self._lock:
            versions = [ModelVersion.model_validate(item) for item in self._read()["models"]]
        if identity is not None:
            versions = [item for item in versions if item.identity.key == identity.key]
        return sorted(versions, key=lambda item: (item.identity.key, item.created_at, item.version))

    def transition(
        self,
        ref: str,
        target: LifecycleStage,
        *,
        actor: str = "system",
        reason: str | None = None,
    ) -> ModelVersion:
        """Apply one legal lifecycle transition and persist it atomically."""
        with self._lock:
            state = self._read()
            index, current = self._locate(state, ref)
            self._lifecycle.validate_transition(current.stage, target)
            if target is LifecycleStage.PRODUCTION:
                self._assert_no_other_production(state, current)
            updated = current.model_copy(update={"stage": target})
            state["models"][index] = updated.model_dump(mode="json")
            self._audit(
                state,
                event_type="lifecycle_transition",
                model=updated,
                actor=actor,
                previous=current.stage,
                new=target,
                reason=reason,
            )
            self._write(state)
            return updated

    def production(self, identity: ModelIdentity) -> ModelVersion:
        """Return the unique production version for an identity."""
        matches = [
            item for item in self.list_versions(identity) if item.stage is LifecycleStage.PRODUCTION
        ]
        if len(matches) != 1:
            raise ModelNotFoundError(
                "A unique production model is not available",
                context={"identity": identity.key, "matches": len(matches)},
            )
        return matches[0]

    def rollback(
        self,
        identity: ModelIdentity,
        to_version: str,
        *,
        actor: str = "system",
        reason: str,
    ) -> ModelVersion:
        """Atomically replace the current production model with a previous champion."""
        with self._lock:
            state = self._read()
            candidates = [
                (index, ModelVersion.model_validate(raw))
                for index, raw in enumerate(state["models"])
                if ModelVersion.model_validate(raw).identity.key == identity.key
            ]
            current = [
                (index, model)
                for index, model in candidates
                if model.stage is LifecycleStage.PRODUCTION
            ]
            target = [(index, model) for index, model in candidates if model.version == to_version]
            if len(current) != 1 or len(target) != 1:
                raise RollbackError(
                    "Rollback requires one production model and one target version",
                    context={"identity": identity.key, "target": to_version},
                )
            current_index, current_model = current[0]
            target_index, target_model = target[0]
            if target_model.stage is not LifecycleStage.CHAMPION:
                raise RollbackError(
                    "Rollback target must be in champion stage",
                    context={"ref": target_model.ref, "stage": target_model.stage.value},
                )
            self._lifecycle.validate_transition(current_model.stage, LifecycleStage.CHAMPION)
            self._lifecycle.validate_transition(target_model.stage, LifecycleStage.PRODUCTION)
            demoted = current_model.model_copy(update={"stage": LifecycleStage.CHAMPION})
            promoted = target_model.model_copy(update={"stage": LifecycleStage.PRODUCTION})
            state["models"][current_index] = demoted.model_dump(mode="json")
            state["models"][target_index] = promoted.model_dump(mode="json")
            self._audit(
                state,
                event_type="model_rollback",
                model=promoted,
                actor=actor,
                previous=current_model.stage,
                new=LifecycleStage.PRODUCTION,
                reason=reason,
                metadata={"from_version": current_model.version},
            )
            self._write(state)
            return promoted

    def audit_events(self) -> list[AuditEvent]:
        """Return the immutable registry audit history."""
        with self._lock:
            return [AuditEvent.model_validate(item) for item in self._read()["audit_events"]]

    @staticmethod
    def _validate_artifacts(model: ModelVersion) -> None:
        if not model.artifacts:
            raise ArtifactIntegrityError(
                "A registered model must reference at least one artifact",
                context={"ref": model.ref},
            )
        missing = [artifact.path for artifact in model.artifacts if not artifact.checksum_sha256]
        if missing:
            raise ArtifactIntegrityError(
                "All registered artifacts require a trusted checksum",
                context={"ref": model.ref, "artifacts": missing},
            )

    def _read(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"schema_version": _SCHEMA_VERSION, "models": [], "audit_events": []}
        try:
            state = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ModelRegistryError(
                "Registry storage is unreadable", context={"file": self._path.name}
            ) from exc
        if state.get("schema_version") != _SCHEMA_VERSION:
            raise ModelRegistryError(
                "Unsupported registry schema version",
                context={"actual": state.get("schema_version"), "expected": _SCHEMA_VERSION},
            )
        return state

    def _write(self, state: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f".{self._path.name}.{os.getpid()}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(state, handle, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self._path)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise ModelRegistryError(
                "Registry storage could not be updated", context={"file": self._path.name}
            ) from exc

    @staticmethod
    def _find(state: dict[str, Any], ref: str) -> dict[str, Any] | None:
        for raw in state["models"]:
            if ModelVersion.model_validate(raw).ref == ref:
                return raw
        return None

    @staticmethod
    def _locate(state: dict[str, Any], ref: str) -> tuple[int, ModelVersion]:
        for index, raw in enumerate(state["models"]):
            model = ModelVersion.model_validate(raw)
            if model.ref == ref:
                return index, model
        raise ModelNotFoundError("Model version was not found", context={"ref": ref})

    @staticmethod
    def _assert_no_other_production(state: dict[str, Any], candidate: ModelVersion) -> None:
        for raw in state["models"]:
            model = ModelVersion.model_validate(raw)
            if (
                model.identity.key == candidate.identity.key
                and model.stage is LifecycleStage.PRODUCTION
                and model.ref != candidate.ref
            ):
                raise ModelVersionConflictError(
                    "A production version already exists",
                    context={"identity": candidate.identity.key, "production": model.version},
                )

    @staticmethod
    def _audit(
        state: dict[str, Any],
        *,
        event_type: str,
        model: ModelVersion,
        actor: str,
        previous: LifecycleStage,
        new: LifecycleStage,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = AuditEvent(
            event_type=event_type,
            actor=actor,
            model_name=model.identity.name,
            model_version=model.version,
            previous_state=previous.value,
            new_state=new.value,
            reason=reason,
            metadata=metadata or {},
        )
        state["audit_events"].append(event.model_dump(mode="json"))
