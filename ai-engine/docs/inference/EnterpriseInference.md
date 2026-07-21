# Enterprise Inference Contract

`EnterpriseInferenceEngine` is the application-layer entry point for future REST, queue, batch, or
banking connector adapters. It deliberately contains no FastAPI, authentication, transport, or
vendor integration code.

The flow is: validate one structured feature mapping → apply the fitted preprocessing dependency →
predict probability of default → assess fraud → apply the unified decision policy → generate local
explanation when requested → emit privacy-safe monitoring metadata.

Every response carries correlation ID, credit and fraud results, recommendation, confidence,
decision reasons, model and feature versions, warnings, processing duration, schema version, and an
optional explanation. Batch processing preserves request order while each item remains independently
auditable. Artifact loading is intentionally outside this service and must use the checksum-verified
model registry boundary before injecting a model.
