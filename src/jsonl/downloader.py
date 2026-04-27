import os

from src.downloader import download_file
from src.utils import config
from src.utils.logger import get_logger
from src.utils.regions import get_jsonl_filename, get_region_info, normalize_region

logger = get_logger(__name__)


def get_jsonl_url(region: str) -> str:
    normalized_region = normalize_region(region)
    if normalized_region is None:
        raise ValueError(f"Unknown region: {region}")

    region_info = get_region_info(normalized_region)
    if not region_info:
        raise ValueError(f"Unknown region: {region}")

    filename = get_jsonl_filename(normalized_region, config.JSONL_FILE_EXTENSION, config.JSONL_RELEASE_CHANNEL)

    if region_info["type"] == "planet":
        return f"{config.BASE_URL}/{filename}"
    if region_info["type"] == "continent":
        return f"{config.BASE_URL}/{normalized_region}/{filename}"

    continent = region_info["continent"]
    return f"{config.BASE_URL}/{continent}/{normalized_region}/{filename}"


def download_jsonl(region: str) -> str:
    os.makedirs(config.TEMP_DIR, exist_ok=True)

    normalized_region = normalize_region(region)
    if normalized_region is None:
        raise ValueError(f"Unknown region: {region}")

    download_url = get_jsonl_url(normalized_region)
    output_path = os.path.join(config.TEMP_DIR, f"{normalized_region}.{config.JSONL_FILE_EXTENSION}")

    logger.info(f"Downloading JSONL dump for {normalized_region} from {download_url}")

    if not download_file(download_url, output_path):
        raise RuntimeError(f"Failed to download JSONL dump from {download_url}")

    return output_path
