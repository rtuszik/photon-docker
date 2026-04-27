PLANET_COUNTRY_CODES = [
    "DZ",
    "EG",
    "EH",
    "LY",
    "MA",
    "SD",
    "TN",
    "BJ",
    "BF",
    "CV",
    "GH",
    "GN",
    "GW",
    "CI",
    "LR",
    "ML",
    "MR",
    "NE",
    "SN",
    "GM",
    "SL",
    "TG",
    "NG",
    "AO",
    "CM",
    "CF",
    "TD",
    "CG",
    "CD",
    "GQ",
    "GA",
    "ST",
    "BI",
    "KE",
    "MW",
    "MZ",
    "RW",
    "TZ",
    "UG",
    "SS",
    "ZM",
    "ZW",
    "ER",
    "ET",
    "DJ",
    "SO",
    "MG",
    "MU",
    "SC",
    "KM",
    "BW",
    "LS",
    "NA",
    "ZA",
    "SZ",
    "SH",
    "KZ",
    "KG",
    "TJ",
    "TM",
    "UZ",
    "BH",
    "KW",
    "OM",
    "QA",
    "SA",
    "AE",
    "YE",
    "MV",
    "LK",
    "IO",
    "AM",
    "AZ",
    "IR",
    "IQ",
    "IL",
    "JO",
    "LB",
    "PS",
    "SY",
    "AF",
    "BD",
    "BT",
    "NP",
    "PK",
    "CN",
    "MN",
    "KP",
    "KR",
    "TW",
    "BN",
    "KH",
    "ID",
    "LA",
    "MY",
    "MM",
    "PH",
    "SG",
    "TH",
    "TL",
    "VN",
    "IN",
    "JP",
    "AU",
    "NZ",
    "CK",
    "FJ",
    "KI",
    "MH",
    "FM",
    "NR",
    "NU",
    "PW",
    "PG",
    "PN",
    "WS",
    "SB",
    "TK",
    "TO",
    "TV",
    "VU",
    "AL",
    "BY",
    "BE",
    "BA",
    "BG",
    "HR",
    "CY",
    "CZ",
    "EE",
    "LT",
    "LV",
    "GB",
    "IM",
    "GG",
    "JE",
    "IS",
    "FO",
    "IE",
    "FI",
    "GE",
    "GR",
    "HU",
    "IT",
    "VA",
    "SM",
    "XK",
    "CH",
    "LI",
    "MK",
    "MT",
    "MD",
    "ME",
    "NO",
    "PL",
    "PT",
    "RO",
    "RS",
    "SI",
    "SE",
    "TR",
    "UA",
    "AD",
    "AT",
    "DK",
    "ES",
    "GI",
    "FR",
    "MC",
    "DE",
    "LU",
    "NL",
    "RU",
    "SK",
    "BZ",
    "CR",
    "SV",
    "GT",
    "HN",
    "NI",
    "PA",
    "BS",
    "CU",
    "HT",
    "DO",
    "JM",
    "AG",
    "AI",
    "BB",
    "DM",
    "GD",
    "KN",
    "KY",
    "LC",
    "MS",
    "TC",
    "TT",
    "VC",
    "VG",
    "GL",
    "BM",
    "CA",
    "US",
    "MX",
    "CL",
    "BR",
    "BO",
    "CO",
    "EC",
    "PY",
    "PE",
    "UY",
    "GY",
    "VE",
    "SR",
    "FK",
    "GS",
    "AR",
]

AFRICA_COUNTRY_CODES = PLANET_COUNTRY_CODES[:56]
ASIA_COUNTRY_CODES = PLANET_COUNTRY_CODES[56:104]
AUSTRALIA_OCEANIA_COUNTRY_CODES = PLANET_COUNTRY_CODES[104:122]
EUROPE_COUNTRY_CODES = PLANET_COUNTRY_CODES[122:176]
NORTH_AMERICA_COUNTRY_CODES = PLANET_COUNTRY_CODES[176:207]
SOUTH_AMERICA_COUNTRY_CODES = PLANET_COUNTRY_CODES[207:220]


def _region(region_type: str, continent: str | None, db_available: bool, country_codes: list[str]) -> dict:
    return {
        "type": region_type,
        "continent": continent,
        "db_available": db_available,
        "jsonl_available": True,
        "country_codes": country_codes,
    }


REGION_MAPPING = {
    "planet": _region("planet", None, True, PLANET_COUNTRY_CODES),
    "africa": _region("continent", "africa", True, AFRICA_COUNTRY_CODES),
    "asia": _region("continent", "asia", True, ASIA_COUNTRY_CODES),
    "australia-oceania": _region("continent", "australia-oceania", True, AUSTRALIA_OCEANIA_COUNTRY_CODES),
    "europe": _region("continent", "europe", True, EUROPE_COUNTRY_CODES),
    "north-america": _region("continent", "north-america", True, NORTH_AMERICA_COUNTRY_CODES),
    "south-america": _region("continent", "south-america", True, SOUTH_AMERICA_COUNTRY_CODES),
    "india": _region("sub-region", "asia", True, ["IN"]),
    "japan": _region("sub-region", "asia", True, ["JP"]),
    "andorra": _region("sub-region", "europe", True, ["AD"]),
    "austria": _region("sub-region", "europe", True, ["AT"]),
    "albania": _region("sub-region", "europe", False, ["AL"]),
    "baltics": _region("sub-region", "europe", False, ["EE", "LT", "LV"]),
    "belarus": _region("sub-region", "europe", False, ["BY"]),
    "belgium": _region("sub-region", "europe", False, ["BE"]),
    "bosnia-herzegovina": _region("sub-region", "europe", False, ["BA"]),
    "british-islands": _region("sub-region", "europe", False, ["GB", "IM", "GG", "JE"]),
    "bulgaria": _region("sub-region", "europe", False, ["BG"]),
    "croatia": _region("sub-region", "europe", False, ["HR"]),
    "cyprus": _region("sub-region", "europe", False, ["CY"]),
    "czech-republic": _region("sub-region", "europe", False, ["CZ"]),
    "denmark": _region("sub-region", "europe", True, ["DK"]),
    "finland": _region("sub-region", "europe", False, ["FI"]),
    "france-monacco": _region("sub-region", "europe", True, ["FR", "MC"]),
    "georgia": _region("sub-region", "europe", False, ["GE"]),
    "germany": _region("sub-region", "europe", True, ["DE"]),
    "greece": _region("sub-region", "europe", False, ["GR"]),
    "hungary": _region("sub-region", "europe", False, ["HU"]),
    "iceland-faroe": _region("sub-region", "europe", False, ["IS", "FO"]),
    "ireland": _region("sub-region", "europe", False, ["IE"]),
    "italy": _region("sub-region", "europe", False, ["IT", "VA", "SM"]),
    "kosovo": _region("sub-region", "europe", False, ["XK"]),
    "luxemburg": _region("sub-region", "europe", True, ["LU"]),
    "macedonia": _region("sub-region", "europe", False, ["MK"]),
    "malta": _region("sub-region", "europe", False, ["MT"]),
    "moldova": _region("sub-region", "europe", False, ["MD"]),
    "montenegro": _region("sub-region", "europe", False, ["ME"]),
    "netherlands": _region("sub-region", "europe", True, ["NL"]),
    "norway": _region("sub-region", "europe", False, ["NO"]),
    "poland": _region("sub-region", "europe", False, ["PL"]),
    "portugal": _region("sub-region", "europe", False, ["PT"]),
    "romania": _region("sub-region", "europe", False, ["RO"]),
    "russia": _region("sub-region", "europe", True, ["RU"]),
    "serbia": _region("sub-region", "europe", False, ["RS"]),
    "slovakia": _region("sub-region", "europe", True, ["SK"]),
    "slovenia": _region("sub-region", "europe", False, ["SI"]),
    "spain": _region("sub-region", "europe", True, ["ES", "GI"]),
    "sweden": _region("sub-region", "europe", False, ["SE"]),
    "switzerland-liechtenstein": _region("sub-region", "europe", False, ["CH", "LI"]),
    "turkey": _region("sub-region", "europe", False, ["TR"]),
    "ukraine": _region("sub-region", "europe", False, ["UA"]),
    "canada": _region("sub-region", "north-america", True, ["CA"]),
    "mexico": _region("sub-region", "north-america", True, ["MX"]),
    "usa": _region("sub-region", "north-america", True, ["US"]),
    "argentina": _region("sub-region", "south-america", True, ["AR"]),
}

REGION_ALIASES = {
    "in": "india",
    "jp": "japan",
    "ad": "andorra",
    "at": "austria",
    "al": "albania",
    "by": "belarus",
    "be": "belgium",
    "ba": "bosnia-herzegovina",
    "bg": "bulgaria",
    "hr": "croatia",
    "cy": "cyprus",
    "cz": "czech-republic",
    "dk": "denmark",
    "fi": "finland",
    "fr": "france-monacco",
    "de": "germany",
    "gr": "greece",
    "hu": "hungary",
    "is": "iceland-faroe",
    "ie": "ireland",
    "it": "italy",
    "xk": "kosovo",
    "lu": "luxemburg",
    "mk": "macedonia",
    "mt": "malta",
    "md": "moldova",
    "me": "montenegro",
    "nl": "netherlands",
    "no": "norway",
    "pl": "poland",
    "pt": "portugal",
    "ro": "romania",
    "ru": "russia",
    "rs": "serbia",
    "sk": "slovakia",
    "si": "slovenia",
    "es": "spain",
    "se": "sweden",
    "ch": "switzerland-liechtenstein",
    "tr": "turkey",
    "ua": "ukraine",
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
    "czechia": "czech-republic",
    "uk": "british-islands",
    "great britain": "british-islands",
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

        normalized_region = normalize_region(region)
        if normalized_region and normalized_region not in validated_regions:
            validated_regions.append(normalized_region)

    return validated_regions


def get_country_codes_for_regions(regions: list[str]) -> list[str]:
    country_codes: list[str] = []

    for region in get_regions_for_jsonl(regions):
        region_info = get_region_info(region)
        if not region_info:
            raise ValueError(f"Unknown region: {region}")

        for country_code in region_info["country_codes"]:
            if country_code not in country_codes:
                country_codes.append(country_code)

    return country_codes


def get_jsonl_parent_region(regions: list[str]) -> str:
    normalized_regions = get_regions_for_jsonl(regions)
    if not normalized_regions:
        raise ValueError("At least one region is required")
    if len(normalized_regions) == 1:
        return normalized_regions[0]

    if "planet" in normalized_regions:
        return "planet"

    continents = {
        REGION_MAPPING[region]["continent"]
        for region in normalized_regions
        if REGION_MAPPING[region]["type"] in {"continent", "sub-region"}
    }

    if len(continents) == 1:
        return continents.pop()

    return "planet"
