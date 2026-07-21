"""creditiq_ai.preprocessing.cleaning — the Data Cleaning Engine.

Strategy + Factory driven; config is injected from the unified EngineConfig.cleaning:

    from creditiq_ai.config import load_config
    from creditiq_ai.preprocessing.cleaning import DataCleaningEngine
    cfg = load_config()
    cleaned, report = DataCleaningEngine(cfg.cleaning).clean(df)
"""

from creditiq_ai.config.models import CleaningConfig, CleanerStep
from creditiq_ai.preprocessing.cleaning.base import (
    BaseCleaner,
    CleaningReport,
    CleaningStepReport,
)
from creditiq_ai.preprocessing.cleaning.engine import DataCleaningEngine
from creditiq_ai.preprocessing.cleaning.factory import CleanerFactory, register

__all__ = [
    "DataCleaningEngine",
    "CleanerFactory",
    "register",
    "BaseCleaner",
    "CleaningConfig",
    "CleanerStep",
    "CleaningReport",
    "CleaningStepReport",
]
