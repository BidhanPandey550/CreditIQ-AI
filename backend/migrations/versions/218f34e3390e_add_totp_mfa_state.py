"""Add encrypted TOTP MFA state and replay counter.

Revision ID: 218f34e3390e
Revises: f2ce32e9bf37
Create Date: 2026-07-22 02:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "218f34e3390e"
down_revision: Union[str, None] = "f2ce32e9bf37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("mfa_secret_encrypted", sa.String(512), nullable=True))
    op.add_column("users", sa.Column("mfa_last_verified_step", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "mfa_last_verified_step")
    op.drop_column("users", "mfa_secret_encrypted")
