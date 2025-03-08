from typing import Dict, Any, Optional, Callable
from utils.logger import get_logger

logger = get_logger(__name__)

class BaseTool:
    """Base class for all tools."""
    
    def __init__(self, name: str, description: str):
        """
        Initialize a tool.
        
        Args:
            name (str): Name of the tool
            description (str): Description of what the tool does
        """
        self.name = name
        self.description = description
    
    def execute(self, parameters: Dict[str, Any], memory: Any) -> Any:
        """
        Execute the tool with the given parameters.
        
        Args:
            parameters (dict): Parameters for the tool
            memory (Memory): Agent's memory
            
        Returns:
            any: Result of the tool execution
        """
        raise NotImplementedError("Tool classes must implement execute method")

class ToolRegistry:
    """Registry for tools that the agent can use."""
    
    def __init__(self):
        """Initialize an empty tool registry."""
        self.tools: Dict[str, BaseTool] = {}
    
    def register_tool(self, name: str, tool: BaseTool) -> None:
        """
        Register a tool with the registry.
        
        Args:
            name (str): Name to register the tool under
            tool (BaseTool): Tool instance to register
        """
        if name in self.tools:
            logger.warning(f"Tool '{name}' already registered. Overwriting.")
        
        self.tools[name] = tool
        logger.debug(f"Registered tool: {name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            name (str): Name of the tool to get
            
        Returns:
            BaseTool or None: The requested tool or None if not found
        """
        tool = self.tools.get(name)
        if not tool:
            logger.warning(f"Tool '{name}' not found in registry")
        return tool
    
    def list_tools(self) -> Dict[str, str]:
        """
        List all registered tools and their descriptions.
        
        Returns:
            dict: Mapping of tool names to descriptions
        """
        return {name: tool.description for name, tool in self.tools.items()}
    
    def register_function_as_tool(self, name: str, description: str, func: Callable) -> None:
        """
        Register a function as a tool.
        
        Args:
            name (str): Name for the tool
            description (str): Description of what the tool does
            func (callable): Function to execute when the tool is called
        """
        class FunctionTool(BaseTool):
            def __init__(self, name, description, func):
                super().__init__(name, description)
                self.func = func
            
            def execute(self, parameters, memory):
                return self.func(**parameters)
        
        self.register_tool(name, FunctionTool(name, description, func))
