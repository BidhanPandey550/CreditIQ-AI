# Registry and Monitoring

## Model registry

`FileModelRegistry` is the durable registry for local and single-node deployments. It stores model
versions and audit events in one schema-versioned JSON document and commits changes using a flushed
temporary file followed by atomic `os.replace`.

Registered artifacts must carry a trusted SHA-256 checksum. Lifecycle transitions are validated by
`LifecycleStateMachine`. Only one production version may exist for a model identity. Rollback
demotes the current production version and promotes a champion in one atomic registry write.

For multi-instance production deployment, replace this adapter with a transactional PostgreSQL or
managed registry adapter behind the same operations; do not share the JSON file across hosts.

## Artifact loading

`ArtifactStore` is the only authorized Joblib deserialization boundary. It validates file existence,
format and checksum before calling `joblib.load`. `BaseTrainer` and `BaseFraudDetector` return a
`ModelArtifact` from `save()` and require its checksum when loading.

## Monitoring

`InMemoryDecisionMonitor` records privacy-safe operational events only: correlation ID, success,
latency, recommendation, model versions and warning codes. It never stores applicant features or
identity data. The bounded event window reports count, failures, average and p95 latency, plus a
configuration-driven health state.

Monitoring is injected into `DecisionEngine`. Failure of the monitoring backend adds
`monitoring_unavailable` and marks the decision `degraded`, but does not discard an otherwise safe
decision. Artifact-integrity failure remains blocking and is never converted into degradation.

The in-memory adapter is an operational baseline, not the final telemetry platform. Durable metrics,
outcome monitoring, drift analysis and alert delivery remain future adapters.
