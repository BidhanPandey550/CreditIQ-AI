"""harden custom role names

Revision ID: a02dac7c6b35
Revises: d62f9f6b2071
Create Date: 2026-07-22 17:10:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a02dac7c6b35"
down_revision: Union[str, None] = "d62f9f6b2071"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_role_org_name", "roles", type_="unique")
    op.execute(
        "CREATE UNIQUE INDEX uq_roles_org_lower_name ON roles (organization_id, lower(name))"
    )


def downgrade() -> None:
    op.drop_index("uq_roles_org_lower_name", table_name="roles")
    op.create_unique_constraint("uq_role_org_name", "roles", ["organization_id", "name"])
