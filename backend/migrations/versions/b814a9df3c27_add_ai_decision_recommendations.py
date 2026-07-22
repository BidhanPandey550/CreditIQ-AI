"""add immutable AI decision recommendations

Revision ID: b814a9df3c27
Revises: 9a31f8b6e20d
Create Date: 2026-07-22 20:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b814a9df3c27"
down_revision: Union[str, None] = "9a31f8b6e20d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_decision_recommendations",
        sa.Column("loan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommendation", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("credit_risk", sa.String(length=20), nullable=False),
        sa.Column("fraud_risk", sa.String(length=20), nullable=True),
        sa.Column("decision_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("correlation_id", sa.String(length=80), nullable=False),
        sa.Column("model_versions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("feature_version", sa.String(length=80), nullable=True),
        sa.Column("processing_duration_ms", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("monitoring_status", sa.String(length=20), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["loan_id"], ["loan_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_decision_recommendations_loan_id", "ai_decision_recommendations", ["loan_id"]
    )
    op.create_index(
        "ix_ai_decision_recommendations_organization_id",
        "ai_decision_recommendations",
        ["organization_id"],
    )
    op.create_index(
        "ix_ai_decision_recommendations_correlation_id",
        "ai_decision_recommendations",
        ["correlation_id"],
    )
    op.execute("ALTER TABLE ai_decision_recommendations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ai_decision_recommendations FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON ai_decision_recommendations "
        "USING (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid) "
        "WITH CHECK (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("ai_decision_recommendations")
