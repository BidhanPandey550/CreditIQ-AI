"""Platform-owner operational APIs that never expose the internal ML service directly."""

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, require
from app.modules.credit_intelligence.ml_client import ml_client
from app.modules.credit_intelligence.schemas import ModelOperationsStatus

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/model-operations", response_model=ModelOperationsStatus)
def model_operations(
    user: CurrentUser = Depends(require("platform:admin")),
) -> ModelOperationsStatus:
    """Expose validated, privacy-safe serving health to platform administrators."""
    return ml_client.operations_status()
