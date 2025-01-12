from typing import Dict, List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class PatternLearner:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.patterns: List[str] = []
        self.solutions: List[Dict] = []

    def add_pattern(self, task: str, solution: Dict):
        self.patterns.append(task)
        self.solutions.append(solution)
        
        if len(self.patterns) > 1:  # Only fit when we have enough data
            self.vectorizer.fit(self.patterns)

    def find_similar_patterns(self, task: str, threshold: float = 0.7) -> List[Tuple[Dict, float]]:
        if not self.patterns:
            return []

        task_vector = self.vectorizer.transform([task])
        pattern_vectors = self.vectorizer.transform(self.patterns)
        
        similarities = cosine_similarity(task_vector, pattern_vectors)[0]
        
        similar_solutions = [
            (self.solutions[i], float(sim))
            for i, sim in enumerate(similarities)
            if sim >= threshold
        ]
        
        return sorted(similar_solutions, key=lambda x: x[1], reverse=True)

    def generalize_solution(self, similar_patterns: List[Tuple[Dict, float]]) -> Dict:
        if not similar_patterns:
            return {}

        # Weight solutions by similarity score
        weighted_solutions = []
        total_weight = 0

        for solution, similarity in similar_patterns:
            weighted_solutions.append((solution, similarity))
            total_weight += similarity

        # Create generalized solution
        generalized = {}
        for solution, weight in weighted_solutions:
            for key, value in solution.items():
                if key not in generalized:
                    generalized[key] = []
                generalized[key].append((value, weight/total_weight))

        # Combine weighted values
        final_solution = {}
        for key, weighted_values in generalized.items():
            if isinstance(weighted_values[0][0], (int, float)):
                final_solution[key] = sum(val * weight for val, weight in weighted_values)
            else:
                # For non-numeric values, take the highest weighted value
                final_solution[key] = max(weighted_values, key=lambda x: x[1])[0]

        return final_solution
