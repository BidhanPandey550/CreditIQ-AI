"""TrainingPipeline — train many algorithms, rank them, pick the best.

Purpose:  Orchestrate multi-model training from a list of TrainingConfigs, producing a ranked
          leaderboard and automatic best-model selection (no manual comparison). Unregistered
          algorithms (e.g. trainers not yet implemented) are skipped with a warning so the same
          config zoo keeps working as new trainers are added.
Inputs:   list[TrainingConfig] + a CreditDataset.
Outputs:  list[TrainingResult]; leaderboard; best (result, trainer).
Deps:     trainers.factory / .context; datasets.CreditDataset; exceptions.
"""

from __future__ import annotations

from creditiq_ai.core.base import BaseComponent
from creditiq_ai.credit_intelligence.datasets.dataset import CreditDataset
from creditiq_ai.credit_intelligence.trainers.base import BaseTrainer
from creditiq_ai.credit_intelligence.trainers.config import TrainingConfig
from creditiq_ai.credit_intelligence.trainers.context import TrainingContext
from creditiq_ai.credit_intelligence.trainers.factory import TrainingFactory
from creditiq_ai.credit_intelligence.trainers.result import TrainingResult
from creditiq_ai.exceptions import ModelTrainingError


class TrainingPipeline(BaseComponent):
    """Trains a set of algorithms and ranks them by their primary metric (higher = better)."""

    def __init__(
        self, configs: list[TrainingConfig], factory: type[TrainingFactory] = TrainingFactory
    ) -> None:
        super().__init__()
        self._configs = configs
        self._factory = factory
        self.trainers: dict[str, BaseTrainer] = {}
        self.results: list[TrainingResult] = []

    def run(self, dataset: CreditDataset) -> list[TrainingResult]:
        results: list[TrainingResult] = []
        for config in self._configs:
            if not self._factory.supports(config.algorithm):
                self.logger.warning(f"Skipping '{config.algorithm}' — no trainer registered yet")
                continue
            trainer = self._factory.create(config)
            result = trainer.train(TrainingContext(dataset=dataset, config=config))
            self.trainers[config.algorithm] = trainer
            results.append(result)

        if not results:
            raise ModelTrainingError("No models were trained (no registered algorithms in config)")

        self.results = results
        self.logger.info(f"Training pipeline complete: {len(results)} model(s) trained")
        return results

    def leaderboard(self) -> list[TrainingResult]:
        """Results ranked best-first by the primary metric (all sklearn scorers: higher = better)."""
        return sorted(self.results, key=lambda r: r.primary_score, reverse=True)

    def best(self) -> tuple[TrainingResult, BaseTrainer]:
        board = self.leaderboard()
        if not board:
            raise ModelTrainingError("No trained models available; call run() first")
        winner = board[0]
        return winner, self.trainers[winner.algorithm]
