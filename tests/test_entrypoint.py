from pathlib import Path
from unittest.mock import patch

import pytest

from src import entrypoint
from src.update import InsufficientSpaceError
from src.utils import config


@pytest.fixture
def base_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    data_dir = tmp_path / "data"
    photon_data_dir = data_dir / "photon_data"
    os_node_dir = photon_data_dir / "node_1"
    data_dir.mkdir()
    monkeypatch.setattr(config, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(config, "PHOTON_DATA_DIR", str(photon_data_dir))
    monkeypatch.setattr(config, "OS_NODE_DIR", str(os_node_dir))
    monkeypatch.setattr(config, "IMPORT_MODE", "db")
    monkeypatch.setattr(config, "FORCE_UPDATE", False)
    monkeypatch.setattr(config, "INITIAL_DOWNLOAD", True)
    monkeypatch.setattr(config, "MIN_INDEX_DATE", None)
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")
    monkeypatch.setattr(config, "FILE_URL", None)
    monkeypatch.setattr(config, "MD5_URL", None)
    monkeypatch.setattr(config, "APPRISE_URLS", None)
    return Path(config.OS_NODE_DIR)


def _patch_common():
    return (patch("src.entrypoint.send_notification"), patch("src.entrypoint.validate_config"))


def test_setup_skips_download_when_index_present(base_config: Path):
    base_config.mkdir(parents=True)
    notify, validate = _patch_common()
    with notify as n, validate as v, patch("src.entrypoint.run_update") as run:
        entrypoint.run_setup()

    n.assert_called()
    v.assert_called_once()
    run.assert_not_called()


def test_setup_runs_initial_sequential_when_no_index(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "PARALLEL")
    notify, validate = _patch_common()
    with notify, validate, patch("src.entrypoint.run_update") as run:
        entrypoint.run_setup()
    run.assert_called_once_with("SEQUENTIAL")


def test_setup_skips_initial_when_disabled(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "INITIAL_DOWNLOAD", False)
    notify, validate = _patch_common()
    with notify, validate, patch("src.entrypoint.run_update") as run:
        entrypoint.run_setup()
    run.assert_not_called()


def test_setup_force_update_uses_parallel_when_set(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "FORCE_UPDATE", True)
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "PARALLEL")
    notify, validate = _patch_common()
    with notify, validate, patch("src.entrypoint.run_update") as run:
        entrypoint.run_setup()
    run.assert_called_once_with("PARALLEL")


def test_setup_force_update_uses_sequential_when_not_parallel(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "FORCE_UPDATE", True)
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")
    notify, validate = _patch_common()
    with notify, validate, patch("src.entrypoint.run_update") as run:
        entrypoint.run_setup()
    run.assert_called_once_with("SEQUENTIAL")


def test_setup_force_update_raises_and_notifies_on_insufficient_space(
    base_config: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(config, "FORCE_UPDATE", True)
    notify, validate = _patch_common()
    with (
        notify as n,
        validate,
        patch("src.entrypoint.run_update", side_effect=InsufficientSpaceError("no space")),
        pytest.raises(InsufficientSpaceError),
    ):
        entrypoint.run_setup()

    messages = [call.args[0] for call in n.call_args_list]
    assert any("force update failed" in m for m in messages)


def test_setup_force_update_propagates_unexpected_error(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "FORCE_UPDATE", True)
    notify, validate = _patch_common()
    with (
        notify,
        validate,
        patch("src.entrypoint.run_update", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError),
    ):
        entrypoint.run_setup()


def test_setup_initial_download_raises_and_notifies_on_insufficient_space(base_config: Path):
    notify, validate = _patch_common()
    with (
        notify as n,
        validate,
        patch("src.entrypoint.run_update", side_effect=InsufficientSpaceError("no space")),
        pytest.raises(InsufficientSpaceError),
    ):
        entrypoint.run_setup()

    messages = [call.args[0] for call in n.call_args_list]
    assert any("cannot start" in m for m in messages)


def test_setup_validate_config_failure_raises(base_config: Path):
    base_config.mkdir(parents=True)
    with (
        patch("src.entrypoint.send_notification"),
        patch("src.entrypoint.validate_config", side_effect=ValueError("bad")),
        pytest.raises(ValueError, match="bad"),
    ):
        entrypoint.run_setup()


def test_setup_reconciles_interrupted_import(base_config: Path):
    base_config.mkdir(parents=True)
    (base_config / "segment.bin").write_text("partial")
    (Path(config.DATA_DIR) / ".photon-import-in-progress").write_text("")

    notify, validate = _patch_common()
    with notify, validate, patch("src.entrypoint.run_update_or_import"):
        entrypoint.run_setup()

    assert not Path(config.PHOTON_DATA_DIR).exists()


def test_setup_min_date_triggers_update(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    base_config.mkdir(parents=True)
    monkeypatch.setattr(config, "MIN_INDEX_DATE", "01.01.26")
    notify, validate = _patch_common()
    with (
        notify,
        validate,
        patch("src.entrypoint.check_index_age", return_value=True),
        patch("src.entrypoint.run_update") as run,
    ):
        entrypoint.run_setup()
    run.assert_called_once_with("SEQUENTIAL")


def test_setup_min_date_skips_when_index_recent(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    base_config.mkdir(parents=True)
    monkeypatch.setattr(config, "MIN_INDEX_DATE", "01.01.26")
    notify, validate = _patch_common()
    with (
        notify,
        validate,
        patch("src.entrypoint.check_index_age", return_value=False),
        patch("src.entrypoint.run_update") as run,
    ):
        entrypoint.run_setup()
    run.assert_not_called()


def test_setup_min_date_raises_and_notifies_on_insufficient_space(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    base_config.mkdir(parents=True)
    monkeypatch.setattr(config, "MIN_INDEX_DATE", "01.01.26")
    notify, validate = _patch_common()
    with (
        notify as n,
        validate,
        patch("src.entrypoint.check_index_age", return_value=True),
        patch("src.entrypoint.run_update", side_effect=InsufficientSpaceError("no")),
        pytest.raises(InsufficientSpaceError),
    ):
        entrypoint.run_setup()

    messages = [call.args[0] for call in n.call_args_list]
    assert any("minimum date update failed" in m for m in messages)


def test_setup_min_date_propagates_unexpected_error(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    base_config.mkdir(parents=True)
    monkeypatch.setattr(config, "MIN_INDEX_DATE", "01.01.26")
    notify, validate = _patch_common()
    with (
        notify,
        validate,
        patch("src.entrypoint.check_index_age", return_value=True),
        patch("src.entrypoint.run_update", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError),
    ):
        entrypoint.run_setup()


def test_setup_logs_apprise_redacted_when_set(
    base_config: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    import logging as _logging

    base_config.mkdir(parents=True)
    monkeypatch.setattr(config, "APPRISE_URLS", "tgram://abc")
    caplog.set_level(_logging.INFO, logger="root")
    with patch("src.entrypoint.send_notification"), patch("src.entrypoint.validate_config"):
        entrypoint.run_setup()
    assert any("APPRISE_URLS: REDACTED" in r.message for r in caplog.records)


def test_setup_runs_jsonl_import_when_no_index(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "IMPORT_MODE", "jsonl")
    notify, validate = _patch_common()
    with notify, validate, patch("src.entrypoint.run_jsonl_import") as imp:
        entrypoint.run_setup()
    imp.assert_called_once()


def test_setup_skips_jsonl_rebuild_when_index_present(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    base_config.mkdir(parents=True)
    monkeypatch.setattr(config, "IMPORT_MODE", "jsonl")
    notify, validate = _patch_common()
    with notify, validate, patch("src.entrypoint.run_jsonl_import") as imp:
        entrypoint.run_setup()
    imp.assert_not_called()


def test_setup_force_update_runs_jsonl_import(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "IMPORT_MODE", "jsonl")
    monkeypatch.setattr(config, "FORCE_UPDATE", True)
    notify, validate = _patch_common()
    with notify, validate, patch("src.entrypoint.run_jsonl_import") as imp, patch("src.entrypoint.run_update") as run:
        entrypoint.run_setup()
    imp.assert_called_once()
    run.assert_not_called()
