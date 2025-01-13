from typing import Dict, List, Optional
import sqlite3
from datetime import datetime
import json
from dataclasses import dataclass
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Memory:
    task: str
    solution: Dict
    performance: float
    timestamp: datetime
    metadata: Dict

class MemoryStore:
    def __init__(self, db_path: str):
        """Initialize the memory store with proper path handling"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
            self.db_path = db_path
            self._initialize_db()
        except Exception as e:
            logger.error(f"Memory store initialization failed: {str(e)}")
            raise
        
    def _initialize_db(self):
        """Create memory tables with proper schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # First, check if table exists
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='memories'
                """)
                table_exists = cursor.fetchone() is not None

                if table_exists:
                    # Drop existing table if it's incompatible
                    try:
                        conn.execute("SELECT task FROM memories LIMIT 1")
                    except sqlite3.OperationalError:
                        conn.execute("DROP TABLE memories")
                        table_exists = False

                if not table_exists:
                    # Create fresh table
                    conn.execute("""
                        CREATE TABLE memories (
                            id INTEGER PRIMARY KEY,
                            task TEXT NOT NULL,
                            solution TEXT NOT NULL,
                            performance REAL NOT NULL,
                            timestamp TEXT NOT NULL,
                            metadata TEXT,
                            embedding BLOB
                        )
                    """)
                    conn.commit()

                    # Create indices after table is created and committed
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_task ON memories(task)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_performance ON memories(performance)")
                    conn.commit()
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise

    def add_memory(self, memory: Memory) -> bool:
        """Store new memory with error handling"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO memories 
                        (task, solution, performance, timestamp, metadata) 
                    VALUES 
                        (?, ?, ?, ?, ?)
                    """,
                    (
                        memory.task,
                        json.dumps(memory.solution),
                        memory.performance,
                        memory.timestamp.isoformat(),
                        json.dumps(memory.metadata)
                    )
                )
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to add memory: {str(e)}")
            return False
            
    def get_relevant_experiences(self, task: str, min_performance: float = 0.7) -> List[Memory]:
        """Retrieve relevant memories with error handling"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT task, solution, performance, timestamp, metadata 
                    FROM memories 
                    WHERE performance >= ?
                    ORDER BY timestamp DESC 
                    LIMIT 10
                    """,
                    (min_performance,)
                )
                
                memories = []
                for row in cursor.fetchall():
                    try:
                        memories.append(Memory(
                            task=row[0],
                            solution=json.loads(row[1]),
                            performance=row[2],
                            timestamp=datetime.fromisoformat(row[3]),
                            metadata=json.loads(row[4]) if row[4] else {}
                        ))
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Failed to parse memory row: {str(e)}")
                        continue
                        
                return memories
                
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve memories: {str(e)}")
            return []

    def clear(self) -> bool:
        """Clear all memories from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM memories")
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Failed to clear memories: {str(e)}")
            return False
