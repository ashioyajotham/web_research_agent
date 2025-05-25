"""Utilities for parsing tasks from files with support for multi-criteria tasks."""

import re
from typing import List
from utils.logger import get_logger

logger = get_logger(__name__)

def parse_tasks_from_file(task_file_path: str) -> List[str]:
    """
    Parse tasks from a file, properly handling multi-line tasks with indentation.
    
    Args:
        task_file_path (str): Path to the task file
        
    Returns:
        List[str]: List of parsed tasks, with multi-line tasks properly combined
    """
    with open(task_file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Split into potential task blocks (separated by blank lines)
    task_blocks = re.split(r'\n\s*\n', content)
    
    tasks = []
    for block in task_blocks:
        if not block.strip():
            continue
        
        # Handle potential multi-line task with indentation
        lines = block.splitlines()
        if len(lines) > 1 and any(line.strip() and (line.startswith(' ') or line.startswith('\t')) 
                                 for line in lines[1:]):
            # This is a multi-line task with indentation - keep as is
            tasks.append(block.strip())
            logger.info(f"Parsed multi-criteria task with {len(lines)} lines")
        else:
            # These might be separate single-line tasks
            for line in lines:
                if line.strip():
                    tasks.append(line.strip())
    
    logger.info(f"Parsed {len(tasks)} tasks from file")
    return tasks