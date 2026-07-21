"""Link applicant users to their owned applicant profile.

Revision ID: f2ce32e9bf37
Revises: 0d870f3296be
Create Date: 2026-07-22 02:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "f2ce32e9bf37"
down_revision: Union[str, None] = "0d870f3296be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("applicant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_applicant_id",
        "users",
        "applicants",
        ["applicant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_applicant_id", "users", ["applicant_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_applicant_id", table_name="users")
    op.drop_constraint("fk_users_applicant_id", "users", type_="foreignkey")
    op.drop_column("users", "applicant_id")
