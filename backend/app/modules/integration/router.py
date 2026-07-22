from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require
from app.modules.audit import service as audit
from app.modules.integration import service
from app.modules.integration.schemas import APIKeyCreate, APIKeyCreated, APIKeyOut

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/api-key-scopes", response_model=dict[str, str])
def api_key_scopes(
    user: CurrentUser = Depends(require("org:configure")),
) -> dict[str, str]:
    return service.assignable_scopes(user)


@router.get("/api-keys", response_model=list[APIKeyOut])
def list_api_keys(
    user: CurrentUser = Depends(require("org:configure")),
    db: Session = Depends(get_db),
) -> list[APIKeyOut]:
    return [APIKeyOut.model_validate(item) for item in service.list_api_keys(db, user.org_id)]


@router.post("/api-keys", response_model=APIKeyCreated, status_code=201)
def create_api_key(
    body: APIKeyCreate,
    user: CurrentUser = Depends(require("org:configure")),
    db: Session = Depends(get_db),
) -> APIKeyCreated:
    created, raw_key = service.create_api_key(db, user, body)
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="api_key.create",
        entity_type="api_key",
        entity_id=created.id,
        after={
            "name": created.name,
            "prefix": created.prefix,
            "scopes": created.scopes,
        },
    )
    return APIKeyCreated(**APIKeyOut.model_validate(created).model_dump(), key=raw_key)


@router.post("/api-keys/{key_id}/revoke", response_model=APIKeyOut)
def revoke_api_key(
    key_id: uuid.UUID,
    user: CurrentUser = Depends(require("org:configure")),
    db: Session = Depends(get_db),
) -> APIKeyOut:
    revoked = service.revoke_api_key(db, user.org_id, key_id)
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="api_key.revoke",
        entity_type="api_key",
        entity_id=revoked.id,
        after={"prefix": revoked.prefix, "revoked_at": revoked.revoked_at.isoformat()},
    )
    return APIKeyOut.model_validate(revoked)
