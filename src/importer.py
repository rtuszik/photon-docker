import os
import shlex
import subprocess

from src.filesystem import clear_temp_dir
from src.jsonl.decompressor import stream_decompress
from src.jsonl.downloader import download_jsonl
from src.utils import config
from src.utils.logger import get_logger
from src.utils.regions import get_regions_for_jsonl

logger = get_logger(__name__)


def run_jsonl_import() -> None:
    regions = get_regions_for_jsonl(config.get_jsonl_regions())
    if len(regions) != 1:
        raise ValueError("JSONL mode currently supports exactly one region.")

    region = regions[0]

    try:
        jsonl_path = download_jsonl(region)
        import_proc = _start_photon_import("-")
        try:
            if import_proc.stdin is None:
                raise RuntimeError("Photon import process stdin is unavailable")
            for chunk in stream_decompress(jsonl_path):
                import_proc.stdin.write(chunk)

            import_proc.stdin.close()
            return_code = import_proc.wait()
            if return_code != 0:
                raise RuntimeError(f"Photon JSONL import failed with exit code {return_code}")
        except Exception:
            import_proc.kill()
            import_proc.wait()
            raise
    finally:
        clear_temp_dir()


def _start_photon_import(input_source: str) -> subprocess.Popen:
    os.makedirs(config.DATA_DIR, exist_ok=True)

    cmd = ["java"]
    if config.JAVA_PARAMS:
        cmd.extend(shlex.split(config.JAVA_PARAMS))

    cmd.extend(["-jar", "/photon/photon.jar", "import", "-import-file", input_source, "-data-dir", config.DATA_DIR])

    languages = config.get_languages()
    if languages:
        cmd.extend(["-languages", ",".join(languages)])

    extra_tags = config.get_extra_tags()
    if extra_tags:
        cmd.extend(["-extra-tags", ",".join(extra_tags)])

    if config.IMPORT_GEOMETRIES:
        cmd.append("-full-geometries")

    logger.info(f"Starting Photon JSONL import for region(s): {', '.join(config.get_jsonl_regions())}")
    return subprocess.Popen(cmd, cwd=config.PHOTON_DIR, stdin=subprocess.PIPE)  # noqa: S603
