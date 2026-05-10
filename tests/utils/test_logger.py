import contextlib
import logging
from pathlib import Path

import pytest

from src.utils import config, logger


@contextlib.contextmanager
def _empty_root_handlers():
    root = logging.getLogger()
    saved = root.handlers[:]
    saved_level = root.level
    root.handlers = []
    try:
        yield root
    finally:
        root.handlers = saved
        root.level = saved_level


def test_setup_logging_attaches_console_and_file_handlers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "LOG_LEVEL", "DEBUG")

    with _empty_root_handlers() as root:
        logger.setup_logging()
        handler_types = {type(h).__name__ for h in root.handlers}
        assert "StreamHandler" in handler_types
        assert "RotatingFileHandler" in handler_types

    assert (tmp_path / "logs" / "photon.log").exists()


def test_setup_logging_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "LOG_LEVEL", "INFO")

    with _empty_root_handlers() as root:
        logger.setup_logging()
        first_count = len(root.handlers)
        logger.setup_logging()
        assert len(root.handlers) == first_count


def test_setup_logging_swallows_oserror_on_log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "LOG_LEVEL", "INFO")

    real_mkdir = Path.mkdir

    def fake_mkdir(self, *args, **kwargs):
        if self.name == "logs":
            raise PermissionError("nope")
        return real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)
    with _empty_root_handlers() as root:
        logger.setup_logging()
        handler_types = {type(h).__name__ for h in root.handlers}
        assert "StreamHandler" in handler_types
        assert "RotatingFileHandler" not in handler_types


def test_get_logger_returns_root_when_no_name():
    assert logger.get_logger() is logging.getLogger()


def test_get_logger_returns_named_logger():
    assert logger.get_logger("foo").name == "foo"
