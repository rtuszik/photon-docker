import datetime
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import RequestException

from src import check_remote
from src.utils import config


@pytest.fixture
def fake_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "data"
    photon_data_dir = data_dir / "photon_data"
    os_node_dir = photon_data_dir / "node_1"
    data_dir.mkdir()
    photon_data_dir.mkdir()
    monkeypatch.setattr(config, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(config, "PHOTON_DATA_DIR", str(photon_data_dir))
    monkeypatch.setattr(config, "OS_NODE_DIR", str(os_node_dir))
    return data_dir


def _mock_response(status_code=200, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    return resp


def test_get_remote_file_size_uses_content_length():
    resp = _mock_response(headers={"content-length": "12345"})
    with patch("src.check_remote.requests.head", return_value=resp):
        assert check_remote.get_remote_file_size("https://example.com/x") == 12345


def test_get_remote_file_size_falls_back_to_range_request():
    head_resp = _mock_response(headers={})
    range_resp = _mock_response(status_code=206, headers={"content-range": "bytes 0-0/9876"})
    with (
        patch("src.check_remote.requests.head", return_value=head_resp),
        patch("src.check_remote.requests.get", return_value=range_resp),
    ):
        assert check_remote.get_remote_file_size("https://example.com/x") == 9876


def test_get_remote_file_size_raises_when_no_size_returned():
    head_resp = _mock_response(headers={})
    range_resp = _mock_response(status_code=200, headers={})
    with (
        patch("src.check_remote.requests.head", return_value=head_resp),
        patch("src.check_remote.requests.get", return_value=range_resp),
        pytest.raises(check_remote.RemoteFileSizeError, match="did not return file size"),
    ):
        check_remote.get_remote_file_size("https://example.com/x")


def test_get_remote_file_size_wraps_request_errors():
    with (
        patch("src.check_remote.requests.head", side_effect=RequestException("boom")),
        pytest.raises(check_remote.RemoteFileSizeError, match="Could not determine remote file size"),
    ):
        check_remote.get_remote_file_size("https://example.com/x")


def test_get_remote_file_size_ignores_non_digit_range_total():
    head_resp = _mock_response(headers={})
    range_resp = _mock_response(status_code=206, headers={"content-range": "bytes 0-0/*"})
    with (
        patch("src.check_remote.requests.head", return_value=head_resp),
        patch("src.check_remote.requests.get", return_value=range_resp),
        pytest.raises(check_remote.RemoteFileSizeError),
    ):
        check_remote.get_remote_file_size("https://example.com/x")


def test_get_remote_time_returns_parsed_datetime():
    resp = _mock_response(headers={"last-modified": "Wed, 21 Oct 2026 07:28:00 GMT"})
    with patch("src.check_remote.requests.head", return_value=resp):
        result = check_remote.get_remote_time("https://example.com")
    assert result is not None
    assert result.year == 2026
    assert result.month == 10
    assert result.day == 21


def test_get_remote_time_returns_none_when_header_missing():
    resp = _mock_response(headers={})
    with patch("src.check_remote.requests.head", return_value=resp):
        assert check_remote.get_remote_time("https://example.com") is None


def test_get_remote_time_returns_none_on_request_error():
    with patch("src.check_remote.requests.head", side_effect=RequestException("nope")):
        assert check_remote.get_remote_time("https://example.com") is None


def test_get_local_time_returns_marker_mtime_when_present(fake_dirs: Path):
    marker = fake_dirs / ".photon-index-updated"
    marker.write_text("")
    os.utime(marker, (1_000_000, 1_000_000))
    assert check_remote.get_local_time(str(fake_dirs / "missing")) == 1_000_000


def test_get_local_time_returns_path_mtime_when_no_marker(fake_dirs: Path):
    target = fake_dirs / "node_1"
    target.mkdir()
    os.utime(target, (2_000_000, 2_000_000))
    assert check_remote.get_local_time(str(target)) == 2_000_000


def test_get_local_time_returns_zero_when_path_missing(fake_dirs: Path):
    assert check_remote.get_local_time(str(fake_dirs / "missing")) == 0.0


def test_compare_mtime_returns_false_when_remote_time_unknown(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "REGION", None)
    monkeypatch.setattr(config, "BASE_URL", "https://example.com")
    with patch("src.check_remote.get_remote_time", return_value=None):
        assert check_remote.compare_mtime() is False


def test_compare_mtime_returns_false_on_invalid_region(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "REGION", "atlantis")
    assert check_remote.compare_mtime() is False


def test_compare_mtime_with_marker_compares_directly(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "REGION", None)
    monkeypatch.setattr(config, "BASE_URL", "https://example.com")

    marker = fake_dirs / ".photon-index-updated"
    marker.write_text("")
    local_ts = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC).timestamp()
    os.utime(marker, (local_ts, local_ts))

    remote_dt = datetime.datetime(2026, 1, 2, tzinfo=datetime.UTC)
    with patch("src.check_remote.get_remote_time", return_value=remote_dt):
        assert check_remote.compare_mtime() is True


def test_compare_mtime_with_marker_returns_false_when_remote_older(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "REGION", None)
    monkeypatch.setattr(config, "BASE_URL", "https://example.com")

    marker = fake_dirs / ".photon-index-updated"
    marker.write_text("")
    local_ts = datetime.datetime(2026, 1, 10, tzinfo=datetime.UTC).timestamp()
    os.utime(marker, (local_ts, local_ts))

    remote_dt = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    with patch("src.check_remote.get_remote_time", return_value=remote_dt):
        assert check_remote.compare_mtime() is False


def test_compare_mtime_directory_uses_grace_period(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "REGION", None)
    monkeypatch.setattr(config, "BASE_URL", "https://example.com")

    node_dir = Path(config.OS_NODE_DIR)
    node_dir.mkdir()
    local_ts = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC).timestamp()
    os.utime(node_dir, (local_ts, local_ts))

    remote_within_grace = datetime.datetime(2026, 1, 5, tzinfo=datetime.UTC)
    with patch("src.check_remote.get_remote_time", return_value=remote_within_grace):
        assert check_remote.compare_mtime() is False

    remote_past_grace = datetime.datetime(2026, 1, 20, tzinfo=datetime.UTC)
    with patch("src.check_remote.get_remote_time", return_value=remote_past_grace):
        assert check_remote.compare_mtime() is True


def test_check_index_age_returns_true_when_min_date_unset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "MIN_INDEX_DATE", None)
    assert check_remote.check_index_age() is True


def test_check_index_age_warns_and_returns_true_on_bad_format(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "MIN_INDEX_DATE", "2026-01-01")
    assert check_remote.check_index_age() is True


def test_check_index_age_returns_true_when_no_local_index(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "MIN_INDEX_DATE", "01.01.26")
    assert check_remote.check_index_age() is True


def test_check_index_age_returns_true_when_update_required_due_to_old_index(
    fake_dirs: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(config, "MIN_INDEX_DATE", "01.06.26")
    node_dir = Path(config.OS_NODE_DIR)
    node_dir.mkdir()
    local_ts = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC).timestamp()
    os.utime(node_dir, (local_ts, local_ts))
    assert check_remote.check_index_age() is True


def test_check_index_age_returns_false_when_local_meets_min(fake_dirs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "MIN_INDEX_DATE", "01.01.26")
    node_dir = Path(config.OS_NODE_DIR)
    node_dir.mkdir()
    local_ts = datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC).timestamp()
    os.utime(node_dir, (local_ts, local_ts))
    assert check_remote.check_index_age() is False
