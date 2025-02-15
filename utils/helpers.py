import json
from typing import Any, Dict, List
import aiohttp
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ResponseFormatter:
    @staticmethod
    def format_json(data: Any) -> str:
        """Format data as pretty-printed JSON"""
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    @staticmethod
    def format_list(items: List[Any]) -> str:
        """Format list items with bullet points"""
        return "\n".join(f"• {item}" for item in items)

class WebUtils:
    @staticmethod
    async def make_http_request(url: str, method: str = "GET", headers: Dict = None, data: Dict = None) -> Dict:
        """Make HTTP requests with error handling and logging"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"HTTP request failed: {str(e)}")
            raise

class Timer:
    def __init__(self):
        self.start_time = None
        
    def start(self):
        """Start the timer"""
        self.start_time = datetime.now()
        
    def elapsed(self) -> float:
        """Get elapsed time in seconds"""
        if not self.start_time:
            return 0
        return (datetime.now() - self.start_time).total_seconds()

def truncate_text(text: str, max_length: int = 1000) -> str:
    """Truncate text to specified length while preserving word boundaries"""
    if len(text) <= max_length:
        return text
    truncated = text[:max_length].rsplit(' ', 1)[0]
    return f"{truncated}..."

def parse_task_file(file_path: str) -> List[str]:
    """Parse tasks from a text file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Failed to parse task file: {str(e)}")
        raise

class MemoryCache:
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Any] = {}
        self.max_size = max_size
        
    def get(self, key: str) -> Any:
        """Get value from cache"""
        return self.cache.get(key)
        
    def set(self, key: str, value: Any):
        """Set value in cache with size limit enforcement"""
        if len(self.cache) >= self.max_size:
            # Remove oldest item
            self.cache.pop(next(iter(self.cache)))
        self.cache[key] = value