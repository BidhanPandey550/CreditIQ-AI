"""Integration test for the complete fraud intelligence path."""

import json

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from creditiq_ai.config import load_config
from creditiq_ai.fraud import FraudDetectionPipeline
from creditiq_ai.fraud_intelligence import BehaviourInput, EnterpriseFraudPipeline, FraudRequest
from tests.fixtures.synthetic import make_credit_dataset

FEATURES = [
    "monthly_income",
    "monthly_expenses",
    "monthly_debt_payments",
    "total_assets",
    "total_liabilities",
    "savings_balance",
]


def test_complete_fraud_pipeline_and_reports(tmp_path) -> None:
    config = load_config()
    frame = make_credit_dataset(250)[FEATURES]
    scaler = StandardScaler().fit(frame)
    reference = pd.DataFrame(scaler.transform(frame), columns=FEATURES)
    detectors = FraudDetectionPipeline(config.fraud).fit(reference)
    outlier = pd.DataFrame([np.full(len(FEATURES), 8.0)], columns=FEATURES)
    pipeline = EnterpriseFraudPipeline(
        config, detectors, duplicate_check=lambda identity: identity.get("government_id") == "DUP"
    )
    result = pipeline.analyze(
        FraudRequest(
            anomaly_features=outlier,
            behaviour=BehaviourInput(
                monthly_income=[30000, 31000, 90000],
                monthly_expenses=[25000, 26000, 85000],
                monthly_savings=[3000, 2500, 0],
                monthly_debt_payments=[5000, 5000, 40000],
                transaction_counts=[20, 21, 95],
            ),
            identity={"full_name": "Test", "government_id": "DUP"},
            application={
                "debt_to_income": 2.5,
                "recent_loan_requests": 8,
                "income_growth_ratio": 4.0,
            },
            model_version="fraud-1.0.0",
        ),
        report_directory=tmp_path,
    )
    assert result.anomaly_detected
    assert result.fraud_score > 0
    assert result.risk_flags
    assert result.explanations
    assert result.recommended_action == "reject"
    assert result.model_version == "fraud-1.0.0"
    payload = json.loads((tmp_path / "fraud-assessment.json").read_text(encoding="utf-8"))
    assert payload["fraud_score"] == result.fraud_score
    assert (tmp_path / "fraud-assessment.md").exists()
