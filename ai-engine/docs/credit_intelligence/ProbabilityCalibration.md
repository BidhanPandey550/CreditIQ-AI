# Probability Calibration

CreditIQ AI calibrates raw probability-of-default outputs through an estimator-independent
strategy contract. `ProbabilityCalibratorFactory` currently provides Platt scaling and isotonic
regression. Both accept raw probabilities and observed holdout labels and return a serializable
quality report containing Brier score, log loss, and expected calibration error before and after.

Platt scaling is the preferred baseline for smaller calibration sets and smooth monotonic
miscalibration. Isotonic regression is more flexible but needs substantially more independent
holdout data and can overfit small samples. Calibration data must not be the model's training data.

All clipping, minimum-sample, binning, and random-seed behavior is controlled by
`CalibrationConfig`. Calibrated probabilities remain bounded strictly inside `(0, 1)` for safe
downstream log-odds scoring.
