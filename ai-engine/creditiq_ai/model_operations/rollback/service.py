"""Explicit rollback facade over the atomic registry operation."""

from creditiq_ai.model_operations.domain import ModelIdentity, ModelRollbackRequest, ModelVersion
from creditiq_ai.model_operations.registry import FileModelRegistry


class RollbackService:
    """Execute a typed rollback request without exposing storage details."""

    def __init__(self, registry: FileModelRegistry) -> None:
        self._registry = registry

    def execute(
        self, request: ModelRollbackRequest, *, environment: str = "development"
    ) -> ModelVersion:
        identity = ModelIdentity(
            name=request.model_name, family=request.family, environment=environment
        )
        current = self._registry.production(identity)
        if current.version != request.from_version:
            from creditiq_ai.exceptions import RollbackError

            raise RollbackError(
                "Rollback source is not the current production version",
                context={"expected": request.from_version, "actual": current.version},
            )
        return self._registry.rollback(
            identity,
            request.to_version,
            actor=request.actor,
            reason=request.reason,
        )
