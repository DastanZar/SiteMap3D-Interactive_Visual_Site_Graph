#!/usr/bin/env python3
"""
SiteMap3D - Interactive Visual Site Graph

Crawls a website and generates an interactive force-directed graph
with embedded screenshots in a single self-contained HTML file.

Usage:
    python main.py --url https://example.com --depth 2 --output ./sitemap3d.html
"""

import argparse
import asyncio
import sys
import time

from core.url_normalizer import normalize_url
from core.queue import CrawlQueue
from crawler.fetcher import PageFetcher
from crawler.parser import LinkParser
from crawler.screenshot import ScreenshotCapture
from graph.builder import GraphBuilder
from graph.html_generator import generate_html


async def crawl(start_url: str, max_depth: int = 2, max_pages: int = 50,
                output_path: str = "./sitemap3d.html"):
    """
    Main crawl orchestration.
    
    1. BFS crawl pages up to max_depth, following internal links.
    2. Capture screenshots of each page concurrently (limited to 5).
    3. Build a PyVis graph with nodes colored by depth and sized by link count.
    4. Generate a self-contained HTML file with embedded screenshots.
    """
    # Normalize start URL
    start_url = normalize_url(start_url)

    print(f"SiteMap3D - Starting crawl")
    print(f"  URL:    {start_url}")
    print(f"  Depth:  {max_depth}")
    print(f"  Max pages: {max_pages}")
    print(f"  Output: {output_path}")
    print()

    # Initialize components
    queue = CrawlQueue(max_depth=max_depth, max_pages=max_pages)
    queue.add(start_url, depth=0)

    graph = GraphBuilder()

    # Crawl pages: fetch HTML and parse links
    print("[Phase 1] Crawling pages...")
    pages: dict[str, dict] = {}  # url -> {html, title, depth, outbound_count}

    async with PageFetcher() as fetcher:
        while not queue.empty():
            item = await queue.get()
            if item is None:
                break

            url, depth = item
            print(f"  [{queue.visited_count}/{max_pages}] Depth {depth}: {url}")

            # Fetch the page
            html = await fetcher.fetch_html(url)

            if html is None:
                # Failed fetch - add as red node
                pages[url] = {
                    "html": None,
                    "title": "Failed to load",
                    "depth": depth,
                    "outbound_count": 0,
                    "failed": True,
                }
                continue

            # Parse links and title
            parser = LinkParser(start_url)
            links = parser.extract_links(html, url)
            title = parser.get_title(html)

            pages[url] = {
                "html": html,
                "title": title,
                "depth": depth,
                "outbound_count": len(links),
                "failed": False,
            }

            # Add discovered links to queue
            for link in links:
                queue.add(link, depth + 1)

    print(f"\n  Crawled {len(pages)} pages.")
    print()

    # Capture screenshots
    print("[Phase 2] Capturing screenshots...")
    screenshots: dict[str, str] = {}

    async with ScreenshotCapture() as capture:
        tasks = {}
        for url, data in pages.items():
            if data["failed"]:
                screenshots[url] = "Screenshot unavailable"
            else:
                tasks[url] = capture.capture(url)

        # Execute all screenshot tasks (semaphore limits concurrency to 5)
        if tasks:
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for url, result in zip(tasks.keys(), results):
                if isinstance(result, Exception) or result is None:
                    screenshots[url] = "Screenshot unavailable"
                else:
                    screenshots[url] = result
                    print(f"  Screenshot captured: {url}")

    print(f"  Screenshots: {sum(1 for v in screenshots.values() if v != 'Screenshot unavailable')}/{len(pages)}")
    print()

    # Build graph
    print("[Phase 3] Building graph...")
    for url, data in pages.items():
        graph.add_page(
            url=url,
            title=data["title"],
            depth=data["depth"],
            outbound_count=data["outbound_count"],
            screenshot_b64=screenshots.get(url, "Screenshot unavailable"),
            failed=data.get("failed", False),
        )

    # Add edges
    for url, data in pages.items():
        if data["html"] and not data.get("failed"):
            parser = LinkParser(start_url)
            links = parser.extract_links(data["html"], url)
            for link in links:
                graph.add_edge(url, link)

    network = graph.build()
    print(f"  Nodes: {len(network.get_nodes())}")
    print(f"  Edges: {len(network.get_edges())}")
    print()

    # Generate HTML
    print("[Phase 4] Generating HTML...")
    output = generate_html(network, output_path)
    print(f"  Output: {output}")
    print()

    print("SiteMap3D - Complete!")
    print(f"  Open {output_path} in a browser to view the interactive graph.")


def main():
    parser = argparse.ArgumentParser(
        description="SiteMap3D - Generate an interactive 3D-like site graph with screenshots."
    )
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="Starting URL to crawl (e.g., https://example.com)"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=2,
        help="Maximum crawl depth (default: 2)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Maximum number of pages to crawl (default: 50)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./sitemap3d.html",
        help="Output HTML file path (default: ./sitemap3d.html)"
    )

    args = parser.parse_args()

    try:
        asyncio.run(crawl(
            start_url=args.url,
            max_depth=args.depth,
            max_pages=args.max_pages,
            output_path=args.output,
        ))
    except KeyboardInterrupt:
        print("\nCrawl interrupted by user.")
        sys.exit(1)


if __name__ == "__main__":
    main()
