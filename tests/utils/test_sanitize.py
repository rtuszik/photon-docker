import pytest

from src.utils.sanitize import sanitize_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (None, None),
        ("", ""),
        ("https://example.com/data.tar.bz2", "https://example.com/data.tar.bz2"),
        ("https://user@example.com/data.tar.bz2", "https://***@example.com/data.tar.bz2"),
        ("https://user:secret@example.com/data.tar.bz2", "https://***@example.com/data.tar.bz2"),
        ("https://user:secret@example.com:8443/data.tar.bz2", "https://***@example.com:8443/data.tar.bz2"),
    ],
)
def test_sanitize_url(url: str | None, expected: str | None):
    assert sanitize_url(url) == expected
