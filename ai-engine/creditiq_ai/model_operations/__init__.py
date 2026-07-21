"""creditiq_ai.model_operations — Model Lifecycle, Registry, Monitoring & Drift subsystem (Sprint 8).

The ONE authoritative model registry + lifecycle home. Manages both credit and fraud models.
Reuses core.schemas.ModelMetadata, the unified config, Loguru logging, joblib serialization, and the
exception hierarchy — no duplicate registries/loggers/config loaders.

Phase 2a (this increment) exposes the domain models + lifecycle state machine. Registry, storage,
lineage, promotion/rollback, experiments, drift, monitoring, health, alerts, audit, reports, and
inference integration are added in subsequent phases.
"""

from creditiq_ai.model_operations.domain import (
    ArtifactKind,
    AuditEvent,
    LifecycleStage,
    ModelArtifact,
    ModelDeploymentRecord,
    ModelEvaluationSnapshot,
    ModelFamily,
    ModelIdentity,
    ModelLineage,
    ModelPromotionRequest,
    ModelRollbackRequest,
    ModelVersion,
)
from creditiq_ai.model_operations.lifecycle.state_machine import LifecycleStateMachine
from creditiq_ai.model_operations.registry import FileModelRegistry
from creditiq_ai.model_operations.monitoring import (
    InferenceEvent,
    InMemoryDecisionMonitor,
    MonitoringSink,
    MonitoringSnapshot,
)
from creditiq_ai.model_operations.storage.artifacts import ArtifactStore, compute_sha256

__all__ = [
    "LifecycleStage",
    "ModelFamily",
    "ArtifactKind",
    "ModelIdentity",
    "ModelArtifact",
    "ModelLineage",
    "ModelVersion",
    "ModelEvaluationSnapshot",
    "ModelDeploymentRecord",
    "ModelPromotionRequest",
    "ModelRollbackRequest",
    "AuditEvent",
    "LifecycleStateMachine",
    "FileModelRegistry",
    "InferenceEvent",
    "InMemoryDecisionMonitor",
    "MonitoringSink",
    "MonitoringSnapshot",
    "ArtifactStore",
    "compute_sha256",
]
