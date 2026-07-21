"""Content-addressed, checksum-verified dataset version storage."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from creditiq_ai.exceptions import DataLoadingError


class DatasetVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version_id: str
    checksum_sha256: str
    rows: int = Field(ge=0)
    columns: int = Field(ge=0)
    path: str
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DatasetRegistry:
    """Atomically persist Parquet data and immutable content-derived metadata."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)

    def save(
        self, frame: pd.DataFrame, *, metadata: dict[str, str] | None = None
    ) -> DatasetVersion:
        checksum = self.checksum(frame)
        version_id = f"ds-{checksum[:12]}"
        directory = self._root / version_id
        directory.mkdir(parents=True, exist_ok=True)
        data_path = directory / "dataset.parquet"
        data_tmp = directory / f".dataset.{os.getpid()}.tmp.parquet"
        frame.to_parquet(data_tmp, index=False)
        os.replace(data_tmp, data_path)
        record = DatasetVersion(
            version_id=version_id,
            checksum_sha256=checksum,
            rows=len(frame),
            columns=frame.shape[1],
            path=str(data_path),
            metadata=metadata or {},
        )
        metadata_path = directory / "metadata.json"
        metadata_tmp = directory / f".metadata.{os.getpid()}.tmp"
        metadata_tmp.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        os.replace(metadata_tmp, metadata_path)
        return record

    def load(self, version_id: str) -> tuple[pd.DataFrame, DatasetVersion]:
        directory = self._root / version_id
        try:
            record = DatasetVersion.model_validate_json(
                (directory / "metadata.json").read_text(encoding="utf-8")
            )
            frame = pd.read_parquet(directory / "dataset.parquet")
        except (OSError, ValueError) as exc:
            raise DataLoadingError(
                "Dataset version could not be loaded", context={"version_id": version_id}
            ) from exc
        if self.checksum(frame) != record.checksum_sha256:
            raise DataLoadingError(
                "Dataset checksum verification failed", context={"version_id": version_id}
            )
        return frame, record

    @staticmethod
    def checksum(frame: pd.DataFrame) -> str:
        digest = hashlib.sha256()
        digest.update("|".join(map(str, frame.columns)).encode())
        digest.update("|".join(map(str, frame.dtypes)).encode())
        digest.update(pd.util.hash_pandas_object(frame, index=True).values.tobytes())
        return digest.hexdigest()
