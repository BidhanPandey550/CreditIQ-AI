"""creditiq_ai.preprocessing — data preprocessing engines.

Canonical, Strategy+Factory-based engines live in subpackages:
    - creditiq_ai.preprocessing.cleaning     (Data Cleaning Engine)
    - creditiq_ai.preprocessing.imputation   (Missing Value Engine)

Sprint-4 will add outlier / encoding / scaling / feature-selection engines here in the same
pattern. The former transformers.py / pipeline.py prototype was removed in Sprint 3.5 (its
imputation & currency logic was superseded by the engines above).
"""
