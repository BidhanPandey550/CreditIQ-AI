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
