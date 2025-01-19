from typing import Dict, List
from dataclasses import dataclass
import json
import numpy as np
from pathlib import Path

@dataclass
class Experience:
    task_pattern: str
    steps: List[Dict]
    outcome: bool
    metrics: Dict

class Learner:
    def __init__(self, storage_path: Path = Path("data/experiences.json")):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.experiences = self._load_experiences()
        
        # Track performance metrics
        self.metrics = {
            'tool_success_rate': {},
            'pattern_effectiveness': {},
            'prompt_performance': {}
        }

    def update(self, step: Dict, result: Dict, outcome: Dict = None) -> None:
        if outcome is None:
            outcome = {
                'success': result.get('success', False),
                'error': result.get('error', None)
            }
        
        experience = {
            'step': step,
            'result': result,
            'outcome': outcome
        }
        
        self.experiences.append(experience)

    def get_recommendations(self, task: str) -> Dict:
        pattern = self._extract_pattern(task)
        similar_experiences = self._find_similar_experiences(pattern)
        
        return {
            'suggested_tools': self._get_successful_tools(similar_experiences),
            'prompt_templates': self._get_effective_prompts(similar_experiences),
            'estimated_success': self._calculate_success_probability(pattern)
        }

    def _extract_pattern(self, task: str) -> str:
        # Simple pattern extraction based on key phrases and structure
        # Can be enhanced with more sophisticated NLP
        patterns = [
            "search and code",
            "browse and extract",
            "code modification",
            "web research"
        ]
        return next((p for p in patterns if p in task.lower()), "general")

    def _calculate_metrics(self, steps: List[Dict], outcome: Dict) -> Dict:
        return {
            'execution_time': outcome.get('execution_time', 0),
            'tool_usage': self._count_tool_usage(steps),
            'success_rate': float(outcome.get('success', False))
        }

    def _update_metrics(self, experience: Experience) -> None:
        # Update tool success rates
        for tool, count in experience.metrics['tool_usage'].items():
            if tool not in self.metrics['tool_success_rate']:
                self.metrics['tool_success_rate'][tool] = []
            self.metrics['tool_success_rate'][tool].append(experience.outcome)

        # Update pattern effectiveness
        pattern = experience.task_pattern
        if pattern not in self.metrics['pattern_effectiveness']:
            self.metrics['pattern_effectiveness'][pattern] = []
        self.metrics['pattern_effectiveness'][pattern].append(experience.outcome)

    def _find_similar_experiences(self, pattern: str) -> List[Experience]:
        return [exp for exp in self.experiences 
                if exp['task_pattern'] == pattern]

    def _get_successful_tools(self, experiences: List[Dict]) -> Dict:
        tool_success = {}
        for exp in experiences:
            if exp['outcome']:
                for tool, count in exp['metrics']['tool_usage'].items():
                    tool_success[tool] = tool_success.get(tool, 0) + count
        return tool_success

    def _count_tool_usage(self, steps: List[Dict]) -> Dict:
        usage = {}
        for step in steps:
            tool = step['tool']
            usage[tool] = usage.get(tool, 0) + 1
        return usage

    def _load_experiences(self) -> List[Dict]:
        if self.storage_path.exists():
            return json.loads(self.storage_path.read_text())
        return []

    def _save_experiences(self) -> None:
        self.storage_path.write_text(json.dumps(self.experiences, indent=2))