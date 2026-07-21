import pandas as pd
import pytest

from creditiq_ai.data import DataQualityAnalyzer, DatasetProfiler, DatasetRegistry
from creditiq_ai.exceptions import DataLoadingError


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "income": [10.0, 11.0, 12.0, 500.0, None],
            "segment": ["a", "a", "b", "b", "b"],
            "default": [0, 0, 0, 0, 1],
        }
    )


def test_quality_analyzer_reports_issues_and_health():
    report = DataQualityAnalyzer().analyze(_frame(), target="default")
    assert report.row_count == 5
    assert report.health_score < 100
    assert "review_missing_values" in report.recommendations
    assert "review_numeric_outliers" in report.recommendations


def test_profiler_reports_numeric_categorical_and_memory():
    profile = DatasetProfiler().profile(_frame())
    assert "income" in profile.numerical
    assert profile.categorical["segment"]["cardinality"] == 2
    assert profile.memory_bytes > 0


def test_dataset_registry_roundtrip_and_integrity(tmp_path):
    registry = DatasetRegistry(tmp_path)
    original = _frame()
    version = registry.save(original, metadata={"purpose": "training"})
    loaded, restored = registry.load(version.version_id)
    pd.testing.assert_frame_equal(loaded, original)
    assert restored.checksum_sha256 == version.checksum_sha256
    (tmp_path / version.version_id / "dataset.parquet").write_bytes(b"corrupt")
    with pytest.raises(DataLoadingError):
        registry.load(version.version_id)
