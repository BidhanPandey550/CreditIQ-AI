"""Bridge training outputs into the authoritative model registry."""

from __future__ import annotations

from creditiq_ai.core.enums import ModelType
from creditiq_ai.core.schemas import ModelMetadata
from creditiq_ai.credit_intelligence.trainers.result import TrainingResult
from creditiq_ai.model_operations.domain import (
    ModelArtifact,
    ModelFamily,
    ModelIdentity,
    ModelLineage,
    ModelVersion,
)
from creditiq_ai.model_operations.registry import FileModelRegistry


class TrainingRegistrationService:
    """Create a fully traceable registry record from one completed training result."""

    def __init__(self, registry: FileModelRegistry) -> None:
        self._registry = registry

    def register(
        self,
        result: TrainingResult,
        artifact: ModelArtifact,
        *,
        name: str,
        version: str,
        environment: str,
        config_hash: str,
        parent_version: str | None = None,
        feature_schema_version: str | None = None,
        actor: str = "training-pipeline",
    ) -> ModelVersion:
        metadata = ModelMetadata(
            name=name,
            version=version,
            model_type=ModelType(result.algorithm),
            trained_at=result.trained_at,
            features=result.feature_names,
            hyperparameters=result.params,
            metrics={
                result.primary_metric: result.primary_score,
                f"{result.primary_metric}_cv_std": result.cv.std,
            },
            config_hash=config_hash,
            artifact_path=artifact.path,
        )
        model = ModelVersion(
            identity=ModelIdentity(name=name, family=ModelFamily.CREDIT, environment=environment),
            version=version,
            metadata=metadata,
            artifacts=[artifact],
            lineage=ModelLineage(
                parent_version=parent_version,
                dataset_version=result.dataset_version,
                feature_schema_version=feature_schema_version,
                hyperparameters=result.params,
                family=ModelFamily.CREDIT,
            ),
            created_by=actor,
        )
        return self._registry.register(model, actor=actor)
