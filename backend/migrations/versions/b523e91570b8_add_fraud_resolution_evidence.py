"""add fraud resolution evidence

Revision ID: b523e91570b8
Revises: 76f511ab91c2
Create Date: 2026-07-22 16:24:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b523e91570b8"
down_revision: Union[str, None] = "76f511ab91c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("fraud_alerts", sa.Column("resolved_by", sa.UUID(), nullable=True))
    op.add_column(
        "fraud_alerts", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("fraud_alerts", sa.Column("resolution_note", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_fraud_alerts_resolved_by_users",
        "fraud_alerts",
        "users",
        ["resolved_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_fraud_alerts_resolved_by", "fraud_alerts", ["resolved_by"])


def downgrade() -> None:
    op.drop_index("ix_fraud_alerts_resolved_by", table_name="fraud_alerts")
    op.drop_constraint("fk_fraud_alerts_resolved_by_users", "fraud_alerts", type_="foreignkey")
    op.drop_column("fraud_alerts", "resolution_note")
    op.drop_column("fraud_alerts", "resolved_at")
    op.drop_column("fraud_alerts", "resolved_by")
