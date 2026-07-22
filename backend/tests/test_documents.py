from __future__ import annotations

import hashlib

import pytest

from app.core.exceptions import ValidationError
from app.modules.applicant.documents import (
    ClamAVScanner,
    LocalDocumentStore,
    safe_filename,
    validate_document_content,
)


def test_document_signature_must_match_declared_type() -> None:
    assert validate_document_content(b"%PDF-1.7\ncontent", "application/pdf") == (
        "application/pdf",
        ".pdf",
    )
    with pytest.raises(ValidationError, match="signature"):
        validate_document_content(b"not a pdf", "application/pdf")


def test_document_rejects_disallowed_content_type() -> None:
    with pytest.raises(ValidationError, match="not allowed"):
        validate_document_content(b"MZ executable", "application/x-msdownload")


def test_filename_is_reduced_to_safe_basename() -> None:
    assert safe_filename('../../dangerous"name.pdf') == "dangerous_name.pdf"


def test_local_store_round_trip_uses_private_generated_key(tmp_path) -> None:
    import uuid

    store = LocalDocumentStore(tmp_path)
    organization_id = uuid.uuid4()
    applicant_id = uuid.uuid4()
    content = b"%PDF-1.7\nprivate"

    key = store.write(organization_id, applicant_id, ".pdf", content)

    assert "private" not in key
    assert key.startswith(f"{organization_id}/{applicant_id}/")
    assert store.read(key) == content
    assert hashlib.sha256(store.read(key)).hexdigest()


def test_scanner_is_explicit_when_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("app.modules.applicant.documents.settings.clamav_host", None)
    monkeypatch.setattr("app.modules.applicant.documents.settings.document_scan_required", False)
    assert ClamAVScanner().scan(b"safe") == "scan_unavailable"
