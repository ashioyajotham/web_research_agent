"""
Web scraping tool for fetching and parsing web page content.
Allows the agent to read and extract information from URLs.
"""

import re
import requests
from bs4 import BeautifulSoup
import html2text
import logging
from typing import Optional
from .base import Tool

# Patterns that indicate prompt injection attempts in scraped content
_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?previous\s+instructions?",
    r"disregard\s+(?:all\s+)?(?:previous|prior|above)",
    r"(?:new\s+)?system\s*(?:prompt|instructions?)\s*:",
    r"you\s+are\s+now\s+(?:a\s+)?(?:different|new|an?\s+)",
    r"<\s*system\s*>",
    r"<\s*/?(?:human|assistant|user|prompt)\s*>",
    r"\[\s*(?:SYSTEM|INST|SYS)\s*\]",
    r"final\s+answer\s*:\s*(?:ignore|the\s+answer\s+is)",
    r"action\s+input\s*:\s*\{[^}]{0,50}inject",
]

logger = logging.getLogger(__name__)


class ScrapeTool(Tool):
    """Tool for fetching and parsing web page content."""

    def __init__(self, timeout: int = 30, max_length: int = 10000):
        """
        Initialize the scrape tool.

        Args:
            timeout: Request timeout in seconds
            max_length: Maximum length of content to return
        """
        self.timeout = timeout
        self.max_length = max_length
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0  # Don't wrap text
        super().__init__()

    @property
    def name(self) -> str:
        return "scrape"

    @property
    def description(self) -> str:
        return """Fetch and extract text content from a web page.

Parameters:
- url (str, required): The URL of the web page to scrape

Returns:
The main text content of the web page in a readable format.
The content is cleaned and converted from HTML to markdown-like text.

Use this tool when you need to:
- Read the full content of a specific web page
- Extract detailed information from articles, reports, or documents
- Get the actual text from a URL found in search results
- Download datasets or files (will return information about the content)

Example usage:
url: "https://www.whitehouse.gov/briefing-room/speeches-remarks/2023/..."
url: "https://epochai.org/data/notable-ai-models"
url: "https://www.volkswagen.com/en/sustainability-report.html"

Note: This tool works best with standard web pages. For PDF files, CSV files,
or other special formats, it will attempt to download and provide information
about the content.
"""

    def execute(self, url: str) -> str:
        """
        Fetch and parse content from a URL.

        Args:
            url: The URL to scrape

        Returns:
            The extracted text content

        Raises:
            Exception: If the request fails
        """
        if not url or not url.strip():
            return "Error: URL cannot be empty"

        try:
            logger.info(f"Scraping URL: {url}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }

            response = requests.get(url, headers=headers, timeout=self.timeout)

            # Surface paywall/auth errors as actionable messages rather than
            # raising into the generic handler (agent should skip, not retry)
            if response.status_code in (401, 403):
                return (
                    f"Skipped (requires login): {url} returned {response.status_code}. "
                    "This page is paywalled or requires authentication. "
                    "Search for a different source covering the same content."
                )
            if response.status_code == 406:
                return (
                    f"Skipped (406 Not Acceptable): {url}. "
                    "The server rejected the request format. "
                    "Search for an alternative source for this content."
                )
            if response.status_code == 429:
                return (
                    f"Skipped (rate limited): {url} returned 429. "
                    "Too many requests to this server. Try a different source."
                )

            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("Content-Type", "").lower()

            # Handle different content types
            if "text/html" in content_type or "application/xhtml" in content_type:
                return self._parse_html(response.text, url)
            elif "text/plain" in content_type:
                return self._truncate_content(response.text)
            elif "application/json" in content_type:
                return f"JSON content from {url}:\n\n{self._truncate_content(response.text)}"
            elif "text/csv" in content_type or url.endswith(".csv"):
                return f"CSV content from {url}:\n\n{self._truncate_content(response.text)}"
            elif "application/pdf" in content_type or url.endswith(".pdf"):
                return f"PDF file detected at {url}. Size: {len(response.content)} bytes. You may need to use a specialized tool to read PDF content, or note this URL for the user to download manually."
            else:
                # Try to parse as HTML anyway
                return self._parse_html(response.text, url)

        except requests.exceptions.Timeout:
            logger.error(f"Request timed out for URL: {url}")
            return (
                f"Error: Request timed out after {self.timeout} seconds for URL: {url}"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for URL {url}: {str(e)}")
            return f"Error: Failed to fetch URL {url}: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {str(e)}")
            return f"Error: Unexpected error scraping {url}: {str(e)}"

    def _parse_html(self, html_content: str, url: str) -> str:
        """
        Parse HTML content and extract readable text.

        Args:
            html_content: The HTML content
            url: The source URL (for context)

        Returns:
            Extracted and formatted text
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Try to find main content area
            main_content = None
            for selector in [
                "main",
                "article",
                '[role="main"]',
                "#content",
                ".content",
            ]:
                main_content = soup.select_one(selector)
                if main_content:
                    break

            # If no main content found, use body
            if not main_content:
                main_content = soup.find("body")

            if not main_content:
                main_content = soup

            # Convert to markdown-like text
            text = self.html_converter.handle(str(main_content))

            # Clean up the text
            lines = text.split("\n")
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if line:
                    cleaned_lines.append(line)

            text = "\n".join(cleaned_lines)

            # Detect JS-only pages: large HTML but almost no extracted text
            _JS_HINTS = [
                "you need to enable javascript",
                "please enable javascript",
                "requires javascript",
                "loading...",
                "app is loading",
            ]
            if len(text.strip()) < 400 and len(html_content) > 3000:
                if any(h in text.lower() for h in _JS_HINTS) or len(text.strip()) < 100:
                    return (
                        f"Content from: {url}\n{'=' * 80}\n\n"
                        "[JS-rendered page] This page requires JavaScript to display "
                        "content. Use the 'scrape_js' tool with this same URL to fetch "
                        "the fully-rendered version."
                    )

            # Detect paywall teasers: large HTML but only a thin slice of text
            # (e.g. Digitimes, Bloomberg, FT — 200 OK with <600 chars of content)
            _PAYWALL_HINTS = [
                "subscribe", "subscription", "sign in to read", "sign up to read",
                "register to read", "continue reading", "unlock this article",
                "premium content", "members only",
            ]
            if len(text.strip()) < 600 and len(html_content) > 5000:
                text_lower = text.lower()
                if any(h in text_lower for h in _PAYWALL_HINTS):
                    return (
                        f"Skipped (paywall teaser): {url} returned minimal content "
                        f"({len(text.strip())} chars). "
                        "This page is likely paywalled. Search for a different source."
                    )

            # Add URL header
            result = f"Content from: {url}\n{'=' * 80}\n\n{text}"

            return self._truncate_content(result)

        except Exception as e:
            logger.error(f"Error parsing HTML: {str(e)}")
            return f"Error parsing HTML from {url}: {str(e)}"

    def _sanitize_content(self, content: str) -> str:
        """
        Strip prompt-injection patterns from scraped content before returning to LLM.

        Args:
            content: Raw scraped text

        Returns:
            Sanitized content with injection patterns replaced by [REDACTED]
        """
        for pattern in _INJECTION_PATTERNS:
            content = re.sub(pattern, "[REDACTED]", content, flags=re.IGNORECASE)
        return content

    def _truncate_content(self, content: str) -> str:
        """
        Truncate content to maximum length.

        Args:
            content: The content to truncate

        Returns:
            Truncated content
        """
        if len(content) <= self.max_length:
            return self._sanitize_content(content)

        truncated = content[: self.max_length]
        truncated += f"\n\n... [Content truncated. Total length: {len(content)} characters, showing first {self.max_length}]"
        return self._sanitize_content(truncated)
