import pytest

from src.utils.regions import get_index_url_path, get_region_info, is_valid_region, normalize_region


@pytest.mark.parametrize(
    ("region", "expected"),
    [
        ("planet", "planet"),
        (" Europe ", "europe"),
        ("mx", "mexico"),
        ("United States", "usa"),
        ("deutschland", "germany"),
        ("españa", "spain"),
        ("unknown", None),
        ("", None),
    ],
)
def test_normalize_region(region: str, expected: str | None):
    assert normalize_region(region) == expected


@pytest.mark.parametrize(
    ("region", "expected"), [("asia", True), ("mx", True), ("monaco", True), ("invalid-region", False)]
)
def test_is_valid_region(region: str, expected: bool):
    assert is_valid_region(region) is expected


def test_get_region_info_for_alias_returns_canonical_region_metadata():
    assert get_region_info("us") == {"type": "sub-region", "continent": "north-america", "available": True}


@pytest.mark.parametrize(
    ("region", "expected"),
    [
        (None, "/photon-db-planet-1.0-latest.tar.bz2"),
        ("planet", "/photon-db-planet-1.0-latest.tar.bz2"),
        ("europe", "/europe/photon-db-europe-1.0-latest.tar.bz2"),
        ("us", "/north-america/usa/photon-db-usa-1.0-latest.tar.bz2"),
        ("United States", "/north-america/usa/photon-db-usa-1.0-latest.tar.bz2"),
    ],
)
def test_get_index_url_path(region: str | None, expected: str):
    assert get_index_url_path(region, "1.0", "tar.bz2") == expected


def test_get_index_url_path_raises_for_unknown_region():
    with pytest.raises(ValueError, match="Unknown region: atlantis"):
        get_index_url_path("atlantis", "1.0", "tar.bz2")
