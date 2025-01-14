from typing import Dict, List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import re



class PatternLearner:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.patterns: List[str] = []
        self.solutions: List[Dict] = []
        
        # Add embeddings support
        self.embedding_model = None
        self.pattern_embeddings = []
        self.performance_metrics = {}
        
        # Add new pattern types
        self.pattern_types = {
            'completion': r'^[a-zA-Z]+\s+is\s*',
            'general_query': r'^(?:tell|explain|describe|what)',
            'factual': r'^(?:who|what|when|where|why|how)',
            'action': r'^(?:find|search|get|list|show)'
        }
        
        # Add solution templates
        self.solution_templates = {
            'completion': {
                'type': 'completion',
                'tool': 'gemini',
                'template': '{task}'
            },
            'general_query': {
                'type': 'general',
                'tool': 'gemini',
                'template': 'Answer this query: {task}'
            }
        }
        
        # Track pattern success rates
        self.pattern_success_rates = {}

    def initialize_embeddings(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
        """Initialize embedding model for better pattern matching"""
        from sentence_transformers import SentenceTransformer
        self.embedding_model = SentenceTransformer(model_name)

    def add_pattern(self, task: str, solution: Dict, performance: float = None):
        """Enhanced pattern storage with type detection"""
        pattern_type = self._detect_pattern_type(task)
        
        # Store pattern with its type
        self.patterns.append({
            'text': task,
            'type': pattern_type,
            'solution': solution,
            'performance': performance
        })
        
        # Update success rates
        if pattern_type not in self.pattern_success_rates:
            self.pattern_success_rates[pattern_type] = []
        self.pattern_success_rates[pattern_type].append(performance if performance else 0.5)
        
        # Generate embeddings if available
        if self.embedding_model:
            embedding = self.embedding_model.encode(task)
            self.pattern_embeddings.append(embedding)

    def find_similar_patterns(self, task: str, threshold: float = 0.7) -> List[Tuple[Dict, float]]:
        """Enhanced pattern matching with type awareness"""
        if not self.patterns:
            return []

        task_type = self._detect_pattern_type(task)
        
        # Get base template if available
        template = self.solution_templates.get(task_type)
        if template:
            return [(template, 0.9)]  # High confidence for direct template matches
        
        # Find similar patterns of the same type
        similar_patterns = []
        
        for i, pattern in enumerate(self.patterns):
            if pattern['type'] == task_type:
                similarity = self._calculate_similarity(task, pattern['text'])
                if similarity >= threshold:
                    similar_patterns.append((pattern['solution'], similarity))
        
        # Sort by similarity score
        return sorted(similar_patterns, key=lambda x: x[1], reverse=True)

    def _detect_pattern_type(self, task: str) -> str:
        """Detect the type of pattern"""
        task_lower = task.lower()
        
        for pattern_type, pattern in self.pattern_types.items():
            if re.search(pattern, task_lower):
                return pattern_type
        
        return 'general_query'  # default type

    def _calculate_similarity(self, task1: str, task2: str) -> float:
        """Calculate similarity between two tasks using multiple methods"""
        # Use embeddings if available
        if self.embedding_model:
            emb1 = self.embedding_model.encode(task1)
            emb2 = self.embedding_model.encode(task2)
            embedding_sim = cosine_similarity([emb1], [emb2])[0][0]
            
            # Combine with other similarity measures
            text_sim = self._calculate_text_similarity(task1, task2)
            return 0.7 * embedding_sim + 0.3 * text_sim
            
        return self._calculate_text_similarity(task1, task2)

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using TF-IDF and other metrics"""
        task_vector = self.vectorizer.transform([text1])
        pattern_vectors = self.vectorizer.transform([text2])
        
        similarities = cosine_similarity(task_vector, pattern_vectors)[0]
        
        return float(similarities[0])

    def generalize_solution(self, similar_patterns: List[Tuple[Dict, float]]) -> Dict:
        """Generate solution with enhanced template handling"""
        if not similar_patterns:
            return {}

        # If first pattern has high confidence, use it directly
        if similar_patterns[0][1] > 0.9:
            return similar_patterns[0][0]

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
