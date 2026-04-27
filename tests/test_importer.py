import io

import pytest

from src import importer
from src.utils import config


def _noop_makedirs(path: str, exist_ok: bool = False) -> None:
    _ = (path, exist_ok)


def test_start_photon_import_builds_expected_command(monkeypatch):
    commands = []

    class DummyProcess:
        def __init__(self):
            self.stdin = io.BytesIO()

    def fake_popen(cmd, cwd, stdin):
        commands.append({"cmd": cmd, "cwd": cwd, "stdin": stdin})
        return DummyProcess()

    monkeypatch.setattr(config, "JAVA_PARAMS", "-Xmx2g")
    monkeypatch.setattr(config, "LANGUAGES", "en,de")
    monkeypatch.setattr(config, "EXTRA_TAGS", "website,phone")
    monkeypatch.setattr(config, "IMPORT_GEOMETRIES", True)
    monkeypatch.setattr(importer.os, "makedirs", _noop_makedirs)
    monkeypatch.setattr(importer.subprocess, "Popen", fake_popen)

    importer._start_photon_import("-")

    assert commands == [
        {
            "cmd": [
                "java",
                "-Xmx2g",
                "-jar",
                "/photon/photon.jar",
                "import",
                "-import-file",
                "-",
                "-data-dir",
                config.DATA_DIR,
                "-languages",
                "en,de",
                "-extra-tags",
                "website,phone",
                "-full-geometries",
            ],
            "cwd": config.PHOTON_DIR,
            "stdin": importer.subprocess.PIPE,
        }
    ]


def test_start_photon_import_includes_country_codes(monkeypatch):
    commands = []

    class DummyProcess:
        def __init__(self):
            self.stdin = io.BytesIO()

    def fake_popen(cmd, cwd, stdin):
        commands.append({"cmd": cmd, "cwd": cwd, "stdin": stdin})
        return DummyProcess()

    monkeypatch.setattr(config, "JAVA_PARAMS", "-Xmx2g")
    monkeypatch.setattr(config, "LANGUAGES", None)
    monkeypatch.setattr(config, "EXTRA_TAGS", None)
    monkeypatch.setattr(config, "IMPORT_GEOMETRIES", False)
    monkeypatch.setattr(importer.os, "makedirs", _noop_makedirs)
    monkeypatch.setattr(importer.subprocess, "Popen", fake_popen)

    importer._start_photon_import("-", country_codes=["AD", "LU"])

    assert commands[0]["cmd"] == [
        "java",
        "-Xmx2g",
        "-jar",
        "/photon/photon.jar",
        "import",
        "-import-file",
        "-",
        "-data-dir",
        config.DATA_DIR,
        "-country-codes",
        "AD,LU",
    ]


def test_run_jsonl_import_uses_parent_region_and_country_codes_for_multi_region(monkeypatch):
    process = RecordingProcess()
    download_args = []

    def fake_download(region):
        download_args.append(region)
        return "/photon/data/temp/europe.jsonl.zst"

    monkeypatch.setattr(config, "REGION", "andorra,luxemburg")
    monkeypatch.setattr(importer, "download_jsonl", fake_download)
    monkeypatch.setattr(importer, "stream_decompress", lambda path: [b'{"type":"Place"}\n'])
    monkeypatch.setattr(importer, "_start_photon_import", lambda input_source, country_codes=None: process)
    monkeypatch.setattr(importer, "clear_temp_dir", lambda: None)

    importer.run_jsonl_import()

    assert download_args == ["europe"]


def test_run_jsonl_import_uses_single_region_without_country_codes(monkeypatch):
    process = RecordingProcess()
    import_args = []

    def fake_start_import(input_source, country_codes=None):
        import_args.append({"input_source": input_source, "country_codes": country_codes})
        return process

    monkeypatch.setattr(config, "REGION", "andorra")
    monkeypatch.setattr(importer, "download_jsonl", lambda region: "/photon/data/temp/andorra.jsonl.zst")
    monkeypatch.setattr(importer, "stream_decompress", lambda path: [b'{"type":"Place"}\n'])
    monkeypatch.setattr(importer, "_start_photon_import", fake_start_import)
    monkeypatch.setattr(importer, "clear_temp_dir", lambda: None)

    importer.run_jsonl_import()

    assert import_args[0]["country_codes"] is None


class RecordingProcess:
    def __init__(self, wait_return_code: int = 0):
        self.stdin = RecordingStdin()
        self.wait_calls = 0
        self.kill_calls = 0
        self.wait_return_code = wait_return_code

    def wait(self):
        self.wait_calls += 1
        return self.wait_return_code

    def kill(self):
        self.kill_calls += 1


class RecordingStdin(io.BytesIO):
    def close(self):
        self.was_closed = True


def test_run_jsonl_import_streams_data_and_cleans_up(monkeypatch):
    process = RecordingProcess()
    cleanup_calls = []
    fake_path = "/photon/data/temp/andorra.jsonl.zst"

    monkeypatch.setattr(config, "REGION", "andorra")
    monkeypatch.setattr(importer, "download_jsonl", lambda region: fake_path)
    monkeypatch.setattr(importer, "stream_decompress", lambda path: [b'{"type":"Place"}\n', b'{"type":"Place2"}\n'])
    monkeypatch.setattr(importer, "_start_photon_import", lambda input_source, country_codes=None: process)
    monkeypatch.setattr(importer, "clear_temp_dir", lambda: cleanup_calls.append(True))

    importer.run_jsonl_import()

    assert process.stdin.getvalue() == b'{"type":"Place"}\n{"type":"Place2"}\n'
    assert process.wait_calls == 1
    assert process.kill_calls == 0
    assert cleanup_calls == [True]


def test_run_jsonl_import_kills_process_and_cleans_up_on_stream_failure(monkeypatch):
    process = RecordingProcess()
    cleanup_calls = []
    fake_path = "/photon/data/temp/andorra.jsonl.zst"

    def broken_stream(path):
        yield b'{"type":"Place"}\n'
        raise RuntimeError("boom")

    monkeypatch.setattr(config, "REGION", "andorra")
    monkeypatch.setattr(importer, "download_jsonl", lambda region: fake_path)
    monkeypatch.setattr(importer, "stream_decompress", broken_stream)
    monkeypatch.setattr(importer, "_start_photon_import", lambda input_source, country_codes=None: process)
    monkeypatch.setattr(importer, "clear_temp_dir", lambda: cleanup_calls.append(True))

    with pytest.raises(RuntimeError, match="boom"):
        importer.run_jsonl_import()

    assert process.kill_calls == 1
    assert process.wait_calls == 1
    assert cleanup_calls == [True]


def test_run_jsonl_import_raises_when_import_process_fails(monkeypatch):
    process = RecordingProcess(wait_return_code=2)
    cleanup_calls = []
    fake_path = "/photon/data/temp/andorra.jsonl.zst"

    monkeypatch.setattr(config, "REGION", "andorra")
    monkeypatch.setattr(importer, "download_jsonl", lambda region: fake_path)
    monkeypatch.setattr(importer, "stream_decompress", lambda path: [b'{"type":"Place"}\n'])
    monkeypatch.setattr(importer, "_start_photon_import", lambda input_source, country_codes=None: process)
    monkeypatch.setattr(importer, "clear_temp_dir", lambda: cleanup_calls.append(True))

    with pytest.raises(RuntimeError, match="exit code 2"):
        importer.run_jsonl_import()

    assert process.kill_calls == 1
    assert process.wait_calls == 2
    assert cleanup_calls == [True]
