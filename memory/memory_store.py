from typing import Dict, List, Optional, Any
import sqlite3
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
import logging
import os
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Memory:
    task: str
    result: Dict[str, Any]
    timestamp: datetime
    importance: float
    embedding: np.ndarray
    context: Dict[str, Any]

class MemoryStore:
    def __init__(self, db_path: str):
        """Initialize the memory store with proper path handling"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
            self.db_path = db_path
            self.embedding_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
            self._initialize_db()
            
            # Memory decay settings
            self.decay_rate = 0.1  # Rate at which memory importance decays
            self.retention_period = timedelta(days=30)  # How long to keep memories
            
            # Memory clustering
            self.semantic_clusters = {}
            self.importance_threshold = 0.5
        except Exception as e:
            logger.error(f"Memory store initialization failed: {str(e)}")
            raise
        
    def _initialize_db(self):
        """Create memory tables with proper schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id INTEGER PRIMARY KEY,
                        task TEXT NOT NULL,
                        result TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        importance REAL NOT NULL,
                        embedding BLOB NOT NULL,
                        context TEXT,
                        cluster_id INTEGER,
                        access_count INTEGER DEFAULT 0
                    )
                """)
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise

    def store_experience(self, task: str, result: Dict[str, Any], context: Optional[Dict] = None) -> None:
        """Store experience with importance calculation and clustering"""
        embedding = self.embedding_model.encode([task])[0]
        importance = self._calculate_importance(task, result)
        
        serialized_result = json.dumps(result)
        serialized_context = json.dumps(context) if context else None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO memories 
                    (task, result, timestamp, importance, embedding, context)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (task, serialized_result, datetime.now(), importance, 
                     embedding.tobytes(), serialized_context)
                )
                
            # Update semantic clusters
            self._update_clusters()
        except sqlite3.Error as e:
            logger.error(f"Failed to store experience: {str(e)}")
            
    def get_relevant_experiences(self, task: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get relevant experiences with semantic and temporal weighting"""
        query_embedding = self.embedding_model.encode([task])[0]
        
        relevant_experiences = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT * FROM memories")
                for row in cursor:
                    stored_embedding = np.frombuffer(row[5])
                    similarity = np.dot(query_embedding, stored_embedding)
                    
                    # Calculate temporal decay
                    age = datetime.now() - datetime.fromisoformat(row[3])
                    temporal_weight = np.exp(-self.decay_rate * age.days)
                    
                    # Combine similarity and temporal weight
                    final_score = similarity * temporal_weight * row[4]  # importance
                    
                    relevant_experiences.append({
                        'task': row[1],
                        'result': json.loads(row[2]),
                        'score': final_score,
                        'context': json.loads(row[6]) if row[6] else None
                    })
            
            # Sort by score and return top results
            return sorted(relevant_experiences, key=lambda x: x['score'], reverse=True)[:limit]
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve relevant experiences: {str(e)}")
            return []

    def _calculate_importance(self, task: str, result: Dict[str, Any]) -> float:
        """Calculate memory importance based on multiple factors"""
        importance = 0.5  # Base importance
        
        # Success factor
        if result.get('success'):
            importance += 0.2
        
        # Confidence factor
        importance += min(result.get('confidence', 0.0), 0.2)
        
        # Complexity factor (based on result size)
        result_size = len(json.dumps(result))
        importance += min(result_size / 10000, 0.1)  # Cap at 0.1
        
        return min(importance, 1.0)

    def _update_clusters(self):
        """Update semantic clusters of memories"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT id, embedding FROM memories")
                embeddings = []
                ids = []
                for row in cursor:
                    ids.append(row[0])
                    embeddings.append(np.frombuffer(row[1]))
                
                if embeddings:
                    # Perform clustering (using simple approach - can be enhanced)
                    from sklearn.cluster import DBSCAN
                    clustering = DBSCAN(eps=0.3, min_samples=2)
                    clusters = clustering.fit_predict(embeddings)
                    
                    # Update cluster assignments
                    for id_, cluster in zip(ids, clusters):
                        conn.execute(
                            "UPDATE memories SET cluster_id = ? WHERE id = ?",
                            (int(cluster), id_)
                        )
        except sqlite3.Error as e:
            logger.error(f"Failed to update clusters: {str(e)}")

    def cleanup_old_memories(self):
        """Remove old and unimportant memories"""
        cutoff_date = datetime.now() - self.retention_period
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    DELETE FROM memories 
                    WHERE timestamp < ? 
                    AND importance < ?
                    """,
                    (cutoff_date, self.importance_threshold)
                )
        except sqlite3.Error as e:
            logger.error(f"Failed to cleanup old memories: {str(e)}")
