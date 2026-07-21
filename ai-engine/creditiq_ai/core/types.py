"""Shared type aliases.

Purpose:  Consistent typing vocabulary without importing heavy libs at module top level
          where avoidable.
Deps:     pandas, numpy (typing only).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias, Union

if TYPE_CHECKING:  # avoid hard import cost where only typing is needed
    import numpy as np
    import pandas as pd

    DataFrame: TypeAlias = pd.DataFrame
    Series: TypeAlias = pd.Series
    NDArray: TypeAlias = np.ndarray
else:  # runtime fallbacks keep annotations importable without the libs installed
    DataFrame = Any
    Series = Any
    NDArray = Any

PathLike: TypeAlias = Union[str, Path]
JSONDict: TypeAlias = dict[str, Any]
FeatureMap: TypeAlias = dict[str, float]
