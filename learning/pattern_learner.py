from typing import Dict, List, Tuple, Any
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

        # Add completion specific patterns
        self.completion_patterns = {
            'is_statement': r'^[a-zA-Z]+\s+is',
            'means_statement': r'^[a-zA-Z]+\s+means',
            'definition': r'^(?:the|a|an)\s+[a-zA-Z]+\s+is',
            'open_ended': r'^.*\.{3}$'
        }
        
        # Add solution templates for completions
        self.solution_templates['completion'] = {
            'type': 'completion',
            'tool': 'gemini',
            'template': 'Complete this thought: {task}'
        }
        
        # Add meta-learning settings
        self.meta_patterns = {}
        self.pattern_effectiveness = {}
        self.adaptation_threshold = 0.6
        self.min_pattern_confidence = 0.5
        
        # Add feedback tracking
        self.pattern_feedback = {}
        self.success_history = []

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
        
        # Update meta-patterns
        meta_features = self._extract_meta_features(task, solution)
        self._update_meta_patterns(meta_features, performance)
        
        # Adapt thresholds based on performance
        self._adapt_thresholds(performance if performance else 0.5)

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
        similar_patterns = sorted(similar_patterns, key=lambda x: x[1], reverse=True)
        
        # Apply meta-pattern matching
        meta_features = self._extract_meta_features(task, {})
        meta_matches = self._find_meta_matches(meta_features)
        
        # Combine with direct pattern matches
        combined_matches = self._combine_matches(similar_patterns, meta_matches)
        
        return combined_matches

    def _detect_pattern_type(self, task: str) -> str:
        """Enhanced pattern type detection"""
        task_lower = task.lower()
        
        # Check completion patterns first
        for pattern in self.completion_patterns.values():
            if re.match(pattern, task_lower):
                return 'completion'
        
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

    def _extract_meta_features(self, task: str, solution: Dict) -> Dict[str, Any]:
        """Extract meta-features from task and solution"""
        return {
            'task_length': len(task.split()),
            'solution_type': solution.get('type', 'unknown'),
            'complexity': self._calculate_complexity(task),
            'pattern_type': self._detect_pattern_type(task),
            'has_entities': bool(re.search(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', task))
        }

    def _update_meta_patterns(self, features: Dict[str, Any], performance: float):
        """Update meta-patterns with new features"""
        pattern_key = f"{features['pattern_type']}_{features['solution_type']}"
        
        if pattern_key not in self.meta_patterns:
            self.meta_patterns[pattern_key] = {
                'features': [],
                'performances': []
            }
            
        self.meta_patterns[pattern_key]['features'].append(features)
        self.meta_patterns[pattern_key]['performances'].append(performance)
        
        # Prune old patterns if needed
        self._prune_old_patterns(pattern_key)

    def _adapt_thresholds(self, latest_performance: float):
        """Adapt thresholds based on performance"""
        self.success_history.append(latest_performance)
        if len(self.success_history) > 10:
            recent_performance = sum(self.success_history[-10:]) / 10
            
            # Adjust thresholds
            if recent_performance < self.adaptation_threshold:
                self.min_pattern_confidence += 0.05
            else:
                self.min_pattern_confidence = max(0.5, self.min_pattern_confidence - 0.02)
                
            # Keep threshold in reasonable range
            self.min_pattern_confidence = min(0.9, max(0.5, self.min_pattern_confidence))

    def _find_meta_matches(self, features: Dict[str, Any]) -> List[Tuple[Dict, float]]:
        """Find matches based on meta-patterns"""
        matches = []
        
        for pattern_key, pattern_data in self.meta_patterns.items():
            similarity = self._calculate_meta_similarity(features, pattern_data['features'])
            if similarity >= self.min_pattern_confidence:
                avg_performance = sum(pattern_data['performances']) / len(pattern_data['performances'])
                matches.append((pattern_data['features'][-1], similarity * avg_performance))
                
        return matches
