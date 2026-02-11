REGION_MAPPING = {
    "planet": {
        "type": "planet",
        "continent": None,
        "available": True,
    },
    "africa": {
        "type": "continent",
        "continent": "africa",
        "available": True,
    },
    "asia": {
        "type": "continent",
        "continent": "asia",
        "available": True,
    },
    "australia-oceania": {
        "type": "continent",
        "continent": "australia-oceania",
        "available": True,
    },
    "europe": {
        "type": "continent",
        "continent": "europe",
        "available": True,
    },
    "north-america": {
        "type": "continent",
        "continent": "north-america",
        "available": True,
    },
    "south-america": {
        "type": "continent",
        "continent": "south-america",
        "available": True,
    },
    "india": {"type": "sub-region", "continent": "asia", "available": True},
    "japan": {"type": "sub-region", "continent": "asia", "available": True},
    "andorra": {"type": "sub-region", "continent": "europe", "available": True},
    "austria": {"type": "sub-region", "continent": "europe", "available": True},
    "denmark": {"type": "sub-region", "continent": "europe", "available": True},
    "france-monacco": {"type": "sub-region", "continent": "europe", "available": True},
    "germany": {"type": "sub-region", "continent": "europe", "available": True},
    "luxemburg": {"type": "sub-region", "continent": "europe", "available": True},
    "netherlands": {"type": "sub-region", "continent": "europe", "available": True},
    "russia": {"type": "sub-region", "continent": "europe", "available": True},
    "slovakia": {"type": "sub-region", "continent": "europe", "available": True},
    "spain": {"type": "sub-region", "continent": "europe", "available": True},
    "canada": {"type": "sub-region", "continent": "north-america", "available": True},
    "mexico": {"type": "sub-region", "continent": "north-america", "available": True},
    "usa": {"type": "sub-region", "continent": "north-america", "available": True},
    "argentina": {"type": "sub-region", "continent": "south-america", "available": True},
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
