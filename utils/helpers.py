import json
from typing import Any, Dict, List
import aiohttp
import logging
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()

def setup_logging(verbose: bool = False) -> logging.Logger:
    """Setup logging configuration"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Always log everything to file
    file_handler = logging.FileHandler(f"logs/run_{timestamp}.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    # Console handler with conditional level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO if verbose else logging.WARNING)
    console_handler.setFormatter(logging.Formatter('%(message)s' if not verbose else '%(levelname)s: %(message)s'))
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

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

class RichProgress:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            TimeElapsedColumn(),
            console=console,
            disable=verbose  # Disable progress bar in verbose mode
        )
    
    def __enter__(self):
        return self.progress.__enter__()
    
    def __exit__(self, *args):
        return self.progress.__exit__(*args)

def print_task_result(task: str, result: str, sources: List[Dict]):
    """Print task result with rich formatting and validated sources"""
    task_text = Text(task, style="bold cyan")
    
    # Parse markdown content
    from rich.markdown import Markdown
    result_md = Markdown(result)
    
    # Add source validation info
    source_text = Text("\nSource Validation:", style="bold yellow")
    if sources:
        for source in sources:
            date = source.get('date', 'No date')
            url = source.get('link', '')
            title = source.get('title', '')
            
            source_text.append(f"\n- [{date}] {title}")
            source_text.append(f"\n  {url}")
    else:
        source_text.append("\n- No sources provided")
    
    # Combine content
    import rich.table
    from rich.table import Table
    content = Table.grid()
    content.add_row(result_md)
    content.add_row(source_text)
    
    panel = Panel(
        content,
        title=task_text,
        border_style="blue",
        padding=(1, 2)
    )
    console.print(panel)
    console.print("─" * console.width, style="dim")