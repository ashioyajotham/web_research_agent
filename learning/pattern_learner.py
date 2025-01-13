from typing import Dict, List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

class PatternLearner:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.patterns: List[str] = []
        self.solutions: List[Dict] = []
        
        # Add embeddings support
        self.embedding_model = None
        self.pattern_embeddings = []
        self.performance_metrics = {}

    def initialize_embeddings(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
        """Initialize embedding model for better pattern matching"""
        from sentence_transformers import SentenceTransformer
        self.embedding_model = SentenceTransformer(model_name)

    def add_pattern(self, task: str, solution: Dict, performance: float = None):
        self.patterns.append(task)
        self.solutions.append(solution)
        
        if len(self.patterns) > 1:  # Only fit when we have enough data
            self.vectorizer.fit(self.patterns)
        
        # Track performance metrics
        if performance:
            self.performance_metrics[task] = {
                'success_rate': performance,
                'timestamp': datetime.now(),
                'solution_type': solution.get('type', 'unknown')
            }
        
        # Generate and store embeddings
        if self.embedding_model:
            embedding = self.embedding_model.encode(task)
            self.pattern_embeddings.append(embedding)

    def find_similar_patterns(self, task: str, threshold: float = 0.7) -> List[Tuple[Dict, float]]:
        """Enhanced pattern matching using both TF-IDF and embeddings"""
        if not self.patterns:
            return []

        results = []
        
        # TF-IDF similarity
        tfidf_similarities = self._get_tfidf_similarities(task)
        
        # Embedding similarity if available
        if self.embedding_model:
            embedding_similarities = self._get_embedding_similarities(task)
            
            # Combine similarities with weighted average
            for i, (solution, tfidf_sim) in enumerate(tfidf_similarities):
                emb_sim = embedding_similarities[i][1]
                combined_sim = (tfidf_sim * 0.4 + emb_sim * 0.6)  # Weight embeddings higher
                
                if combined_sim >= threshold:
                    results.append((solution, combined_sim))
        else:
            results = [s for s in tfidf_similarities if s[1] >= threshold]
            
        return sorted(results, key=lambda x: x[1], reverse=True)

    def _get_embedding_similarities(self, task: str) -> List[Tuple[Dict, float]]:
        """Calculate embedding-based similarities"""
        task_embedding = self.embedding_model.encode(task)
        similarities = []
        
        for i, pattern_embedding in enumerate(self.pattern_embeddings):
            similarity = cosine_similarity([task_embedding], [pattern_embedding])[0][0]
            similarities.append((self.solutions[i], float(similarity)))
            
        return similarities

    def _get_tfidf_similarities(self, task: str) -> List[Tuple[Dict, float]]:
        task_vector = self.vectorizer.transform([task])
        pattern_vectors = self.vectorizer.transform(self.patterns)
        
        similarities = cosine_similarity(task_vector, pattern_vectors)[0]
        
        return [
            (self.solutions[i], float(sim))
            for i, sim in enumerate(similarities)
        ]

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
