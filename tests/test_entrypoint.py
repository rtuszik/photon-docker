import pytest

from src import entrypoint
from src.utils import config


def _set_base_config(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "IMPORT_MODE", "db")
    monkeypatch.setattr(config, "FORCE_UPDATE", False)
    monkeypatch.setattr(config, "INITIAL_DOWNLOAD", True)
    monkeypatch.setattr(config, "MIN_INDEX_DATE", None)
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")


def test_main_runs_jsonl_import_when_no_index_exists(monkeypatch: pytest.MonkeyPatch):
    calls = []

    _set_base_config(monkeypatch)
    monkeypatch.setattr(config, "IMPORT_MODE", "jsonl")
    monkeypatch.setattr(entrypoint, "send_notification", lambda message: None)
    monkeypatch.setattr(entrypoint, "log_config", lambda: None)
    monkeypatch.setattr(entrypoint, "validate_config", lambda: None)
    monkeypatch.setattr(entrypoint.os.path, "isdir", lambda path: False)
    monkeypatch.setattr(entrypoint, "run_update_or_import", lambda force_update=False: calls.append(force_update))

    entrypoint.main()

    assert calls == [False]


def test_main_skips_jsonl_rebuild_when_index_exists(monkeypatch: pytest.MonkeyPatch):
    calls = []

    _set_base_config(monkeypatch)
    monkeypatch.setattr(config, "IMPORT_MODE", "jsonl")
    monkeypatch.setattr(entrypoint, "send_notification", lambda message: None)
    monkeypatch.setattr(entrypoint, "log_config", lambda: None)
    monkeypatch.setattr(entrypoint, "validate_config", lambda: None)
    monkeypatch.setattr(entrypoint.os.path, "isdir", lambda path: True)
    monkeypatch.setattr(entrypoint, "run_update_or_import", lambda force_update=False: calls.append(force_update))

    entrypoint.main()

    assert calls == []


def test_main_uses_force_update_path_for_jsonl(monkeypatch: pytest.MonkeyPatch):
    calls = []

    _set_base_config(monkeypatch)
    monkeypatch.setattr(config, "IMPORT_MODE", "jsonl")
    monkeypatch.setattr(config, "FORCE_UPDATE", True)
    monkeypatch.setattr(entrypoint, "send_notification", lambda message: None)
    monkeypatch.setattr(entrypoint, "log_config", lambda: None)
    monkeypatch.setattr(entrypoint, "validate_config", lambda: None)
    monkeypatch.setattr(entrypoint, "run_update_or_import", lambda force_update=False: calls.append(force_update))

    entrypoint.main()

    assert calls == [True]


def test_run_update_or_import_uses_db_parallel_update(monkeypatch: pytest.MonkeyPatch):
    calls = []

    _set_base_config(monkeypatch)
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "PARALLEL")
    monkeypatch.setattr(entrypoint, "parallel_update", lambda: calls.append("parallel"))
    monkeypatch.setattr(entrypoint, "sequential_update", lambda: calls.append("sequential"))

    entrypoint.run_update_or_import(force_update=True)

    assert calls == ["parallel"]


def test_run_update_or_import_uses_db_sequential_update_for_initial_setup(monkeypatch: pytest.MonkeyPatch):
    calls = []

    _set_base_config(monkeypatch)
    monkeypatch.setattr(entrypoint, "sequential_update", lambda: calls.append("sequential"))

    entrypoint.run_update_or_import(force_update=False)

    assert calls == ["sequential"]
