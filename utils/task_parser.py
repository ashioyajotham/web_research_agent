from typing import List, Dict
import re

class TaskParser:
    def __init__(self):
        self.criteria_markers = [
            'following criteria:',
            'criteria:',
            'following requirements:',
            'requirements:'
        ]

    def parse_tasks(self, content: str) -> List[Dict]:
        lines = content.splitlines()
        tasks = []
        current_task = None
        current_criteria = []
        collecting_criteria = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line indicates criteria collection should start
            if any(marker in line.lower() for marker in self.criteria_markers):
                collecting_criteria = True
                current_task = line
                continue
                
            # If we're collecting criteria and line is indented or starts with criteria markers
            if collecting_criteria and (line.startswith(('They ', 'It ', 'The '))):
                current_criteria.append(line)
                continue
                
            # If this is a new main task
            if not collecting_criteria or line[0].isupper():
                # Save previous task if exists
                if current_task:
                    tasks.append({
                        'task': current_task,
                        'subtasks': current_criteria,
                        'type': 'criteria' if current_criteria else 'single'
                    })
                current_task = line
                current_criteria = []
                collecting_criteria = False
                
        # Add the last task
        if current_task:
            tasks.append({
                'task': current_task,
                'subtasks': current_criteria,
                'type': 'criteria' if current_criteria else 'single'
            })
            
        return tasks
