import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import RequestException

from src import downloader
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


def _mock_response(status_code=200, headers=None, chunks=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    resp.iter_content = MagicMock(return_value=iter(chunks or []))
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_get_available_space_returns_bytes(tmp_path: Path):
    space = downloader.get_available_space(str(tmp_path))
    assert space > 0


def test_get_available_space_returns_zero_on_invalid_path():
    assert downloader.get_available_space("/this/does/not/exist") == 0


def test_check_disk_space_requirements_parallel_passes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(downloader, "get_available_space", lambda _: 100 * 1024**3)
    assert downloader.check_disk_space_requirements(10 * 1024**3, is_parallel=True) is True


def test_check_disk_space_requirements_parallel_fails_on_temp(monkeypatch: pytest.MonkeyPatch):
    sizes = iter([1, 100 * 1024**3])
    monkeypatch.setattr(downloader, "get_available_space", lambda _: next(sizes))
    assert downloader.check_disk_space_requirements(10 * 1024**3, is_parallel=True) is False


def test_check_disk_space_requirements_parallel_fails_on_data(monkeypatch: pytest.MonkeyPatch):
    sizes = iter([100 * 1024**3, 1])
    monkeypatch.setattr(downloader, "get_available_space", lambda _: next(sizes))
    assert downloader.check_disk_space_requirements(10 * 1024**3, is_parallel=True) is False


def test_check_disk_space_requirements_sequential_passes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(downloader, "get_available_space", lambda _: 100 * 1024**3)
    assert downloader.check_disk_space_requirements(10 * 1024**3, is_parallel=False) is True


def test_check_disk_space_requirements_sequential_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(downloader, "get_available_space", lambda _: 1)
    assert downloader.check_disk_space_requirements(10 * 1024**3, is_parallel=False) is False


def test_get_download_state_file_appends_suffix():
    assert downloader.get_download_state_file("/x/y/file.bin") == "/x/y/file.bin.download_state"


def test_save_and_load_download_state_roundtrip(tmp_path: Path):
    dest = tmp_path / "file.bin"
    dest.write_bytes(b"hello")
    downloader.save_download_state(str(dest), "https://example.com/x", 5, 100)
    state = downloader.load_download_state(str(dest))
    assert state["url"] == "https://example.com/x"
    assert state["downloaded_bytes"] == 5
    assert state["total_size"] == 100
    assert state["file_size"] == 5


def test_load_download_state_returns_empty_when_no_state_file(tmp_path: Path):
    assert downloader.load_download_state(str(tmp_path / "nope")) == {}


def test_load_download_state_resyncs_with_actual_file_size(tmp_path: Path):
    dest = tmp_path / "file.bin"
    dest.write_bytes(b"x" * 200)
    state_file = Path(downloader.get_download_state_file(str(dest)))
    state_file.write_text(json.dumps({"url": "u", "downloaded_bytes": 50, "total_size": 1000, "file_size": 50}))

    state = downloader.load_download_state(str(dest))
    assert state["downloaded_bytes"] == 200
    assert state["file_size"] == 200


def test_load_download_state_drops_state_when_file_smaller(tmp_path: Path):
    dest = tmp_path / "file.bin"
    dest.write_bytes(b"x" * 10)
    state_file = Path(downloader.get_download_state_file(str(dest)))
    state_file.write_text(json.dumps({"url": "u", "downloaded_bytes": 50, "total_size": 1000, "file_size": 50}))

    assert downloader.load_download_state(str(dest)) == {}
    assert not state_file.exists()


def test_load_download_state_handles_corrupted_state(tmp_path: Path):
    dest = tmp_path / "file.bin"
    dest.write_bytes(b"data")
    state_file = Path(downloader.get_download_state_file(str(dest)))
    state_file.write_text("{not json")

    assert downloader.load_download_state(str(dest)) == {}
    assert not state_file.exists()


def test_cleanup_download_state_removes_file(tmp_path: Path):
    dest = tmp_path / "file.bin"
    state_file = Path(downloader.get_download_state_file(str(dest)))
    state_file.write_text("{}")
    downloader.cleanup_download_state(str(dest))
    assert not state_file.exists()


def test_cleanup_download_state_no_op_when_missing(tmp_path: Path):
    downloader.cleanup_download_state(str(tmp_path / "missing"))


def test_cleanup_download_state_swallows_remove_errors(tmp_path: Path):
    dest = tmp_path / "file.bin"
    state_file = Path(downloader.get_download_state_file(str(dest)))
    state_file.write_text("{}")
    with patch("src.downloader.os.remove", side_effect=OSError("locked")):
        downloader.cleanup_download_state(str(dest))


def test_supports_range_requests_true():
    resp = _mock_response(headers={"accept-ranges": "bytes"})
    with patch("src.downloader.requests.head", return_value=resp):
        assert downloader.supports_range_requests("https://example.com/x") is True


def test_supports_range_requests_false_when_header_missing():
    resp = _mock_response(headers={})
    with patch("src.downloader.requests.head", return_value=resp):
        assert downloader.supports_range_requests("https://example.com/x") is False


def test_supports_range_requests_false_on_error():
    with patch("src.downloader.requests.head", side_effect=RequestException("nope")):
        assert downloader.supports_range_requests("https://example.com/x") is False


def test_get_download_url_uses_file_url_when_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "FILE_URL", "https://override.example/file.tar.bz2")
    assert downloader.get_download_url() == "https://override.example/file.tar.bz2"


def test_get_download_url_constructs_from_region_and_base(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "FILE_URL", None)
    monkeypatch.setattr(config, "BASE_URL", "https://example.com/public")
    monkeypatch.setattr(config, "REGION", "europe")
    monkeypatch.setattr(config, "INDEX_DB_VERSION", "1.0")
    monkeypatch.setattr(config, "INDEX_FILE_EXTENSION", "tar.bz2")
    url = downloader.get_download_url()
    assert url == "https://example.com/public/europe/photon-db-europe-1.0-latest.tar.bz2"


def test_prepare_download_no_state(tmp_path: Path):
    dest = tmp_path / "file.bin"
    pos, mode = downloader._prepare_download("https://example.com/x", str(dest))
    assert pos == 0
    assert mode == "wb"


def test_prepare_download_resumes_when_state_matches(tmp_path: Path):
    dest = tmp_path / "file.bin"
    dest.write_bytes(b"x" * 50)
    downloader.save_download_state(str(dest), "https://example.com/x", 50, 100)

    pos, mode = downloader._prepare_download("https://example.com/x", str(dest))
    assert pos == 50
    assert mode == "ab"


def test_prepare_download_starts_fresh_when_url_changed(tmp_path: Path):
    dest = tmp_path / "file.bin"
    dest.write_bytes(b"x" * 50)
    downloader.save_download_state(str(dest), "https://old.example.com/x", 50, 100)

    pos, mode = downloader._prepare_download("https://new.example.com/x", str(dest))
    assert pos == 0
    assert mode == "wb"


def test_get_download_headers_returns_range_when_resuming(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(downloader, "supports_range_requests", lambda _: True)
    assert downloader._get_download_headers(123, "https://example.com/x") == {"Range": "bytes=123-"}


def test_get_download_headers_empty_when_no_resume():
    assert downloader._get_download_headers(0, "https://example.com/x") == {}


def test_get_download_headers_empty_when_no_range_support(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(downloader, "supports_range_requests", lambda _: False)
    assert downloader._get_download_headers(123, "https://example.com/x") == {}


def test_calculate_total_size_with_range_response_using_content_range():
    resp = _mock_response(status_code=206, headers={"content-range": "bytes 0-99/12345"})
    assert downloader._calculate_total_size(resp, {"Range": "bytes=0-"}, 0) == 12345


def test_calculate_total_size_with_range_response_no_content_range():
    resp = _mock_response(status_code=206, headers={"content-length": "100"})
    assert downloader._calculate_total_size(resp, {"Range": "bytes=50-"}, 50) == 150


def test_calculate_total_size_without_range_uses_content_length():
    resp = _mock_response(status_code=200, headers={"content-length": "9999"})
    assert downloader._calculate_total_size(resp, {}, 0) == 9999


def test_handle_no_range_support_resets_when_resuming(tmp_path: Path):
    dest = tmp_path / "file.bin"
    dest.write_bytes(b"x" * 100)
    pos, mode = downloader._handle_no_range_support(100, str(dest))
    assert pos == 0
    assert mode == "wb"
    assert not dest.exists()


def test_handle_no_range_support_no_op_when_not_resuming(tmp_path: Path):
    dest = tmp_path / "file.bin"
    pos, mode = downloader._handle_no_range_support(0, str(dest))
    assert pos == 0
    assert mode is None


def test_create_progress_bar_returns_none_when_no_size(tmp_path: Path):
    assert downloader._create_progress_bar(0, 0, str(tmp_path / "file.bin")) is None


def test_create_progress_bar_returns_tqdm_when_size_known(tmp_path: Path):
    bar = downloader._create_progress_bar(1024, 0, str(tmp_path / "file.bin"))
    assert bar is not None
    bar.close()


def test_log_download_metrics_handles_long_download(caplog: pytest.LogCaptureFixture, tmp_path: Path):
    import logging as _logging
    import time

    caplog.set_level(_logging.INFO, logger="root")
    downloader._log_download_metrics(10 * 1024**3, time.time() - (3 * 60 * 60), str(tmp_path / "f"))
    msgs = "\n".join(r.message for r in caplog.records)
    assert "Download completed" in msgs
    assert "h" in msgs


def test_log_download_metrics_handles_short_download(caplog: pytest.LogCaptureFixture, tmp_path: Path):
    import logging as _logging
    import time

    caplog.set_level(_logging.INFO, logger="root")
    downloader._log_download_metrics(1024**3, time.time() - 10, str(tmp_path / "f"))
    assert any("Download completed" in r.message for r in caplog.records)


def test_log_download_metrics_no_size(caplog: pytest.LogCaptureFixture, tmp_path: Path):
    import logging as _logging

    caplog.set_level(_logging.INFO, logger="root")
    downloader._log_download_metrics(0, 0.0, str(tmp_path / "f"))
    assert any("successfully" in r.message for r in caplog.records)


def test_download_file_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dest = tmp_path / "out.bin"
    monkeypatch.setattr(config, "DOWNLOAD_MAX_RETRIES", "1")

    resp = _mock_response(status_code=200, headers={"content-length": "5"}, chunks=[b"hello"])
    with patch("src.downloader.requests.get", return_value=resp):
        assert downloader.download_file("https://example.com/x", str(dest)) is True

    assert dest.read_bytes() == b"hello"
    assert not Path(downloader.get_download_state_file(str(dest))).exists()


def test_download_file_incomplete_raises_and_returns_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dest = tmp_path / "out.bin"
    monkeypatch.setattr(config, "DOWNLOAD_MAX_RETRIES", "1")

    resp = _mock_response(status_code=200, headers={"content-length": "10"}, chunks=[b"hi"])
    with patch("src.downloader.requests.get", return_value=resp):
        assert downloader.download_file("https://example.com/x", str(dest)) is False


def test_download_file_retries_on_request_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dest = tmp_path / "out.bin"
    monkeypatch.setattr(config, "DOWNLOAD_MAX_RETRIES", "3")
    monkeypatch.setattr(downloader.time, "sleep", lambda *_: None)

    good_resp = _mock_response(status_code=200, headers={"content-length": "3"}, chunks=[b"abc"])

    calls = {"n": 0}

    def fake_get(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RequestException("transient")
        return good_resp

    with patch("src.downloader.requests.get", side_effect=fake_get):
        assert downloader.download_file("https://example.com/x", str(dest)) is True
    assert calls["n"] == 3


def test_download_file_returns_false_when_retries_exhausted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dest = tmp_path / "out.bin"
    monkeypatch.setattr(config, "DOWNLOAD_MAX_RETRIES", "2")
    monkeypatch.setattr(downloader.time, "sleep", lambda *_: None)
    with patch("src.downloader.requests.get", side_effect=RequestException("always")):
        assert downloader.download_file("https://example.com/x", str(dest)) is False


def test_download_file_returns_false_on_unexpected_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dest = tmp_path / "out.bin"
    monkeypatch.setattr(config, "DOWNLOAD_MAX_RETRIES", "1")
    with patch("src.downloader.requests.get", side_effect=RuntimeError("boom")):
        assert downloader.download_file("https://example.com/x", str(dest)) is False


def test_download_index_returns_path(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "INDEX_FILE_EXTENSION", "tar.bz2")
    monkeypatch.setattr(downloader, "get_download_url", lambda: "https://example.com/x")
    Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)

    def fake_download(_url, output):
        Path(output).write_bytes(b"x")
        return True

    with patch("src.downloader.download_file", side_effect=fake_download):
        out = downloader.download_index()

    assert out == os.path.join(config.TEMP_DIR, "photon-db-latest.tar.bz2")
    assert Path(out).exists()


def test_download_index_raises_on_failure(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "INDEX_FILE_EXTENSION", "tar.bz2")
    monkeypatch.setattr(downloader, "get_download_url", lambda: "https://example.com/x")
    Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)
    with (
        patch("src.downloader.download_file", return_value=False),
        pytest.raises(Exception, match="Failed to download index"),
    ):
        downloader.download_index()


def test_download_md5_uses_explicit_url(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "MD5_URL", "https://example.com/custom.md5")
    monkeypatch.setattr(config, "INDEX_FILE_EXTENSION", "tar.bz2")
    Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)

    captured = {}

    def fake_download(url, output):
        captured["url"] = url
        captured["output"] = output
        Path(output).write_text("md5")
        return True

    with patch("src.downloader.download_file", side_effect=fake_download):
        out = downloader.download_md5()

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

    with patch("src.downloader.download_file", side_effect=fake_download):
        downloader.download_md5()

    assert captured["url"] == "https://example.com/public/photon-db-planet-1.0-latest.tar.bz2.md5"


def test_download_md5_raises_on_failure(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "MD5_URL", "https://example.com/x.md5")
    monkeypatch.setattr(config, "INDEX_FILE_EXTENSION", "tar.bz2")
    Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)
    with (
        patch("src.downloader.download_file", return_value=False),
        pytest.raises(Exception, match="Failed to download MD5"),
    ):
        downloader.download_md5()


def _make_orchestrator_patches(monkeypatch: pytest.MonkeyPatch):
    fake_index = str(Path(config.TEMP_DIR) / "index.tar.bz2")
    fake_md5 = fake_index + ".md5"
    monkeypatch.setattr(downloader, "get_download_url", lambda: "https://example.com/x")
    monkeypatch.setattr(downloader, "get_remote_file_size", lambda _: 1024)
    monkeypatch.setattr(downloader, "check_disk_space_requirements", lambda *_, **__: True)
    monkeypatch.setattr(downloader, "download_index", lambda: fake_index)
    monkeypatch.setattr(downloader, "download_md5", lambda: fake_md5)
    monkeypatch.setattr(downloader, "extract_index", lambda _: None)
    monkeypatch.setattr(downloader, "verify_checksum", lambda *_: True)
    monkeypatch.setattr(downloader, "move_index", lambda: True)
    monkeypatch.setattr(downloader, "clear_temp_dir", lambda: None)


def test_parallel_update_happy_path(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "SKIP_MD5_CHECK", False)
    _make_orchestrator_patches(monkeypatch)
    downloader.parallel_update()
    assert Path(config.TEMP_DIR).exists()


def test_parallel_update_skips_md5_when_configured(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "SKIP_MD5_CHECK", True)
    _make_orchestrator_patches(monkeypatch)

    md5_called = {"n": 0}

    def fake_md5():
        md5_called["n"] += 1
        return str(Path(config.TEMP_DIR) / "x.md5")

    monkeypatch.setattr(downloader, "download_md5", fake_md5)
    downloader.parallel_update()
    assert md5_called["n"] == 0


def test_parallel_update_raises_on_insufficient_space(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    _make_orchestrator_patches(monkeypatch)
    monkeypatch.setattr(downloader, "check_disk_space_requirements", lambda *_, **__: False)
    with pytest.raises(SystemExit):
        downloader.parallel_update()


def test_parallel_update_skip_space_check_proceeds_on_size_error(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "SKIP_SPACE_CHECK", True)
    monkeypatch.setattr(config, "SKIP_MD5_CHECK", True)
    _make_orchestrator_patches(monkeypatch)

    def boom(_url):
        raise downloader.RemoteFileSizeError("no size")

    monkeypatch.setattr(downloader, "get_remote_file_size", boom)
    downloader.parallel_update()


def test_sequential_update_happy_path(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "SKIP_MD5_CHECK", False)
    _make_orchestrator_patches(monkeypatch)
    downloader.sequential_update()


def test_sequential_update_raises_on_size_error_without_skip(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "SKIP_SPACE_CHECK", False)
    _make_orchestrator_patches(monkeypatch)

    def boom(_url):
        raise downloader.RemoteFileSizeError("no size")

    monkeypatch.setattr(downloader, "get_remote_file_size", boom)
    with pytest.raises(SystemExit):
        downloader.sequential_update()
