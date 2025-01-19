import logging
from typing import Dict, Any, List
from pathlib import Path
import json
import re

def setup_logging(config: Dict) -> logging.Logger:
    """Configure logging based on config settings"""
    log_path = Path(config['logging']['file'])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=config['logging']['level'],
        format=config['logging']['format'],
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean and normalize text content"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove special characters
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return text

def save_json(data: Any, filepath: Path) -> None:
    """Save data to JSON file"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_json(filepath: Path) -> Any:
    """Load data from JSON file"""
    if not filepath.exists():
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def validate_task(task: str) -> bool:
    """Validate task input"""
    if not task or not isinstance(task, str):
        return False
    return len(task.strip()) > 0

def chunk_text(text: str, chunk_size: int = 1000) -> List[str]:
    """Split text into manageable chunks"""
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

def create_directory(path: Path) -> None:
    """Create directory if it doesn't exist"""
    path.mkdir(parents=True, exist_ok=True)

def sanitize_filename(filename: str) -> str:
    """Convert string to valid filename"""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)