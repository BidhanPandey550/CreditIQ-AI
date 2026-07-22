"""AI outputs — all versioned and explainable."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin
from app.shared.enums import FraudSeverity, FraudStatus, RiskBand


class ModelVersion(Base, UUIDMixin, TimestampMixin):
    """Registry entry (platform-level, not tenant-scoped)."""

    __tablename__ = "model_versions"
    task: Mapped[str] = mapped_column(String(40))  # risk | credit_score | default | fraud
    algorithm: Mapped[str] = mapped_column(String(60))
    version: Mapped[str] = mapped_column(String(30))
    stage: Mapped[str] = mapped_column(
        String(20), default="production"
    )  # staging|production|archived
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    artifact_uri: Mapped[str | None] = mapped_column(String(300))


class RiskScore(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "risk_scores"
    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        index=True,
    )
    band: Mapped[RiskBand] = mapped_column(String(10))
    probability: Mapped[float] = mapped_column(Numeric(6, 4))
    model_version: Mapped[str | None] = mapped_column(String(40))
    feature_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)


class CreditScore(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "credit_scores"
    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        index=True,
    )
    score: Mapped[int] = mapped_column()  # 300-850 canonical credit-score range
    subscores: Mapped[dict] = mapped_column(JSONB, default=dict)
    model_version: Mapped[str | None] = mapped_column(String(40))


class DefaultPrediction(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "default_predictions"
    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        index=True,
    )
    probability: Mapped[float] = mapped_column(Numeric(6, 4))
    horizon_months: Mapped[int] = mapped_column(default=12)
    model_version: Mapped[str | None] = mapped_column(String(40))


class FraudAlert(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "fraud_alerts"
    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(80))
    severity: Mapped[FraudSeverity] = mapped_column(String(10))
    status: Mapped[FraudStatus] = mapped_column(String(15), default=FraudStatus.open)
    reasons: Mapped[list] = mapped_column(JSONB, default=list)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(Text)


class AiExplanation(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "ai_explanations"
    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        index=True,
    )
    prediction_type: Mapped[str] = mapped_column(String(40))  # risk|credit_score|default
    shap_contributions: Mapped[list] = mapped_column(JSONB, default=list)
    narrative: Mapped[str | None] = mapped_column(Text)


class AiDecisionRecommendation(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """Immutable AI decision-support evidence; never a human lending decision."""

    __tablename__ = "ai_decision_recommendations"
    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        index=True,
    )
    recommendation: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Numeric(6, 4))
    credit_risk: Mapped[str] = mapped_column(String(20))
    fraud_risk: Mapped[str | None] = mapped_column(String(20))
    decision_reasons: Mapped[list] = mapped_column(JSONB, default=list)
    warnings: Mapped[list] = mapped_column(JSONB, default=list)
    correlation_id: Mapped[str] = mapped_column(String(80), index=True)
    model_versions: Mapped[dict] = mapped_column(JSONB, default=dict)
    feature_version: Mapped[str | None] = mapped_column(String(80))
    processing_duration_ms: Mapped[float] = mapped_column(Numeric(12, 3))
    monitoring_status: Mapped[str] = mapped_column(String(20))
