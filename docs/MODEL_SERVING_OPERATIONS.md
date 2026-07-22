# Model Serving Operations

## Runtime policy

CreditIQ separates development convenience from production safety:

- Development trains the deterministic synthetic baseline and uses process-local monitoring.
- Production never trains on startup. It loads exactly one promoted registry bundle, verifies its
  SHA-256 artifact checksum, and refuses startup when the registry, artifact, or schema is invalid.
- Production requires Redis-backed inference monitoring. Startup verifies Redis connectivity so a
  deployment cannot silently claim durable monitoring while using process memory.

## Production configuration

Set these values through the deployment secret/configuration system:

```text
ML_SERVING_ENVIRONMENT=production
ML_SERVING_REGISTRY_PATH=/run/creditiq/registry.json
ML_SERVING_MODEL_NAME=credit-risk
ML_SERVING_MODEL_ENVIRONMENT=production
ML_SERVING_MONITORING_BACKEND=redis
ML_SERVING_REDIS_URL=redis://redis:6379/1
ML_SERVING_MONITORING_KEY=creditiq:ml:inference-events
ML_SERVING_MONITORING_TTL_SECONDS=604800
```

The registry path and every artifact it references must be mounted read-only into each serving
replica from the same release-controlled storage snapshot. The current registry is atomic and
durable but remains a single-writer filesystem adapter; do not run concurrent registry writers.

## Monitoring semantics

Each successful or failed inference appends one strict `InferenceEvent` to a bounded Redis list.
The append, retention trim, and TTL refresh execute in one Redis transaction. All replicas use the
same key, so `/monitoring` and `/health` aggregate the shared window rather than one process.

Events deliberately exclude applicant identifiers, feature values, names, KYC data, and financial
records. They contain only correlation ID, success state, latency, recommendation, model versions,
warning codes, and timestamp.

Monitoring failure after startup never changes a valid lending result: the runtime logs the error
and returns the governed decision. A Redis outage does make monitoring/health unavailable, allowing
the orchestrator and operators to detect degraded observability.

## Scaling and recovery

- Scale ML replicas only when they share the same immutable production bundle and Redis key.
- Use a dedicated Redis database/key prefix and enforce network access controls and encryption in
  the target environment.
- The event window is operational telemetry, not the authoritative lending audit record. Unified
  recommendations and correlation evidence are persisted by the backend in PostgreSQL.
- Redis recovery restores monitoring for new requests; expired telemetry is not reconstructed from
  customer records.

## Remaining production boundary

The registry and artifact store still use local/single-writer filesystem adapters. A distributed
deployment requires transactional registry persistence plus object storage with immutable versions,
checksum validation, encryption, access control, and promotion audit integration.
