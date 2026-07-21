# Data Quality, Profiling, and Versioning

`DataQualityAnalyzer` produces aggregate completeness, duplicate, cardinality, IQR-outlier, target
balance, recommendation, and health-score results. `DatasetProfiler` records bounded numerical and
categorical summaries plus memory usage without persisting raw applicant values.

`DatasetRegistry` writes processed frames as Parquet with atomic replacement. A deterministic
SHA-256 digest over schema, dtypes, index, and values creates the version ID. Every load recomputes
the checksum and rejects corrupted or substituted data. Metadata remains immutable and can record
pipeline version, source, purpose, and configuration hash.
