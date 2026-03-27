"""URL normalization and deduplication logic."""

from urllib.parse import urlsplit, urlunsplit, urljoin, urlparse


def normalize_url(url: str) -> str:
    """
    Normalize a URL for deduplication:
    - lowercase scheme and host
    - strip trailing slash (except for root)
    - remove default port (80 for http, 443 for https)
    - strip fragment
    """
    parsed = urlsplit(url)

    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower() if parsed.hostname else ""

    # Remove default ports
    port = parsed.port
    if port is not None:
        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
            port = None

    # Build netloc
    if port:
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    # Strip trailing slash (but keep root as "/")
    path = parsed.path
    if path and path != "/":
        path = path.rstrip("/")
    if not path:
        path = "/"

    # Rebuild URL (no fragment, no query for dedup purposes)
    normalized = urlunsplit((scheme, netloc, path, "", ""))
    return normalized


def resolve_url(base_url: str, relative_url: str) -> str:
    """Resolve a relative URL against a base URL."""
    return urljoin(base_url, relative_url)


def is_same_domain(url: str, base_url: str) -> bool:
    """Check if a URL belongs to the same domain as the base URL."""
    parsed_url = urlparse(url)
    parsed_base = urlparse(base_url)

    url_host = parsed_url.hostname.lower() if parsed_url.hostname else ""
    base_host = parsed_base.hostname.lower() if parsed_base.hostname else ""

    return url_host == base_host
