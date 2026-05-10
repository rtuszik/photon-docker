import hashlib
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from src import filesystem
from src.utils import config


@pytest.fixture
def fake_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "data"
    photon_data_dir = data_dir / "photon_data"
    temp_dir = data_dir / "temp"
    os_node_dir = photon_data_dir / "node_1"
    data_dir.mkdir()

    monkeypatch.setattr(config, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(config, "PHOTON_DATA_DIR", str(photon_data_dir))
    monkeypatch.setattr(config, "TEMP_DIR", str(temp_dir))
    monkeypatch.setattr(config, "OS_NODE_DIR", str(os_node_dir))
    return data_dir


def test_verify_checksum_returns_true_on_match(tmp_path: Path):
    index_file = tmp_path / "index.bin"
    index_file.write_bytes(b"hello world")
    expected = hashlib.md5(b"hello world").hexdigest()  # noqa: S324
    md5_file = tmp_path / "index.bin.md5"
    md5_file.write_text(f"{expected}  index.bin\n")

    assert filesystem.verify_checksum(str(md5_file), str(index_file)) is True


def test_verify_checksum_raises_on_mismatch(tmp_path: Path):
    index_file = tmp_path / "index.bin"
    index_file.write_bytes(b"hello world")
    md5_file = tmp_path / "index.bin.md5"
    md5_file.write_text("00000000000000000000000000000000  index.bin\n")

    with pytest.raises(Exception, match="Checksum mismatch"):
        filesystem.verify_checksum(str(md5_file), str(index_file))


def test_verify_checksum_raises_when_index_missing(tmp_path: Path):
    md5_file = tmp_path / "x.md5"
    md5_file.write_text("0" * 32)
    with pytest.raises(FileNotFoundError):
        filesystem.verify_checksum(str(md5_file), str(tmp_path / "missing"))


def test_verify_checksum_raises_when_md5_missing(tmp_path: Path):
    index_file = tmp_path / "index.bin"
    index_file.write_bytes(b"data")
    with pytest.raises(FileNotFoundError):
        filesystem.verify_checksum(str(tmp_path / "missing.md5"), str(index_file))


def test_verify_checksum_raises_on_empty_md5_file(tmp_path: Path):
    index_file = tmp_path / "index.bin"
    index_file.write_bytes(b"data")
    md5_file = tmp_path / "empty.md5"
    md5_file.write_text("")
    with pytest.raises((IndexError, ValueError)):
        filesystem.verify_checksum(str(md5_file), str(index_file))


def test_clear_temp_dir_removes_existing_temp(fake_dirs: Path):
    temp = Path(config.TEMP_DIR)
    temp.mkdir()
    (temp / "file.txt").write_text("x")
    (temp / "sub").mkdir()
    (temp / "sub" / "nested").write_text("y")

    filesystem.clear_temp_dir()

    assert not temp.exists()


def test_clear_temp_dir_handles_missing_temp_dir(fake_dirs: Path):
    assert not Path(config.TEMP_DIR).exists()
    filesystem.clear_temp_dir()


def test_update_timestamp_marker_creates_marker(fake_dirs: Path):
    filesystem.update_timestamp_marker()
    marker = Path(config.DATA_DIR) / ".photon-index-updated"
    assert marker.exists()


def test_update_timestamp_marker_swallows_errors(fake_dirs: Path):
    with patch("src.filesystem.Path.touch", side_effect=OSError("nope")):
        filesystem.update_timestamp_marker()


def test_cleanup_staging_and_temp_backup_removes_both(tmp_path: Path):
    staging = tmp_path / "staging"
    backup = tmp_path / "backup"
    staging.mkdir()
    backup.mkdir()
    (staging / "f").write_text("x")
    (backup / "f").write_text("y")

    filesystem.cleanup_staging_and_temp_backup(str(staging), str(backup))

    assert not staging.exists()
    assert not backup.exists()


def test_cleanup_staging_and_temp_backup_no_op_when_missing(tmp_path: Path):
    filesystem.cleanup_staging_and_temp_backup(str(tmp_path / "a"), str(tmp_path / "b"))


def test_cleanup_staging_and_temp_backup_swallows_rmtree_errors(tmp_path: Path):
    staging = tmp_path / "staging"
    staging.mkdir()
    with patch("src.filesystem.shutil.rmtree", side_effect=OSError("locked")):
        filesystem.cleanup_staging_and_temp_backup(str(staging), str(tmp_path / "missing"))


def test_cleanup_backup_after_verification_removes_backup(tmp_path: Path):
    target = tmp_path / "node_1"
    backup = Path(str(target) + ".backup")
    backup.mkdir()
    (backup / "x").write_text("x")

    assert filesystem.cleanup_backup_after_verification(str(target)) is True
    assert not backup.exists()


def test_cleanup_backup_after_verification_returns_true_when_no_backup(tmp_path: Path):
    target = tmp_path / "node_1"
    assert filesystem.cleanup_backup_after_verification(str(target)) is True


def test_cleanup_backup_after_verification_returns_false_on_failure(tmp_path: Path):
    target = tmp_path / "node_1"
    backup = Path(str(target) + ".backup")
    backup.mkdir()
    with patch("src.filesystem.shutil.rmtree", side_effect=OSError("locked")):
        assert filesystem.cleanup_backup_after_verification(str(target)) is False


def test_move_index_atomic_swaps_into_target(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "data.txt").write_text("new")

    target = tmp_path / "target"

    assert filesystem.move_index_atomic(str(source), str(target)) is True
    assert (target / "data.txt").read_text() == "new"
    assert not source.exists()
    assert not (tmp_path / "target.staging").exists()


def test_move_index_atomic_replaces_existing_target(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "old.txt").write_text("old")

    source = tmp_path / "source"
    source.mkdir()
    (source / "new.txt").write_text("new")

    assert filesystem.move_index_atomic(str(source), str(target)) is True
    assert (target / "new.txt").read_text() == "new"
    assert not (target / "old.txt").exists()
    backup = Path(str(target) + ".backup")
    assert backup.exists()
    assert (backup / "old.txt").read_text() == "old"


def test_move_index_atomic_cleans_existing_staging_dir(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "x.txt").write_text("x")
    target = tmp_path / "target"
    leftover_staging = Path(str(target) + ".staging")
    leftover_staging.mkdir()
    (leftover_staging / "stale.txt").write_text("stale")

    assert filesystem.move_index_atomic(str(source), str(target)) is True
    assert (target / "x.txt").read_text() == "x"
    assert not leftover_staging.exists()


def test_move_index_atomic_rolls_back_on_failure(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "new.txt").write_text("new")
    target = tmp_path / "target"
    target.mkdir()
    (target / "old.txt").write_text("old")

    real_rename = os.rename
    call_count = {"n": 0}

    def fake_rename(src, dst):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError("rename boom")
        real_rename(src, dst)

    with patch("src.filesystem.os.rename", side_effect=fake_rename), pytest.raises(OSError, match="rename boom"):
        filesystem.move_index_atomic(str(source), str(target))

    assert (target / "old.txt").read_text() == "old"
    assert not Path(str(target) + ".backup").exists()


def test_rollback_atomic_move_keeps_new_index_when_succeeded(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "fresh.txt").write_text("fresh")

    filesystem.rollback_atomic_move(
        str(tmp_path / "source"), str(target), str(tmp_path / "staging"), str(tmp_path / "backup")
    )

    assert (target / "fresh.txt").read_text() == "fresh"


def test_rollback_atomic_move_swallows_inner_exceptions(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    backup = tmp_path / "backup"
    backup.mkdir()

    with patch("src.filesystem.shutil.rmtree", side_effect=OSError("nope")):
        filesystem.rollback_atomic_move(str(tmp_path / "source"), str(target), str(tmp_path / "staging"), str(backup))


def test_move_index_calls_atomic_and_writes_marker(fake_dirs: Path):
    temp_photon = Path(config.TEMP_DIR) / "photon_data"
    temp_photon.mkdir(parents=True)
    (temp_photon / "node_1").mkdir()
    (temp_photon / "node_1" / "data.bin").write_text("payload")

    assert filesystem.move_index() is True

    marker = Path(config.DATA_DIR) / ".photon-index-updated"
    assert marker.exists()
    target = Path(config.PHOTON_DATA_DIR)
    assert (target / "node_1" / "data.bin").read_text() == "payload"


def test_move_index_returns_false_when_atomic_returns_false(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(filesystem, "move_index_atomic", lambda *_: False)
    assert filesystem.move_index() is False
    marker = Path(config.DATA_DIR) / ".photon-index-updated"
    assert not marker.exists()


def test_extract_index_runs_lbzip2_command(fake_dirs: Path):
    index_file = Path(config.TEMP_DIR).parent / "index.tar.bz2"
    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_bytes(b"x")

    completed = subprocess.CompletedProcess(args="cmd", returncode=0, stdout="ok", stderr="")
    with patch("src.filesystem.subprocess.run", return_value=completed) as run:
        filesystem.extract_index(str(index_file))

    args, kwargs = run.call_args
    assert "lbzip2 -d -c" in args[0]
    assert str(index_file) in args[0]
    assert kwargs["shell"] is True
    assert kwargs["check"] is True
    assert Path(config.TEMP_DIR).exists()


def test_extract_index_creates_temp_dir_when_missing(fake_dirs: Path):
    index_file = Path(config.DATA_DIR) / "index.tar.bz2"
    index_file.write_bytes(b"x")

    assert not Path(config.TEMP_DIR).exists()
    completed = subprocess.CompletedProcess(args="cmd", returncode=0, stdout="", stderr="")
    with patch("src.filesystem.subprocess.run", return_value=completed):
        filesystem.extract_index(str(index_file))

    assert Path(config.TEMP_DIR).exists()


def test_extract_index_propagates_called_process_error(fake_dirs: Path):
    index_file = Path(config.DATA_DIR) / "index.tar.bz2"
    index_file.write_bytes(b"x")
    err = subprocess.CalledProcessError(returncode=1, cmd="lbzip2 ...", output="", stderr="boom")
    with patch("src.filesystem.subprocess.run", side_effect=err), pytest.raises(subprocess.CalledProcessError):
        filesystem.extract_index(str(index_file))


def test_extract_index_propagates_unexpected_error(fake_dirs: Path):
    index_file = Path(config.DATA_DIR) / "index.tar.bz2"
    index_file.write_bytes(b"x")
    with patch("src.filesystem.subprocess.run", side_effect=RuntimeError("nope")), pytest.raises(RuntimeError):
        filesystem.extract_index(str(index_file))
