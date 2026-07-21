from __future__ import annotations

import pandas as pd
import pytest

from creditiq_ai.config.models import (
    EncodingColumnConfig,
    EncodingConfig,
    FeatureSelectionConfig,
    OutlierConfig,
    ScalingConfig,
)
from creditiq_ai.exceptions import ArtifactIntegrityError, PreprocessingError
from creditiq_ai.preprocessing import (
    EncodingEngine,
    FeatureSelectionEngine,
    OutlierEngine,
    PipelineSerializer,
    PreprocessingPipeline,
    ScalingEngine,
)


@pytest.mark.parametrize(
    ("strategy", "params"),
    [
        ("iqr", {"multiplier": 1.5}),
        ("zscore", {"threshold": 2.0}),
        ("percentile", {"lower": 0.05, "upper": 0.95}),
        ("winsorization", {"lower": 0.05, "upper": 0.95}),
    ],
)
def test_statistical_outlier_strategies_clip(strategy, params):
    frame = pd.DataFrame({"value": list(range(20)) + [1000]})
    transformed, report = OutlierEngine(
        OutlierConfig(strategy=strategy, columns=["value"], action="clip", params=params)
    ).fit_transform(frame)
    assert transformed["value"].max() < 1000
    assert report.columns[0].count >= 1


def test_isolation_forest_can_remove_anomalies():
    frame = pd.DataFrame({"x": [0.0] * 30 + [100.0], "y": [0.0] * 31})
    transformed, report = OutlierEngine(
        OutlierConfig(
            strategy="isolation_forest",
            columns=["x", "y"],
            action="remove",
            params={"contamination": 0.05, "random_state": 42},
        )
    ).fit_transform(frame)
    assert report.rows_removed >= 1
    assert len(transformed) < len(frame)


@pytest.mark.parametrize("strategy", ["one_hot", "ordinal", "label", "frequency", "hash"])
def test_unsupervised_encoding_strategies_have_stable_schema(strategy):
    params = {"dimensions": 3} if strategy == "hash" else {}
    config = EncodingConfig(
        columns={"segment": EncodingColumnConfig(strategy=strategy, params=params)}
    )
    engine = EncodingEngine(config)
    training, _ = engine.fit_transform(pd.DataFrame({"segment": ["a", "b", "a"], "x": [1, 2, 3]}))
    inference, report = engine.transform(pd.DataFrame({"segment": ["unknown"], "x": [4]}))
    assert list(training.columns) == list(inference.columns)
    assert report.unknown_values["segment"] == 1


def test_target_encoding_requires_and_uses_labels():
    config = EncodingConfig(
        columns={"segment": EncodingColumnConfig(strategy="target", params={"smoothing": 1})}
    )
    frame = pd.DataFrame({"segment": ["a", "a", "b", "b"]})
    with pytest.raises(PreprocessingError):
        EncodingEngine(config).fit(frame)
    transformed, _ = EncodingEngine(config).fit_transform(frame, pd.Series([0, 0, 1, 1]))
    assert transformed.loc[0, "segment"] < transformed.loc[2, "segment"]


@pytest.mark.parametrize("strategy", ["standard", "minmax", "robust", "maxabs", "normalizer"])
def test_scaling_strategies_preserve_dataframe(strategy):
    frame = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [2.0, 4.0, 8.0], "id": [1, 2, 3]})
    transformed, report = ScalingEngine(
        ScalingConfig(strategy=strategy, columns=["a", "b"])
    ).fit_transform(frame)
    assert list(transformed.columns) == list(frame.columns)
    assert transformed["id"].equals(frame["id"])
    assert report.strategy == strategy


@pytest.mark.parametrize(
    "strategy", ["variance", "correlation", "mutual_information", "chi_square", "rfe", "importance"]
)
def test_feature_selection_strategies_return_stable_subset(strategy):
    frame = pd.DataFrame(
        {"a": [0, 0, 1, 1, 0, 1, 0, 1], "b": [0, 0, 1, 1, 0, 1, 0, 1], "constant": [1] * 8}
    )
    labels = pd.Series([0, 0, 1, 1, 0, 1, 0, 1])
    params = {"threshold": 0.9} if strategy == "correlation" else {"k": 1, "random_state": 42}
    transformed, report = FeatureSelectionEngine(
        FeatureSelectionConfig(strategy=strategy, params=params)
    ).fit_transform(frame, labels)
    assert 1 <= transformed.shape[1] < frame.shape[1]
    assert report.selected == list(transformed.columns)


def test_pipeline_serialization_verifies_integrity(tmp_path):
    pipeline = PreprocessingPipeline(
        scaling=ScalingEngine(ScalingConfig(strategy="standard", columns=["x"]))
    )
    training, report = pipeline.fit_transform(pd.DataFrame({"x": [1.0, 2.0, 3.0]}))
    assert "scale" in report.stages
    assert len(training) == 3
    serializer = PipelineSerializer()
    artifact = serializer.save(pipeline, tmp_path / "pipeline.joblib", version="1")
    loaded = serializer.load(artifact)
    assert loaded.transform(pd.DataFrame({"x": [4.0]})).shape == (1, 1)
    (tmp_path / "pipeline.joblib").write_bytes(b"tampered")
    with pytest.raises(ArtifactIntegrityError):
        serializer.load(artifact)
