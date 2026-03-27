"""HTML parser for extracting internal links from pages."""

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from core.url_normalizer import normalize_url, resolve_url, is_same_domain


class LinkParser:
    """
    Parses HTML and extracts internal links (same domain as base URL).
    Returns normalized, deduplicated link set.
    """

    def __init__(self, base_url: str):
        """
        Args:
            base_url: The starting URL to determine the domain scope.
        """
        self.base_url = base_url
        self._base_host = urlparse(base_url).hostname

    def extract_links(self, html: str, page_url: str) -> list[str]:
        """
        Extract all internal links from the given HTML content.
        
        Args:
            html: The HTML content to parse.
            page_url: The URL of the page being parsed (for resolving relative links).
        
        Returns:
            List of normalized, same-domain URLs found in the page.
        """
        soup = BeautifulSoup(html, "html.parser")
        links = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()

            # Skip empty, javascript, mailto, tel, and fragment-only links
            if not href:
                continue
            if href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue

            # Resolve relative URL
            absolute_url = resolve_url(page_url, href)

            # Only include same-domain links
            if not is_same_domain(absolute_url, self.base_url):
                continue

            # Normalize for dedup
            normalized = normalize_url(absolute_url)
            links.add(normalized)

        return sorted(links)

    def get_outbound_link_count(self, html: str, page_url: str) -> int:
        """
        Count the number of outbound (same-domain) links on a page.
        """
        return len(self.extract_links(html, page_url))

    def get_title(self, html: str) -> str:
        """
        Extract the page title from HTML.
        Falls back to 'Untitled' if no <title> tag found.
        """
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        return "Untitled"
