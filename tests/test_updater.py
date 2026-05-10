from unittest.mock import patch

import pytest

from src import updater
from src.utils import config


def test_updater_main_runs_parallel(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "PARALLEL")
    with (
        patch("src.updater.parallel_update") as parallel,
        patch("src.updater.sequential_update") as sequential,
        patch("src.updater.send_notification") as notify,
    ):
        updater.main()
    parallel.assert_called_once_with()
    sequential.assert_not_called()
    notify.assert_called_once_with("Photon Index Updated Successfully")


def test_updater_main_runs_sequential(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")
    with (
        patch("src.updater.parallel_update") as parallel,
        patch("src.updater.sequential_update") as sequential,
        patch("src.updater.send_notification"),
    ):
        updater.main()
    parallel.assert_not_called()
    sequential.assert_called_once_with()


def test_updater_main_exits_on_unknown_strategy(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "BOGUS")
    with (
        patch("src.updater.parallel_update"),
        patch("src.updater.sequential_update"),
        patch("src.updater.send_notification"),
        pytest.raises(SystemExit) as exc,
    ):
        updater.main()
    assert exc.value.code == 1


def test_updater_main_notifies_on_failure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "PARALLEL")
    with (
        patch("src.updater.parallel_update", side_effect=RuntimeError("boom")),
        patch("src.updater.send_notification") as notify,
        pytest.raises(SystemExit) as exc,
    ):
        updater.main()
    assert exc.value.code == 1

    args = [call.args[0] for call in notify.call_args_list]
    assert any("Photon Update Failed" in a for a in args)
