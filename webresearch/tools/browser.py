"""
Browser-based scraping tool using Playwright for JavaScript-rendered pages.
Gracefully unavailable when Playwright is not installed.
"""

import logging
from typing import Optional

from .base import Tool
from .scrape import ScrapeTool

logger = logging.getLogger(__name__)


def playwright_available() -> bool:
    """Return True if Playwright is installed and Chromium is accessible."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except ImportError:
        return False


def fetch_with_playwright(url: str, timeout_ms: int = 30_000) -> Optional[str]:
    """
    Fetch fully-rendered page HTML using a headless Chromium browser.

    Returns the rendered HTML string, or None if Playwright is unavailable
    or the fetch fails.
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                html = page.content()
            finally:
                browser.close()
        return html

    except ImportError:
        logger.debug("Playwright not installed")
        return None
    except Exception as e:
        logger.warning(f"Playwright fetch failed for {url}: {e}")
        return None


class BrowserScrapeTool(Tool):
    """
    Playwright-based scraper for JavaScript-rendered pages.

    Tool name: 'scrape_js'
    Use this when the basic 'scrape' tool returns thin or empty content,
    which indicates a JS-only single-page application.
    """

    def __init__(self, timeout_ms: int = 30_000, max_length: int = 10_000):
        self.timeout_ms = timeout_ms
        # Reuse ScrapeTool's HTML parsing and sanitization pipeline
        self._parser = ScrapeTool(max_length=max_length)
        super().__init__()

    @property
    def name(self) -> str:
        return "scrape_js"

    @property
    def description(self) -> str:
        return """Fetch and extract text from JavaScript-rendered web pages using a headless browser.

Parameters:
- url (str, required): The URL of the web page to scrape

Returns:
The fully-rendered text content of the page after JavaScript execution.

Use this tool when:
- The basic 'scrape' tool returned thin, empty, or "enable JavaScript" content
- The page is a React / Vue / Angular single-page application
- Content loads lazily or requires user interaction to appear
- You are scraping dashboards, web apps, or interactive data visualisations

Note: Slower than 'scrape' (~5-15s per page). Requires Playwright to be installed:
  pip install playwright && playwright install chromium
"""

    def execute(self, url: str) -> str:
        if not url or not url.strip():
            return "Error: URL cannot be empty"

        if not playwright_available():
            return (
                "Error: Playwright is not installed. "
                "Install it with:\n"
                "  pip install playwright && playwright install chromium\n\n"
                "Alternatively, try the basic 'scrape' tool."
            )

        logger.info(f"BrowserScrapeTool fetching: {url}")
        html = fetch_with_playwright(url, self.timeout_ms)

        if html is None:
            return (
                f"Error: Headless browser failed to load {url}. "
                "Try the basic 'scrape' tool as a fallback."
            )

        # Reuse the same HTML parsing + sanitization from ScrapeTool
        return self._parser._parse_html(html, url)
