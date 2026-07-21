"""Optuna-backed hyperparameter optimization integrated with the trainer factory."""

from __future__ import annotations

from typing import Any

import optuna

from creditiq_ai.core.base import BaseComponent
from creditiq_ai.credit_intelligence.datasets.dataset import CreditDataset
from creditiq_ai.credit_intelligence.trainers.config import TrainingConfig
from creditiq_ai.credit_intelligence.trainers.context import TrainingContext
from creditiq_ai.credit_intelligence.trainers.factory import TrainingFactory
from creditiq_ai.credit_intelligence.trainers.optimization_models import (
    OptimizationConfig,
    OptimizationResult,
    OptimizationTrial,
    SearchDimension,
    SearchDimensionType,
)
from creditiq_ai.exceptions import ModelTrainingError


class OptunaOptimizationService(BaseComponent):
    """Optimize any registered trainer using its configuration-defined search space."""

    def __init__(
        self,
        config: OptimizationConfig,
        factory: type[TrainingFactory] = TrainingFactory,
    ) -> None:
        super().__init__()
        self.optimization_config = config
        self._factory = factory

    def optimize(self, dataset: CreditDataset) -> OptimizationResult:
        config = self.optimization_config
        if not self._factory.supports(config.algorithm):
            raise ModelTrainingError(f"Trainer '{config.algorithm}' is unavailable")
        sampler = optuna.samplers.TPESampler(seed=config.random_seed)
        pruner = optuna.pruners.MedianPruner(n_startup_trials=config.pruning_startup_trials)
        study = optuna.create_study(
            direction="maximize",
            sampler=sampler,
            pruner=pruner,
            study_name=config.study_name,
            storage=config.storage_url,
            load_if_exists=config.storage_url is not None,
        )
        study.optimize(
            lambda trial: self._objective(trial, dataset),
            n_trials=config.trials,
            timeout=config.timeout_seconds,
            n_jobs=config.n_jobs,
            gc_after_trial=True,
        )
        if study.best_trial.value is None:
            raise ModelTrainingError(
                f"Optimization produced no completed trial for {config.algorithm}"
            )
        result = OptimizationResult(
            algorithm=config.algorithm,
            study_name=study.study_name,
            best_score=float(study.best_trial.value),
            best_params={**config.fixed_params, **study.best_trial.params},
            trials=[
                OptimizationTrial(
                    number=trial.number,
                    score=None if trial.value is None else float(trial.value),
                    state=trial.state.name.lower(),
                    params=dict(trial.params),
                )
                for trial in study.trials
            ],
        )
        self.logger.info(
            "Optimized {} | trials={} best_{}={:.4f}",
            config.algorithm,
            len(result.trials),
            config.primary_metric,
            result.best_score,
        )
        return result

    def _objective(self, trial: optuna.Trial, dataset: CreditDataset) -> float:
        config = self.optimization_config
        sampled = {
            name: self._suggest(trial, name, dimension)
            for name, dimension in config.search_space.items()
        }
        training_config = TrainingConfig(
            algorithm=config.algorithm,
            params={**config.fixed_params, **sampled},
            cv_folds=config.cv_folds,
            primary_metric=config.primary_metric,
            random_seed=config.random_seed,
        )
        trainer = self._factory.create(training_config)
        result = trainer.train(TrainingContext(dataset=dataset, config=training_config))
        trial.report(result.primary_score, step=0)
        if trial.should_prune():
            raise optuna.TrialPruned()
        return result.primary_score

    @staticmethod
    def _suggest(trial: optuna.Trial, name: str, dimension: SearchDimension) -> Any:
        if dimension.type == SearchDimensionType.INTEGER:
            assert dimension.low is not None and dimension.high is not None
            return trial.suggest_int(
                name,
                int(dimension.low),
                int(dimension.high),
                step=1 if dimension.step is None else int(dimension.step),
                log=dimension.log,
            )
        if dimension.type == SearchDimensionType.FLOAT:
            assert dimension.low is not None and dimension.high is not None
            return trial.suggest_float(
                name,
                float(dimension.low),
                float(dimension.high),
                step=None if dimension.step is None else float(dimension.step),
                log=dimension.log,
            )
        return trial.suggest_categorical(name, dimension.choices)
