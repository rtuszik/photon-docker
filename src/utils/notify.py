# notification module for apprise notifications

import apprise

from . import config
from .logger import get_logger

logging = get_logger()


def send_notification(message: str, title: str = "Photon Status"):
    apprise_urls = config.APPRISE_URLS
    if not apprise_urls:
        logging.info("No APPRISE_URLS set, skipping notification.")
        return

    apobj = apprise.Apprise()

    for url in apprise_urls.split(","):
        if url.strip():
            apobj.add(url.strip())

    if not apobj.servers:
        logging.warning(
            "No valid Apprise URLs were found after processing the APPRISE_URLS variable."
        )
        return

    if not apobj.notify(body=message, title=title):
        logging.error("Failed to send notification to one or more Apprise targets.")
    else:
        logging.info("Successfully sent notification.")
