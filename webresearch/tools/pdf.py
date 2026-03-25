"""
PDF extraction tool for fetching and parsing PDF documents.
Extracts text and tables from PDFs — critical for sustainability reports,
academic papers, and financial documents.
"""

import io
import logging
import re
import requests
from typing import Optional

from .base import Tool

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    pdfplumber_available = True
except ImportError:
    pdfplumber_available = False


def pdf_available() -> bool:
    return pdfplumber_available


class PDFExtractTool(Tool):
    """Tool for extracting text and tables from PDF documents."""

    def __init__(self, timeout: int = 30, max_length: int = 12000):
        self.timeout = timeout
        self.max_length = max_length
        super().__init__()

    @property
    def name(self) -> str:
        return "pdf_extract"

    @property
    def description(self) -> str:
        return """Download and extract text and tables from a PDF document.

Parameters:
- url (str, required): The URL of the PDF file
- pages (str, optional): Page range to extract, e.g. "1-5" or "3" or "all" (default: "all")

Returns:
Extracted text content and tables from the PDF, formatted for readability.
Tables are rendered with aligned columns so numerical values are clear.
The header shows total page count so you can request specific page ranges
if the document is too large.

Use this tool when you need to:
- Read sustainability/ESG reports for emissions data (Scope 1, 2, 3)
- Extract financial figures from annual reports
- Parse tables from academic papers or datasets
- Get specific numerical data from regulatory filings

Example usage:
url: "https://www.volkswagenag.com/en/sustainability/report.pdf"
url: "https://example.com/annual-report-2023.pdf", pages: "12-18"

Note: For large PDFs, first call without pages to see the page count and
table of contents, then call again with a targeted page range.
"""

    def execute(self, url: str, pages: str = "all") -> str:
        if not pdfplumber_available:
            return (
                "Error: pdfplumber is not installed. "
                "Install it with: pip install pdfplumber"
            )

        if not url or not url.strip():
            return "Error: URL cannot be empty"

        try:
            logger.info(f"Downloading PDF: {url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/pdf,*/*",
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)

            if response.status_code in (401, 403):
                return (
                    f"Skipped (requires login): {url} returned {response.status_code}. "
                    "This PDF is behind a paywall or requires authentication."
                )
            if response.status_code == 429:
                return f"Skipped (rate limited): {url} returned 429. Try a different source."

            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" in content_type:
                return (
                    f"URL returned HTML instead of PDF: {url}. "
                    "The PDF may be behind a login page. Use the scrape tool instead."
                )

            pdf_bytes = io.BytesIO(response.content)
            return self._extract(pdf_bytes, url, pages)

        except requests.exceptions.Timeout:
            return f"Error: Request timed out after {self.timeout}s for: {url}"
        except requests.exceptions.RequestException as e:
            return f"Error: Failed to fetch PDF {url}: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error extracting PDF {url}: {str(e)}")
            return f"Error: Unexpected error reading PDF {url}: {str(e)}"

    def _parse_page_range(self, pages_str: str, total_pages: int):
        """Parse pages string into a list of 0-based page indices."""
        if not pages_str or pages_str.strip().lower() == "all":
            return list(range(total_pages))

        pages_str = pages_str.strip()
        indices = []
        for part in pages_str.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                try:
                    s = max(0, int(start.strip()) - 1)
                    e = min(total_pages, int(end.strip()))
                    indices.extend(range(s, e))
                except ValueError:
                    pass
            else:
                try:
                    idx = int(part) - 1
                    if 0 <= idx < total_pages:
                        indices.append(idx)
                except ValueError:
                    pass

        return indices if indices else list(range(total_pages))

    def _format_table(self, table) -> str:
        """Format a pdfplumber table as an aligned plain-text grid."""
        if not table:
            return ""

        # Normalise: replace None with empty string, strip whitespace
        rows = []
        for row in table:
            rows.append([
                str(cell).strip() if cell is not None else ""
                for cell in row
            ])

        if not rows:
            return ""

        # Compute column widths
        n_cols = max(len(r) for r in rows)
        col_widths = [0] * n_cols
        for row in rows:
            for j, cell in enumerate(row):
                if j < n_cols:
                    col_widths[j] = max(col_widths[j], len(cell))

        # Render
        sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        lines = [sep]
        for i, row in enumerate(rows):
            padded = []
            for j in range(n_cols):
                cell = row[j] if j < len(row) else ""
                padded.append(f" {cell:<{col_widths[j]}} ")
            lines.append("|" + "|".join(padded) + "|")
            if i == 0:  # header separator
                lines.append(sep)
        lines.append(sep)
        return "\n".join(lines)

    def _extract(self, pdf_bytes: io.BytesIO, url: str, pages_str: str) -> str:
        with pdfplumber.open(pdf_bytes) as pdf:
            total = len(pdf.pages)
            page_indices = self._parse_page_range(pages_str, total)

            sections = [
                f"PDF: {url}",
                f"Total pages: {total}  |  Extracting pages: {page_indices[0]+1}–{page_indices[-1]+1} of {total}",
                "=" * 80,
            ]

            for idx in page_indices:
                page = pdf.pages[idx]
                sections.append(f"\n--- Page {idx + 1} ---")

                # Extract tables first (structural data is most valuable)
                tables = page.extract_tables()
                if tables:
                    for t_idx, table in enumerate(tables):
                        if table and any(any(cell for cell in row) for row in table):
                            sections.append(f"\n[Table {t_idx + 1}]")
                            sections.append(self._format_table(table))

                # Extract remaining text (exclude table bounding boxes to avoid duplication)
                try:
                    table_bboxes = [t.bbox for t in page.find_tables()]
                    if table_bboxes:
                        # Crop out table regions and extract text from the rest
                        remaining_text = page.filter(
                            lambda obj: not any(
                                obj["x0"] >= bbox[0] and obj["top"] >= bbox[1]
                                and obj["x1"] <= bbox[2] and obj["bottom"] <= bbox[3]
                                for bbox in table_bboxes
                            )
                        ).extract_text()
                    else:
                        remaining_text = page.extract_text()
                except Exception:
                    remaining_text = page.extract_text()

                if remaining_text and remaining_text.strip():
                    cleaned = _clean_text(remaining_text)
                    if cleaned:
                        sections.append(cleaned)

            result = "\n".join(sections)

            if len(result) > self.max_length:
                result = result[: self.max_length]
                result += (
                    f"\n\n... [Truncated. Total extracted: {len(result)} chars. "
                    f"Use pages= parameter to target specific pages, e.g. pages=\"{page_indices[0]+1}-{min(page_indices[0]+5, total)}\"]"
                )

            return result


def _clean_text(text: str) -> str:
    """Remove excessive whitespace and blank lines from extracted text."""
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if line:
            lines.append(line)
    # Collapse 3+ blank lines to 2
    result = []
    blank_count = 0
    for line in lines:
        if not line:
            blank_count += 1
            if blank_count <= 1:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    return "\n".join(result)
