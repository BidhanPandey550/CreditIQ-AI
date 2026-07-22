"""Fraud alert investigation API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require
from app.modules.fraud import service
from app.modules.fraud.schemas import FraudAlertOut, FraudAlertResolution
from app.shared.enums import FraudSeverity, FraudStatus

router = APIRouter(prefix="/fraud", tags=["fraud"])


@router.get("/alerts", response_model=list[FraudAlertOut])
def list_alerts(
    status: FraudStatus | None = Query(default=None),
    severity: FraudSeverity | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(require("fraud:read")),
    db: Session = Depends(get_db),
) -> list[FraudAlertOut]:
    return service.list_alerts(
        db, user, status=status, severity=severity, limit=limit, offset=offset
    )


@router.get("/alerts/{alert_id}", response_model=FraudAlertOut)
def get_alert(
    alert_id: uuid.UUID,
    user: CurrentUser = Depends(require("fraud:read")),
    db: Session = Depends(get_db),
) -> FraudAlertOut:
    return service.present_alert(service.get_alert(db, user, alert_id))


@router.post("/alerts/{alert_id}/resolve", response_model=FraudAlertOut)
def resolve_alert(
    alert_id: uuid.UUID,
    body: FraudAlertResolution,
    user: CurrentUser = Depends(require("fraud:resolve")),
    db: Session = Depends(get_db),
) -> FraudAlertOut:
    return service.resolve_alert(db, user, alert_id, body.status, body.note)
