from typing import Dict, List, Tuple, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
from datetime import datetime
from pathlib import Path
import re

class PatternLearner:
    def __init__(self, storage_path: str = "./patterns"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Core components
        self.vectorizer = TfidfVectorizer()
        self.patterns: Dict[str, List[Dict]] = {}
        self.threshold = 0.75
        
        # Load existing patterns
        self._load_patterns()

    def learn_pattern(self, task: str, solution: Dict, success: bool) -> None:
        """Learn new pattern from task execution"""
        task_type = self._identify_task_type(task)
        pattern = {
            "task": task,
            "solution": solution,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "similarity_scores": []
        }
        
        if task_type not in self.patterns:
            self.patterns[task_type] = []
            
        self.patterns[task_type].append(pattern)
        self._save_patterns()

    def find_similar_pattern(self, task: str) -> Tuple[Dict, float]:
        """Find most similar previous pattern"""
        task_type = self._identify_task_type(task)
        if task_type not in self.patterns:
            return None, 0.0
            
        task_vector = self.vectorizer.fit_transform([task])
        max_similarity = 0.0
        best_match = None
        
        for pattern in self.patterns[task_type]:
            pattern_vector = self.vectorizer.transform([pattern["task"]])
            similarity = cosine_similarity(task_vector, pattern_vector)[0][0]
            
            if similarity > max_similarity and similarity > self.threshold:
                max_similarity = similarity
                best_match = pattern
                
        return best_match, max_similarity

    def _identify_task_type(self, task: str) -> str:
        """Identify task type based on content"""
        if any(term in task.lower() for term in ["list", "compile", "gather"]):
            return "collection"
        elif any(term in task.lower() for term in ["analyze", "compare", "evaluate"]):
            return "analysis"
        elif any(term in task.lower() for term in ["find", "search", "locate"]):
            return "search"
        return "general"

    def _save_patterns(self) -> None:
        """Save patterns to disk"""
        patterns_file = self.storage_path / "patterns.json"
        with open(patterns_file, 'w') as f:
            json.dump(self.patterns, f, indent=2)

    def _load_patterns(self) -> None:
        """Load patterns from disk"""
        patterns_file = self.storage_path / "patterns.json"
        if patterns_file.exists():
            with open(patterns_file) as f:
                self.patterns = json.load(f)
