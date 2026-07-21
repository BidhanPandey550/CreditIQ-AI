"""TrainingFactory — Factory pattern for instantiating trainers from config.

Purpose:  Turn a TrainingConfig into a ready BaseTrainer without callers knowing concrete classes.
Inputs:   TrainingConfig (or algorithm name + config).
Outputs:  BaseTrainer instance.
Deps:     trainers.registry, trainers.base, trainers.config.
"""

from __future__ import annotations

from creditiq_ai.credit_intelligence.trainers.base import BaseTrainer
from creditiq_ai.credit_intelligence.trainers.config import TrainingConfig
from creditiq_ai.credit_intelligence.trainers.registry import (
    available_algorithms,
    get_trainer_class,
    is_registered,
)


class TrainingFactory:
    @staticmethod
    def create(config: TrainingConfig) -> BaseTrainer:
        return get_trainer_class(config.algorithm)(config)

    @staticmethod
    def available() -> list[str]:
        return available_algorithms()

    @staticmethod
    def supports(algorithm: str) -> bool:
        return is_registered(algorithm) and get_trainer_class(algorithm).dependency_available()
