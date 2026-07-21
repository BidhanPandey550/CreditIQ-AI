"""Compatibility shim. Canonical exceptions now live in ``creditiq_ai.exceptions``.

Kept so existing imports (``from creditiq_ai.core.exceptions import ...``) continue to work
after the Sprint 1 restructure. New code should import from ``creditiq_ai.exceptions``.
"""

from creditiq_ai.exceptions import *  # noqa: F401,F403
from creditiq_ai.exceptions import __all__  # noqa: F401
