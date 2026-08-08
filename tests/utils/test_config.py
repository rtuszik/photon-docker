import pytest

from src.utils import config


@pytest.mark.parametrize(
    ("interval", "expected"),
    [("30d", 30 * 86400), ("12h", 12 * 3600), ("30m", 30 * 60), ("720H", 720 * 3600), (" 7d ", 7 * 86400)],
)
def test_parse_interval_returns_seconds(interval: str, expected: int):
    assert config.parse_interval(interval) == expected


@pytest.mark.parametrize("interval", ["garbage", "", "d", "30", "30s", "-1d", "1.5d"])
def test_parse_interval_falls_back_to_one_day_without_raising(interval: str):
    assert config.parse_interval(interval) == 86400
