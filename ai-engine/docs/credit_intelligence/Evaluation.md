# Credit Model Evaluation

`CreditModelEvaluator` is the canonical evaluation service for binary probability-of-default
models. It is estimator-agnostic: callers provide observed labels and positive-class default
probabilities, so the same contract works for local models and future remote inference adapters.

## Metrics

The report contains accuracy, precision, recall, F1, ROC-AUC, PR-AUC, log loss, Brier score,
Matthews correlation coefficient, balanced accuracy, a 2×2 confusion matrix, a classification
report, and quantile-binned calibration points.

Threshold and calibration-bin choices are supplied with `EvaluationConfig`. They must be selected
and governed for each lender and portfolio; the defaults are engineering defaults, not an approval
policy. Model evaluation does not itself make lending decisions.

## Example

```python
from creditiq_ai.credit_intelligence.evaluation import CreditModelEvaluator, EvaluationConfig

evaluator = CreditModelEvaluator(EvaluationConfig(decision_threshold=0.45))
report = evaluator.evaluate(y_test, pd_probabilities, model_name="candidate", model_version="1.0")
payload = report.model_dump(mode="json")
```

## Extension points

Fairness, segment stability, temporal backtesting, learning curves, and threshold-cost analysis
belong in separate evaluators that consume this report rather than duplicating its metric logic.
