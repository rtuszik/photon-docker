import pytest

from src.utils import config
from src.utils.validate_config import validate_config


def _set_base_config(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "IMPORT_MODE", "db")
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")
    monkeypatch.setattr(config, "UPDATE_INTERVAL", "30d")
    monkeypatch.setattr(config, "REGION", None)
    monkeypatch.setattr(config, "FILE_URL", None)
    monkeypatch.setattr(config, "MD5_URL", None)


def test_validate_config_accepts_valid_configuration(monkeypatch: pytest.MonkeyPatch):
    _set_base_config(monkeypatch)

    validate_config()


@pytest.mark.parametrize("strategy", ["parallel", "FULL", ""])
def test_validate_config_rejects_invalid_strategy(monkeypatch: pytest.MonkeyPatch, strategy: str):
    _set_base_config(monkeypatch)
    monkeypatch.setattr(config, "UPDATE_STRATEGY", strategy)

    with pytest.raises(ValueError, match=f"Invalid UPDATE_STRATEGY: '{strategy}'"):
        validate_config()


@pytest.mark.parametrize("interval", ["30", "d30", "30w", "1D", ""])
def test_validate_config_rejects_invalid_interval(monkeypatch: pytest.MonkeyPatch, interval: str):
    _set_base_config(monkeypatch)
    monkeypatch.setattr(config, "UPDATE_INTERVAL", interval)

    with pytest.raises(ValueError, match=f"Invalid UPDATE_INTERVAL format: '{interval}'"):
        validate_config()


def test_validate_config_rejects_invalid_region(monkeypatch: pytest.MonkeyPatch):
    _set_base_config(monkeypatch)
    monkeypatch.setattr(config, "REGION", "atlantis")

    with pytest.raises(ValueError, match="Invalid REGION: 'atlantis'"):
        validate_config()


def test_validate_config_rejects_invalid_import_mode(monkeypatch: pytest.MonkeyPatch):
    _set_base_config(monkeypatch)
    monkeypatch.setattr(config, "IMPORT_MODE", "archive")

    with pytest.raises(ValueError, match="Invalid IMPORT_MODE: 'archive'"):
        validate_config()


def test_validate_config_accepts_jsonl_single_region(monkeypatch: pytest.MonkeyPatch):
    _set_base_config(monkeypatch)
    monkeypatch.setattr(config, "IMPORT_MODE", "jsonl")
    monkeypatch.setattr(config, "REGION", "de")

    validate_config()


def test_validate_config_requires_regions_for_jsonl(monkeypatch: pytest.MonkeyPatch):
    _set_base_config(monkeypatch)
    monkeypatch.setattr(config, "IMPORT_MODE", "jsonl")

    with pytest.raises(ValueError, match="REGION is required when IMPORT_MODE=jsonl"):
        validate_config()


def test_validate_config_accepts_multiple_jsonl_regions(monkeypatch: pytest.MonkeyPatch):
    _set_base_config(monkeypatch)
    monkeypatch.setattr(config, "IMPORT_MODE", "jsonl")
    monkeypatch.setattr(config, "REGION", "de,fr")

    validate_config()


def test_validate_config_rejects_multiple_db_regions(monkeypatch: pytest.MonkeyPatch):
    _set_base_config(monkeypatch)
    monkeypatch.setattr(config, "REGION", "germany,andorra")

    with pytest.raises(ValueError, match="DB mode supports exactly one region"):
        validate_config()


def test_validate_config_reports_multiple_errors(monkeypatch: pytest.MonkeyPatch):
    _set_base_config(monkeypatch)
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "WRONG")
    monkeypatch.setattr(config, "UPDATE_INTERVAL", "hourly")
    monkeypatch.setattr(config, "REGION", "atlantis")

    with pytest.raises(ValueError) as exc_info:
        validate_config()

    message = str(exc_info.value)

    assert "Configuration validation failed:" in message
    assert "Invalid UPDATE_STRATEGY: 'WRONG'" in message
    assert "Invalid UPDATE_INTERVAL format: 'hourly'" in message
    assert "Invalid REGION: 'atlantis'" in message
