"""Tests for Sprint 4 Module 1 — the Training Framework."""

import numpy as np
import pandas as pd
import pytest

from creditiq_ai.config import load_config
from creditiq_ai.credit_intelligence import (
    CreditDataset,
    TrainingConfig,
    TrainingContext,
    TrainingFactory,
    TrainingPipeline,
    training_configs_from_models,
)
from creditiq_ai.credit_intelligence.algorithms.logistic_regression import (
    LogisticRegressionTrainer,
)
from creditiq_ai.exceptions import ArtifactIntegrityError, ModelTrainingError
from tests.fixtures.synthetic import make_credit_dataset


def _dataset(n: int = 200) -> CreditDataset:
    df = make_credit_dataset(n)
    X = df.drop(columns=["applicant_id", "default"])
    y = df["default"]
    return CreditDataset(X=X, y=y, name="test")


# --------------------------------------------------------------------------- config
def test_training_config_rejects_bad_metric():
    with pytest.raises(ValueError):
        TrainingConfig(algorithm="logistic_regression", primary_metric="banana")


def test_configs_built_from_unified_model_zoo():
    configs = training_configs_from_models(load_config().models)
    algos = {c.algorithm for c in configs}
    assert {"logistic_regression", "random_forest", "xgboost", "lightgbm", "catboost"} <= algos


# --------------------------------------------------------------------------- registry / factory
def test_registry_lists_implemented_trainers():
    available = TrainingFactory.available()
    assert "logistic_regression" in available
    assert "random_forest" in available


def test_factory_creates_trainer():
    trainer = TrainingFactory.create(TrainingConfig(algorithm="logistic_regression"))
    assert isinstance(trainer, LogisticRegressionTrainer)


# --------------------------------------------------------------------------- single trainer
def test_trainer_trains_and_scores():
    cfg = TrainingConfig(algorithm="logistic_regression", params={"max_iter": 1000}, cv_folds=3)
    trainer = LogisticRegressionTrainer(cfg)
    result = trainer.train(TrainingContext(dataset=_dataset(), config=cfg))
    assert 0.0 <= result.primary_score <= 1.0
    assert len(result.cv.folds) == 3
    assert result.n_train == 200
    assert result.dataset_version  # provenance recorded


def test_trainer_predicts():
    cfg = TrainingConfig(algorithm="logistic_regression", params={"max_iter": 1000}, cv_folds=3)
    trainer = LogisticRegressionTrainer(cfg)
    ds = _dataset()
    trainer.train(TrainingContext(dataset=ds, config=cfg))
    proba = trainer.predict_proba(ds.X)
    assert proba.shape == (200,)
    assert ((proba >= 0) & (proba <= 1)).all()


def test_unfitted_trainer_raises():
    trainer = LogisticRegressionTrainer(TrainingConfig(algorithm="logistic_regression"))
    with pytest.raises(Exception):
        trainer.predict_proba(_dataset().X)


def test_single_class_target_raises():
    ds = _dataset()
    single = CreditDataset(X=ds.X, y=pd.Series(np.zeros(len(ds.X), dtype=int)), name="single")
    cfg = TrainingConfig(algorithm="logistic_regression", cv_folds=3)
    with pytest.raises(ModelTrainingError):
        LogisticRegressionTrainer(cfg).train(TrainingContext(dataset=single, config=cfg))


# --------------------------------------------------------------------------- persistence
def test_save_and_load_roundtrip(tmp_path):
    cfg = TrainingConfig(algorithm="logistic_regression", params={"max_iter": 1000}, cv_folds=3)
    trainer = LogisticRegressionTrainer(cfg)
    ds = _dataset()
    trainer.train(TrainingContext(dataset=ds, config=cfg))
    path = tmp_path / "model.joblib"
    artifact = trainer.save(path)
    reloaded = LogisticRegressionTrainer.load_artifact(artifact)
    np.testing.assert_allclose(trainer.predict_proba(ds.X), reloaded.predict_proba(ds.X))


def test_trainer_load_without_checksum_fails_closed(tmp_path):
    path = tmp_path / "model.joblib"
    trainer = LogisticRegressionTrainer(
        TrainingConfig(algorithm="logistic_regression", params={"max_iter": 1000}, cv_folds=3)
    )
    trainer.train(TrainingContext(dataset=_dataset(), config=trainer.train_config))
    trainer.save(path)
    with pytest.raises(ArtifactIntegrityError):
        LogisticRegressionTrainer.load(path)


# --------------------------------------------------------------------------- pipeline / leaderboard
def test_pipeline_trains_and_ranks():
    configs = [
        TrainingConfig(algorithm="logistic_regression", params={"max_iter": 1000}, cv_folds=3),
        TrainingConfig(algorithm="random_forest", params={"n_estimators": 50}, cv_folds=3),
    ]
    pipeline = TrainingPipeline(configs)
    results = pipeline.run(_dataset())
    assert len(results) == 2
    board = pipeline.leaderboard()
    assert board[0].primary_score >= board[1].primary_score  # ranked best-first
    best_result, best_trainer = pipeline.best()
    assert best_result is board[0]
    assert best_trainer.algorithm == best_result.algorithm


def test_pipeline_skips_unregistered_algorithms():
    configs = [
        TrainingConfig(algorithm="logistic_regression", params={"max_iter": 1000}, cv_folds=3),
        TrainingConfig(algorithm="xgboost", cv_folds=3),  # trainer not implemented yet
    ]
    results = TrainingPipeline(configs).run(_dataset())
    assert {r.algorithm for r in results} == {"logistic_regression"}


def test_pipeline_from_unified_config_trains_registered_only():
    configs = training_configs_from_models(load_config().models)
    results = TrainingPipeline(configs).run(_dataset())
    # Only logistic_regression + random_forest are implemented in Module 1.
    assert {r.algorithm for r in results} == {"logistic_regression", "random_forest"}
