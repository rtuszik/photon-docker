import hashlib
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from src import update
from src.check_remote import RemoteFileSizeError
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


def test_get_download_url_uses_file_url_when_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "FILE_URL", "https://override.example/file.tar.bz2")
    assert update.get_download_url() == "https://override.example/file.tar.bz2"


def test_get_download_url_constructs_from_region_and_base(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "FILE_URL", None)
    monkeypatch.setattr(config, "BASE_URL", "https://example.com/public")
    monkeypatch.setattr(config, "REGION", "europe")
    monkeypatch.setattr(config, "INDEX_DB_VERSION", "1.0")
    monkeypatch.setattr(config, "INDEX_FILE_EXTENSION", "tar.bz2")
    url = update.get_download_url()
    assert url == "https://example.com/public/europe/photon-db-europe-1.0-latest.tar.bz2"


def test_download_index_returns_path(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "INDEX_FILE_EXTENSION", "tar.bz2")
    monkeypatch.setattr(update, "get_download_url", lambda: "https://example.com/x")
    Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)

    def fake_download(_url, output):
        Path(output).write_bytes(b"x")
        return True

    with patch("src.update.download_file", side_effect=fake_download):
        out = update.download_index()

    assert out == str(Path(config.TEMP_DIR) / "photon-db-latest.tar.bz2")
    assert Path(out).exists()


def test_download_index_raises_on_failure(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "INDEX_FILE_EXTENSION", "tar.bz2")
    monkeypatch.setattr(update, "get_download_url", lambda: "https://example.com/x")
    Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)
    with (
        patch("src.update.download_file", return_value=False),
        pytest.raises(update.DownloadError, match="Failed to download index"),
    ):
        update.download_index()


def test_download_md5_uses_explicit_url(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "MD5_URL", "https://example.com/custom.md5")
    monkeypatch.setattr(config, "INDEX_FILE_EXTENSION", "tar.bz2")
    Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)

    captured = {}

    def fake_download(url, output):
        captured["url"] = url
        Path(output).write_text("md5")
        return True

    with patch("src.update.download_file", side_effect=fake_download):
        out = update.download_md5()

    assert captured["url"] == "https://example.com/custom.md5"
    assert out.endswith("photon-db-latest.tar.bz2.md5")


def test_download_md5_constructs_url_when_unset(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "MD5_URL", None)
    monkeypatch.setattr(config, "FILE_URL", None)
    monkeypatch.setattr(config, "BASE_URL", "https://example.com/public")
    monkeypatch.setattr(config, "REGION", None)
    monkeypatch.setattr(config, "INDEX_DB_VERSION", "1.0")
    monkeypatch.setattr(config, "INDEX_FILE_EXTENSION", "tar.bz2")
    Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)

    captured = {}

    def fake_download(url, output):
        captured["url"] = url
        Path(output).write_text("md5")
        return True

    with patch("src.update.download_file", side_effect=fake_download):
        update.download_md5()

    assert captured["url"] == "https://example.com/public/photon-db-planet-1.0-latest.tar.bz2.md5"


def test_download_md5_raises_on_failure(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "MD5_URL", "https://example.com/x.md5")
    monkeypatch.setattr(config, "INDEX_FILE_EXTENSION", "tar.bz2")
    Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)
    with (
        patch("src.update.download_file", return_value=False),
        pytest.raises(update.DownloadError, match="Failed to download MD5"),
    ):
        update.download_md5()


def test_extract_index_runs_lbzip2_command(fake_dirs: Path):
    index_file = fake_dirs / "index.tar.bz2"
    index_file.write_bytes(b"x")

    completed = subprocess.CompletedProcess(args="cmd", returncode=0, stdout="ok", stderr="")
    with patch("src.update.subprocess.run", return_value=completed) as run:
        update.extract_index(str(index_file))

    args, kwargs = run.call_args
    cmd = args[0]
    assert cmd[:4] == ["/bin/bash", "-o", "pipefail", "-c"]
    assert "lbzip2 -d -c" in cmd[4]
    assert str(index_file) in cmd[4]
    assert kwargs["check"] is True
    assert Path(config.TEMP_DIR).exists()


def test_extract_index_raises_extraction_error_on_failure(fake_dirs: Path):
    index_file = fake_dirs / "index.tar.bz2"
    index_file.write_bytes(b"x")
    err = subprocess.CalledProcessError(returncode=1, cmd="lbzip2 ...", output="", stderr="boom")
    with (
        patch("src.update.subprocess.run", side_effect=err),
        pytest.raises(update.ExtractionError, match="return code 1"),
    ):
        update.extract_index(str(index_file))


def test_verify_checksum_returns_true_on_match(tmp_path: Path):
    index_file = tmp_path / "index.bin"
    index_file.write_bytes(b"hello world")
    expected = hashlib.md5(b"hello world").hexdigest()  # noqa: S324
    md5_file = tmp_path / "index.bin.md5"
    md5_file.write_text(f"{expected}  index.bin\n")

    assert update.verify_checksum(str(md5_file), str(index_file)) is True


def test_verify_checksum_raises_on_mismatch(tmp_path: Path):
    index_file = tmp_path / "index.bin"
    index_file.write_bytes(b"hello world")
    md5_file = tmp_path / "index.bin.md5"
    md5_file.write_text("00000000000000000000000000000000  index.bin\n")

    with pytest.raises(update.ChecksumMismatchError, match="Checksum mismatch"):
        update.verify_checksum(str(md5_file), str(index_file))


def test_verify_checksum_raises_when_index_missing(tmp_path: Path):
    md5_file = tmp_path / "x.md5"
    md5_file.write_text("0" * 32)
    with pytest.raises(FileNotFoundError):
        update.verify_checksum(str(md5_file), str(tmp_path / "missing"))


def test_verify_checksum_raises_when_md5_missing(tmp_path: Path):
    index_file = tmp_path / "index.bin"
    index_file.write_bytes(b"data")
    with pytest.raises(FileNotFoundError):
        update.verify_checksum(str(tmp_path / "missing.md5"), str(index_file))


def test_verify_checksum_raises_on_empty_md5_file(tmp_path: Path):
    index_file = tmp_path / "index.bin"
    index_file.write_bytes(b"data")
    md5_file = tmp_path / "empty.md5"
    md5_file.write_text("")
    with pytest.raises((IndexError, ValueError)):
        update.verify_checksum(str(md5_file), str(index_file))


def _make_pipeline_patches(monkeypatch: pytest.MonkeyPatch):
    fake_index = str(Path(config.TEMP_DIR) / "index.tar.bz2")
    fake_md5 = fake_index + ".md5"
    monkeypatch.setattr(update, "get_download_url", lambda: "https://example.com/x")
    monkeypatch.setattr(update, "get_remote_file_size", lambda _: 1024)
    monkeypatch.setattr(update, "check_disk_space_requirements", lambda *_, **__: True)
    monkeypatch.setattr(update, "download_index", lambda: fake_index)
    monkeypatch.setattr(update, "download_md5", lambda: fake_md5)
    monkeypatch.setattr(update, "extract_index", lambda _: None)
    monkeypatch.setattr(update, "verify_checksum", lambda *_: True)
    monkeypatch.setattr(update.index, "activate", lambda _: None)
    monkeypatch.setattr(update, "clear_temp_dir", lambda: None)


def test_run_update_happy_path(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "SKIP_MD5_CHECK", False)
    _make_pipeline_patches(monkeypatch)
    update.run_update("PARALLEL")
    assert Path(config.TEMP_DIR).exists()


def test_run_update_passes_strategy_to_space_check(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "SKIP_MD5_CHECK", True)
    _make_pipeline_patches(monkeypatch)

    captured = {}

    def fake_check(size, is_parallel):
        captured["is_parallel"] = is_parallel
        return True

    monkeypatch.setattr(update, "check_disk_space_requirements", fake_check)

    update.run_update("PARALLEL")
    assert captured["is_parallel"] is True

    update.run_update("SEQUENTIAL")
    assert captured["is_parallel"] is False


def test_run_update_skips_md5_when_configured(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "SKIP_MD5_CHECK", True)
    _make_pipeline_patches(monkeypatch)

    md5_called = {"n": 0}

    def fake_md5():
        md5_called["n"] += 1
        return str(Path(config.TEMP_DIR) / "x.md5")

    monkeypatch.setattr(update, "download_md5", fake_md5)
    update.run_update("PARALLEL")
    assert md5_called["n"] == 0


def test_run_update_raises_insufficient_space(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    _make_pipeline_patches(monkeypatch)
    monkeypatch.setattr(update, "check_disk_space_requirements", lambda *_, **__: False)
    with pytest.raises(update.InsufficientSpaceError):
        update.run_update("PARALLEL")


def test_run_update_skip_space_check_proceeds_on_size_error(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "SKIP_SPACE_CHECK", True)
    monkeypatch.setattr(config, "SKIP_MD5_CHECK", True)
    _make_pipeline_patches(monkeypatch)

    def boom(_url):
        raise RemoteFileSizeError("no size")

    monkeypatch.setattr(update, "get_remote_file_size", boom)
    update.run_update("PARALLEL")


def test_run_update_raises_on_size_error_without_skip(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "SKIP_SPACE_CHECK", False)
    _make_pipeline_patches(monkeypatch)

    def boom(_url):
        raise RemoteFileSizeError("no size")

    monkeypatch.setattr(update, "get_remote_file_size", boom)
    with pytest.raises(update.UpdateError, match="no size"):
        update.run_update("SEQUENTIAL")


def test_run_update_propagates_download_error(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "SKIP_MD5_CHECK", True)
    _make_pipeline_patches(monkeypatch)

    def boom():
        raise update.DownloadError("download died")

    monkeypatch.setattr(update, "download_index", boom)
    with pytest.raises(update.DownloadError, match="download died"):
        update.run_update("SEQUENTIAL")


def test_run_update_checksum_mismatch_prevents_activation(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "SKIP_MD5_CHECK", False)
    _make_pipeline_patches(monkeypatch)

    activated = {"n": 0}

    def fake_activate(_):
        activated["n"] += 1

    monkeypatch.setattr(update.index, "activate", fake_activate)

    def boom(*_):
        raise update.ChecksumMismatchError("checksum mismatch")

    monkeypatch.setattr(update, "verify_checksum", boom)

    with pytest.raises(update.ChecksumMismatchError, match="checksum mismatch"):
        update.run_update("PARALLEL")
    assert activated["n"] == 0


def test_run_update_extraction_failure_prevents_activation(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "SKIP_MD5_CHECK", True)
    _make_pipeline_patches(monkeypatch)

    activated = {"n": 0}

    def fake_activate(_):
        activated["n"] += 1

    monkeypatch.setattr(update.index, "activate", fake_activate)

    def boom(_):
        raise update.ExtractionError("truncated archive")

    monkeypatch.setattr(update, "extract_index", boom)

    with pytest.raises(update.ExtractionError, match="truncated archive"):
        update.run_update("SEQUENTIAL")
    assert activated["n"] == 0
