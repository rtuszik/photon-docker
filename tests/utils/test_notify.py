from unittest.mock import MagicMock, patch

import pytest

from src.utils import config, notify


class _FakeApprise:
    def __init__(self, valid_count=1, notify_result=True):
        self._added = []
        self._valid_count = valid_count
        self._notify_result = notify_result
        self.notify = MagicMock(return_value=notify_result)

    def add(self, url):
        self._added.append(url)

    def __len__(self):
        return self._valid_count


def test_send_notification_skips_when_no_urls(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    import logging as _logging

    monkeypatch.setattr(config, "APPRISE_URLS", "")
    caplog.set_level(_logging.INFO, logger="root")
    with patch("src.utils.notify.apprise.Apprise") as factory:
        notify.send_notification("hello")
    factory.assert_not_called()
    assert any("skipping notification" in r.message for r in caplog.records)


def test_send_notification_sends_to_each_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "APPRISE_URLS", "tgram://abc, slack://xyz , ")
    fake = _FakeApprise(valid_count=2)
    with patch("src.utils.notify.apprise.Apprise", return_value=fake):
        notify.send_notification("hello", title="Title")

    assert fake._added == ["tgram://abc", "slack://xyz"]
    fake.notify.assert_called_once_with(body="hello", title="Title")


def test_send_notification_warns_when_all_invalid(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    import logging as _logging

    monkeypatch.setattr(config, "APPRISE_URLS", "garbage")
    fake = _FakeApprise(valid_count=0)
    caplog.set_level(_logging.WARNING, logger="root")
    with patch("src.utils.notify.apprise.Apprise", return_value=fake):
        notify.send_notification("hello")
    assert any("No valid Apprise URLs" in r.message for r in caplog.records)
    fake.notify.assert_not_called()


def test_send_notification_logs_error_when_apprise_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    import logging as _logging

    monkeypatch.setattr(config, "APPRISE_URLS", "tgram://abc")
    fake = _FakeApprise(valid_count=1, notify_result=False)
    caplog.set_level(_logging.ERROR, logger="root")
    with patch("src.utils.notify.apprise.Apprise", return_value=fake):
        notify.send_notification("hello")
    assert any("Failed to send notification" in r.message for r in caplog.records)
