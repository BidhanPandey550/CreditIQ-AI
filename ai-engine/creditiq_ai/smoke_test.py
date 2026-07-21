"""End-to-end platform smoke test.

Run:  python -m creditiq_ai.smoke_test   (add --json for machine-readable output)

Exercises the real, deterministic end-to-end path that exists today and exits non-zero if any
critical step fails. Steps whose subsystem is not yet implemented are reported honestly as
``not_implemented`` rather than faked. No external services / credentials / internet required.

Importing this module has NO side effects — all work runs under main().
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from typing import Any

import numpy as np
import pandas as pd


def _synthetic(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 300
    income = rng.uniform(20_000, 150_000, n).round(2)
    expenses = (income * rng.uniform(0.3, 0.9, n)).round(2)
    debt = (income * rng.uniform(0.0, 0.5, n)).round(2)
    dti = debt / income
    prob = 1 / (1 + np.exp(-(-1.0 + 3.0 * dti)))
    return pd.DataFrame(
        {
            "applicant_id": [f"A{i:05d}" for i in range(n)],
            "monthly_income": income,
            "monthly_expenses": expenses,
            "monthly_debt_payments": debt,
            "total_assets": rng.uniform(0, 2_000_000, n).round(2),
            "total_liabilities": rng.uniform(0, 1_000_000, n).round(2),
            "savings_balance": rng.uniform(0, 500_000, n).round(2),
            "employment_months": rng.integers(0, 120, n),
            "num_existing_loans": rng.integers(0, 5, n),
            "has_delinquency": rng.binomial(1, 0.15, n),
            "default": rng.binomial(1, prob),
        }
    )


def run() -> dict[str, Any]:
    from sklearn.preprocessing import StandardScaler

    from creditiq_ai.config import load_config
    from creditiq_ai.credit_intelligence import CreditDataset, TrainingConfig, TrainingContext
    from creditiq_ai.credit_intelligence.algorithms.logistic_regression import (
        LogisticRegressionTrainer,
    )
    from creditiq_ai.explainability import LocalExplanationService, build_context
    from creditiq_ai.feature_engineering import FeatureEngineeringPipeline
    from creditiq_ai.fraud import FraudDetectionPipeline
    from creditiq_ai.fraud_intelligence import FraudScoringEngine, FraudSignals
    from creditiq_ai.model_operations import (
        FileModelRegistry,
        InMemoryDecisionMonitor,
        LifecycleStage,
        LifecycleStateMachine,
        ModelFamily,
        ModelIdentity,
        ModelVersion,
    )
    from creditiq_ai.core.enums import ModelType
    from creditiq_ai.core.schemas import ModelMetadata

    steps: dict[str, Any] = {}
    started = time.perf_counter()

    cfg = load_config()
    steps["1_config"] = {"status": "ok", "environment": cfg.environment.value}

    raw = _synthetic()
    steps["2_synthetic_data"] = {"status": "ok", "rows": len(raw)}

    from creditiq_ai.preprocessing.cleaning import DataCleaningEngine
    from creditiq_ai.preprocessing.imputation import MissingValueEngine

    cleaned, _ = DataCleaningEngine(cfg.cleaning).clean(raw)
    imputed, _ = MissingValueEngine(cfg.imputation).fit_transform(cleaned)
    engineered = FeatureEngineeringPipeline(cfg.features).transform(imputed)
    steps["3_features"] = {"status": "ok", "n_features": engineered.shape[1]}

    y = raw["default"]
    X = engineered.select_dtypes(include=[np.number]).drop(columns=["default"], errors="ignore")
    tcfg = TrainingConfig(algorithm="logistic_regression", params={"max_iter": 1000}, cv_folds=3)
    trainer = LogisticRegressionTrainer(tcfg)
    train_result = trainer.train(TrainingContext(dataset=CreditDataset(X, y), config=tcfg))
    steps["4_credit_training"] = {"status": "ok", "roc_auc": round(train_result.primary_score, 4)}

    pd_hat = float(trainer.predict_proba(X.iloc[[0]])[0])
    assert 0.0 <= pd_hat <= 1.0
    steps["5_credit_inference"] = {"status": "ok", "probability_of_default": round(pd_hat, 4)}

    explanation = LocalExplanationService(cfg.explainability).explain(
        build_context(trainer, X, model_version="credit_lr-1.0.0"), X.iloc[[0]]
    )
    steps["6_explanation"] = {
        "status": "ok",
        "method": explanation.method,
        "complete": explanation.complete,
    }

    scaler = StandardScaler().fit(X[["monthly_income", "monthly_expenses"]])
    ref = pd.DataFrame(
        scaler.transform(X[["monthly_income", "monthly_expenses"]]),
        columns=["monthly_income", "monthly_expenses"],
    )
    fraud_result = FraudDetectionPipeline(cfg.fraud).fit(ref).analyze(ref.iloc[[0]])[0]
    steps["7_fraud_detection"] = {
        "status": "ok",
        "anomaly_probability": fraud_result.fraud_probability,
    }

    fraud_score = FraudScoringEngine(cfg.fraud_intelligence.scoring).score(
        FraudSignals(anomaly_probability=fraud_result.fraud_probability)
    )
    steps["8_fraud_scoring"] = {
        "status": "ok",
        "fraud_score": fraud_score.fraud_score,
        "fraud_risk_level": fraud_score.fraud_risk_level.value,
    }

    sm = LifecycleStateMachine()
    mv = ModelVersion(
        identity=ModelIdentity(name="credit_lr", family=ModelFamily.CREDIT),
        version="1.0.0",
        metadata=ModelMetadata(
            name="credit_lr", version="1.0.0", model_type=ModelType.LOGISTIC_REGRESSION
        ),
    )
    sm.validate_transition(mv.stage, LifecycleStage.REGISTERED)
    steps["9_model_ops_lifecycle"] = {"status": "ok", "ref": mv.ref}

    # 10. Artifact integrity (D1): save + integrity-verified reload of the credit model.
    import os
    import tempfile

    from creditiq_ai.decision import DecisionEngine, DecisionRequest
    from creditiq_ai.model_operations import ArtifactStore

    store = ArtifactStore()
    runtime_dir = tempfile.mkdtemp()
    artifact = store.save(trainer, os.path.join(runtime_dir, "credit.joblib"))
    verified_model = store.load_artifact(artifact)  # checksum-verified load
    steps["10_artifact_integrity"] = {"status": "ok", "sha256": artifact.checksum_sha256[:12] + "…"}

    # 11. Unified decision (D2) using the VERIFIED model + fraud ensemble.
    fpipe = FraudDetectionPipeline(cfg.fraud).fit(ref)

    def _credit(r):
        return float(verified_model.predict_proba(r[list(X.columns)])[0])

    def _fraud(r):
        scaled = pd.DataFrame(
            scaler.transform(r[["monthly_income", "monthly_expenses"]]),
            columns=["monthly_income", "monthly_expenses"],
        )
        return FraudSignals(anomaly_probability=fpipe.analyze(scaled)[0].fraud_probability)

    monitor = InMemoryDecisionMonitor(cfg.monitoring)
    engine = DecisionEngine(cfg, credit_predictor=_credit, fraud_assessor=_fraud, monitor=monitor)
    decision = engine.decide(
        DecisionRequest(
            row=X.iloc[[0]], model_versions={"credit": mv.ref}, feature_version="feat-1"
        )
    )
    steps["11_unified_decision"] = {"status": "ok", "recommendation": decision.recommendation}

    # 12. Durable registry + production-version selection (D3).
    registry = FileModelRegistry(os.path.join(runtime_dir, "registry.json"))
    registered = registry.register(mv.model_copy(update={"artifacts": [artifact]}))
    for stage in (
        LifecycleStage.VALIDATED,
        LifecycleStage.STAGING,
        LifecycleStage.CHALLENGER,
        LifecycleStage.CHAMPION,
        LifecycleStage.PRODUCTION,
    ):
        registered = registry.transition(registered.ref, stage)
    production = registry.production(registered.identity)
    steps["12_registry_persistence"] = {
        "status": "ok",
        "production_version": production.version,
    }

    # 13–14. Privacy-safe inference event + operational health snapshot (D4 baseline).
    snapshot = monitor.snapshot()
    steps["13_monitoring_events"] = {
        "status": "ok",
        "prediction_count": snapshot.prediction_count,
    }
    steps["14_model_health"] = {"status": "ok", "health": snapshot.status}

    return {
        "smoke": "creditiq_ai",
        "duration_seconds": round(time.perf_counter() - started, 3),
        "unified_decision": decision.model_dump(mode="json"),
        "steps": steps,
    }


def main(argv: list[str] | None = None) -> int:
    as_json = "--json" in (argv if argv is not None else sys.argv[1:])
    try:
        summary = run()
    except Exception as exc:  # any critical step failure → non-zero exit
        print(f"SMOKE TEST FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1

    if as_json:
        print(json.dumps(summary, indent=2))
    else:
        print("CreditIQ AI — smoke test PASSED")
        for name, info in summary["steps"].items():
            print(f"  {name:32s} {info.get('status')}")
        ud = summary["unified_decision"]
        print(
            f"  unified decision: recommendation={ud['recommendation']} "
            f"credit_score={ud['credit_score']} pd={ud['probability_of_default']} "
            f"fraud_score={ud['fraud_score']} confidence={ud['confidence']}"
        )
        print(f"  ({summary['duration_seconds']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
