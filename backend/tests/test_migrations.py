"""Migration history is singular, compilable, and protects every tenant table."""

from __future__ import annotations

from alembic.script import ScriptDirectory

from app.db.all_models import RLS_TABLES
from app.db.bootstrap import _alembic_config
from migrations.versions.c3094e1cde73_enforce_tenant_row_level_security import TENANT_TABLES


def test_repository_has_one_migration_head() -> None:
    script = ScriptDirectory.from_config(_alembic_config())
    assert script.get_heads() == ["c3094e1cde73"]


def test_rls_migration_covers_every_tenant_table() -> None:
    assert set(TENANT_TABLES) == set(RLS_TABLES)
