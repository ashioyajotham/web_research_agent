from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from .tool_registry import BaseTool
from utils.logger import get_logger
from config.config import get_config
import re
import requests
import random

logger = get_logger(__name__)

TEXT_CT_PAT = re.compile(r"(text/|application/(json|xml|xhtml|javascript))", re.I)
PLACEHOLDER_PAT = re.compile(r"\{\{\s*search_result_(\d+)_url\s*\}\}", re.I)

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

def _safe_decode(response: requests.Response) -> str:
    try:
        response.encoding = response.encoding or response.apparent_encoding or "utf-8"
        return response.text or ""
    except Exception:
        try:
            return response.content.decode("utf-8", errors="replace")
        except Exception:
            return ""

def _extract_title_and_text(html: str) -> Dict[str, str]:
    soup = BeautifulSoup(html or "", "html.parser")
    title = (soup.title.string or "").strip() if soup.title else ""
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return {"title": title, "text": text}

def _resolve_url_placeholder(raw_url: Optional[str], memory: Any) -> Optional[str]:
    if not raw_url or not isinstance(raw_url, str):
        return None
    raw = raw_url.strip()
    m = PLACEHOLDER_PAT.fullmatch(raw)
    results = getattr(memory, "search_results", None) or []
    if m:
        idx = int(m.group(1))
        if 0 <= idx < len(results):
            return results[idx].get("link") or results[idx].get("url")
        return None
    if raw.lower() in {"{from_search}", "from_search", "${from_search}", "{{from_search}}"}:
        if results:
            return results[0].get("link") or results[0].get("url")
        return None
    return raw

class BrowserTool(BaseTool):
    """Tool for browsing websites and extracting content."""
    def __init__(self):
        super().__init__(name="browser", description="Fetch web pages and extract text")
        self.config = get_config()
        self.base_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.6",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        }

    def execute(self, parameters: Dict[str, Any], memory: Any) -> Dict[str, Any]:
        params = parameters or {}
        raw_url = params.get("url")
        url = _resolve_url_placeholder(raw_url, memory)
        if not url:
            return {"status": "error", "error": "Missing URL"}
        
        headers = {**self.base_headers, "User-Agent": random.choice(UA_LIST)}
        try:
            resp = requests.get(url, headers=headers, timeout=self.config.get("http_timeout", 25))
            ct = resp.headers.get("Content-Type", "")
            is_text = bool(TEXT_CT_PAT.search(ct))
            
            output: Dict[str, Any] = {"url": url, "title": "", "extracted_text": "", "_binary": False}
            if is_text:
                html = _safe_decode(resp)
                tt = _extract_title_and_text(html)
                output["title"] = tt["title"]
                output["extracted_text"] = tt["text"]
            else:
                output["_binary"] = True
                
            return {"status": "success", **output}
        except Exception as e:
            logger.warning(f"Fetch failed for {url}: {e}")
            return {"status": "error", "error": str(e), "url": url}
