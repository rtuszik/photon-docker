from src.jsonl.downloader import get_jsonl_url
from src.utils import config


def test_get_jsonl_url_uses_base_url():
    assert get_jsonl_url("germany") == f"{config.BASE_URL}/europe/germany/photon-dump-germany-master-latest.jsonl.zst"
