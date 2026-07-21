"""Abstract base classes (ports) for every pluggable component.

Purpose:  Define the stable interfaces that concrete modules implement, enforcing the
          dependency-inversion and open/closed principles across the engine.
Inputs:   n/a (interfaces).
Outputs:  n/a.
Deps:     stdlib abc; core.logging, core.schemas, core.types (typing only).
Extend:   Subclass the relevant base; do not add framework/library imports here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from creditiq_ai.core.exceptions import ModelNotFittedError
from creditiq_ai.core.logging import get_logger
from creditiq_ai.core.schemas import (
    CreditScoreResult,
    EvaluationReport,
    Explanation,
    GlobalImportance,
    ModelMetadata,
    ValidationReport,
)
from creditiq_ai.core.types import DataFrame, NDArray, PathLike


class BaseComponent(ABC):
    """Common lifecycle for every engine component: a name, injected config, a logger.

    ``logger`` is a lazy property (not a stored attribute) so components stay picklable —
    Loguru loggers hold unpicklable sinks, and fitted components are serialised with joblib.
    """

    def __init__(self, name: str | None = None, config: dict[str, Any] | None = None) -> None:
        self.name = name or self.__class__.__name__
        self.config = config or {}

    @property
    def logger(self):
        return get_logger(f"creditiq_ai.{self.name}")


# --------------------------------------------------------------------------- data (M1)
class BaseDataLoader(BaseComponent):
    @abstractmethod
    def load(self, source: PathLike, **kwargs: Any) -> DataFrame:
        """Read a source into a validated DataFrame."""


class BaseValidator(BaseComponent):
    @abstractmethod
    def validate(self, df: DataFrame) -> ValidationReport:
        """Run validation rules; return a report (never raise for warnings)."""


# --------------------------------------------------------------------------- transforms (M2)
class BaseTransformer(BaseComponent):
    """sklearn-compatible transformer so steps compose in a Pipeline and serialise together."""

    _fitted: bool = False

    @abstractmethod
    def fit(self, X: DataFrame, y: NDArray | None = None) -> "BaseTransformer": ...

    @abstractmethod
    def transform(self, X: DataFrame) -> DataFrame: ...

    def fit_transform(self, X: DataFrame, y: NDArray | None = None) -> DataFrame:
        return self.fit(X, y).transform(X)

    def _check_fitted(self) -> None:
        if not self._fitted:
            raise ModelNotFittedError(f"{self.name} must be fitted before transform().")


# --------------------------------------------------------------------------- features (M3)
class BaseFeatureGenerator(BaseComponent):
    """Produces ONE feature or a cohesive feature group. Registered, never hard-wired.

    `dependencies` lists the input columns required so the pipeline can order generators and
    fail fast with a clear message if an input is missing.
    """

    feature_names: list[str] = []
    dependencies: list[str] = []

    @abstractmethod
    def generate(self, df: DataFrame) -> DataFrame:
        """Return `df` with the new feature column(s) added (pure; no in-place mutation)."""


# --------------------------------------------------------------------------- models (M4)
class BaseModel(BaseComponent):
    """Uniform wrapper over any estimator (sklearn / XGBoost / LightGBM / CatBoost)."""

    model_type: Any = None

    @abstractmethod
    def fit(self, X: DataFrame, y: NDArray) -> "BaseModel": ...

    @abstractmethod
    def predict(self, X: DataFrame) -> NDArray: ...

    @abstractmethod
    def predict_proba(self, X: DataFrame) -> NDArray: ...

    @abstractmethod
    def get_params(self) -> dict[str, Any]: ...

    @abstractmethod
    def save(self, path: PathLike) -> None: ...

    @classmethod
    @abstractmethod
    def load(cls, path: PathLike) -> "BaseModel": ...


# --------------------------------------------------------------------------- fraud (M7)
class BaseAnomalyDetector(BaseComponent):
    @abstractmethod
    def fit(self, X: DataFrame) -> "BaseAnomalyDetector": ...

    @abstractmethod
    def score(self, X: DataFrame) -> NDArray:
        """Anomaly scores (lower = more anomalous)."""

    @abstractmethod
    def predict(self, X: DataFrame) -> NDArray:
        """Return {-1 (anomaly), 1 (normal)} per row."""


# --------------------------------------------------------------------------- explain (M8)
class BaseExplainer(BaseComponent):
    @abstractmethod
    def explain_local(self, model: BaseModel, x: DataFrame) -> Explanation: ...

    @abstractmethod
    def explain_global(self, model: BaseModel, X: DataFrame) -> GlobalImportance: ...


# --------------------------------------------------------------------------- scoring (M5)
class BaseScorer(BaseComponent):
    """Strategy for mapping model output / features to the 300–850 score."""

    @abstractmethod
    def score(
        self, *, probability: float | None = None, features: dict[str, float] | None = None
    ) -> CreditScoreResult: ...


# --------------------------------------------------------------------------- evaluation (M9)
class BaseEvaluator(BaseComponent):
    @abstractmethod
    def evaluate(
        self, y_true: NDArray, y_pred: NDArray, y_proba: NDArray | None = None
    ) -> EvaluationReport: ...


# --------------------------------------------------------------------------- registry (M12)
class BaseRegistry(BaseComponent):
    @abstractmethod
    def save(self, model: BaseModel, metadata: ModelMetadata) -> str:
        """Persist a model + metadata; return the assigned version id."""

    @abstractmethod
    def load(self, name: str, version: str | None = None) -> tuple[BaseModel, ModelMetadata]:
        """Load a model version (latest if version is None)."""

    @abstractmethod
    def list_versions(self, name: str) -> list[ModelMetadata]: ...
