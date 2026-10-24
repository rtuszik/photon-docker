import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src import index
from src.utils import config


def test_is_present_false_when_no_index(fake_dirs: Path):
    assert index.is_present() is False


def test_is_present_true_when_node_dir_exists(fake_dirs: Path):
    Path(config.OS_NODE_DIR).mkdir(parents=True)
    assert index.is_present() is True


def test_last_updated_uses_marker_when_present(fake_dirs: Path):
    marker = fake_dirs / ".photon-index-updated"
    marker.write_text("")
    os.utime(marker, (1_000_000, 1_000_000))
    assert index.last_updated() == 1_000_000
    assert index.has_update_timestamp() is True


def test_last_updated_falls_back_to_node_dir_mtime(fake_dirs: Path):
    node_dir = Path(config.OS_NODE_DIR)
    node_dir.mkdir(parents=True)
    os.utime(node_dir, (2_000_000, 2_000_000))
    assert index.last_updated() == 2_000_000
    assert index.has_update_timestamp() is False


def test_last_updated_returns_zero_when_nothing_exists(fake_dirs: Path):
    assert index.last_updated() == 0.0


def test_age_seconds_is_infinite_when_nothing_exists(fake_dirs: Path):
    assert index.age_seconds() == float("inf")


def test_age_seconds_measures_marker_age(fake_dirs: Path):
    marker = fake_dirs / ".photon-index-updated"
    marker.write_text("")
    mtime = time.time() - 3600
    os.utime(marker, (mtime, mtime))
    assert index.age_seconds() == pytest.approx(3600, abs=5)


def test_age_seconds_never_negative_for_future_marker(fake_dirs: Path):
    marker = fake_dirs / ".photon-index-updated"
    marker.write_text("")
    mtime = time.time() + 3600
    os.utime(marker, (mtime, mtime))
    assert index.age_seconds() == 0.0


def test_mark_updated_creates_marker(fake_dirs: Path):
    index.mark_updated()
    assert (fake_dirs / ".photon-index-updated").exists()


def test_mark_updated_raises_when_marker_cannot_be_written(fake_dirs: Path):
    with patch("src.index.Path.touch", side_effect=OSError("read-only")), pytest.raises(OSError, match="read-only"):
        index.mark_updated()


def test_mark_updated_clears_update_attempt_record(fake_dirs: Path):
    index.record_update_attempt(5)
    index.mark_updated()
    assert not (fake_dirs / ".photon-update-attempt").exists()
    assert index.last_update_attempt() == (0.0, 0)


def test_last_update_attempt_defaults_when_never_recorded(fake_dirs: Path):
    assert index.last_update_attempt() == (0.0, 0)


def test_update_attempt_roundtrip(fake_dirs: Path):
    index.record_update_attempt(3)
    marker = fake_dirs / ".photon-update-attempt"
    os.utime(marker, (1_500_000, 1_500_000))
    assert index.last_update_attempt() == (1_500_000, 3)


@pytest.mark.parametrize(("content", "failures"), [("", 0), ("-4\n", 0), ("2", 2)])
def test_last_update_attempt_normalises_failure_count(fake_dirs: Path, content: str, failures: int):
    (fake_dirs / ".photon-update-attempt").write_text(content)
    assert index.last_update_attempt()[1] == failures


def test_last_update_attempt_ignores_malformed_marker(fake_dirs: Path):
    (fake_dirs / ".photon-update-attempt").write_text("garbage")
    assert index.last_update_attempt() == (0.0, 0)


def test_last_update_attempt_ignores_unreadable_marker(fake_dirs: Path):
    (fake_dirs / ".photon-update-attempt").write_text("1")
    with patch("src.index.Path.read_text", side_effect=PermissionError("denied")):
        assert index.last_update_attempt() == (0.0, 0)


def test_record_update_attempt_swallows_write_errors(fake_dirs: Path):
    with patch("src.index.Path.write_text", side_effect=PermissionError("denied")):
        index.record_update_attempt(1)
    assert not (fake_dirs / ".photon-update-attempt").exists()


def test_record_update_attempt_keeps_previous_record_when_replace_fails(fake_dirs: Path):
    index.record_update_attempt(2)
    with patch("src.index.os.replace", side_effect=OSError("disk full")):
        index.record_update_attempt(5)
    assert index.last_update_attempt()[1] == 2


def test_import_marker_roundtrip(fake_dirs: Path):
    assert index.import_was_interrupted() is False

    index.mark_import_started()
    assert index.import_was_interrupted() is True

    index.mark_import_complete()
    assert index.import_was_interrupted() is False


def test_mark_import_complete_touches_update_timestamp(fake_dirs: Path):
    index.mark_import_started()
    index.mark_import_complete()
    assert index.has_update_timestamp() is True


def test_mark_import_complete_is_idempotent(fake_dirs: Path):
    index.mark_import_complete()
    assert index.import_was_interrupted() is False


def test_mark_import_started_raises_when_marker_cannot_be_written(fake_dirs: Path):
    with patch("src.index.Path.touch", side_effect=OSError("read-only")), pytest.raises(OSError, match="read-only"):
        index.mark_import_started()


def test_mark_import_complete_raises_when_marker_cannot_be_cleared(fake_dirs: Path):
    index.mark_import_started()
    with patch("src.index.Path.unlink", side_effect=OSError("read-only")), pytest.raises(OSError, match="read-only"):
        index.mark_import_complete()


def test_mark_import_complete_does_not_mark_updated_when_clear_fails(fake_dirs: Path):
    index.mark_import_started()
    with patch("src.index.Path.unlink", side_effect=OSError("read-only")), pytest.raises(OSError, match="read-only"):
        index.mark_import_complete()
    assert index.has_update_timestamp() is False


def test_reconcile_cleans_partial_index(fake_dirs: Path):
    node_dir = Path(config.OS_NODE_DIR)
    node_dir.mkdir(parents=True)
    (node_dir / "segment.bin").write_text("partial")
    index.mark_import_started()

    index.reconcile()

    assert not Path(config.PHOTON_DATA_DIR).exists()
    assert index.import_was_interrupted() is False


def test_reconcile_noop_without_marker(fake_dirs: Path):
    node_dir = Path(config.OS_NODE_DIR)
    node_dir.mkdir(parents=True)
    (node_dir / "segment.bin").write_text("complete")

    index.reconcile()

    assert Path(config.OS_NODE_DIR).exists()


def test_remove_deletes_index(fake_dirs: Path):
    node_dir = Path(config.OS_NODE_DIR)
    node_dir.mkdir(parents=True)
    (node_dir / "segment.bin").write_text("old")

    index.remove()
    index.remove()

    assert not Path(config.PHOTON_DATA_DIR).exists()


def test_activate_swaps_into_target(fake_dirs: Path):
    source = fake_dirs / "source"
    source.mkdir()
    (source / "data.txt").write_text("new")

    index.activate(str(source))

    target = Path(config.PHOTON_DATA_DIR)
    assert (target / "data.txt").read_text() == "new"
    assert not source.exists()
    assert not Path(str(target) + ".staging").exists()
    assert index.has_update_timestamp() is True


def test_activate_raises_after_swap_when_marker_cannot_be_written(fake_dirs: Path):
    source = fake_dirs / "source"
    source.mkdir()
    (source / "data.txt").write_text("new")

    with patch("src.index.Path.touch", side_effect=OSError("read-only")), pytest.raises(OSError, match="read-only"):
        index.activate(str(source))

    assert (Path(config.PHOTON_DATA_DIR) / "data.txt").read_text() == "new"
    assert index.has_update_timestamp() is False


def test_activate_replaces_existing_target_keeping_backup(fake_dirs: Path):
    target = Path(config.PHOTON_DATA_DIR)
    target.mkdir(parents=True)
    (target / "old.txt").write_text("old")

    source = fake_dirs / "source"
    source.mkdir()
    (source / "new.txt").write_text("new")

    index.activate(str(source))

    assert (target / "new.txt").read_text() == "new"
    assert not (target / "old.txt").exists()
    backup = Path(str(target) + ".backup")
    assert backup.exists()
    assert (backup / "old.txt").read_text() == "old"


def test_activate_cleans_leftover_staging_dir(fake_dirs: Path):
    source = fake_dirs / "source"
    source.mkdir()
    (source / "x.txt").write_text("x")
    leftover_staging = Path(config.PHOTON_DATA_DIR + ".staging")
    leftover_staging.mkdir(parents=True)
    (leftover_staging / "stale.txt").write_text("stale")

    index.activate(str(source))

    assert (Path(config.PHOTON_DATA_DIR) / "x.txt").read_text() == "x"
    assert not leftover_staging.exists()


def _fail_staging_to_target_rename():
    real_rename = os.rename

    def fake_rename(src, dst):
        if str(src).endswith(".staging") and str(dst) == config.PHOTON_DATA_DIR:
            raise OSError("rename boom")
        real_rename(src, dst)

    return fake_rename


def test_activate_rolls_back_on_failure(fake_dirs: Path):
    source = fake_dirs / "source"
    source.mkdir()
    (source / "new.txt").write_text("new")
    target = Path(config.PHOTON_DATA_DIR)
    target.mkdir(parents=True)
    (target / "old.txt").write_text("old")

    with (
        patch("src.index.os.rename", side_effect=_fail_staging_to_target_rename()),
        pytest.raises(OSError, match="rename boom"),
    ):
        index.activate(str(source))

    assert (target / "old.txt").read_text() == "old"
    assert (source / "new.txt").read_text() == "new"
    assert not Path(str(target) + ".backup").exists()
    assert not Path(str(target) + ".staging").exists()
    assert index.has_update_timestamp() is False


def test_activate_rolls_back_on_failure_without_existing_target(fake_dirs: Path):
    source = fake_dirs / "source"
    source.mkdir()
    (source / "new.txt").write_text("new")

    with (
        patch("src.index.os.rename", side_effect=_fail_staging_to_target_rename()),
        pytest.raises(OSError, match="rename boom"),
    ):
        index.activate(str(source))

    assert not Path(config.PHOTON_DATA_DIR).exists()
    assert (source / "new.txt").read_text() == "new"
    assert not Path(config.PHOTON_DATA_DIR + ".staging").exists()


def test_activate_raises_rollback_error_when_rollback_fails(fake_dirs: Path):
    source = fake_dirs / "source"
    source.mkdir()
    (source / "new.txt").write_text("new")
    target = Path(config.PHOTON_DATA_DIR)
    target.mkdir(parents=True)
    (target / "old.txt").write_text("old")

    real_rename = os.rename

    def fake_rename(src, dst):
        if str(dst) == config.PHOTON_DATA_DIR:
            raise OSError("rename boom")
        real_rename(src, dst)

    with (
        patch("src.index.os.rename", side_effect=fake_rename),
        pytest.raises(index.IndexRollbackError, match="manual intervention"),
    ):
        index.activate(str(source))


def test_activate_aborts_when_leftover_cleanup_fails(fake_dirs: Path):
    source = fake_dirs / "source"
    source.mkdir()
    (source / "new.txt").write_text("new")
    leftover = Path(config.PHOTON_DATA_DIR + ".staging")
    leftover.mkdir(parents=True)

    with patch("src.index.shutil.rmtree", side_effect=OSError("locked")), pytest.raises(OSError, match="locked"):
        index.activate(str(source))

    assert (source / "new.txt").read_text() == "new"
    assert not Path(config.PHOTON_DATA_DIR).exists()


def test_drop_backup_removes_backup(fake_dirs: Path):
    backup = Path(config.PHOTON_DATA_DIR + ".backup")
    backup.mkdir(parents=True)
    (backup / "x").write_text("x")

    assert index.drop_backup() is True
    assert not backup.exists()


def test_drop_backup_returns_true_when_no_backup(fake_dirs: Path):
    assert index.drop_backup() is True


def test_drop_backup_returns_false_on_failure(fake_dirs: Path):
    backup = Path(config.PHOTON_DATA_DIR + ".backup")
    backup.mkdir(parents=True)
    with patch("src.index.shutil.rmtree", side_effect=OSError("locked")):
        assert index.drop_backup() is False
