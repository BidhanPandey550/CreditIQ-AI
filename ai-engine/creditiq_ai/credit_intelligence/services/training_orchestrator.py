"""End-to-end holdout training, evaluation, comparison, and report orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from creditiq_ai.core.base import BaseComponent
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
from creditiq_ai.credit_intelligence.reports import CreditReportGenerator, ReportArtifact
from creditiq_ai.credit_intelligence.trainers.base import BaseTrainer
from creditiq_ai.credit_intelligence.trainers.config import TrainingConfig
from creditiq_ai.credit_intelligence.trainers.result import TrainingResult


class OrchestrationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    test_size: float = Field(default=0.2, gt=0.0, lt=0.5)
    random_seed: int = 42
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    comparison: ComparisonConfig = Field(default_factory=ComparisonConfig)


@dataclass(frozen=True)
class CreditTrainingRun:
    training_results: list[TrainingResult]
    evaluation_reports: list[CreditEvaluationReport]
    comparison: ModelComparisonReport
    champion: BaseTrainer
    report_artifacts: list[ReportArtifact]
    training_dataset_version: str
    holdout_dataset_version: str


class CreditTrainingOrchestrator(BaseComponent):
    """Coordinate existing services while keeping each stage independently replaceable."""

    def __init__(
        self,
        training_configs: list[TrainingConfig],
        config: OrchestrationConfig | None = None,
    ) -> None:
        super().__init__()
        self.training_configs = training_configs
        self.orchestration_config = config or OrchestrationConfig()

    def run(
        self, dataset: CreditDataset, *, report_directory: str | Path | None = None
    ) -> CreditTrainingRun:
        config = self.orchestration_config
        training_set, holdout_set = dataset.split(config.test_size, config.random_seed)
        pipeline = TrainingPipeline(self.training_configs)
        training_results = pipeline.run(training_set)
        evaluator = CreditModelEvaluator(config.evaluation)
        evaluations = [
            evaluator.evaluate(
                holdout_set.y,
                trainer.predict_proba(holdout_set.X),
                model_name=result.algorithm,
                model_version=training_set.version,
            )
            for result in training_results
            for trainer in [pipeline.trainers[result.algorithm]]
        ]
        comparison = ModelComparisonService(config.comparison).compare(evaluations)
        champion = pipeline.trainers[comparison.selected_model]
        artifacts = (
            CreditReportGenerator().generate(
                report_directory,
                training=training_results,
                evaluations=evaluations,
                comparison=comparison,
            )
            if report_directory is not None
            else []
        )
        self.logger.info(
            "Credit training run completed | champion={} train={} holdout={}",
            comparison.selected_model,
            training_set.n_rows,
            holdout_set.n_rows,
        )
        return CreditTrainingRun(
            training_results=training_results,
            evaluation_reports=evaluations,
            comparison=comparison,
            champion=champion,
            report_artifacts=artifacts,
            training_dataset_version=training_set.version,
            holdout_dataset_version=holdout_set.version,
        )
