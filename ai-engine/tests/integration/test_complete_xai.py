"""Integration coverage for global, counterfactual, summary, and audit XAI."""

import json

from creditiq_ai.config import load_config
from creditiq_ai.credit_intelligence import CreditDataset, TrainingConfig, TrainingContext
from creditiq_ai.credit_intelligence.algorithms.logistic_regression import LogisticRegressionTrainer
from creditiq_ai.explainability import (
    CounterfactualService,
    DecisionSummaryService,
    GlobalImportanceService,
    LocalExplanationService,
    XAIAuditReportGenerator,
    build_context,
)
from tests.fixtures.synthetic import make_credit_dataset


def test_complete_xai_flow_and_audit_reports(tmp_path) -> None:
    config = load_config()
    frame = make_credit_dataset(180)
    features = frame.drop(columns=["applicant_id", "default"])
    training = TrainingConfig("logistic_regression", {"max_iter": 500}, cv_folds=2)
    trainer = LogisticRegressionTrainer(training)
    trainer.train(TrainingContext(CreditDataset(features, frame["default"]), training))
    context = build_context(
        trainer, features, model_version="credit-1", feature_version="features-1"
    )
    row = features.iloc[[0]]
    local = LocalExplanationService(config.explainability).explain(context, row)
    global_report = GlobalImportanceService(config.explainability).analyze(context, features)
    counterfactual = CounterfactualService(config.explainability).generate(context, row)
    summary = DecisionSummaryService().create(
        credit_score=680,
        risk_level="medium",
        recommendation="review",
        confidence=0.82,
        local=local,
        counterfactual=counterfactual,
    )
    artifacts = XAIAuditReportGenerator().generate(
        tmp_path, summary=summary, local=local, global_importance=global_report
    )
    assert global_report.features[0].rank == 1
    assert global_report.sample_count == 180
    assert summary.model_version == "credit-1"
    assert len(artifacts) == 2
    payload = json.loads((tmp_path / "xai-audit-report.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["model_version"] == "credit-1"
    assert (tmp_path / "xai-audit-report.md").exists()
