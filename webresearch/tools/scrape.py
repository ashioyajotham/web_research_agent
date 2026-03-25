"""
Web scraping tool for fetching and parsing web page content.
Allows the agent to read and extract information from URLs.
"""

import re
import time
import random
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

# Rotated UA pool — avoids trivial single-string fingerprinting
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# CSS selectors tried in priority order to isolate main content
_CONTENT_SELECTORS = [
    # Semantic HTML5
    "main",
    "article",
    '[role="main"]',
    # Generic content IDs
    "#content",
    "#main-content",
    "#main",
    "#article",
    "#story",
    "#page-content",
    # Common CMS / blog class names
    ".content",
    ".main-content",
    ".article-body",
    ".article-content",
    ".article__body",
    ".article__content",
    ".post-content",
    ".post-body",
    ".entry-content",
    ".entry-body",
    ".story-body",
    ".story-content",
    ".body-content",
    ".page-content",
    ".text-content",
    # News-site specific
    '[data-component="article-body"]',
    '[data-testid="article-body"]',
    '[data-module="ArticleBody"]',
    ".c-article-body",
    ".l-article-body",
    ".RichTextArticleBody",
    ".paywall-article",
    # Generic wrappers
    ".container article",
    ".wrapper article",
]

# Login-wall patterns detectable in 200-OK HTML even when text is substantial
_AUTH_REDIRECT_PATTERNS = [
    r'<form[^>]+(?:action|id|class)[^>]*(?:login|sign.?in|signin|auth)[^>]*>',
    r'<input[^>]+(?:name|id)[^>]*(?:password|passwd)[^>]*>',
    r'(?:please\s+)?(?:log\s*in|sign\s*in)\s+to\s+(?:continue|read|access|view)',
    r'create\s+(?:an?\s+)?(?:free\s+)?account\s+to\s+(?:continue|read)',
    r'(?:you\s+must|you\'ll\s+need\s+to)\s+(?:be\s+logged\s+in|log\s+in|sign\s+in)',
]

logger = logging.getLogger(__name__)


class ScrapeTool(Tool):
    """Tool for fetching and parsing web page content."""

    def __init__(self, timeout: int = 30, max_length: int = 10000):
        self.timeout = timeout
        self.max_length = max_length
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0
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
HTML tables are extracted as properly aligned markdown tables.
The content is cleaned and converted from HTML to markdown-like text.

Use this tool when you need to:
- Read the full content of a specific web page
- Extract detailed information from articles, reports, or documents
- Get the actual text from a URL found in search results

Note: For PDF files use the pdf_extract tool. For JS-heavy pages that
return no content, use the scrape_js tool.
"""

    def execute(self, url: str) -> str:
        if not url or not url.strip():
            return "Error: URL cannot be empty"

        try:
            logger.info(f"Scraping URL: {url}")
            response = self._fetch_with_retry(url)
            if isinstance(response, str):
                # Error message returned from _fetch_with_retry
                return response
        except requests.exceptions.Timeout:
            return f"Error: Request timed out after {self.timeout} seconds for URL: {url}"
        except requests.exceptions.RequestException as e:
            return f"Error: Failed to fetch URL {url}: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {str(e)}")
            return f"Error: Unexpected error scraping {url}: {str(e)}"

        content_type = response.headers.get("Content-Type", "").lower()

        if "text/html" in content_type or "application/xhtml" in content_type:
            # Fix encoding before accessing .text — requests defaults to ISO-8859-1
            # when charset is absent, which mangles special chars on EU/gov sites
            if response.encoding and response.encoding.upper() in ("ISO-8859-1", "LATIN-1"):
                response.encoding = response.apparent_encoding
            return self._parse_html(response.text, url)
        elif "text/plain" in content_type:
            return self._truncate_content(response.text)
        elif "application/json" in content_type:
            return f"JSON content from {url}:\n\n{self._truncate_content(response.text)}"
        elif "text/csv" in content_type or url.endswith(".csv"):
            return f"CSV content from {url}:\n\n{self._truncate_content(response.text)}"
        elif "application/pdf" in content_type or url.endswith(".pdf"):
            return (
                f"PDF detected at {url} ({len(response.content):,} bytes). "
                "Use the pdf_extract tool with this URL to read its text and tables. "
                'Example: Action: pdf_extract / Action Input: {"url": "' + url + '"}'
            )
        else:
            return self._parse_html(response.text, url)

    def _fetch_with_retry(self, url: str):
        """
        Fetch URL with randomised UA, Brotli accept-encoding, and 5xx retry.
        Returns a Response on success or a str error message for 4xx skip conditions.
        """
        headers = {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        last_exc = None
        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)

                # 4xx — return actionable skip messages immediately, no retry
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

                # 5xx — retry with backoff
                if response.status_code in (500, 502, 503, 504):
                    if attempt < 2:
                        wait = 2 ** (attempt + 1)  # 2s, 4s
                        logger.warning(f"{response.status_code} from {url}, retrying in {wait}s")
                        time.sleep(wait)
                        continue
                    return (
                        f"Skipped (server error {response.status_code}): {url}. "
                        "The server is temporarily unavailable. Try a different source."
                    )

                response.raise_for_status()
                return response

            except requests.exceptions.Timeout:
                raise
            except requests.exceptions.RequestException as e:
                last_exc = e
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise

        if last_exc:
            raise last_exc

    def _parse_html(self, html_content: str, url: str) -> str:
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove non-content elements
            for tag in soup(["script", "style", "nav", "footer", "header",
                              "aside", "noscript", "iframe", "svg"]):
                tag.decompose()

            # Try to isolate main content region
            main_content = None
            for selector in _CONTENT_SELECTORS:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            if not main_content:
                main_content = soup.find("body") or soup

            # Convert HTML tables to markdown before html2text (which mangles them)
            self._replace_tables_with_markdown(main_content, soup)

            # Convert to markdown-like text
            text = self.html_converter.handle(str(main_content))

            # Clean up whitespace
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            text = "\n".join(lines)

            # JS-only page detection
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

            # Auth-redirect detection (200 OK but actually a login wall)
            # Check raw HTML for login form signatures regardless of extracted text length
            html_lower = html_content.lower()
            for pattern in _AUTH_REDIRECT_PATTERNS:
                if re.search(pattern, html_lower, re.IGNORECASE):
                    return (
                        f"Skipped (auth redirect): {url} returned 200 but contains a "
                        "login form or sign-in wall. "
                        "Search for a different source covering the same content."
                    )

            # Paywall teaser: large HTML, thin text, subscribe keywords
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

            result = f"Content from: {url}\n{'=' * 80}\n\n{text}"
            return self._truncate_content(result)

        except Exception as e:
            logger.error(f"Error parsing HTML: {str(e)}")
            return f"Error parsing HTML from {url}: {str(e)}"

    def _replace_tables_with_markdown(self, content_tag, soup) -> None:
        """
        Find all <table> elements within content_tag and replace each with a
        <pre> block containing a proper markdown table.  This runs before html2text
        so structural data (emissions tables, financial statements) is preserved.
        """
        for table in content_tag.find_all("table"):
            md = self._table_to_markdown(table)
            if md:
                pre = soup.new_tag("pre")
                pre.string = "\n" + md + "\n"
                table.replace_with(pre)
            # If table is empty / un-parseable, leave html2text to deal with it

    def _table_to_markdown(self, table_tag) -> str:
        """Convert a BS4 <table> element to an aligned markdown table string."""
        rows = []
        for tr in table_tag.find_all("tr"):
            cells = []
            for cell in tr.find_all(["td", "th"]):
                text = cell.get_text(separator=" ", strip=True)
                text = re.sub(r"\s+", " ", text).strip()
                cells.append(text)
            if any(cells):
                rows.append(cells)

        if not rows:
            return ""

        # Normalise column count across all rows
        n_cols = max(len(r) for r in rows)
        rows = [r + [""] * (n_cols - len(r)) for r in rows]

        # Column widths (minimum 3 for the separator dashes)
        col_widths = [
            max(max(len(rows[i][j]) for i in range(len(rows))), 3)
            for j in range(n_cols)
        ]

        def fmt_row(row):
            return "| " + " | ".join(
                cell.ljust(col_widths[j]) for j, cell in enumerate(row)
            ) + " |"

        lines = [fmt_row(rows[0])]
        lines.append("| " + " | ".join("-" * w for w in col_widths) + " |")
        for row in rows[1:]:
            lines.append(fmt_row(row))

        return "\n".join(lines)

    def _sanitize_content(self, content: str) -> str:
        for pattern in _INJECTION_PATTERNS:
            content = re.sub(pattern, "[REDACTED]", content, flags=re.IGNORECASE)
        return content

    def _truncate_content(self, content: str) -> str:
        if len(content) <= self.max_length:
            return self._sanitize_content(content)
        truncated = content[: self.max_length]
        truncated += f"\n\n... [Content truncated. Total length: {len(content)} characters, showing first {self.max_length}]"
        return self._sanitize_content(truncated)
