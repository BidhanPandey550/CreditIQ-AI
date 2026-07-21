"""CreditIQ AI — production credit-intelligence ML engine.

A framework-free library: risk modelling, alternative credit scoring, default probability,
fraud detection, and explainability, behind stable typed contracts. See docs/ARCHITECTURE.md.
"""

from creditiq_ai.config import EngineConfig, get_config, load_config
from creditiq_ai.core.logging import get_logger

__version__ = "0.1.0"
__all__ = ["EngineConfig", "load_config", "get_config", "get_logger", "__version__"]
