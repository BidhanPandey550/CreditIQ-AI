"""creditiq_ai.credit_intelligence — the Credit Intelligence Engine (Sprint 4).

Module 1 (Training Framework) public API. Importing this package registers the built-in trainers.

    from creditiq_ai.config import load_config
    from creditiq_ai.credit_intelligence import (
        CreditDataset, TrainingPipeline, training_configs_from_models,
    )
    configs = training_configs_from_models(load_config().models)
    pipeline = TrainingPipeline(configs)
    results = pipeline.run(dataset)
    best_result, best_trainer = pipeline.best()
"""

from creditiq_ai.credit_intelligence import algorithms  # noqa: F401  (registers trainers)
from creditiq_ai.credit_intelligence.calibration import (
    CalibrationConfig,
    CalibrationMethod,
    ProbabilityCalibratorFactory,
)
from creditiq_ai.credit_intelligence.datasets.dataset import CreditDataset
from creditiq_ai.credit_intelligence.evaluation import (
    ComparisonConfig,
    CreditEvaluationReport,
    CreditModelEvaluator,
    EvaluationConfig,
    ModelComparisonReport,
    ModelComparisonService,
)
from creditiq_ai.credit_intelligence.pipelines.training_pipeline import TrainingPipeline
from creditiq_ai.credit_intelligence.trainers.base import BaseTrainer
from creditiq_ai.credit_intelligence.trainers.config import (
    TrainingConfig,
    training_configs_from_models,
)
from creditiq_ai.credit_intelligence.trainers.context import TrainingContext
from creditiq_ai.credit_intelligence.trainers.factory import TrainingFactory
from creditiq_ai.credit_intelligence.trainers.registry import (
    available_algorithms,
    register,
)
from creditiq_ai.credit_intelligence.trainers.result import TrainingResult

__all__ = [
    "CreditDataset",
    "CalibrationConfig",
    "CalibrationMethod",
    "ProbabilityCalibratorFactory",
    "CreditEvaluationReport",
    "CreditModelEvaluator",
    "ComparisonConfig",
    "EvaluationConfig",
    "ModelComparisonReport",
    "ModelComparisonService",
    "TrainingConfig",
    "training_configs_from_models",
    "TrainingContext",
    "TrainingResult",
    "BaseTrainer",
    "TrainingFactory",
    "TrainingPipeline",
    "register",
    "available_algorithms",
]
