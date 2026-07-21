"""creditiq_ai.preprocessing — data preprocessing engines.

Canonical, Strategy+Factory-based engines live in subpackages:
    - creditiq_ai.preprocessing.cleaning     (Data Cleaning Engine)
    - creditiq_ai.preprocessing.imputation   (Missing Value Engine)

Sprint-4 will add outlier / encoding / scaling / feature-selection engines here in the same
pattern. The former transformers.py / pipeline.py prototype was removed in Sprint 3.5 (its
imputation & currency logic was superseded by the engines above).
"""

from creditiq_ai.preprocessing.encoding import EncodingEngine, EncodingReport
from creditiq_ai.preprocessing.outliers import OutlierEngine, OutlierReport
from creditiq_ai.preprocessing.pipeline import PreprocessingPipeline, PreprocessingReport
from creditiq_ai.preprocessing.scaling import ScalingEngine, ScalingReport
from creditiq_ai.preprocessing.selection import FeatureSelectionEngine, FeatureSelectionReport
from creditiq_ai.preprocessing.serialization import PipelineArtifact, PipelineSerializer

__all__ = [
    "EncodingEngine",
    "EncodingReport",
    "OutlierEngine",
    "OutlierReport",
    "PreprocessingPipeline",
    "PreprocessingReport",
    "ScalingEngine",
    "ScalingReport",
    "FeatureSelectionEngine",
    "FeatureSelectionReport",
    "PipelineArtifact",
    "PipelineSerializer",
]
