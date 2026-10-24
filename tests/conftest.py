from pathlib import Path

import pytest

from src.utils import config


@pytest.fixture(autouse=True)
def fake_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "data"
    photon_data_dir = data_dir / "photon_data"
    temp_dir = data_dir / "temp"
    os_node_dir = photon_data_dir / "node_1"
    data_dir.mkdir()

    monkeypatch.setattr(config, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(config, "PHOTON_DATA_DIR", str(photon_data_dir))
    monkeypatch.setattr(config, "TEMP_DIR", str(temp_dir))
    monkeypatch.setattr(config, "OS_NODE_DIR", str(os_node_dir))
    return data_dir
