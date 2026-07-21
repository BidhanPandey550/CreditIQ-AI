# Transformation Engines

The preprocessing subsystem exposes independent, dependency-injected engines with fitted training
state reused unchanged during inference.

- **Outliers:** IQR is robust for skewed financial data; Z-score suits approximately normal data;
  percentile/winsorization offers explicit tail control; Isolation Forest handles multivariate
  anomalies. Clipping preserves rows, while removal must be restricted to training workflows.
- **Encoding:** one-hot suits low-cardinality nominal data; ordinal requires meaningful ordering;
  labels provide compact identifiers; frequency handles moderate cardinality; target encoding is
  smoothed and must be fitted only on training folds; hashing provides bounded dimensionality.
- **Scaling:** standard, min-max, robust, max-absolute, and row normalization retain DataFrame
  labels. Robust scaling is generally preferred when legitimate financial extremes remain.
- **Selection:** variance and correlation are unsupervised; mutual information and chi-square are
  filter methods; RFE is a wrapper; random-forest importance is embedded selection.

`PreprocessingPipeline` composes these stages without hiding their reports. `PipelineSerializer`
supports Joblib and Pickle for compatibility, but verifies SHA-256 before either deserializer runs.
Artifacts include immutable version and metadata manifests.
