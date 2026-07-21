"""Tests for Sprint 8 Phase 2a — Model Operations domain models + lifecycle state machine."""

import pytest

from creditiq_ai.core.enums import ModelType
from creditiq_ai.core.schemas import ModelMetadata
from creditiq_ai.exceptions import (
    CreditIQError,
    InvalidLifecycleTransitionError,
    ModelRegistryError,
)
from creditiq_ai.model_operations import (
    ArtifactKind,
    FileModelRegistry,
    LifecycleStage,
    LifecycleStateMachine,
    ModelArtifact,
    ModelFamily,
    ModelIdentity,
    ModelVersion,
)


# --------------------------------------------------------------------------- controlled vocab
def test_lifecycle_has_all_spec_stages():
    assert {s.value for s in LifecycleStage} == {
        "created",
        "registered",
        "validated",
        "staging",
        "challenger",
        "champion",
        "production",
        "archived",
        "rejected",
        "retired",
    }


# --------------------------------------------------------------------------- state machine
def test_legal_transition_passes():
    sm = LifecycleStateMachine()
    assert sm.can_transition(LifecycleStage.CREATED, LifecycleStage.REGISTERED)
    sm.validate_transition(LifecycleStage.CREATED, LifecycleStage.REGISTERED)  # no raise


def test_illegal_transition_raises():
    sm = LifecycleStateMachine()
    with pytest.raises(InvalidLifecycleTransitionError):
        sm.validate_transition(LifecycleStage.CREATED, LifecycleStage.CHAMPION)


def test_noop_transition_raises():
    sm = LifecycleStateMachine()
    with pytest.raises(InvalidLifecycleTransitionError):
        sm.validate_transition(LifecycleStage.STAGING, LifecycleStage.STAGING)


def test_full_promotion_path_is_legal():
    sm = LifecycleStateMachine()
    path = [
        LifecycleStage.CREATED,
        LifecycleStage.REGISTERED,
        LifecycleStage.VALIDATED,
        LifecycleStage.STAGING,
        LifecycleStage.CHALLENGER,
        LifecycleStage.CHAMPION,
        LifecycleStage.PRODUCTION,
    ]
    for current, target in zip(path, path[1:]):
        assert sm.can_transition(current, target), f"{current} → {target}"


def test_demotion_and_rollback_transitions_allowed():
    sm = LifecycleStateMachine()
    assert sm.can_transition(LifecycleStage.CHAMPION, LifecycleStage.CHALLENGER)  # demote
    assert sm.can_transition(LifecycleStage.PRODUCTION, LifecycleStage.CHAMPION)  # rollback


def test_terminal_stages_have_no_transitions():
    sm = LifecycleStateMachine()
    for terminal in (LifecycleStage.ARCHIVED, LifecycleStage.REJECTED, LifecycleStage.RETIRED):
        assert sm.is_terminal(terminal)
        with pytest.raises(InvalidLifecycleTransitionError):
            sm.validate_transition(terminal, LifecycleStage.PRODUCTION)


def test_exception_is_in_registry_hierarchy():
    assert issubclass(InvalidLifecycleTransitionError, ModelRegistryError)
    assert issubclass(ModelRegistryError, CreditIQError)


# --------------------------------------------------------------------------- domain models
def _version(**overrides) -> ModelVersion:
    meta = ModelMetadata(
        name="credit_lr",
        version="1.0.0",
        model_type=ModelType.LOGISTIC_REGRESSION,
        metrics={"roc_auc": 0.81},
    )
    base = dict(
        identity=ModelIdentity(name="credit_lr", family=ModelFamily.CREDIT),
        version="1.0.0",
        metadata=meta,
        artifacts=[ModelArtifact(kind=ArtifactKind.MODEL, path="artifacts/credit_lr.joblib")],
    )
    base.update(overrides)
    return ModelVersion(**base)


def test_model_version_reuses_core_metadata():
    mv = _version()
    assert mv.metadata.metrics["roc_auc"] == 0.81
    assert mv.ref == "credit:credit_lr:development@1.0.0"
    assert mv.identity.key == "credit:credit_lr:development"
    assert mv.stage is LifecycleStage.CREATED  # default


def test_domain_model_forbids_unknown_fields():
    with pytest.raises(Exception):
        ModelIdentity(name="x", family=ModelFamily.FRAUD, bogus=True)


def test_model_family_values():
    assert ModelFamily.CREDIT.value == "credit"
    assert ModelFamily.FRAUD.value == "fraud"


# --------------------------------------------------------------------------- persistent registry
def _registrable(version: str = "1.0.0") -> ModelVersion:
    return _version(
        version=version,
        metadata=ModelMetadata(
            name="credit_lr",
            version=version,
            model_type=ModelType.LOGISTIC_REGRESSION,
            metrics={"roc_auc": 0.81},
        ),
        artifacts=[
            ModelArtifact(
                kind=ArtifactKind.MODEL,
                path=f"artifacts/credit_lr-{version}.joblib",
                checksum_sha256="a" * 64,
            )
        ],
    )


def _promote_to_production(registry: FileModelRegistry, model: ModelVersion) -> ModelVersion:
    current = registry.register(model)
    for stage in (
        LifecycleStage.VALIDATED,
        LifecycleStage.STAGING,
        LifecycleStage.CHALLENGER,
        LifecycleStage.CHAMPION,
        LifecycleStage.PRODUCTION,
    ):
        current = registry.transition(current.ref, stage)
    return current


def test_file_registry_persists_and_reopens(tmp_path):
    path = tmp_path / "registry.json"
    registered = FileModelRegistry(path).register(_registrable())
    reopened = FileModelRegistry(path)
    assert reopened.get(registered.ref) == registered
    assert reopened.audit_events()[0].event_type == "model_registered"


def test_registry_rejects_artifact_without_checksum(tmp_path):
    registry = FileModelRegistry(tmp_path / "registry.json")
    with pytest.raises(Exception):
        registry.register(_version())


def test_registry_rejects_duplicate_version(tmp_path):
    registry = FileModelRegistry(tmp_path / "registry.json")
    registry.register(_registrable())
    with pytest.raises(Exception):
        registry.register(_registrable())


def test_registry_selects_unique_production_version(tmp_path):
    registry = FileModelRegistry(tmp_path / "registry.json")
    production = _promote_to_production(registry, _registrable())
    assert registry.production(production.identity).ref == production.ref


def test_registry_blocks_second_production_version(tmp_path):
    registry = FileModelRegistry(tmp_path / "registry.json")
    first = _promote_to_production(registry, _registrable("1.0.0"))
    second = registry.register(_registrable("2.0.0"))
    for stage in (
        LifecycleStage.VALIDATED,
        LifecycleStage.STAGING,
        LifecycleStage.CHALLENGER,
        LifecycleStage.CHAMPION,
    ):
        second = registry.transition(second.ref, stage)
    with pytest.raises(Exception):
        registry.transition(second.ref, LifecycleStage.PRODUCTION)
    assert registry.production(first.identity).version == "1.0.0"


def test_registry_rollback_switches_production_atomically(tmp_path):
    registry = FileModelRegistry(tmp_path / "registry.json")
    first = _promote_to_production(registry, _registrable("1.0.0"))
    second = registry.register(_registrable("2.0.0"))
    for stage in (
        LifecycleStage.VALIDATED,
        LifecycleStage.STAGING,
        LifecycleStage.CHALLENGER,
        LifecycleStage.CHAMPION,
    ):
        second = registry.transition(second.ref, stage)

    promoted = registry.rollback(
        first.identity, "2.0.0", actor="risk-admin", reason="champion rollback test"
    )
    assert promoted.stage is LifecycleStage.PRODUCTION
    assert registry.production(first.identity).version == "2.0.0"
    assert registry.get(first.ref).stage is LifecycleStage.CHAMPION
    assert registry.audit_events()[-1].event_type == "model_rollback"
