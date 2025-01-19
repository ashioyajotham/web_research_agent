from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class TaskIntent(Enum):
    COMPILE = "compile"        # For gathering and organizing information
    FIND = "find"             # For specific fact-finding
    ANALYZE = "analyze"       # For processing and interpreting data
    CALCULATE = "calculate"   # For numerical computations
    EXTRACT = "extract"       # For pulling specific data from sources
    VERIFY = "verify"         # For fact-checking or validation

@dataclass
class TaskRequirements:
    intent: TaskIntent
    count: Optional[int] = None           # Required number of items
    time_scope: Optional[str] = None      # Temporal requirements
    format_requirements: List[str] = None  # Specific formatting needs
    validation_rules: List[str] = None    # Validation criteria
    sources_required: bool = False        # Whether sources are needed

class TaskAnalyzer:
    def analyze(self, task: str) -> TaskRequirements:
        """Analyze task text to understand requirements and constraints."""
        task = task.lower().strip()
        requirements = TaskRequirements(
            intent=self._determine_intent(task),
            count=self._extract_count(task),
            time_scope=self._extract_time_scope(task),
            format_requirements=self._extract_format_requirements(task),
            validation_rules=self._extract_validation_rules(task),
            sources_required='source' in task or 'reference' in task
        )
        return requirements

    def _determine_intent(self, task: str) -> TaskIntent:
        """Determine the primary intent of the task."""
        intent_indicators = {
            TaskIntent.COMPILE: ['compile', 'list', 'gather', 'collect'],
            TaskIntent.FIND: ['find', 'identify', 'name', 'who', 'what', 'where'],
            TaskIntent.ANALYZE: ['analyze', 'compare', 'evaluate', 'assess'],
            TaskIntent.CALCULATE: ['calculate', 'compute', 'percentage', 'rate'],
            TaskIntent.EXTRACT: ['extract', 'pull', 'from', 'get'],
            TaskIntent.VERIFY: ['verify', 'check', 'validate', 'confirm']
        }

        for intent, indicators in intent_indicators.items():
            if any(ind in task for ind in indicators):
                return intent
        return TaskIntent.FIND  # Default intent

    def _extract_count(self, task: str) -> Optional[int]:
        """Extract required count of items if specified."""
        import re
        count_patterns = [
            r'(\d+)\s*(items?|statements?|points?|examples?)',
            r'list\s+(\d+)',
            r'compile\s+(\d+)',
            r'find\s+(\d+)'
        ]
        
        for pattern in count_patterns:
            if match := re.search(pattern, task):
                return int(match.group(1))
        return None

    def _extract_time_scope(self, task: str) -> Optional[str]:
        """Extract time-related requirements."""
        import re
        time_patterns = [
            r'in\s+(\d{4})',
            r'between\s+(\d{4})\s+and\s+(\d{4})',
            r'from\s+(\d{4})\s+to\s+(\d{4})',
            r'(\d{4})-(\d{4})'
        ]
        
        for pattern in time_patterns:
            if match := re.search(pattern, task):
                return match.group(0)
        return None

    def _extract_format_requirements(self, task: str) -> List[str]:
        """Extract formatting requirements."""
        requirements = []
        if 'separate' in task:
            requirements.append('separate_items')
        if 'source' in task or 'reference' in task:
            requirements.append('include_sources')
        if 'date' in task:
            requirements.append('include_dates')
        return requirements

    def _extract_validation_rules(self, task: str) -> List[str]:
        """Extract validation rules from task."""
        rules = []
        # Example validation rules
        if 'must' in task:
            rules.extend(part.strip() for part in task.split('must')[1:])
        if 'should' in task:
            rules.extend(part.strip() for part in task.split('should')[1:])
        return rules
