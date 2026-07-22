from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.organization.schemas import BranchCreate, OrganizationSettings


def test_branch_code_is_normalized_and_restricted() -> None:
    assert BranchCreate(name="Pokhara", code=" pkr-01 ").code == "PKR-01"
    with pytest.raises(ValidationError, match="Branch code"):
        BranchCreate(name="Pokhara", code="PKR/01")


def test_organization_settings_validate_timezone_and_currency() -> None:
    settings = OrganizationSettings(currency="npr", timezone="Asia/Kathmandu")
    assert settings.currency == "NPR"
    with pytest.raises(ValidationError, match="IANA"):
        OrganizationSettings(timezone="Nepal/Invalid")
