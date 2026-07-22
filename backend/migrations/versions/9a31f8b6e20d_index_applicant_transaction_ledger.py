"""index applicant transaction ledger

Revision ID: 9a31f8b6e20d
Revises: a02dac7c6b35
Create Date: 2026-07-22 17:20:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "9a31f8b6e20d"
down_revision: Union[str, None] = "a02dac7c6b35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_transaction_records_org_applicant_date",
        "transaction_records",
        ["organization_id", "applicant_id", "txn_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_transaction_records_org_applicant_date", table_name="transaction_records")
