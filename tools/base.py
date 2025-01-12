from abc import ABC, abstractmethod
from typing import Any

class BaseTool(ABC):
    @abstractmethod
    def execute(self, input_data: str) -> str:
        """Execute the tool with the given input"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return a description of what the tool does"""
        pass
    
    @property
    def name(self) -> str:
        """Return the tool's name"""
        return self.__class__.__name__.lower()
