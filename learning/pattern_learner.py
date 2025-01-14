from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
import json
from datetime import datetime
from pathlib import Path
import re
from collections import defaultdict


class PatternCluster:
    """Represents a cluster of similar patterns"""
    def __init__(self, base_pattern: str):
        self.base_pattern = base_pattern
        self.variations = []
        self.success_rate = 0.0
        self.usage_count = 0
        self.last_updated = datetime.now()
        self.metadata = {}

    def add_variation(self, pattern: str, success: bool):
        self.variations.append({
            'pattern': pattern,
            'success': success,
            'timestamp': datetime.now()
        })
        self.update_metrics()

    def update_metrics(self):
        if self.variations:
            successful = sum(1 for v in self.variations if v['success'])
            self.success_rate = successful / len(self.variations)
        self.usage_count += 1
        self.last_updated = datetime.now()

class AdaptivePatternLearner:
    """More flexible and adaptive pattern learning system"""
    def __init__(self, storage_path: str = "./patterns"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Enhanced vectorization with multiple models
        self.vectorizers = {
            'tfidf': TfidfVectorizer(ngram_range=(1, 3)),
            'char': TfidfVectorizer(analyzer='char', ngram_range=(2, 4))
        }
        
        # Pattern storage with hierarchical organization
        self.patterns: Dict[str, Dict[str, PatternCluster]] = defaultdict(dict)
        self.pattern_hierarchy = defaultdict(list)
        
        # Adaptive thresholds
        self.similarity_threshold = 0.75  # Dynamically adjusted
        self.minimum_confidence = 0.6
        self.learning_rate = 0.1
        
        # Performance tracking
        self.performance_history = []
        self.adaptation_metrics = defaultdict(list)
        
        # Load existing patterns
        self._load_patterns()

    def learn_pattern(self, task: str, solution: Dict, performance: float) -> None:
        """Learn new pattern with enhanced context awareness"""
        try:
            # Extract task characteristics
            task_type = self._identify_task_type(task)
            task_components = self._extract_components(task)
            
            # Create or update pattern cluster
            pattern_key = self._generate_pattern_key(task_components)
            
            if pattern_key not in self.patterns[task_type]:
                self.patterns[task_type][pattern_key] = PatternCluster(task)
            
            cluster = self.patterns[task_type][pattern_key]
            cluster.add_variation(task, performance >= self.minimum_confidence)
            
            # Update pattern hierarchy            self._update_hierarchy(task_type, pattern_key, task_components)
            
            # Adapt thresholds based on performance
            self._adapt_thresholds(performance)
            
            # Store performance metrics
            self._track_performance(task_type, performance)
            
            # Periodically save patterns
            self._save_patterns()
            
        except Exception as e:
            print(f"Pattern learning failed: {e}")

    def find_similar_patterns(self, task: str, context: Dict = None) -> List[Dict]:
        """Find similar patterns with context awareness"""
        try:
            task_type = self._identify_task_type(task)
            task_components = self._extract_components(task)
            
            # Get relevant patterns based on hierarchy
            relevant_patterns = self._get_relevant_patterns(task_type, task_components)
            
            if not relevant_patterns:
                return []
            
            # Calculate similarities using multiple methods
            similarities = self._calculate_similarities(task, relevant_patterns)
            
            # Filter and rank patterns
            matched_patterns = self._rank_patterns(similarities, context)
            
            return matched_patterns
            
        except Exception as e:
            print(f"Pattern matching failed: {e}")
            return []

    def _identify_task_type(self, task: str) -> str:
        """Enhanced task type identification"""
        task_lower = task.lower()
        
        # Use more flexible pattern matching
        type_indicators = {
            'search': ['find', 'search', 'locate', 'get'],
            'analysis': ['analyze', 'compare', 'evaluate', 'assess'],
            'generation': ['create', 'generate', 'write', 'compose'],
            'transformation': ['convert', 'transform', 'change', 'modify'],
            'extraction': ['extract', 'pull', 'gather', 'collect']
        }
        
        # Score each type
        type_scores = defaultdict(float)
        for type_name, indicators in type_indicators.items():
            for indicator in indicators:
                if indicator in task_lower:
                    type_scores[type_name] += 1
                    
        # Return highest scoring type or 'general'
        return max(type_scores.items(), key=lambda x: x[1])[0] if type_scores else 'general'

    def _extract_components(self, task: str) -> Dict[str, Any]:
        """Extract task components for better pattern matching"""
        return {
            'verbs': self._extract_verbs(task),
            'entities': self._extract_entities(task),
            'constraints': self._extract_constraints(task),
            'structure': self._analyze_structure(task)
        }

    def _adapt_thresholds(self, performance: float):
        """Adapt thresholds based on performance"""
        if len(self.performance_history) >= 10:
            avg_performance = np.mean(self.performance_history[-10:])
            
            # Adjust similarity threshold
            if avg_performance < 0.7:
                self.similarity_threshold = min(0.9, self.similarity_threshold + self.learning_rate)
            elif avg_performance > 0.8:
                self.similarity_threshold = max(0.6, self.similarity_threshold - self.learning_rate)
                
            # Adjust minimum confidence
            if avg_performance > 0.8:
                self.minimum_confidence = min(0.8, self.minimum_confidence + self.learning_rate)
            elif avg_performance < 0.6:
                self.minimum_confidence = max(0.4, self.minimum_confidence - self.learning_rate)

    def _calculate_similarities(self, task: str, patterns: List[Dict]) -> List[Tuple[Dict, float]]:
        """Calculate similarities using multiple methods"""
        similarities = []
        
        for pattern in patterns:
            # Calculate different similarity scores
            tfidf_sim = self._calculate_tfidf_similarity(task, pattern['pattern'])
            struct_sim = self._calculate_structural_similarity(task, pattern['pattern'])
            semantic_sim = self._calculate_semantic_similarity(task, pattern['pattern'])
            
            # Weighted combination of similarities
            combined_sim = (0.5 * tfidf_sim + 0.3 * struct_sim + 0.2 * semantic_sim)
            
            similarities.append((pattern, combined_sim))
            
        return similarities

    def _rank_patterns(self, similarities: List[Tuple[Dict, float]], context: Dict = None) -> List[Dict]:
        """Rank patterns considering context and performance history"""
        ranked_patterns = []
        
        for pattern, similarity in similarities:
            if similarity >= self.similarity_threshold:
                # Adjust score based on pattern's success rate and context
                adjusted_score = similarity
                
                if context:
                    context_boost = self._calculate_context_relevance(pattern, context)
                    adjusted_score *= (1 + context_boost)
                
                pattern['match_score'] = adjusted_score
                ranked_patterns.append(pattern)
        
        # Sort by adjusted score
        return sorted(ranked_patterns, key=lambda x: x['match_score'], reverse=True)

    def _save_patterns(self):
        """Save patterns with enhanced metadata"""
        try:
            data = {
                'patterns': {
                    task_type: {
                        key: {
                            'base_pattern': cluster.base_pattern,
                            'variations': cluster.variations,
                            'success_rate': cluster.success_rate,
                            'usage_count': cluster.usage_count,
                            'last_updated': cluster.last_updated.isoformat(),
                            'metadata': cluster.metadata
                        }
                        for key, cluster in patterns.items()
                    }
                    for task_type, patterns in self.patterns.items()
                },
                'hierarchy': dict(self.pattern_hierarchy),
                'metrics': {
                    'similarity_threshold': self.similarity_threshold,
                    'minimum_confidence': self.minimum_confidence,
                    'adaptation_metrics': dict(self.adaptation_metrics)
                }
            }
            
            with open(self.storage_path / "patterns.json", 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Pattern saving failed: {e}")

    def _load_patterns(self):
        """Load patterns with backwards compatibility"""
        try:
            if (self.storage_path / "patterns.json").exists():
                with open(self.storage_path / "patterns.json") as f:
                    data = json.load(f)
                
                # Load patterns with conversion to PatternCluster objects
                for task_type, patterns in data.get('patterns', {}).items():
                    for key, pattern_data in patterns.items():
                        cluster = PatternCluster(pattern_data['base_pattern'])
                        cluster.variations = pattern_data['variations']
                        cluster.success_rate = pattern_data['success_rate']
                        cluster.usage_count = pattern_data['usage_count']
                        cluster.last_updated = datetime.fromisoformat(pattern_data['last_updated'])
                        cluster.metadata = pattern_data.get('metadata', {})
                        self.patterns[task_type][key] = cluster
                
                # Load additional data
                self.pattern_hierarchy = defaultdict(list, data.get('hierarchy', {}))
                metrics = data.get('metrics', {})
                self.similarity_threshold = metrics.get('similarity_threshold', self.similarity_threshold)
                self.minimum_confidence = metrics.get('minimum_confidence', self.minimum_confidence)
                self.adaptation_metrics = defaultdict(list, metrics.get('adaptation_metrics', {}))
                
        except Exception as e:
            print(f"Pattern loading failed: {e}")
            # Initialize empty state
            self.patterns = defaultdict(dict)
            self.pattern_hierarchy = defaultdict(list)
``` 
