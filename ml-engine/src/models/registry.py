"""Model registry — trains and holds the served models with their metrics.

For the MVP this trains in-memory on startup. Production loads versioned artifacts from
object storage by stage/binding (see ARCHITECTURE §10.4). Swapping GradientBoosting for
XGBoost/CatBoost/LightGBM is a registry change only — the serving contract is unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, IsolationForest
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from src.features.synthetic import generate


@dataclass
class ModelBundle:
    default_model: object
    fraud_model: object
    version: str = "gbdt-v1"
    algorithm: str = "GradientBoostingClassifier + IsolationForest"
    metrics: dict = field(default_factory=dict)
    train_means: list[float] = field(default_factory=list)


def train() -> ModelBundle:
    X, y = generate()
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=7)

    # Plain GBDT keeps SHAP TreeExplainer attachable. Production adds probability
    # calibration (isotonic/Platt) — see ARCHITECTURE §10.4.
    model = GradientBoostingClassifier(n_estimators=150, max_depth=3, learning_rate=0.08)
    model.fit(X_tr, y_tr)

    # Unsupervised anomaly detector for the hybrid fraud engine (complements the rules).
    fraud = IsolationForest(n_estimators=120, contamination=0.05, random_state=7)
    fraud.fit(X_tr)

    proba = model.predict_proba(X_te)[:, 1]
    auc = float(roc_auc_score(y_te, proba))

    return ModelBundle(
        default_model=model,
        fraud_model=fraud,
        metrics={"auc": round(auc, 4), "n_train": int(len(X_tr)),
                 "default_rate": round(float(y.mean()), 4)},
        train_means=[float(m) for m in X.mean(axis=0)],
    )


class Registry:
    def __init__(self) -> None:
        self.bundle: ModelBundle | None = None

    def load(self) -> ModelBundle:
        if self.bundle is None:
            self.bundle = train()
        return self.bundle


registry = Registry()
