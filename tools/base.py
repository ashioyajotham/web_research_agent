from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ToolMetadata:
    """Metadata about a tool's capabilities"""
    requires_api_key: bool = False
    rate_limited: bool = False
    batch_capable: bool = False
    supports_async: bool = True
    average_response_time: float = 1.0  # seconds
    max_retries: int = 3
    timeout: int = 30  # seconds
    supported_formats: List[str] = None

    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ['text']

@dataclass
class ToolResponse:
    """Standardized response format for tools"""
    success: bool
    output: Dict[str, Any]
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}

class BaseTool(ABC):
    """Base class for all tools with enhanced functionality"""

    def __init__(self):
        self.metadata = self.get_metadata()

    @abstractmethod
    def get_description(self) -> str:
        """Return a description of what the tool does"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResponse:
        """Execute the tool's main functionality"""
        pass

    @abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """Return metadata about the tool's capabilities"""
        return ToolMetadata()

    @property
    def name(self) -> str:
        """Return the tool's name"""
        return self.__class__.__name__.lower()

    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters before execution"""
        return True

    def handle_error(self, error: Exception) -> ToolResponse:
        """Standard error handling for tools"""
        return ToolResponse(
            success=False,
            output={},
            error=str(error),
            metadata={
                'error_type': error.__class__.__name__,
                'tool_name': self.name
            }
        )

    def format_response(self, output: Dict[str, Any], execution_time: float) -> ToolResponse:
        """Format successful response"""
        return ToolResponse(
            success=True,
            output=output,
            execution_time=execution_time,
            metadata={
                'tool_name': self.name,
                'timestamp': datetime.now()
            }
        )
