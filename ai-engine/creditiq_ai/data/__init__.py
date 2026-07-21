"""creditiq_ai.data — Module 1 data loaders + datatype coercion."""

from creditiq_ai.data.dtypes import coerce_dtypes
from creditiq_ai.data.loaders import (
    CsvLoader,
    DatabaseLoader,
    ParquetLoader,
    get_loader,
    load_dataset,
)
from creditiq_ai.data.profiling import DatasetProfile, DatasetProfiler
from creditiq_ai.data.quality import ColumnQuality, DataQualityAnalyzer, DataQualityReport
from creditiq_ai.data.registry import DatasetRegistry, DatasetVersion

__all__ = [
    "CsvLoader",
    "ParquetLoader",
    "DatabaseLoader",
    "get_loader",
    "load_dataset",
    "coerce_dtypes",
    "DatasetProfile",
    "DatasetProfiler",
    "ColumnQuality",
    "DataQualityAnalyzer",
    "DataQualityReport",
    "DatasetRegistry",
    "DatasetVersion",
]
