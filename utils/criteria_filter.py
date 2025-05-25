"""Utilities for filtering data against multiple criteria."""

from typing import List, Dict, Any
from utils.logger import get_logger

import re

logger = get_logger(__name__)

def extract_criteria_from_task(task: str) -> List[str]:
    """
    Extract criteria from a multi-criteria task.
    
    Args:
        task (str): The task description
        
    Returns:
        List[str]: List of individual criteria
    """
    lines = task.strip().split('\n')
    
    # Skip the first line (task title)
    criteria = []
    header_found = False
    
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
            
        # Look for criteria header
        if stripped.lower().endswith('criteria:') or stripped.lower().endswith('criteria'):
            header_found = True
            continue
            
        # Collect criteria lines (indented or with bullet points)
        if header_found or stripped.startswith('-') or stripped.startswith('•') or stripped.startswith('*'):
            # Clean up bullet points and leading/trailing whitespace
            cleaned = re.sub(r'^[-•*]\s*', '', stripped)
            if cleaned:
                criteria.append(cleaned)
    
    # If no criteria found using the above method, try a simpler approach for indented lines
    if not criteria:
        for line in lines[1:]:
            stripped = line.strip()
            if stripped and (line.startswith(' ') or line.startswith('\t')):
                criteria.append(stripped)
    
    return criteria

def filter_results_by_criteria(results: List[Dict[str, Any]], criteria: List[str]) -> List[Dict[str, Any]]:
    """
    Filter results to only those matching all criteria.
    
    Args:
        results: List of result objects
        criteria: List of criteria strings
        
    Returns:
        List of results matching all criteria
    """
    # Implementation depends on the structure of your results
    # This is a simplified example
    matching_results = []
    
    for result in results:
        matches_all = True
        for criterion in criteria:
            # Convert criterion to lowercase keywords for fuzzy matching
            keywords = [k.strip() for k in criterion.lower().split() if len(k.strip()) > 3]
            
            # Check if result content contains all keywords from this criterion
            content = str(result.get('content', '')).lower()
            if not all(keyword in content for keyword in keywords):
                matches_all = False
                break
                
        if matches_all:
            matching_results.append(result)
    
    return matching_results