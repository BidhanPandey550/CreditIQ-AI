"""Migration history is singular, compilable, and protects every tenant table."""

from __future__ import annotations

from importlib import import_module

from alembic.script import ScriptDirectory

from app.db.all_models import RLS_TABLES
from app.db.bootstrap import _alembic_config
from migrations.versions.c3094e1cde73_enforce_tenant_row_level_security import TENANT_TABLES

API_KEY_TENANT_TABLES = import_module(
    "migrations.versions.748dadfd87d2_add_tenant_api_keys"
).TENANT_TABLES
HARDENED_TENANT_TABLES = import_module(
    "migrations.versions.0d870f3296be_harden_empty_tenant_context"
).RLS_TABLES


def test_repository_has_one_migration_head() -> None:
    script = ScriptDirectory.from_config(_alembic_config())
    assert script.get_heads() == ["748dadfd87d2"]


def test_rls_migration_covers_every_tenant_table() -> None:
    assert set(TENANT_TABLES).union(API_KEY_TENANT_TABLES) == set(RLS_TABLES)


def test_historical_rls_migration_uses_its_frozen_table_set() -> None:
    assert HARDENED_TENANT_TABLES == TENANT_TABLES
