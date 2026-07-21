"""creditiq_ai.feature_engineering — Module 3 modular feature generators + pipeline."""

from creditiq_ai.feature_engineering.pipeline import FeatureEngineeringPipeline
from creditiq_ai.feature_engineering.registry import (
    available_features,
    get_generator_class,
    register,
)

__all__ = [
    "FeatureEngineeringPipeline",
    "register",
    "get_generator_class",
    "available_features",
]
