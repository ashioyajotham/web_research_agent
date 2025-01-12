import sqlite3
from typing import Dict, List, Any
from datetime import datetime
import json

class MemoryStore:
    def __init__(self, db_path: str = "agent_memory.db"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY,
                    task_type TEXT,
                    pattern TEXT,
                    solution TEXT,
                    effectiveness FLOAT,
                    timestamp DATETIME,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_patterns (
                    id INTEGER PRIMARY KEY,
                    pattern TEXT,
                    frequency INTEGER,
                    success_rate FLOAT
                )
            """)

    def store_memory(self, task_type: str, pattern: str, solution: Dict, effectiveness: float):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memories (task_type, pattern, solution, effectiveness, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (task_type, pattern, json.dumps(solution), effectiveness, datetime.now(), "{}")
            )

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
