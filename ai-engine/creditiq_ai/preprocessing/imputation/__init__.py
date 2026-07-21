"""creditiq_ai.preprocessing.imputation — the Missing Value Engine.

Config is injected from the unified EngineConfig.imputation:

    from creditiq_ai.config import load_config
    from creditiq_ai.preprocessing.imputation import MissingValueEngine
    cfg = load_config()
    imputed, report = MissingValueEngine(cfg.imputation).fit_transform(df)
"""

from creditiq_ai.config.models import ColumnStrategy, ImputationConfig
from creditiq_ai.preprocessing.imputation.base import (
    BaseImputer,
    ColumnImputation,
    ImputationReport,
)
from creditiq_ai.preprocessing.imputation.engine import MissingValueEngine
from creditiq_ai.preprocessing.imputation.factory import ImputerFactory, register

__all__ = [
    "MissingValueEngine",
    "ImputerFactory",
    "register",
    "BaseImputer",
    "ImputationConfig",
    "ColumnStrategy",
    "ImputationReport",
    "ColumnImputation",
]
