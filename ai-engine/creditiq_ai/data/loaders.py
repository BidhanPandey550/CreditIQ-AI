"""Module 1 — Data loaders.

Purpose:  Read tabular data from heterogeneous sources into a pandas DataFrame behind one
          interface, so downstream stages are source-agnostic.
Inputs:   a path (CSV / Parquet) or a connection spec (future DB).
Outputs:  pandas.DataFrame.
Deps:     pandas (+ pyarrow for parquet); core.base, core.exceptions.
Extend:   implement BaseDataLoader for a new source and register it in DATA_LOADERS / get_loader.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from creditiq_ai.core.base import BaseDataLoader
from creditiq_ai.core.exceptions import DataLoadError
from creditiq_ai.core.types import PathLike


class CsvLoader(BaseDataLoader):
    """Load a CSV file."""

    def load(self, source: PathLike, **kwargs: Any) -> pd.DataFrame:
        path = Path(source)
        if not path.exists():
            raise DataLoadError(f"CSV not found: {path}")
        try:
            df = pd.read_csv(path, **kwargs)
        except Exception as exc:  # noqa: BLE001
            raise DataLoadError(f"Failed to read CSV {path}", context={"error": str(exc)}) from exc
        self.logger.info(f"Loaded CSV {path.name} ({len(df)} rows, {df.shape[1]} cols)")
        return df


class ParquetLoader(BaseDataLoader):
    """Load a Parquet file (columnar; efficient for large datasets)."""

    def load(self, source: PathLike, **kwargs: Any) -> pd.DataFrame:
        path = Path(source)
        if not path.exists():
            raise DataLoadError(f"Parquet not found: {path}")
        try:
            df = pd.read_parquet(path, **kwargs)
        except Exception as exc:  # noqa: BLE001
            raise DataLoadError(
                f"Failed to read Parquet {path}", context={"error": str(exc)}
            ) from exc
        self.logger.info(f"Loaded Parquet {path.name} ({len(df)} rows, {df.shape[1]} cols)")
        return df


class DatabaseLoader(BaseDataLoader):
    """Future DB connector. Interface defined now; implementation deferred by design.

    A concrete version will accept a SQLAlchemy engine/URL + query and stream results.
    Kept as an explicit, documented extension point rather than a fake integration.
    """

    def load(self, source: PathLike, **kwargs: Any) -> pd.DataFrame:  # pragma: no cover
        raise NotImplementedError(
            "DatabaseLoader is a planned connector. Implement BaseDataLoader with a real "
            "SQLAlchemy engine and register it in DATA_LOADERS."
        )


# Registry keyed by file extension → loader class (open/closed).
DATA_LOADERS: dict[str, type[BaseDataLoader]] = {
    ".csv": CsvLoader,
    ".parquet": ParquetLoader,
    ".pq": ParquetLoader,
}


def get_loader(source: PathLike) -> BaseDataLoader:
    """Factory: choose a loader by file extension."""
    suffix = Path(source).suffix.lower()
    loader_cls = DATA_LOADERS.get(suffix)
    if loader_cls is None:
        raise DataLoadError(
            f"No loader registered for '{suffix}'",
            context={"supported": sorted(DATA_LOADERS)},
        )
    return loader_cls()


def load_dataset(source: PathLike, **kwargs: Any) -> pd.DataFrame:
    """Convenience: pick the right loader and read the source."""
    return get_loader(source).load(source, **kwargs)
