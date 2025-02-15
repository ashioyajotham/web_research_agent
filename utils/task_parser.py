from typing import List, Dict
import re

class TaskParser:
    def __init__(self):
        self.bullet_patterns = [
            r'^\s+\w+',  # Indented text
            r'^\s*•\s+',  # Bullet point
            r'^\s*[-*]\s+',  # Hyphen or asterisk
            r'^\s*\d+\.\s+'  # Numbered
        ]

    def parse_tasks(self, content: str) -> List[Dict]:
        lines = content.splitlines()
        tasks = []
        current_task = None
        current_criteria = []
        in_criteria_block = False
        prev_indent = 0
        
        for line in lines:
            if not line.strip():
                continue
            
            # Calculate indentation level
            indent = len(line) - len(line.lstrip())
            
            # Check if this is a criteria list header
            if 'criteria:' in line.lower():
                in_criteria_block = True
                current_task = line.strip()
                prev_indent = indent
                continue
            
            # Handle criteria items
            if in_criteria_block and indent > prev_indent:
                current_criteria.append(line.strip())
                continue
            
            # New main task detected
            if indent == 0:
                if current_task:
                    tasks.append({
                        'task': current_task,
                        'subtasks': current_criteria,
                        'type': 'criteria' if current_criteria else 'single'
                    })
                current_task = line.strip()
                current_criteria = []
                in_criteria_block = False
                
            prev_indent = indent
        
        # Add final task
        if current_task:
            tasks.append({
                'task': current_task,
                'subtasks': current_criteria,
                'type': 'criteria' if current_criteria else 'single'
            })
            
        return tasks
