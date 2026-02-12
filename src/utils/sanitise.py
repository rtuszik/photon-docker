from urllib.parse import urlparse, urlunparse


def sanitise_url(url):
    """
    Strip credentials, query parameters, and fragments from a URL.

    Returns a clean URL containing only the scheme, hostname, port, and path.

    If passed an empty or None URL, returns it unchanged.
    """
    if not url:
        return url


    parsed = urlparse(url)

    if not parsed.scheme or not parsed.netloc:
        # Do not report the original invalid URL as may be sensitive.
        raise ValueError("Invalid URL")

    # Get clean netloc (hostname + port, no credentials)
    clean_netloc = parsed.hostname
    if parsed.port:
        clean_netloc = f"{clean_netloc}:{parsed.port}"

    # Use _replace for explicit, named parameters
    sanitised = parsed._replace(
        netloc=clean_netloc,
        query='',
        fragment=''
    )

    return urlunparse(sanitised)
