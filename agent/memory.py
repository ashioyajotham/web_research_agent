from typing import Dict, List
import datetime

class Memory:
    def __init__(self):
        self.short_term = []  # Recent interactions
        self.long_term = {}   # Learned patterns/experiences
        
    def add(self, step: Dict, result: Dict):
        timestamp = datetime.datetime.now()
        self.short_term.append({
            'timestamp': timestamp,
            'step': step,
            'result': result
        })
        
    def get_relevant_context(self, query: str) -> List[Dict]:
        # Implement semantic search over memory
        return []