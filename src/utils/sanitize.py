from urllib.parse import urlparse


def sanitize_url(url: str | None) -> str | None:
    if not url:
        return url
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        return parsed._replace(netloc=f"***@{parsed.hostname}{':%d' % parsed.port if parsed.port else ''}").geturl()
    return url
