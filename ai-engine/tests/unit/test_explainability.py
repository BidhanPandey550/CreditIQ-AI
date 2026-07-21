"""Tests for Sprint 6 Module 1 — Local Explanations (framework + marginal + SHAP fallback)."""

from creditiq_ai.config import load_config
from creditiq_ai.core.schemas import FeatureContribution
from creditiq_ai.credit_intelligence import CreditDataset, TrainingConfig, TrainingContext
from creditiq_ai.credit_intelligence.algorithms.logistic_regression import (
    LogisticRegressionTrainer,
)
from creditiq_ai.explainability import (
    LocalExplanation,
    LocalExplanationService,
    available_explainers,
    build_context,
)
from creditiq_ai.explainability.explainers.base import RawContributions
from creditiq_ai.explainability.templates.renderer import NarrativeRenderer
from creditiq_ai.explainability.validators.completeness import CompletenessValidator
from tests.fixtures.synthetic import make_credit_dataset


def _trained():
    df = make_credit_dataset(200)
    X, y = df.drop(columns=["applicant_id", "default"]), df["default"]
    cfg = TrainingConfig(algorithm="logistic_regression", params={"max_iter": 1000}, cv_folds=3)
    trainer = LogisticRegressionTrainer(cfg)
    trainer.train(TrainingContext(dataset=CreditDataset(X, y), config=cfg))
    return trainer, X


# --------------------------------------------------------------------------- registry / context
def test_registry_has_marginal_and_shap():
    assert {"marginal", "shap"} <= set(available_explainers())


def test_build_context_infers_model_kind():
    trainer, X = _trained()
    ctx = build_context(trainer, X)
    assert ctx.model_kind == "linear"
    assert ctx.feature_names == list(X.columns)


# --------------------------------------------------------------------------- end-to-end service
def test_local_explanation_end_to_end():
    trainer, X = _trained()
    ctx = build_context(trainer, X, model_version="lr-v1", feature_version="feat-v1")
    service = LocalExplanationService(load_config().explainability)
    result = service.explain(ctx, X.iloc[[0]])

    assert isinstance(result, LocalExplanation)
    assert result.method == "marginal"  # SHAP absent → agnostic fallback
    assert 0.0 <= result.explanation.prediction <= 1.0
    assert len(result.explanation.top_contributors) > 0
    assert result.explanation.narrative  # rendered from config templates
    assert result.confidence_explanation
    assert result.model_version == "lr-v1"


def test_every_feature_is_attributed():
    trainer, X = _trained()
    ctx = build_context(trainer, X)
    service = LocalExplanationService(load_config().explainability)
    result = service.explain(ctx, X.iloc[[3]])
    # marginal attributes every feature → explanation is complete
    assert result.complete
    assert result.issues == []


# --------------------------------------------------------------------------- narrative (config)
def test_narrative_uses_config_labels_and_templates():
    renderer = NarrativeRenderer(load_config().explainability)
    text = renderer.render(
        prediction=0.72,
        positives=[FeatureContribution(feature="debt_to_income", value=0.5, contribution=0.1)],
        negatives=[FeatureContribution(feature="savings_ratio", value=0.3, contribution=-0.05)],
    )
    assert "debt-to-income ratio" in text  # human label from config
    assert "savings ratio" in text
    assert "72%" in text  # summary template filled


# --------------------------------------------------------------------------- validation
def test_validator_flags_missing_contributions():
    raw = RawContributions(
        base_value=0.4,
        prediction=0.6,
        contributions=[FeatureContribution(feature="a", value=1.0, contribution=0.2)],
    )
    result = CompletenessValidator(["a", "b"], tolerance=0.05).validate(raw)
    assert not result.complete
    assert any("Missing" in issue for issue in result.issues)


def test_validator_flags_out_of_range_prediction():
    raw = RawContributions(
        base_value=0.4,
        prediction=1.4,
        contributions=[FeatureContribution(feature="a", value=1.0, contribution=1.0)],
    )
    result = CompletenessValidator(["a"], tolerance=0.05).validate(raw)
    assert not result.complete
    assert any("outside" in issue for issue in result.issues)


def test_validator_passes_consistent_explanation():
    raw = RawContributions(
        base_value=0.3,
        prediction=0.7,
        contributions=[
            FeatureContribution(feature="a", value=1.0, contribution=0.25),
            FeatureContribution(feature="b", value=2.0, contribution=0.15),
        ],
    )
    result = CompletenessValidator(["a", "b"], tolerance=0.05).validate(raw)
    assert result.complete
