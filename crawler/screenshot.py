"""Playwright-based screenshot capture with concurrency limiting."""

import asyncio
import base64
import io
from typing import Optional

from PIL import Image


class ScreenshotCapture:
    """
    Captures screenshots of web pages using Playwright.
    Uses asyncio.Semaphore to limit concurrent screenshot calls to 5.
    Resizes images to 320x200 using Pillow before base64 encoding.
    """

    def __init__(self, max_concurrent: int = 5, viewport_width: int = 1280, viewport_height: int = 720):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self._playwright = None
        self._browser = None

    async def __aenter__(self):
        from playwright.async_api import async_playwright
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, *args):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def capture(self, url: str) -> Optional[str]:
        """
        Capture a screenshot of the given URL.
        Returns base64-encoded JPEG string, or "Screenshot unavailable" on failure.
        """
        async with self._semaphore:
            return await self._capture_internal(url)

    async def _capture_internal(self, url: str) -> Optional[str]:
        """Internal capture method (called under semaphore)."""
        if not self._browser:
            raise RuntimeError("ScreenshotCapture must be used as an async context manager")

        try:
            page = await self._browser.new_page(
                viewport={"width": self.viewport_width, "height": self.viewport_height}
            )

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(2000)  # Let page settle

                screenshot_bytes = await page.screenshot(type="jpeg", quality=80)

                # Resize to 320x200 using Pillow
                img = Image.open(io.BytesIO(screenshot_bytes))
                img = img.resize((320, 200), Image.LANCZOS)

                # Encode to base64
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=75)
                b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

                return b64

            finally:
                await page.close()

        except Exception as e:
            print(f"  [screenshot] Error capturing {url}: {e}")
            return None
