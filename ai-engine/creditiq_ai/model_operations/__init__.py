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
from creditiq_ai.model_operations.alerts import AlertManager, ModelAlert
from creditiq_ai.model_operations.drift import (
    DriftReport,
    FeatureDrift,
    PopulationStabilityDetector,
)
from creditiq_ai.model_operations.health import ModelHealthReport, ModelHealthService
from creditiq_ai.model_operations.lineage import LineageGraph
from creditiq_ai.model_operations.performance import PerformanceMonitor, PerformanceSnapshot
from creditiq_ai.model_operations.promotion import (
    PromotionDecision,
    PromotionPolicy,
    PromotionService,
)
from creditiq_ai.model_operations.rollback import RollbackService

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
    "AlertManager",
    "ModelAlert",
    "DriftReport",
    "FeatureDrift",
    "PopulationStabilityDetector",
    "ModelHealthReport",
    "ModelHealthService",
    "LineageGraph",
    "PerformanceMonitor",
    "PerformanceSnapshot",
    "PromotionDecision",
    "PromotionPolicy",
    "PromotionService",
    "RollbackService",
]
