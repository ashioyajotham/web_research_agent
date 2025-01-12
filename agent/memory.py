from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import json
from datetime import datetime

@dataclass
class Experience:
    task: str
    plan: Dict[str, Any]
    result: Dict[str, Any]
    evaluation: Dict[str, Any]
    timestamp: datetime

class Memory:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.experiences = self._load_experiences()

    def _load_experiences(self) -> List[Experience]:
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                return [Experience(**exp) for exp in data]
        except FileNotFoundError:
            return []

    def store_experience(self, experience: Experience):
        self.experiences.append(experience)
        self._save_experiences()

    def get_relevant_experiences(self, task: str, limit: int = 5) -> List[Experience]:
        # Simple relevance sorting based on task similarity
        sorted_experiences = sorted(
            self.experiences,
            key=lambda x: self._calculate_similarity(x.task, task),
            reverse=True
        )
        return sorted_experiences[:limit]

    def _save_experiences(self):
        with open(self.storage_path, 'w') as f:
            json.dump([asdict(exp) for exp in self.experiences], f)

    def _calculate_similarity(self, task1: str, task2: str) -> float:
        # Simple word overlap similarity
        words1 = set(task1.lower().split())
        words2 = set(task2.lower().split())
        return len(words1.intersection(words2)) / len(words1.union(words2))
