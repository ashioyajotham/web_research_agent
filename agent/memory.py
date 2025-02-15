from typing import Dict, List, Any
from utils.helpers import logger

class Memory:
    def __init__(self):
        self.storage: Dict[str, Any] = {}
        self.context_window: int = 5  # Number of recent items to keep in context

    def store(self, key: str, value: Any) -> None:
        """Store information with a key"""
        try:
            self.storage[key] = value
            logger.info(f"Stored information with key: {key}")
        except Exception as e:
            logger.error(f"Failed to store in memory: {str(e)}")
            raise

    def get(self, key: str) -> Any:
        """Retrieve information by key"""
        return self.storage.get(key)

    def get_related(self, query: str) -> List[str]:
        """Get all stored information related to a query"""
        try:
            related_items = []
            for key, value in self.storage.items():
                if query in key:
                    # Convert dictionary results to strings
                    if isinstance(value, dict):
                        value = str(value)
                    related_items.append(value)
            return related_items
        except Exception as e:
            logger.error(f"Failed to retrieve related items: {str(e)}")
            return []

    def clear(self) -> None:
        """Clear all stored information"""
        self.storage.clear()
        logger.info("Memory cleared")

    def get_all(self) -> Dict[str, Any]:
        """Get all stored information"""
        return self.storage.copy()