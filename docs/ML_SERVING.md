# ML Serving and Production Model Loading

The `ml-engine` is a thin process boundary over the canonical `creditiq_ai` library. It does not own
a second model registry or training implementation.

## Startup policy

- `development` and `testing` create the deterministic synthetic baseline used by local demos and
  contract tests. The `/models` endpoint reports `stage=development` and `data_source=synthetic`.
- `production` never trains at startup. It requires `ML_SERVING_REGISTRY_PATH`, resolves the unique
  promoted credit model using `ML_SERVING_MODEL_NAME` and `ML_SERVING_MODEL_ENVIRONMENT`, and loads
  exactly one model artifact through the canonical `ArtifactStore`.
- Missing promotion, incompatible bundle schema, missing artifact, or checksum mismatch aborts
  application startup. The service does not fall back to a synthetic or stale model.

## Deployable artifact contract

The registered model artifact is a versioned `ServingBundle` containing the fitted credit trainer,
fitted fraud pipeline, explanation reference population, feature version, and training metrics. The
registry record remains authoritative for lifecycle stage, model version, dataset lineage, and the
trusted SHA-256 checksum.

Required production environment variables:

```text
ML_SERVING_ENVIRONMENT=production
ML_SERVING_REGISTRY_PATH=/run/creditiq/registry.json
ML_SERVING_MODEL_NAME=credit-risk
ML_SERVING_MODEL_ENVIRONMENT=production
```

The registry and referenced artifacts must be mounted read-only into the serving container. Artifact
promotion is an offline governance action; the serving process has no registry mutation capability.

## Operational disclosure

`GET /health` reports the loaded version and metrics. `GET /models` additionally reports lifecycle
stage, dataset source/version, feature version, algorithm, and feature count. These values come from
the loaded registry record and bundle rather than hardcoded production claims.

The backend gateway maintains a pooled HTTP client, forwards `X-Request-ID`, and validates every
nested prediction field with a strict Pydantic contract before persistence. Network failures,
non-success responses, invalid JSON, unknown fields, missing fields, and out-of-range financial
scores all fail closed as service-unavailable errors; no partial lending intelligence is stored.

## Runtime monitoring

Every inference attempt records a bounded, privacy-safe event containing its correlation ID,
success state, duration, model version, recommendation, and warning codes. Raw feature values and
applicant identifiers are deliberately excluded. `GET /monitoring` returns counts, failure rate,
average and p95 latency, and configured health status; `GET /health` embeds the same snapshot.

The current monitor is process-local and intentionally bounded. Recording failures are logged but
do not replace or block an otherwise valid model result. A durable multi-replica telemetry adapter
is still required before distributed production deployment.

The ML port is bound to loopback in Docker Compose rather than all host interfaces. Platform owners
consume model identity and monitoring through the authenticated `GET /api/v1/admin/model-operations`
backend endpoint and the corresponding Model Operations dashboard. The backend validates both
downstream contracts before disclosure; tenant administrators and ordinary staff do not receive the
platform-level `platform:admin` permission required by this endpoint.
