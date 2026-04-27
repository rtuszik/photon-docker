import pytest

from src.utils.regions import (
    get_country_codes_for_regions,
    get_index_url_path,
    get_jsonl_parent_region,
    get_jsonl_url_path,
    get_region_info,
    get_regions_for_jsonl,
    is_valid_region,
    normalize_region,
)


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
    assert get_region_info("us") == {
        "type": "sub-region",
        "continent": "north-america",
        "db_available": True,
        "jsonl_available": True,
        "country_codes": ["US"],
    }


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


@pytest.mark.parametrize(
    ("region", "expected"),
    [
        ("planet", "/photon-dump-planet-master-latest.jsonl.zst"),
        ("europe", "/europe/photon-dump-europe-master-latest.jsonl.zst"),
        ("us", "/north-america/usa/photon-dump-usa-master-latest.jsonl.zst"),
    ],
)
def test_get_jsonl_url_path(region: str, expected: str):
    assert get_jsonl_url_path(region, "jsonl.zst") == expected


def test_get_regions_for_jsonl_normalizes_aliases():
    assert get_regions_for_jsonl(["DE"]) == ["germany"]


def test_get_regions_for_jsonl_deduplicates():
    result = get_regions_for_jsonl(["de", "germany", "DE"])
    assert result == ["germany"]


def test_get_regions_for_jsonl_multiple_regions():
    result = get_regions_for_jsonl(["andorra", "luxemburg"])
    assert result == ["andorra", "luxemburg"]


def test_get_regions_for_jsonl_rejects_unknown():
    with pytest.raises(ValueError, match="Unknown region"):
        get_regions_for_jsonl(["germany", "atlantis"])


def test_get_country_codes_for_regions_single():
    assert get_country_codes_for_regions(["andorra"]) == ["AD"]


def test_get_country_codes_for_regions_multiple_deduplicates():
    codes = get_country_codes_for_regions(["andorra", "luxemburg"])
    assert codes == ["AD", "LU"]


def test_get_country_codes_for_regions_overlapping():
    codes = get_country_codes_for_regions(["france-monacco", "monaco"])
    assert "FR" in codes
    assert "MC" in codes
    assert codes.count("FR") == 1
    assert codes.count("MC") == 1


def test_get_jsonl_parent_region_single():
    assert get_jsonl_parent_region(["andorra"]) == "andorra"


def test_get_jsonl_parent_region_same_continent():
    assert get_jsonl_parent_region(["andorra", "luxemburg"]) == "europe"


def test_get_jsonl_parent_region_across_continents():
    assert get_jsonl_parent_region(["germany", "japan"]) == "planet"


def test_get_jsonl_parent_region_with_planet():
    assert get_jsonl_parent_region(["planet", "germany"]) == "planet"


def test_get_jsonl_parent_region_rejects_empty():
    with pytest.raises(ValueError, match="At least one region"):
        get_jsonl_parent_region([])
