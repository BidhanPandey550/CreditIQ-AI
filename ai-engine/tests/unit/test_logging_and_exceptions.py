"""Tests for the exceptions hierarchy and the Loguru logging system."""

import pytest

from creditiq_ai.exceptions import (
    ConfigurationError,
    CreditIQError,
    DataLoadingError,
    ValidationError,
)
from creditiq_ai.logging import CHANNEL_TRAINING, configure_logging, get_logger


# --------------------------------------------------------------------------- exceptions
def test_structured_error_to_dict():
    err = ConfigurationError("bad config", context={"file": "x.yaml"})
    payload = err.to_dict()
    assert payload["error_code"] == "configuration_error"
    assert payload["type"] == "ConfigurationError"
    assert payload["context"] == {"file": "x.yaml"}


def test_error_str_includes_code_and_context():
    err = DataLoadingError("nope", context={"path": "/tmp/x"})
    text = str(err)
    assert "data_loading_error" in text
    assert "path" in text


def test_all_categories_share_base():
    for exc in (ConfigurationError, DataLoadingError, ValidationError):
        assert issubclass(exc, CreditIQError)


def test_backward_compatible_aliases():
    from creditiq_ai.exceptions import DataLoadError

    assert DataLoadError is DataLoadingError


def test_raise_and_catch_as_base():
    with pytest.raises(CreditIQError):
        raise ValidationError("schema mismatch", context={"missing": ["income"]})


# --------------------------------------------------------------------------- logging
def test_domain_channel_routes_to_its_file(tmp_path):
    configure_logging(log_dir=tmp_path, enqueue=False)
    get_logger("trainer", channel=CHANNEL_TRAINING).info("epoch complete")

    training_log = (tmp_path / "training.log").read_text()
    app_log = (tmp_path / "app.log").read_text()
    assert "epoch complete" in training_log  # routed to the training channel
    assert "epoch complete" in app_log  # app.log captures everything


def test_error_log_only_receives_errors(tmp_path):
    configure_logging(log_dir=tmp_path, enqueue=False)
    log = get_logger("svc")
    log.info("just info")
    log.error("boom")

    errors_log = (tmp_path / "errors.log").read_text()
    assert "boom" in errors_log
    assert "just info" not in errors_log


def test_logger_binds_component_name(tmp_path):
    configure_logging(log_dir=tmp_path, enqueue=False)
    get_logger("my_component").info("hello")
    assert "my_component" in (tmp_path / "app.log").read_text()
