REGION_MAPPING = {
    "planet": {"type": "planet", "continent": None, "db_available": True, "jsonl_available": True},
    "africa": {"type": "continent", "continent": "africa", "db_available": True, "jsonl_available": True},
    "asia": {"type": "continent", "continent": "asia", "db_available": True, "jsonl_available": True},
    "australia-oceania": {
        "type": "continent",
        "continent": "australia-oceania",
        "db_available": True,
        "jsonl_available": True,
    },
    "europe": {"type": "continent", "continent": "europe", "db_available": True, "jsonl_available": True},
    "north-america": {"type": "continent", "continent": "north-america", "db_available": True, "jsonl_available": True},
    "south-america": {"type": "continent", "continent": "south-america", "db_available": True, "jsonl_available": True},
    "india": {"type": "sub-region", "continent": "asia", "db_available": True, "jsonl_available": True},
    "japan": {"type": "sub-region", "continent": "asia", "db_available": True, "jsonl_available": True},
    "andorra": {"type": "sub-region", "continent": "europe", "db_available": True, "jsonl_available": True},
    "austria": {"type": "sub-region", "continent": "europe", "db_available": True, "jsonl_available": True},
    "denmark": {"type": "sub-region", "continent": "europe", "db_available": True, "jsonl_available": True},
    "france-monacco": {"type": "sub-region", "continent": "europe", "db_available": True, "jsonl_available": True},
    "germany": {"type": "sub-region", "continent": "europe", "db_available": True, "jsonl_available": True},
    "luxemburg": {"type": "sub-region", "continent": "europe", "db_available": True, "jsonl_available": True},
    "netherlands": {"type": "sub-region", "continent": "europe", "db_available": True, "jsonl_available": True},
    "russia": {"type": "sub-region", "continent": "europe", "db_available": True, "jsonl_available": True},
    "slovakia": {"type": "sub-region", "continent": "europe", "db_available": True, "jsonl_available": True},
    "spain": {"type": "sub-region", "continent": "europe", "db_available": True, "jsonl_available": True},
    "canada": {"type": "sub-region", "continent": "north-america", "db_available": True, "jsonl_available": True},
    "mexico": {"type": "sub-region", "continent": "north-america", "db_available": True, "jsonl_available": True},
    "usa": {"type": "sub-region", "continent": "north-america", "db_available": True, "jsonl_available": True},
    "argentina": {"type": "sub-region", "continent": "south-america", "db_available": True, "jsonl_available": True},
}

REGION_ALIASES = {
    "in": "india",
    "jp": "japan",
    "ad": "andorra",
    "at": "austria",
    "dk": "denmark",
    "fr": "france-monacco",
    "de": "germany",
    "lu": "luxemburg",
    "nl": "netherlands",
    "ru": "russia",
    "sk": "slovakia",
    "es": "spain",
    "ca": "canada",
    "mx": "mexico",
    "us": "usa",
    "ar": "argentina",
    "united states": "usa",
    "united states of america": "usa",
    "deutschland": "germany",
    "france": "france-monacco",
    "monaco": "france-monacco",
    "luxembourg": "luxemburg",
    "the netherlands": "netherlands",
    "holland": "netherlands",
    "espana": "spain",
    "españa": "spain",
}


def normalize_region(region: str) -> str | None:
    if not region:
        return None

    region_lower = region.lower().strip()

    if region_lower in REGION_MAPPING:
        return region_lower

    if region_lower in REGION_ALIASES:
        return REGION_ALIASES[region_lower]

    return None


def get_region_info(region: str) -> dict | None:
    normalized = normalize_region(region)
    return REGION_MAPPING.get(normalized) if normalized else None


def is_valid_region(region: str) -> bool:
    return get_region_info(region) is not None


def get_index_filename(region_name: str, db_version: str, extension: str) -> str:
    return f"photon-db-{region_name}-{db_version}-latest.{extension}"


def get_jsonl_filename(region_name: str, extension: str, channel: str = "master") -> str:
    return f"photon-dump-{region_name}-{channel}-latest.{extension}"


def get_index_url_path(region: str | None, db_version: str, extension: str) -> str:
    if region:
        normalized = normalize_region(region)
        if normalized is None:
            raise ValueError(f"Unknown region: {region}")

        region_info = get_region_info(region)
        if not region_info:
            raise ValueError(f"Unknown region: {region}")

        region_type = region_info["type"]
        filename = get_index_filename(normalized, db_version, extension)

        if region_type == "planet":
            return f"/{filename}"
        if region_type == "continent":
            return f"/{normalized}/{filename}"
        if region_type == "sub-region":
            continent = region_info["continent"]
            return f"/{continent}/{normalized}/{filename}"

        raise ValueError(f"Invalid region type: {region_type}")

    return f"/{get_index_filename('planet', db_version, extension)}"


def get_jsonl_url_path(region: str, extension: str) -> str:
    normalized = normalize_region(region)
    if normalized is None:
        raise ValueError(f"Unknown region: {region}")

    region_info = get_region_info(region)
    if not region_info:
        raise ValueError(f"Unknown region: {region}")

    if not region_info.get("jsonl_available", False):
        raise ValueError(f"JSONL not available for region: {region}")

    filename = get_jsonl_filename(normalized, extension)
    region_type = region_info["type"]

    if region_type == "planet":
        return f"/{filename}"
    if region_type == "continent":
        return f"/{normalized}/{filename}"
    if region_type == "sub-region":
        continent = region_info["continent"]
        return f"/{continent}/{normalized}/{filename}"

    raise ValueError(f"Invalid region type: {region_type}")


def get_regions_for_jsonl(regions: list[str]) -> list[str]:
    validated_regions = []

    for region in regions:
        region_info = get_region_info(region)
        if not region_info:
            raise ValueError(f"Unknown region: {region}")
        if not region_info.get("jsonl_available", False):
            raise ValueError(f"JSONL not available for region: {region}")
        validated_regions.append(normalize_region(region))

    return [region for region in validated_regions if region]
