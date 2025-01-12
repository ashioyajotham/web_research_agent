from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass
import json
import os
from datetime import datetime
import re
from collections import Counter
import nltk
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

@dataclass
class LearningEntry:
    task_pattern: str
    successful_strategies: List[Dict[str, Any]]
    failed_strategies: List[Dict[str, Any]]
    tool_effectiveness: Dict[str, float]
    timestamp: str

class TaskPattern:
    def __init__(self, task_type: str, key_entities: Set[str], action_verbs: Set[str]):
        self.task_type = task_type
        self.key_entities = key_entities
        self.action_verbs = action_verbs
        
    def similarity_score(self, other: 'TaskPattern') -> float:
        entity_similarity = len(self.key_entities & other.key_entities) / \
                          max(len(self.key_entities | other.key_entities), 1)
        verb_similarity = len(self.action_verbs & other.action_verbs) / \
                         max(len(self.action_verbs | other.action_verbs), 1)
        type_match = 1.0 if self.task_type == other.task_type else 0.0
        
        return (entity_similarity * 0.4 + verb_similarity * 0.3 + type_match * 0.3)

class Learner:
    def __init__(self, learning_file: str = "agent_learning.json"):
        self.learning_file = learning_file
        self.learnings: Dict[str, LearningEntry] = {}
        self._load_learning()
        
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
            nltk.download('averaged_perceptron_tagger')
            nltk.download('stopwords')
            nltk.download('wordnet')
            
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        self.task_types = {
            'research': r'find|search|analyze|summarize|explain|describe|what|how|when|where|why',
            'coding': r'implement|code|write|create|develop|build|generate|function|class|algorithm',
            'analysis': r'compare|evaluate|assess|measure|calculate|determine|analyze',
            'extraction': r'extract|pull|gather|collect|obtain|get',
        }
        
    def _load_learning(self):
        """Load past learnings from file"""
        if os.path.exists(self.learning_file):
            with open(self.learning_file, 'r') as f:
                data = json.load(f)
                for pattern, entry in data.items():
                    self.learnings[pattern] = LearningEntry(**entry)

    def _save_learning(self):
        """Save learnings to file"""
        with open(self.learning_file, 'w') as f:
            data = {
                pattern: vars(entry) 
                for pattern, entry in self.learnings.items()
            }
            json.dump(data, f, indent=2)

    def learn_from_execution(self, 
                           task: str, 
                           execution_data: Dict[str, Any],
                           evaluation_result: Dict[str, Any]):
        """Learn from task execution with pattern matching"""
        pattern = self._extract_task_pattern(task)
        
        if pattern not in self.learnings:
            self.learnings[pattern] = LearningEntry(
                task_pattern=pattern,
                successful_strategies=[],
                failed_strategies=[],
                tool_effectiveness={},
                timestamp=datetime.now().isoformat()
            )
            
        entry = self.learnings[pattern]
        
        # Update strategies
        strategy = execution_data.get('strategy', {})
        if evaluation_result.get('success', False):
            entry.successful_strategies.append(strategy)
        else:
            entry.failed_strategies.append(strategy)
            
        # Update tool effectiveness
        self._update_tool_effectiveness(entry, execution_data)
        
        self._save_learning()

    def get_learned_strategies(self, task: str) -> Dict[str, Any]:
        """Get learned strategies using pattern matching"""
        pattern = self._extract_task_pattern(task)
        task_pattern = TaskPattern(
            task_type=self._determine_task_type(task, set()),
            key_entities=self._extract_key_entities(pos_tag(word_tokenize(task))),
            action_verbs=self._extract_action_verbs(pos_tag(word_tokenize(task)))
        )
        
        # Find similar patterns
        similar_patterns = []
        for stored_pattern in self.learnings.keys():
            stored_type, stored_verbs, stored_entities = stored_pattern.split(':')
            stored_task_pattern = TaskPattern(
                task_type=stored_type,
                key_entities=set(stored_entities.split(',')),
                action_verbs=set(stored_verbs.split(','))
            )
            
            similarity = task_pattern.similarity_score(stored_task_pattern)
            if similarity > 0.5:  # Threshold for similarity
                similar_patterns.append((stored_pattern, similarity))
        
        # Get strategies from similar patterns
        strategies = {}
        for pattern, similarity in sorted(similar_patterns, key=lambda x: x[1], reverse=True):
            if pattern in self.learnings:
                entry = self.learnings[pattern]
                strategies[pattern] = {
                    'similarity': similarity,
                    'recommended_tools': self._get_effective_tools(entry),
                    'successful_patterns': self._extract_patterns(entry.successful_strategies),
                    'anti_patterns': self._extract_patterns(entry.failed_strategies)
                }
        
        return strategies

    def _extract_task_pattern(self, task: str) -> str:
        """Enhanced task pattern extraction"""
        # Basic text preprocessing
        tokens = word_tokenize(task.lower())
        pos_tags = pos_tag(tokens)
        
        # Extract key components
        action_verbs = self._extract_action_verbs(pos_tags)
        key_entities = self._extract_key_entities(pos_tags)
        task_type = self._determine_task_type(task, action_verbs)
        
        # Create pattern object
        pattern = TaskPattern(
            task_type=task_type,
            key_entities=key_entities,
            action_verbs=action_verbs
        )
        
        # Generate pattern string
        pattern_str = f"{task_type}:{','.join(sorted(action_verbs))}:{','.join(sorted(key_entities))}"
        
        return pattern_str

    def _extract_action_verbs(self, pos_tags: List[Tuple[str, str]]) -> Set[str]:
        """Extract and normalize action verbs from text"""
        verbs = set()
        for word, tag in pos_tags:
            if tag.startswith('VB') and word not in self.stop_words:
                lemma = self.lemmatizer.lemmatize(word, 'v')
                verbs.add(lemma)
        return verbs

    def _extract_key_entities(self, pos_tags: List[Tuple[str, str]]) -> Set[str]:
        """Extract key entities (nouns, proper nouns) from text"""
        entities = set()
        current_entity = []
        
        for word, tag in pos_tags:
            if tag in ['NN', 'NNS', 'NNP', 'NNPS']:
                current_entity.append(word)
            else:
                if current_entity:
                    entity = '_'.join(current_entity)
                    lemma = self.lemmatizer.lemmatize(entity)
                    if lemma not in self.stop_words:
                        entities.add(lemma)
                    current_entity = []
        
        # Add last entity if exists
        if current_entity:
            entity = '_'.join(current_entity)
            lemma = self.lemmatizer.lemmatize(entity)
            if lemma not in self.stop_words:
                entities.add(lemma)
                
        return entities

    def _determine_task_type(self, task: str, action_verbs: Set[str]) -> str:
        """Determine the type of task based on patterns and verbs"""
        task_lower = task.lower()
        type_scores = Counter()
        
        # Check pattern matches
        for task_type, pattern in self.task_types.items():
            matches = len(re.findall(pattern, task_lower))
            type_scores[task_type] += matches * 2
        
        # Check verb associations
        verb_type_associations = {
            'research': {'find', 'search', 'analyze', 'explain'},
            'coding': {'implement', 'code', 'write', 'create'},
            'analysis': {'compare', 'evaluate', 'assess', 'analyze'},
            'extraction': {'extract', 'gather', 'collect', 'obtain'}
        }
        
        for verb in action_verbs:
            for task_type, associated_verbs in verb_type_associations.items():
                if verb in associated_verbs:
                    type_scores[task_type] += 1
        
        # Get most likely type
        if type_scores:
            return type_scores.most_common(1)[0][0]
        return 'general'

    def _update_tool_effectiveness(self, 
                                entry: LearningEntry, 
                                execution_data: Dict[str, Any]):
        """Update tool effectiveness scores"""
        for step in execution_data.get('steps', []):
            tool = step.get('tool')
            if tool:
                current_score = entry.tool_effectiveness.get(tool, 0.5)
                success_factor = 1 if step.get('success', False) else -0.1
                entry.tool_effectiveness[tool] = min(
                    1.0, 
                    max(0.0, current_score + success_factor * 0.1)
                )

    def _get_effective_tools(self, entry: LearningEntry) -> List[str]:
        """Get most effective tools for this task pattern"""
        return [
            tool for tool, score in sorted(
                entry.tool_effectiveness.items(),
                key=lambda x: x[1],
                reverse=True
            )
            if score > 0.6
        ]

    def _extract_patterns(self, strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract common patterns from strategies"""
        patterns = []
        if strategies:
            # Group similar strategies
            for strategy in strategies[-5:]:  # Consider last 5 strategies
                patterns.append({
                    'steps': strategy.get('steps', []),
                    'success_factors': strategy.get('success_factors', [])
                })
        return patterns