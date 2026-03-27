"""BFS crawl queue with depth tracking and max page cap."""

import asyncio
from typing import Optional


class CrawlQueue:
    """
    Manages a BFS queue for crawling with depth tracking.
    Ensures URLs are only crawled once and respects max depth/page limits.
    """

    def __init__(self, max_depth: int = 3, max_pages: int = 50):
        self.max_depth = max_depth
        self.max_pages = max_pages
        self._queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
        self._visited: set[str] = set()
        self._visited_count = 0

    def add(self, url: str, depth: int) -> bool:
        """
        Add a URL to the queue if it hasn't been visited and is within limits.
        Returns True if added, False otherwise.
        """
        if url in self._visited:
            return False
        if depth > self.max_depth:
            return False
        if self._visited_count >= self.max_pages:
            return False

        self._visited.add(url)
        self._visited_count += 1
        self._queue.put_nowait((url, depth))
        return True

    async def get(self) -> Optional[tuple[str, int]]:
        """Get the next (url, depth) tuple, or None if queue is empty."""
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def empty(self) -> bool:
        """Check if the queue is empty."""
        return self._queue.empty()

    @property
    def visited_count(self) -> int:
        """Number of URLs that have been queued (visited or being visited)."""
        return self._visited_count

    @property
    def visited_urls(self) -> set[str]:
        """Set of all queued URLs."""
        return self._visited
