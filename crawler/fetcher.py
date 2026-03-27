"""Async HTTP client using httpx for fetching pages."""

import httpx
import warnings
import urllib3
from typing import Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PageFetcher:
    """
    Async HTTP client that fetches page HTML with follow_redirects enabled.
    Handles errors gracefully and returns None on failure.
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            verify=False,
            follow_redirects=True,
            timeout=self.timeout,
            headers={
                "User-Agent": "SiteMap3D/1.0 (Async Site Crawler)"
            }
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def fetch(self, url: str) -> Optional[httpx.Response]:
        """
        Fetch a URL and return the response, or None on failure.
        Handles connection errors, timeouts, HTTP errors gracefully.
        """
        if not self._client:
            raise RuntimeError("PageFetcher must be used as an async context manager")

        try:
            response = await self._client.get(url)
            response.raise_for_status()
            return response
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.ConnectError, Exception) as e:
            print(f"  [fetcher] Error fetching {url}: {e}")
            return None

    async def fetch_html(self, url: str) -> Optional[str]:
        """Fetch a URL and return the HTML text, or None on failure."""
        response = await self.fetch(url)
        if response:
            return response.text
        return None

    async def fetch_final_url(self, url: str) -> str:
        """
        Fetch a URL and return the final URL after redirects.
        Returns the original URL if fetch fails.
        """
        if not self._client:
            raise RuntimeError("PageFetcher must be used as an async context manager")

        try:
            response = await self._client.head(url)
            return str(response.url)
        except Exception:
            return url
