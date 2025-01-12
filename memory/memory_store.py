import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path

class MemoryStore:
    def __init__(self, db_path: str = "agent_memory.db"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        """Initialize the SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Create tables if they don't exist
        c.execute('''CREATE TABLE IF NOT EXISTS memories
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     task_type TEXT,
                     pattern TEXT,
                     solution TEXT,
                     effectiveness REAL,
                     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS task_history
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     task TEXT,
                     result TEXT,
                     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.commit()
        conn.close()

    def get_relevant_experiences(self, task: str) -> List[Dict[str, Any]]:
        """Get relevant past experiences for a given task"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Get the 5 most recent similar tasks
            c.execute('''SELECT task, result FROM task_history 
                        WHERE task LIKE ? ORDER BY timestamp DESC LIMIT 5''',
                     (f'%{task[:50]}%',))
            
            experiences = []
            for task_text, result_json in c.fetchall():
                try:
                    result = json.loads(result_json)
                    if result.get('success'):
                        experiences.append({
                            'task': task_text,
                            'solution': result
                        })
                except json.JSONDecodeError:
                    continue
            
            conn.close()
            return experiences
            
        except sqlite3.Error:
            # Return empty list if database access fails
            return []

    def store_memory(self, task_type: str, pattern: str, solution: Dict[str, Any], effectiveness: float):
        """Store a new memory entry"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''INSERT INTO memories (task_type, pattern, solution, effectiveness)
                        VALUES (?, ?, ?, ?)''',
                     (task_type, pattern, json.dumps(solution), effectiveness))
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error:
            pass  # Fail silently but log in production

    def store_task_result(self, task: str, result: Dict[str, Any]):
        """Store a task result in history"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''INSERT INTO task_history (task, result)
                        VALUES (?, ?)''',
                     (task, json.dumps(result)))
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error:
            pass  # Fail silently but log in production

    def clear_old_memories(self, days: int = 30):
        """Clear memories older than specified days"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''DELETE FROM memories 
                        WHERE datetime(timestamp) < datetime('now', ?)''',
                     (f'-{days} days',))
            
            c.execute('''DELETE FROM task_history 
                        WHERE datetime(timestamp) < datetime('now', ?)''',
                     (f'-{days} days',))
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error:
            pass  # Fail silently but log in production

    def retrieve_similar_patterns(self, task_pattern: str, threshold: float = 0.7) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT pattern, solution, effectiveness FROM memories WHERE effectiveness > ?",
                (threshold,)
            )
            return [
                {
                    "pattern": row[0],
                    "solution": json.loads(row[1]),
                    "effectiveness": row[2]
                }
                for row in cursor.fetchall()
            ]

    def update_pattern_success(self, pattern: str, success: bool):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO task_patterns (pattern, frequency, success_rate)
                VALUES (?, 1, ?)
                ON CONFLICT(pattern) DO UPDATE SET
                    frequency = frequency + 1,
                    success_rate = ((success_rate * frequency) + ?) / (frequency + 1)
            """, (pattern, 1.0 if success else 0.0, 1.0 if success else 0.0))
