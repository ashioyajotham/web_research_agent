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
                experiences = []
                for exp in data:
                    # Convert timestamp string back to datetime
                    exp['timestamp'] = datetime.fromisoformat(exp['timestamp'])
                    experiences.append(Experience(**exp))
                return experiences
        except FileNotFoundError:
            # Create empty file if it doesn't exist
            with open(self.storage_path, 'w') as f:
                json.dump([], f)
            return []
        except json.JSONDecodeError:
            # Handle corrupted file by creating new empty file
            with open(self.storage_path, 'w') as f:
                json.dump([], f)
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
            # Convert experiences to dict and datetime to ISO format string
            experiences_data = []
            for exp in self.experiences:
                exp_dict = asdict(exp)
                exp_dict['timestamp'] = exp_dict['timestamp'].isoformat()
                experiences_data.append(exp_dict)
            json.dump(experiences_data, f, indent=2)

    def _calculate_similarity(self, task1: str, task2: str) -> float:
        # Simple word overlap similarity
        words1 = set(task1.lower().split())
        words2 = set(task2.lower().split())
        return len(words1.intersection(words2)) / len(words1.union(words2))
