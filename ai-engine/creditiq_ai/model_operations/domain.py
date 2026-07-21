"""Model Operations domain models (Sprint 8, Phase 2a).

Purpose:  Strongly-typed, validated domain objects for the model registry & lifecycle. Reuses the
          frozen `core.schemas.ModelMetadata` (embedded, not duplicated). Lifecycle stages and the
          legal transition graph are defined here; transitions are enforced by the state machine.
Deps:     pydantic v2; core.schemas.ModelMetadata.
Note:     monitoring/drift/health/alert domain models are defined in their own phases.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from creditiq_ai.core.schemas import ModelMetadata


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# --------------------------------------------------------------------------- controlled vocab
class LifecycleStage(str, Enum):
    CREATED = "created"
    REGISTERED = "registered"
    VALIDATED = "validated"
    STAGING = "staging"
    CHALLENGER = "challenger"
    CHAMPION = "champion"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    REJECTED = "rejected"
    RETIRED = "retired"


class ModelFamily(str, Enum):
    CREDIT = "credit"
    FRAUD = "fraud"


class ArtifactKind(str, Enum):
    MODEL = "model"
    PREPROCESSING = "preprocessing"
    FEATURE_SCHEMA = "feature_schema"


# Legal lifecycle transitions (State Machine). Terminal stages map to an empty set.
LIFECYCLE_TRANSITIONS: dict[LifecycleStage, set[LifecycleStage]] = {
    LifecycleStage.CREATED: {LifecycleStage.REGISTERED, LifecycleStage.REJECTED},
    LifecycleStage.REGISTERED: {
        LifecycleStage.VALIDATED,
        LifecycleStage.REJECTED,
        LifecycleStage.ARCHIVED,
    },
    LifecycleStage.VALIDATED: {
        LifecycleStage.STAGING,
        LifecycleStage.REJECTED,
        LifecycleStage.ARCHIVED,
    },
    LifecycleStage.STAGING: {
        LifecycleStage.CHALLENGER,
        LifecycleStage.ARCHIVED,
        LifecycleStage.REJECTED,
    },
    LifecycleStage.CHALLENGER: {
        LifecycleStage.CHAMPION,
        LifecycleStage.STAGING,
        LifecycleStage.ARCHIVED,
    },
    LifecycleStage.CHAMPION: {
        LifecycleStage.PRODUCTION,
        LifecycleStage.CHALLENGER,
        LifecycleStage.ARCHIVED,
    },
    LifecycleStage.PRODUCTION: {
        LifecycleStage.CHAMPION,
        LifecycleStage.RETIRED,
        LifecycleStage.ARCHIVED,
    },
    LifecycleStage.ARCHIVED: set(),  # terminal
    LifecycleStage.REJECTED: set(),  # terminal
    LifecycleStage.RETIRED: set(),  # terminal
}


class _Domain(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- identity & artifacts
class ModelIdentity(_Domain):
    name: str
    family: ModelFamily
    environment: str = "development"

    @property
    def key(self) -> str:
        return f"{self.family.value}:{self.name}:{self.environment}"


class ModelArtifact(_Domain):
    kind: ArtifactKind
    path: str
    checksum_sha256: str | None = None
    serialization_format: str = "joblib"
    size_bytes: int | None = None


class ModelLineage(_Domain):
    parent_version: str | None = None
    training_run_id: str | None = None
    dataset_version: str | None = None
    feature_schema_version: str | None = None
    preprocessing_version: str | None = None
    feature_engineering_version: str | None = None
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    source_build: str | None = None
    evaluation_report_ref: str | None = None
    calibration_report_ref: str | None = None
    explainability_report_ref: str | None = None
    family: ModelFamily | None = None
    registered_at: datetime = Field(default_factory=_utcnow)


class ModelVersion(_Domain):
    """One registered version of a model — the registry's core record."""

    identity: ModelIdentity
    version: str
    stage: LifecycleStage = LifecycleStage.CREATED
    metadata: ModelMetadata  # reused frozen Sprint-1 schema (not duplicated)
    artifacts: list[ModelArtifact] = Field(default_factory=list)
    lineage: ModelLineage = Field(default_factory=ModelLineage)
    integrity_hash: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    created_by: str = "system"
    created_at: datetime = Field(default_factory=_utcnow)

    @property
    def ref(self) -> str:
        return f"{self.identity.key}@{self.version}"


# --------------------------------------------------------------------------- lifecycle records
class ModelEvaluationSnapshot(_Domain):
    model_name: str
    version: str
    family: ModelFamily
    metrics: dict[str, float] = Field(default_factory=dict)
    evaluated_at: datetime = Field(default_factory=_utcnow)


class ModelDeploymentRecord(_Domain):
    model_name: str
    version: str
    stage: LifecycleStage
    environment: str
    actor: str = "system"
    deployed_at: datetime = Field(default_factory=_utcnow)


class ModelPromotionRequest(_Domain):
    model_name: str
    family: ModelFamily
    candidate_version: str
    target_stage: LifecycleStage
    requested_by: str = "system"
    reason: str | None = None
    requested_at: datetime = Field(default_factory=_utcnow)


class ModelRollbackRequest(_Domain):
    model_name: str
    family: ModelFamily
    from_version: str
    to_version: str
    reason: str
    actor: str = "system"
    requested_at: datetime = Field(default_factory=_utcnow)


# --------------------------------------------------------------------------- audit
class AuditEvent(_Domain):
    """Immutable audit record (services never mutate these after creation)."""

    event_id: str = Field(default_factory=_uuid)
    event_type: str
    timestamp: datetime = Field(default_factory=_utcnow)
    actor: str = "system"
    model_name: str | None = None
    model_version: str | None = None
    previous_state: str | None = None
    new_state: str | None = None
    reason: str | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
