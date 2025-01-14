from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re

@dataclass
class TaskComponent:
    text: str
    criteria: List[str]
    parent_task: Optional[str] = None
    is_subtask: bool = False

@dataclass
class ParsedTask:
    main_task: str
    components: List[TaskComponent]
    context: Dict[str, Any]

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
            r'criteria:'
        ]

    def parse_tasks(self, content: str) -> List[ParsedTask]:
        """Parse content into structured tasks with relationships"""
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        tasks = []
        current_task = None
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if line starts a new multi-criteria task
            if self._is_list_task(line):
                current_task = self._parse_multi_criteria_task(lines[i:])
                tasks.append(current_task)
                i += len(current_task.components)
            else:
                # Single independent task
                tasks.append(ParsedTask(
                    main_task=line,
                    components=[TaskComponent(text=line, criteria=[])],
                    context={}
                ))
                i += 1
                
        return tasks

    def _is_list_task(self, text: str) -> bool:
        """Check if text indicates a list-compilation task"""
        return any(re.search(pattern, text.lower()) for pattern in self.list_indicators)

    def _parse_multi_criteria_task(self, lines: List[str]) -> ParsedTask:
        """Parse a task with multiple criteria"""
        main_task = lines[0]
        components = [TaskComponent(text=main_task, criteria=[])]
        criteria = []
        
        # Find criteria in subsequent lines
        for line in lines[1:]:
            if line.startswith('-') or line.startswith('•'):
                criteria.append(line.lstrip('- •').strip())
                components.append(TaskComponent(
                    text=line.lstrip('- •').strip(),
                    criteria=[],
                    parent_task=main_task,
                    is_subtask=True
                ))
                
        # Update main task component with criteria
        components[0].criteria = criteria
        
        return ParsedTask(
            main_task=main_task,
            components=components,
            context={'type': 'multi_criteria', 'criteria_count': len(criteria)}
        )
