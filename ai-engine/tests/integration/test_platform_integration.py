"""Sprint 8.5 — cross-sprint integration tests (what genuinely integrates today).

Exercises the REAL end-to-end path that exists in the repository:
  data cleaning → imputation → feature engineering → credit training → PD → explanation,
  fraud detection ensemble → fraud scoring,
  model-operations domain + lifecycle.

Deterministic (fixed seed). Does NOT assert capabilities that are not yet built (credit-score
engine, unified decision engine, registry ops, monitoring) — those are tracked as audit findings.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from creditiq_ai.config import load_config
from creditiq_ai.core.enums import ModelType
from creditiq_ai.core.schemas import ModelMetadata
from creditiq_ai.credit_intelligence import CreditDataset, TrainingConfig, TrainingContext
from creditiq_ai.credit_intelligence.algorithms.logistic_regression import (
    LogisticRegressionTrainer,
)
from creditiq_ai.explainability import LocalExplanationService, build_context
from creditiq_ai.fraud import FraudDetectionPipeline
from creditiq_ai.fraud_intelligence import FraudScoringEngine, FraudSignals
from creditiq_ai.model_operations import (
    LifecycleStage,
    LifecycleStateMachine,
    ModelFamily,
    ModelIdentity,
    ModelVersion,
)
from tests.fixtures.synthetic import make_credit_dataset

CONTINUOUS = [
    "monthly_income",
    "monthly_expenses",
    "monthly_debt_payments",
    "total_assets",
    "total_liabilities",
    "savings_balance",
]


# --------------------------------------------------------------------------- DATA → FEATURES → CREDIT
def test_data_to_features_to_credit_to_explanation_integrates():
    cfg = load_config()

    # data engineering (Sprint 2) — cleaning is exercised on raw applicant data
    from creditiq_ai.preprocessing.cleaning import DataCleaningEngine
    from creditiq_ai.preprocessing.imputation import MissingValueEngine
    from creditiq_ai.feature_engineering import FeatureEngineeringPipeline

    raw = make_credit_dataset(300)
    cleaned, clean_report = DataCleaningEngine(cfg.cleaning).clean(raw)
    imputed, _ = MissingValueEngine(cfg.imputation).fit_transform(cleaned)
    engineered = FeatureEngineeringPipeline(cfg.features).transform(imputed)

    # contract: feature engineering produced the credit features
    for feat in ("debt_to_income", "savings_ratio", "financial_behaviour_index"):
        assert feat in engineered.columns

    # credit training (Sprint 4) on the engineered numeric features
    y = raw["default"]
    X = engineered.select_dtypes(include=[np.number]).drop(columns=["default"], errors="ignore")
    tcfg = TrainingConfig(algorithm="logistic_regression", params={"max_iter": 1000}, cv_folds=3)
    trainer = LogisticRegressionTrainer(tcfg)
    result = trainer.train(TrainingContext(dataset=CreditDataset(X, y), config=tcfg))

    pd_hat = trainer.predict_proba(X)
    assert ((pd_hat >= 0) & (pd_hat <= 1)).all()  # probability of default is valid
    assert 0.0 <= result.primary_score <= 1.0

    # explainability (Sprint 6) integrates with the trained credit model
    ctx = build_context(trainer, X, model_version="credit_lr-1.0.0")
    explanation = LocalExplanationService(cfg.explainability).explain(ctx, X.iloc[[0]])
    assert explanation.explanation.narrative
    assert explanation.model_version == "credit_lr-1.0.0"

    # privacy: applicant identifier must NOT appear in the human explanation
    assert "a00000" not in explanation.explanation.narrative.lower()
    assert "applicant_id" not in explanation.explanation.narrative.lower()


# --------------------------------------------------------------------------- FRAUD ensemble → scoring
def test_fraud_detection_to_scoring_integrates():
    cfg = load_config()
    df = make_credit_dataset(300)[CONTINUOUS]
    scaler = StandardScaler().fit(df)
    ref = pd.DataFrame(scaler.transform(df), columns=CONTINUOUS)
    suspicious = pd.DataFrame([np.full(len(CONTINUOUS), 7.0)], columns=CONTINUOUS)

    detection = FraudDetectionPipeline(cfg.fraud).fit(ref)
    fraud_result = detection.analyze(suspicious)[0]
    assert 0.0 <= fraud_result.fraud_probability <= 1.0

    # detector ensemble anomaly probability feeds the 0–1000 scoring engine (Sprint 7)
    scoring = FraudScoringEngine(cfg.fraud_intelligence.scoring)
    fraud_score = scoring.score(FraudSignals(anomaly_probability=fraud_result.fraud_probability))
    assert 0 <= fraud_score.fraud_score <= 1000
    assert fraud_score.fraud_risk_level.value in {"very_low", "low", "moderate", "high", "critical"}
    assert fraud_score.recommended_action in {"approve", "review", "manual_review", "reject"}


# --------------------------------------------------------------------------- MODEL OPS domain/lifecycle
def test_model_operations_registration_contract_and_lifecycle():
    meta = ModelMetadata(
        name="credit_lr",
        version="1.0.0",
        model_type=ModelType.LOGISTIC_REGRESSION,
        metrics={"roc_auc": 0.8},
    )
    mv = ModelVersion(
        identity=ModelIdentity(name="credit_lr", family=ModelFamily.CREDIT),
        version="1.0.0",
        metadata=meta,
    )
    assert mv.stage is LifecycleStage.CREATED

    sm = LifecycleStateMachine()
    # a legal promotion chain validates without raising
    for a, b in [
        (LifecycleStage.CREATED, LifecycleStage.REGISTERED),
        (LifecycleStage.REGISTERED, LifecycleStage.VALIDATED),
        (LifecycleStage.VALIDATED, LifecycleStage.STAGING),
    ]:
        sm.validate_transition(a, b)


# --------------------------------------------------------------------------- config contract
def test_all_engine_config_sections_present():
    cfg = load_config()
    for section in (
        "cleaning",
        "imputation",
        "features",
        "models",
        "scoring",
        "fraud",
        "explainability",
        "fraud_intelligence",
    ):
        assert hasattr(cfg, section), section
