import os
import signal
import subprocess
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import schedule
from requests.exceptions import RequestException

from src import process_manager
from src.utils import config


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(process_manager.time, "sleep", lambda *_: None)


@pytest.fixture(autouse=True)
def _stub_signal(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(process_manager.signal, "signal", lambda *_: None)


@pytest.fixture(autouse=True)
def _clear_schedule():
    schedule.clear()
    yield
    schedule.clear()


@pytest.fixture
def manager() -> process_manager.PhotonManager:
    return process_manager.PhotonManager()


def _ok_response():
    resp = MagicMock()
    resp.status_code = 200
    return resp


def test_check_photon_health_returns_true_on_200():
    with patch("src.process_manager.requests.get", return_value=_ok_response()):
        assert process_manager.check_photon_health(timeout=1, max_retries=1) is True


def test_check_photon_health_returns_false_after_retries():
    bad = MagicMock()
    bad.status_code = 500
    with patch("src.process_manager.requests.get", return_value=bad):
        assert process_manager.check_photon_health(timeout=1, max_retries=2) is False


def test_check_photon_health_handles_request_exception():
    with patch("src.process_manager.requests.get", side_effect=RequestException("nope")):
        assert process_manager.check_photon_health(timeout=1, max_retries=2) is False


def test_wait_for_photon_ready_true_when_health_ok():
    with patch("src.process_manager.check_photon_health", return_value=True):
        assert process_manager.wait_for_photon_ready(timeout=1) is True


def test_wait_for_photon_ready_false_on_timeout(monkeypatch: pytest.MonkeyPatch):
    times = iter([0, 0, 999])

    def fake_time():
        return next(times)

    monkeypatch.setattr(process_manager.time, "time", fake_time)
    with patch("src.process_manager.check_photon_health", return_value=False):
        assert process_manager.wait_for_photon_ready(timeout=1) is False


def test_handle_shutdown_sets_exit_and_calls_shutdown(manager: process_manager.PhotonManager):
    with patch.object(manager, "shutdown") as shutdown:
        manager.handle_shutdown(signal.SIGTERM, None)
    assert manager.should_exit is True
    shutdown.assert_called_once()


def test_start_photon_builds_full_command(manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "ENABLE_METRICS", True)
    monkeypatch.setattr(config, "JAVA_PARAMS", "-Xmx4g")
    monkeypatch.setattr(config, "PHOTON_PARAMS", "-cors-any")
    monkeypatch.setattr(config, "PHOTON_LISTEN_IP", "127.0.0.1")
    monkeypatch.setattr(config, "DATA_DIR", "/data")

    fake_proc = MagicMock()
    fake_proc.pid = 1234
    with (
        patch("src.process_manager.subprocess.Popen", return_value=fake_proc) as popen,
        patch("src.process_manager.wait_for_photon_ready", return_value=True),
    ):
        assert manager.start_photon(max_startup_retries=1) is True

    cmd = popen.call_args.args[0]
    assert cmd[0] == "java"
    assert "-Xmx4g" in cmd
    assert "-cors-any" in cmd
    assert "/photon/photon.jar" in cmd
    assert "-listen-ip" in cmd
    assert "127.0.0.1" in cmd
    assert "-data-dir" in cmd
    assert "/data" in cmd
    assert "-metrics-enable" in cmd
    assert "prometheus" in cmd


def test_start_photon_retries_until_failure(manager: process_manager.PhotonManager):
    fake_proc = MagicMock()
    fake_proc.pid = 1
    with (
        patch("src.process_manager.subprocess.Popen", return_value=fake_proc) as popen,
        patch("src.process_manager.wait_for_photon_ready", return_value=False),
        patch.object(manager, "stop_photon"),
    ):
        assert manager.start_photon(max_startup_retries=3) is False
    assert popen.call_count == 3


def test_stop_photon_no_op_when_no_process(manager: process_manager.PhotonManager):
    manager.photon_process = None
    manager.stop_photon()


def test_stop_photon_sigterm_path(manager: process_manager.PhotonManager):
    fake_proc = MagicMock()
    fake_proc.pid = 4321
    fake_proc.wait = MagicMock()
    manager.photon_process = fake_proc
    with (
        patch("src.process_manager.os.killpg") as killpg,
        patch("src.process_manager.os.getpgid", return_value=99),
        patch.object(manager, "cleanup_orphaned_photon_processes"),
        patch.object(manager, "_cleanup_lock_files"),
    ):
        manager.stop_photon()
    killpg.assert_called_once_with(99, signal.SIGTERM)
    assert manager.photon_process is None


def test_stop_photon_force_kills_on_timeout(manager: process_manager.PhotonManager):
    fake_proc = MagicMock()
    fake_proc.pid = 4321
    fake_proc.wait.side_effect = [subprocess.TimeoutExpired(cmd="x", timeout=30), None]
    manager.photon_process = fake_proc

    with (
        patch("src.process_manager.os.killpg") as killpg,
        patch("src.process_manager.os.getpgid", return_value=99),
        patch.object(manager, "cleanup_orphaned_photon_processes"),
        patch.object(manager, "_cleanup_lock_files"),
    ):
        manager.stop_photon()
    signals = [c.args[1] for c in killpg.call_args_list]
    assert signal.SIGTERM in signals
    assert signal.SIGKILL in signals


def test_stop_photon_handles_lookup_error(manager: process_manager.PhotonManager):
    fake_proc = MagicMock()
    fake_proc.pid = 4321
    manager.photon_process = fake_proc
    with (
        patch("src.process_manager.os.killpg", side_effect=ProcessLookupError),
        patch("src.process_manager.os.getpgid", return_value=99),
        patch.object(manager, "cleanup_orphaned_photon_processes"),
        patch.object(manager, "_cleanup_lock_files"),
    ):
        manager.stop_photon()
    assert manager.photon_process is None


def test_cleanup_orphaned_photon_processes_terminates_matches(manager: process_manager.PhotonManager):
    proc_a = MagicMock()
    proc_a.info = {"pid": 1, "name": "java", "cmdline": ["java", "-jar", "/photon/photon.jar"]}
    proc_b = MagicMock()
    proc_b.info = {"pid": 2, "name": "python", "cmdline": ["python", "x"]}
    proc_c = MagicMock()
    proc_c.info = {"pid": 3, "name": "java", "cmdline": ["java", "-jar", "other.jar"]}

    with patch("src.process_manager.psutil.process_iter", return_value=[proc_a, proc_b, proc_c]):
        manager.cleanup_orphaned_photon_processes()

    proc_a.terminate.assert_called_once()
    proc_b.terminate.assert_not_called()
    proc_c.terminate.assert_not_called()


def test_cleanup_orphaned_photon_processes_kills_on_timeout(manager: process_manager.PhotonManager):
    import psutil

    proc = MagicMock()
    proc.info = {"pid": 1, "name": "java", "cmdline": ["java", "-jar", "/photon/photon.jar"]}
    proc.wait.side_effect = psutil.TimeoutExpired(seconds=5)

    with patch("src.process_manager.psutil.process_iter", return_value=[proc]):
        manager.cleanup_orphaned_photon_processes()
    proc.kill.assert_called_once()


def test_cleanup_orphaned_photon_processes_swallows_exceptions(manager: process_manager.PhotonManager):
    with patch("src.process_manager.psutil.process_iter", side_effect=RuntimeError("nope")):
        manager.cleanup_orphaned_photon_processes()


def test_cleanup_lock_files_removes_existing(
    manager: process_manager.PhotonManager, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    node = tmp_path / "node_1"
    node.mkdir()
    (node / "node.lock").write_text("")
    (node / "data").mkdir()
    (node / "data" / "node.lock").write_text("")

    monkeypatch.setattr(config, "OS_NODE_DIR", str(node))
    manager._cleanup_lock_files()
    assert not (node / "node.lock").exists()
    assert not (node / "data" / "node.lock").exists()


def test_cleanup_lock_files_swallows_remove_errors(
    manager: process_manager.PhotonManager, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    node = tmp_path / "node_1"
    node.mkdir()
    (node / "node.lock").write_text("")
    monkeypatch.setattr(config, "OS_NODE_DIR", str(node))
    with patch("src.process_manager.os.remove", side_effect=OSError("locked")):
        manager._cleanup_lock_files()


def test_run_update_skips_when_disabled(manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "DISABLED")
    with patch("src.process_manager.update.run_update") as run:
        manager.run_update()
    run.assert_not_called()


def test_run_update_no_op_when_index_up_to_date(
    manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")
    with (
        patch("src.process_manager.compare_mtime", return_value=False),
        patch("src.process_manager.update.run_update") as run,
    ):
        manager.run_update()
    run.assert_not_called()
    assert manager.state == process_manager.AppState.RUNNING


def test_run_update_parallel_path(manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "PARALLEL")
    with (
        patch("src.process_manager.compare_mtime", return_value=True),
        patch("src.process_manager.update.run_update") as run,
        patch("src.process_manager.send_notification"),
        patch.object(manager, "stop_photon") as stop,
        patch.object(manager, "start_photon", return_value=True) as start,
        patch("src.process_manager.index.drop_backup") as cleanup,
    ):
        manager.run_update()
    run.assert_called_once_with("PARALLEL")
    stop.assert_called_once()
    start.assert_called_once()
    cleanup.assert_called_once()
    assert manager.state == process_manager.AppState.RUNNING


def test_run_update_parallel_keeps_backup_when_health_check_fails(
    manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "PARALLEL")
    with (
        patch("src.process_manager.compare_mtime", return_value=True),
        patch("src.process_manager.update.run_update"),
        patch("src.process_manager.send_notification"),
        patch.object(manager, "stop_photon"),
        patch.object(manager, "start_photon", return_value=False),
        patch("src.process_manager.index.drop_backup") as cleanup,
    ):
        manager.run_update()
    cleanup.assert_not_called()
    assert manager.state == process_manager.AppState.RUNNING


def test_run_update_sequential_path(manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")
    with (
        patch("src.process_manager.compare_mtime", return_value=True),
        patch("src.process_manager.update.run_update") as run,
        patch("src.process_manager.send_notification"),
        patch.object(manager, "stop_photon") as stop,
        patch.object(manager, "start_photon", return_value=True) as start,
        patch("src.process_manager.index.drop_backup") as cleanup,
    ):
        manager.run_update()
    run.assert_called_once_with("SEQUENTIAL")
    assert stop.call_count == 2
    start.assert_called_once()
    cleanup.assert_called_once()


def test_run_update_restarts_photon_and_notifies_after_failed_update(
    manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")
    manager.photon_process = None
    with (
        patch("src.process_manager.compare_mtime", return_value=True),
        patch("src.process_manager.update.run_update", side_effect=process_manager.update.UpdateError("boom")),
        patch("src.process_manager.send_notification") as notify,
        patch.object(manager, "stop_photon"),
        patch.object(manager, "start_photon", return_value=True) as start,
        patch("src.process_manager.index.drop_backup") as cleanup,
    ):
        manager.run_update()
    start.assert_called_once()
    cleanup.assert_not_called()
    assert manager.state == process_manager.AppState.RUNNING

    messages = [call.args[0] for call in notify.call_args_list]
    assert any("Photon Update Failed" in m for m in messages)


def test_run_update_notifies_success(manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")
    with (
        patch("src.process_manager.compare_mtime", return_value=True),
        patch("src.process_manager.update.run_update"),
        patch("src.process_manager.send_notification") as notify,
        patch.object(manager, "stop_photon"),
        patch.object(manager, "start_photon", return_value=True),
        patch("src.process_manager.index.drop_backup"),
    ):
        manager.run_update()

    messages = [call.args[0] for call in notify.call_args_list]
    assert any("Updated Successfully" in m for m in messages)


def test_run_update_restores_state_when_pipeline_raises_unexpectedly(
    manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "PARALLEL")
    manager.photon_process = MagicMock()
    with (
        patch("src.process_manager.compare_mtime", return_value=True),
        patch("src.process_manager.update.run_update", side_effect=RuntimeError("unexpected")),
        patch("src.process_manager.send_notification"),
        patch.object(manager, "stop_photon") as stop,
        patch.object(manager, "start_photon", return_value=True) as start,
    ):
        manager.run_update()
    assert manager.state == process_manager.AppState.RUNNING
    stop.assert_not_called()
    start.assert_not_called()


def test_run_update_survives_error_outside_pipeline(
    manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")
    with (
        patch("src.process_manager.compare_mtime", side_effect=RuntimeError("header parse boom")),
        patch("src.process_manager.send_notification") as notify,
    ):
        manager.run_update()
    assert manager.state == process_manager.AppState.RUNNING
    messages = [call.args[0] for call in notify.call_args_list]
    assert any("Photon Update Failed" in m for m in messages)


def test_run_update_notifies_when_health_check_fails_after_swap(
    manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "PARALLEL")
    with (
        patch("src.process_manager.compare_mtime", return_value=True),
        patch("src.process_manager.update.run_update"),
        patch("src.process_manager.send_notification") as notify,
        patch.object(manager, "stop_photon"),
        patch.object(manager, "start_photon", return_value=False),
        patch("src.process_manager.index.drop_backup"),
    ):
        manager.run_update()
    messages = [call.args[0] for call in notify.call_args_list]
    assert any("Photon Update Failed" in m for m in messages)
    assert not any("Updated Successfully" in m for m in messages)


def test_run_pending_jobs_survives_job_exception(
    manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(process_manager.schedule, "run_pending", MagicMock(side_effect=RuntimeError("job boom")))
    manager._run_pending_jobs()


@pytest.mark.parametrize("interval", ["3d", "12h", "30m"])
def test_schedule_updates_polls_daily_regardless_of_interval(
    manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch, interval: str
):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "SEQUENTIAL")
    monkeypatch.setattr(config, "UPDATE_INTERVAL", interval)
    monkeypatch.setattr(process_manager.threading, "Thread", lambda **_: MagicMock(start=lambda: None))
    manager.schedule_updates()
    jobs = schedule.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].unit == "days"


@pytest.mark.parametrize(
    ("interval", "expected"),
    [("3d", timedelta(days=3)), ("12h", timedelta(hours=12)), ("30m", timedelta(minutes=30))],
)
def test_parse_interval(manager: process_manager.PhotonManager, interval: str, expected: timedelta):
    assert manager._parse_interval(interval) == expected


def test_is_update_due_when_marker_missing(
    manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    assert manager._is_update_due() is True


@pytest.mark.parametrize(("age_days", "due"), [(31, True), (1, False)])
def test_is_update_due_compares_marker_age_to_interval(
    manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, age_days: int, due: bool
):
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "UPDATE_INTERVAL", "30d")
    marker = tmp_path / ".photon-index-updated"
    marker.touch()
    mtime = time.time() - age_days * 86400
    os.utime(marker, (mtime, mtime))
    assert manager._is_update_due() is due


def test_schedule_updates_skipped_when_disabled(
    manager: process_manager.PhotonManager, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(config, "UPDATE_STRATEGY", "DISABLED")
    monkeypatch.setattr(process_manager.threading, "Thread", lambda **_: MagicMock(start=lambda: None))
    manager.schedule_updates()
    assert schedule.get_jobs() == []


def test_monitor_photon_restarts_on_unexpected_exit(manager: process_manager.PhotonManager):
    fake_proc = MagicMock()
    fake_proc.poll.side_effect = [1, None]
    manager.photon_process = fake_proc
    manager.state = process_manager.AppState.RUNNING

    call_count = {"n": 0}

    def restart():
        call_count["n"] += 1
        manager.should_exit = True
        return True

    with patch.object(manager, "start_photon", side_effect=restart):
        manager.monitor_photon()
    assert call_count["n"] == 1


def test_monitor_photon_exits_on_failed_restart(manager: process_manager.PhotonManager):
    fake_proc = MagicMock()
    fake_proc.poll.return_value = 1
    manager.photon_process = fake_proc
    manager.state = process_manager.AppState.RUNNING

    with patch.object(manager, "start_photon", return_value=False), pytest.raises(SystemExit) as exc:
        manager.monitor_photon()
    assert exc.value.code == 1


def test_monitor_photon_restarts_when_process_handle_missing(manager: process_manager.PhotonManager):
    manager.photon_process = None
    manager.state = process_manager.AppState.RUNNING

    call_count = {"n": 0}

    def restart():
        call_count["n"] += 1
        manager.should_exit = True
        return True

    with patch.object(manager, "start_photon", side_effect=restart):
        manager.monitor_photon()
    assert call_count["n"] == 1


def test_monitor_photon_exits_when_handle_missing_and_restart_fails(manager: process_manager.PhotonManager):
    manager.photon_process = None
    manager.state = process_manager.AppState.RUNNING

    with patch.object(manager, "start_photon", return_value=False), pytest.raises(SystemExit) as exc:
        manager.monitor_photon()
    assert exc.value.code == 1


def test_shutdown_calls_stop_and_exits(manager: process_manager.PhotonManager):
    with patch.object(manager, "stop_photon") as stop, pytest.raises(SystemExit) as exc:
        manager.shutdown()
    stop.assert_called_once()
    assert exc.value.code == 0


def test_run_invokes_setup_then_starts_photon(manager: process_manager.PhotonManager):
    with (
        patch("src.process_manager.run_setup") as setup,
        patch.object(manager, "start_photon", return_value=True) as start,
        patch.object(manager, "schedule_updates") as sched,
        patch.object(manager, "monitor_photon"),
    ):
        manager.run()
    setup.assert_called_once()
    start.assert_called_once()
    sched.assert_called_once()


def test_run_exits_75_when_setup_hits_insufficient_space(manager: process_manager.PhotonManager):
    with (
        patch("src.process_manager.run_setup", side_effect=process_manager.update.InsufficientSpaceError("no space")),
        pytest.raises(SystemExit) as exc,
    ):
        manager.run()
    assert exc.value.code == 75


def test_run_exits_1_when_setup_fails(manager: process_manager.PhotonManager):
    with patch("src.process_manager.run_setup", side_effect=ValueError("bad config")), pytest.raises(SystemExit) as exc:
        manager.run()
    assert exc.value.code == 1


def test_run_exits_when_photon_fails_to_start(manager: process_manager.PhotonManager):
    with (
        patch("src.process_manager.run_setup"),
        patch.object(manager, "start_photon", return_value=False),
        pytest.raises(SystemExit) as exc,
    ):
        manager.run()
    assert exc.value.code == 1
