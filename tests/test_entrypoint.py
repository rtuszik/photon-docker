from pathlib import Path
from unittest.mock import patch

import pytest

from src import entrypoint
from src.downloader import InsufficientSpaceError
from src.utils import config


@pytest.fixture
def base_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    os_node_dir = tmp_path / "node_1"
    monkeypatch.setattr(config, "OS_NODE_DIR", str(os_node_dir))
    monkeypatch.setattr(config, "FORCE_UPDATE", False)
    monkeypatch.setattr(config, "INITIAL_DOWNLOAD", True)
    monkeypatch.setattr(config, "MIN_INDEX_DATE", None)
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")
    monkeypatch.setattr(config, "FILE_URL", None)
    monkeypatch.setattr(config, "MD5_URL", None)
    monkeypatch.setattr(config, "APPRISE_URLS", None)
    return os_node_dir


def _patch_common():
    return (patch("src.entrypoint.send_notification"), patch("src.entrypoint.validate_config"))


def test_entrypoint_skips_download_when_index_present(base_config: Path):
    base_config.mkdir()
    notify, validate = _patch_common()
    with (
        notify as n,
        validate as v,
        patch("src.entrypoint.sequential_update") as seq,
        patch("src.entrypoint.parallel_update") as par,
    ):
        entrypoint.main()

    n.assert_called()
    v.assert_called_once()
    seq.assert_not_called()
    par.assert_not_called()


def test_entrypoint_runs_initial_sequential_when_no_index(base_config: Path):
    notify, validate = _patch_common()
    with notify, validate, patch("src.entrypoint.sequential_update") as seq:
        entrypoint.main()
    seq.assert_called_once()


def test_entrypoint_skips_initial_when_disabled(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "INITIAL_DOWNLOAD", False)
    notify, validate = _patch_common()
    with notify, validate, patch("src.entrypoint.sequential_update") as seq:
        entrypoint.main()
    seq.assert_not_called()


def test_entrypoint_force_update_uses_parallel_when_set(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "FORCE_UPDATE", True)
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "PARALLEL")
    notify, validate = _patch_common()
    with (
        notify,
        validate,
        patch("src.entrypoint.parallel_update") as par,
        patch("src.entrypoint.sequential_update") as seq,
    ):
        entrypoint.main()
    par.assert_called_once()
    seq.assert_not_called()


def test_entrypoint_force_update_uses_sequential_when_not_parallel(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "FORCE_UPDATE", True)
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")
    notify, validate = _patch_common()
    with (
        notify,
        validate,
        patch("src.entrypoint.sequential_update") as seq,
        patch("src.entrypoint.parallel_update") as par,
    ):
        entrypoint.main()
    seq.assert_called_once()
    par.assert_not_called()


def test_entrypoint_force_update_exits_on_insufficient_space(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "FORCE_UPDATE", True)
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")
    notify, validate = _patch_common()
    with (
        notify,
        validate,
        patch("src.entrypoint.sequential_update", side_effect=InsufficientSpaceError("no space")),
        pytest.raises(SystemExit) as exc,
    ):
        entrypoint.main()
    assert exc.value.code == 75


def test_entrypoint_force_update_propagates_unexpected_error(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "FORCE_UPDATE", True)
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")
    notify, validate = _patch_common()
    with (
        notify,
        validate,
        patch("src.entrypoint.sequential_update", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError),
    ):
        entrypoint.main()


def test_entrypoint_initial_download_exits_on_insufficient_space(base_config: Path):
    notify, validate = _patch_common()
    with (
        notify,
        validate,
        patch("src.entrypoint.sequential_update", side_effect=InsufficientSpaceError("no space")),
        pytest.raises(SystemExit) as exc,
    ):
        entrypoint.main()
    assert exc.value.code == 75


def test_entrypoint_validate_config_failure_exits(base_config: Path):
    base_config.mkdir()
    with (
        patch("src.entrypoint.send_notification"),
        patch("src.entrypoint.validate_config", side_effect=ValueError("bad")),
        pytest.raises(SystemExit) as exc,
    ):
        entrypoint.main()
    assert exc.value.code == 1


def test_entrypoint_min_date_triggers_update(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    base_config.mkdir()
    monkeypatch.setattr(config, "MIN_INDEX_DATE", "01.01.26")
    notify, validate = _patch_common()
    with (
        notify,
        validate,
        patch("src.entrypoint.check_index_age", return_value=True),
        patch("src.entrypoint.sequential_update") as seq,
    ):
        entrypoint.main()
    seq.assert_called_once()


def test_entrypoint_min_date_skips_when_index_recent(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    base_config.mkdir()
    monkeypatch.setattr(config, "MIN_INDEX_DATE", "01.01.26")
    notify, validate = _patch_common()
    with (
        notify,
        validate,
        patch("src.entrypoint.check_index_age", return_value=False),
        patch("src.entrypoint.sequential_update") as seq,
    ):
        entrypoint.main()
    seq.assert_not_called()


def test_entrypoint_min_date_exits_on_insufficient_space(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    base_config.mkdir()
    monkeypatch.setattr(config, "MIN_INDEX_DATE", "01.01.26")
    notify, validate = _patch_common()
    with (
        notify,
        validate,
        patch("src.entrypoint.check_index_age", return_value=True),
        patch("src.entrypoint.sequential_update", side_effect=InsufficientSpaceError("no")),
        pytest.raises(SystemExit) as exc,
    ):
        entrypoint.main()
    assert exc.value.code == 75


def test_entrypoint_min_date_propagates_unexpected_error(base_config: Path, monkeypatch: pytest.MonkeyPatch):
    base_config.mkdir()
    monkeypatch.setattr(config, "MIN_INDEX_DATE", "01.01.26")
    notify, validate = _patch_common()
    with (
        notify,
        validate,
        patch("src.entrypoint.check_index_age", return_value=True),
        patch("src.entrypoint.sequential_update", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError),
    ):
        entrypoint.main()


def test_entrypoint_logs_apprise_redacted_when_set(
    base_config: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    import logging as _logging

    base_config.mkdir()
    monkeypatch.setattr(config, "APPRISE_URLS", "tgram://abc")
    caplog.set_level(_logging.INFO, logger="root")
    with patch("src.entrypoint.send_notification"), patch("src.entrypoint.validate_config"):
        entrypoint.main()
    assert any("APPRISE_URLS: REDACTED" in r.message for r in caplog.records)
