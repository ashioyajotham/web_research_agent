from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re

@dataclass
class TaskComponent:
    text: str
    criteria: List[str]
    parent_task: Optional[str] = None
    is_subtask: bool = False
    criteria_type: Optional[str] = None  # New field to track criteria type
    search_scope: Optional[str] = None  # Add field to track search scope
    filter_type: Optional[str] = None   # Add field to track how criterion should be applied

@dataclass
class ParsedTask:
    main_task: str
    components: List[TaskComponent]
    context: Dict[str, Any]
    task_type: str = "general"  # New field to track task type
    is_multi_criteria: bool = False
    search_parameters: Dict[str, Any] = None

class TaskParser:
    def __init__(self):
        self.list_indicators = [
            r'compile\s+a\s+list',
            r'list\s+all',
            r'find\s+all',
            r'identify\s+all'
        ]
        
        self.criteria_indicators = [
            r'(?:satisfying|meeting|with)\s+(?:the\s+)?(?:following|these)\s+criteria',
            r'(?:that|which|who)\s+(?:are|have|meet)',
            r'criteria:',
            r'(?:following|these)\s+criteria:?$',
            r'(?:must|should)\s+(?:meet|satisfy|have)\s+(?:the\s+)?(?:following|these):?$'
        ]
        
        self.list_markers = [
            r'^\s*[-•]\s+',  # Bullet points
            r'^\s*\d+\.\s+',  # Numbered lists
            r'^\s*[a-z]\)\s+',  # Letter lists
        ]

        self.criteria_types = {
            'location': r'(?:based|headquartered)\s+in',
            'industry': r'(?:operate|operating)\s+(?:in|within)',
            'financial': r'(?:earned|revenue|worth|value|market)',
            'status': r'(?:are|is|not)\s+(?:a|an|the)\s+subsidiary'
        }
        
        # Add more specific criteria patterns
        self.criteria_patterns = {
            'location': [
                r'based\s+in\s+(?:the\s+)?([A-Za-z\s]+)',
                r'headquartered\s+in\s+(?:the\s+)?([A-Za-z\s]+)',
                r'(?:are|is)\s+(?:in|from)\s+(?:the\s+)?([A-Za-z\s]+)'
            ],
            'industry': [
                r'(?:Industry|sector):\s*([^,\n]+)',
                r'operate.*within\s+(?:the\s+)?([^,\.]+)\s+sector',
                r'(?:in|within)\s+(?:the\s+)?([^,\.]+)\s+(?:sector|industry)',
            ],
            'financial': [
                r'(?:revenue|earnings|worth)[\s:]+(?:over|more\s+than|exceeding|above)\s*[€\$]?\s*(\d+(?:\.\d+)?[BMT]?)',
                r'(?:market\s+cap|capitalization)[\s:]+(?:of|over|above)\s*[€\$]?\s*(\d+(?:\.\d+)?[BMT]?)',
            ],
            'reporting': [
                r'provide\s+([^,\.]+)\s+information',
                r'report(?:ing)?\s+(?:on|about)\s+([^,\.]+)',
                r'(?:data|metrics)\s+(?:on|for|about)\s+([^,\.]+)',
            ],
            'temporal': [
                r'(?:in|for|during)\s+(?:the\s+)?(?:year\s+)?(\d{4})',
                r'(?:from|between)\s+(\d{4})(?:\s*-\s*|\s+to\s+)(\d{4})',
            ]
        }

    def parse_tasks(self, content: str) -> List[ParsedTask]:
        """Parse content into structured tasks with relationships"""
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        tasks = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check for list-based task with criteria
            if self._is_criteria_task(line):
                criteria_task = self._parse_criteria_task(lines[i:])
                tasks.append(criteria_task)
                i += len(criteria_task.components)
            # Check for regular list task
            elif self._is_list_task(line):
                list_task = self._parse_multi_criteria_task(lines[i:])
                tasks.append(list_task)
                i += len(list_task.components)
            else:
                tasks.append(ParsedTask(
                    main_task=line,
                    components=[TaskComponent(text=line, criteria=[])],
                    context={},
                    task_type="general"
                ))
                i += 1
                
        return tasks

    def _is_criteria_task(self, text: str) -> bool:
        """Check if text indicates a criteria-based task"""
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in self.criteria_indicators)

    def _parse_criteria_task(self, lines: List[str]) -> ParsedTask:
        """Parse a task with multiple criteria"""
        main_task = lines[0]
        criteria = []
        i = 1
        
        # Keep collecting criteria until we hit an empty line or end of lines
        while i < len(lines):
            line = lines[i].strip()
            # Skip empty lines
            if not line:
                break
            # Add line as criterion if it's not just a header
            if line and not line.endswith(':'):
                criteria.append(line)
            i += 1
            
        return ParsedTask(
            main_task=main_task,
            components=[TaskComponent(text=main_task, criteria=criteria)],
            context={"criteria": criteria},
            task_type="criteria_search"
        )

    def _analyze_criterion(self, criterion: str) -> Dict[str, Any]:
        """Enhanced criterion analysis with value extraction"""
        for ctype, patterns in self.criteria_patterns.items():
            for pattern in patterns:
                if match := re.search(pattern, criterion, re.IGNORECASE):
                    return {
                        'type': ctype,
                        'value': match.group(1) if match.groups() else None,
                        'filter_type': self._determine_filter_type(ctype, criterion),
                        'original': criterion
                    }
        
        return {
            'type': 'general',
            'value': criterion,
            'filter_type': 'contains',
            'original': criterion
        }

    def _determine_filter_type(self, criterion_type: str, criterion: str) -> str:
        """Determine how the criterion should be applied as a filter"""
        if criterion_type == 'financial':
            return 'greater_than' if re.search(r'more|greater|over|above', criterion, re.IGNORECASE) else 'equals'
        elif criterion_type == 'status':
            return 'not_contains' if 'not' in criterion.lower() else 'contains'
        elif criterion_type == 'temporal':
            return 'range' if re.search(r'between|from.*to', criterion, re.IGNORECASE) else 'equals'
        return 'contains'

    def _extract_base_query(self, task: str) -> str:
        """Extract the base search query from the main task"""
        # Remove common prefixes more accurately
        cleaned = re.sub(
            r'^(?:please\s+)?(?:compile|create|make|get|find)?\s*(?:a|the)?\s*list\s*of\s*',
            '',
            task,
            flags=re.IGNORECASE
        )
        # Get the part before any criteria indicators, preserving key terms
        base = re.split(r'(?:with|having|meeting|satisfying)\s+(?:the\s+)?(?:following|these)', cleaned)[0]
        # Clean up but preserve important qualifiers
        base = re.sub(r'\s+', ' ', base).strip()
        return base

    def _is_list_task(self, text: str) -> bool:
        """Check if text indicates a list-compilation task"""
        return any(re.search(pattern, text.lower()) for pattern in self.list_indicators)

    def _parse_multi_criteria_task(self, lines: List[str]) -> ParsedTask:
        """Parse a task with multiple criteria"""
        main_task = lines[0]
        criteria = []
        i = 1
        
        # Keep collecting criteria until we hit an empty line or end of lines
        while i < len(lines) and lines[i].strip():
            if not lines[i].startswith('They '):  # Skip prefix if present
                criteria.append(lines[i].strip())
            i += 1
            
        return ParsedTask(
            main_task=main_task,
            components=[TaskComponent(text=main_task, criteria=criteria)],
            context={"criteria": criteria},
            task_type="criteria_search"
        )
