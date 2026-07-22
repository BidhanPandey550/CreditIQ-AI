"""Private financial-document storage, validation, scanning, and integrity checks."""

from __future__ import annotations

import hashlib
import re
import socket
import struct
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import CurrentUser
from app.core.exceptions import NotFoundError, ServiceUnavailableError, ValidationError
from app.modules.applicant import service as applicant_service
from app.modules.applicant.models import FinancialDocument

CONTENT_SIGNATURES: dict[str, tuple[bytes, str]] = {
    "application/pdf": (b"%PDF-", ".pdf"),
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
    "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
}


def validate_document_content(content: bytes, declared_content_type: str | None) -> tuple[str, str]:
    """Validate size, allowlist, and file signature; return canonical MIME and extension."""
    if not content:
        raise ValidationError("Document is empty")
    if len(content) > settings.document_max_bytes:
        raise ValidationError("Document exceeds the configured upload size limit")
    content_type = (declared_content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in settings.allowed_document_content_types:
        raise ValidationError("Document content type is not allowed")
    signature = CONTENT_SIGNATURES.get(content_type)
    if signature is None or not content.startswith(signature[0]):
        raise ValidationError("Document signature does not match its declared content type")
    return content_type, signature[1]


class ClamAVScanner:
    """Minimal ClamAV INSTREAM adapter; no external Python package required."""

    def scan(self, content: bytes) -> str:
        if not settings.clamav_host:
            if settings.document_scan_required:
                raise ServiceUnavailableError("Document malware scanner is not configured")
            return "scan_unavailable"
        try:
            with socket.create_connection(
                (settings.clamav_host, settings.clamav_port),
                timeout=settings.clamav_timeout_seconds,
            ) as connection:
                connection.sendall(b"zINSTREAM\0")
                for offset in range(0, len(content), 65_536):
                    chunk = content[offset : offset + 65_536]
                    connection.sendall(struct.pack(">I", len(chunk)) + chunk)
                connection.sendall(struct.pack(">I", 0))
                response = connection.recv(4096).decode("utf-8", errors="replace")
        except OSError as exc:
            if settings.document_scan_required:
                raise ServiceUnavailableError("Document malware scanner is unavailable") from exc
            return "scan_unavailable"
        if " FOUND" in response:
            raise ValidationError("Document failed malware screening")
        if not response.rstrip("\0").endswith("OK"):
            raise ServiceUnavailableError("Document malware scanner returned an invalid response")
        return "clean"


class LocalDocumentStore:
    """Single-node private storage adapter with atomic writes and traversal protection."""

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or settings.document_storage_root).resolve()

    def write(
        self, org_id: uuid.UUID, applicant_id: uuid.UUID, extension: str, content: bytes
    ) -> str:
        relative = Path(str(org_id)) / str(applicant_id) / f"{uuid.uuid4().hex}{extension}"
        destination = (self.root / relative).resolve()
        if self.root not in destination.parents:
            raise ValidationError("Invalid document storage path")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.parent.chmod(0o700)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_bytes(content)
        temporary.chmod(0o600)
        temporary.replace(destination)
        return relative.as_posix()

    def read(self, storage_key: str) -> bytes:
        source = (self.root / storage_key).resolve()
        if self.root not in source.parents or not source.is_file():
            raise NotFoundError("Document content not found")
        return source.read_bytes()

    def remove(self, storage_key: str) -> None:
        target = (self.root / storage_key).resolve()
        if self.root in target.parents:
            target.unlink(missing_ok=True)


def safe_filename(filename: str | None) -> str:
    base = Path(filename or "document").name
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(". ")
    return cleaned[:255] or "document"


def create_document(
    db: Session,
    user: CurrentUser,
    applicant_id: uuid.UUID,
    *,
    doc_type: str,
    filename: str | None,
    declared_content_type: str | None,
    content: bytes,
    store: LocalDocumentStore | None = None,
    scanner: ClamAVScanner | None = None,
) -> FinancialDocument:
    applicant_service.get_applicant(db, applicant_id, user)
    if not doc_type.strip():
        raise ValidationError("Document type is required")
    content_type, extension = validate_document_content(content, declared_content_type)
    scan_status = (scanner or ClamAVScanner()).scan(content)
    storage = store or LocalDocumentStore()
    storage_key = storage.write(user.org_id, applicant_id, extension, content)
    document = FinancialDocument(
        organization_id=user.org_id,
        applicant_id=applicant_id,
        doc_type=doc_type.strip(),
        storage_key=storage_key,
        original_filename=safe_filename(filename),
        content_type=content_type,
        size_bytes=len(content),
        checksum=hashlib.sha256(content).hexdigest(),
        scan_status=scan_status,
        uploaded_by=user.user_id,
    )
    try:
        db.add(document)
        db.flush()
    except Exception:
        storage.remove(storage_key)
        raise
    return document


def list_documents(
    db: Session, user: CurrentUser, applicant_id: uuid.UUID
) -> list[FinancialDocument]:
    applicant_service.get_applicant(db, applicant_id, user)
    return list(
        db.scalars(
            select(FinancialDocument)
            .where(FinancialDocument.applicant_id == applicant_id)
            .order_by(FinancialDocument.created_at.desc())
        ).all()
    )


def read_document(
    db: Session,
    user: CurrentUser,
    applicant_id: uuid.UUID,
    document_id: uuid.UUID,
    store: LocalDocumentStore | None = None,
) -> tuple[FinancialDocument, bytes]:
    applicant_service.get_applicant(db, applicant_id, user)
    document = db.get(FinancialDocument, document_id)
    if document is None or document.applicant_id != applicant_id:
        raise NotFoundError("Document not found")
    content = (store or LocalDocumentStore()).read(document.storage_key)
    actual_checksum = hashlib.sha256(content).hexdigest()
    if not document.checksum or actual_checksum != document.checksum:
        raise ServiceUnavailableError("Document integrity verification failed")
    scan_is_acceptable = document.scan_status == "clean" or (
        document.scan_status == "scan_unavailable" and not settings.document_scan_required
    )
    if not scan_is_acceptable:
        raise ServiceUnavailableError("Document is not cleared for download")
    return document, content
