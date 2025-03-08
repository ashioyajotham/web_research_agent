from typing import Dict, Any, List, Optional
from .tool_registry import BaseTool
from utils.logger import get_logger

logger = get_logger(__name__)

class PresentationTool(BaseTool):
    """Tool for organizing and presenting information without writing code."""
    
    def __init__(self):
        """Initialize the presentation tool."""
        super().__init__(
            name="present",
            description="Organizes and formats information into tables, lists, or summaries"
        )
    
    def execute(self, parameters: Dict[str, Any], memory: Any) -> str:
        """
        Execute the presentation tool with the given parameters.
        
        Args:
            parameters (dict): Parameters for the tool
                - data (dict or list, optional): Data to present
                - format_type (str): Type of presentation ('table', 'list', 'summary', 'comparison')
                - title (str, optional): Title for the presentation
                - prompt (str): Description of what to present and how
            memory (Memory): Agent's memory
            
        Returns:
            str: Formatted presentation of the information
        """
        format_type = parameters.get("format_type", "table")
        title = parameters.get("title", "Information")
        prompt = parameters.get("prompt", "")
        data = parameters.get("data", {})
        
        # Construct the formatted output based on the format type
        if format_type == "table":
            return self._format_as_table(title, prompt, data)
        elif format_type == "list":
            return self._format_as_list(title, prompt, data)
        elif format_type == "summary":
            return self._format_as_summary(title, prompt, data)
        elif format_type == "comparison":
            return self._format_as_comparison(title, prompt, data)
        else:
            return self._format_as_generic(title, prompt, data)
    
    def _format_as_table(self, title: str, prompt: str, data: Any) -> str:
        """Format information as a markdown table."""
        output = [f"# {title}", "", prompt, ""]
        
        # Generate a table based on the data structure
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # List of dictionaries - create table with headers
            headers = list(data[0].keys())
            output.append("| " + " | ".join(headers) + " |")
            output.append("| " + " | ".join(["---" for _ in headers]) + " |")
            
            for item in data:
                row = [str(item.get(header, "")) for header in headers]
                output.append("| " + " | ".join(row) + " |")
        else:
            # For other data structures, create a simple key-value table
            output.append("| Key | Value |")
            output.append("| --- | --- |")
            
            if isinstance(data, dict):
                for key, value in data.items():
                    output.append(f"| {key} | {value} |")
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    output.append(f"| Item {i+1} | {item} |")
            else:
                # If data isn't structured, use the prompt to generate a meaningful table
                output.append("| Note | No structured data provided |")
                output.append(f"| Prompt | {prompt} |")
        
        return "\n".join(output)
    
    def _format_as_list(self, title: str, prompt: str, data: Any) -> str:
        """Format information as a markdown list."""
        output = [f"# {title}", "", prompt, ""]
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    output.append(f"- **{next(iter(item))}**: {item[next(iter(item))]}")
                    for key, value in list(item.items())[1:]:
                        output.append(f"  - {key}: {value}")
                else:
                    output.append(f"- {item}")
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    output.append(f"- **{key}**:")
                    for subkey, subvalue in value.items():
                        output.append(f"  - {subkey}: {subvalue}")
                elif isinstance(value, list):
                    output.append(f"- **{key}**:")
                    for item in value:
                        output.append(f"  - {item}")
                else:
                    output.append(f"- **{key}**: {value}")
        else:
            # If data isn't structured, use the prompt to generate a list
            output.append("- This is a presentation of the requested information:")
            output.append(f"  - Based on: {prompt}")
            output.append("- No structured data was provided")
        
        return "\n".join(output)
    
    def _format_as_summary(self, title: str, prompt: str, data: Any) -> str:
        """Format information as a markdown summary."""
        output = [f"# {title}", "", prompt, "", "## Summary", ""]
        
        # For summary format, we mostly rely on the prompt
        output.append(f"This is a summary based on the request: '{prompt}'")
        output.append("")
        
        if isinstance(data, dict) and len(data) > 0:
            output.append("### Key Points")
            for key, value in data.items():
                output.append(f"- **{key}**: {value}")
        elif isinstance(data, list) and len(data) > 0:
            output.append("### Key Points")
            for item in data:
                if isinstance(item, dict):
                    for key, value in item.items():
                        output.append(f"- **{key}**: {value}")
                else:
                    output.append(f"- {item}")
        else:
            output.append("No structured data was provided for this summary.")
        
        return "\n".join(output)
    
    def _format_as_comparison(self, title: str, prompt: str, data: Any) -> str:
        """Format information as a comparison."""
        output = [f"# {title}", "", prompt, "", "## Comparison", ""]
        
        if isinstance(data, dict) and len(data) >= 2:
            # Compare dictionary values
            items = list(data.items())
            output.append(f"### Comparing {items[0][0]} vs {items[1][0]}")
            output.append("")
            output.append("| Aspect | " + " | ".join([key for key, _ in items]) + " |")
            output.append("| --- | " + " | ".join(["---" for _ in items]) + " |")
            
            # Find all unique keys in the nested dictionaries
            all_aspects = set()
            for _, value in items:
                if isinstance(value, dict):
                    all_aspects.update(value.keys())
            
            # Create comparison rows
            for aspect in all_aspects:
                row = [aspect]
                for _, value in items:
                    if isinstance(value, dict):
                        row.append(str(value.get(aspect, "N/A")))
                    else:
                        row.append("N/A")
                output.append("| " + " | ".join(row) + " |")
        elif isinstance(data, list) and len(data) >= 2:
            # Compare list items
            output.append("| Aspect | " + " | ".join([f"Item {i+1}" for i in range(len(data))]) + " |")
            output.append("| --- | " + " | ".join(["---" for _ in data]) + " |")
            
            # If list contains dictionaries, compare their values
            if all(isinstance(item, dict) for item in data):
                all_keys = set()
                for item in data:
                    all_keys.update(item.keys())
                
                for key in all_keys:
                    row = [key]
                    for item in data:
                        row.append(str(item.get(key, "N/A")))
                    output.append("| " + " | ".join(row) + " |")
            else:
                # Simple list comparison
                output.append("| Value | " + " | ".join([str(item) for item in data]) + " |")
        else:
            output.append("Insufficient data provided for meaningful comparison. Need multiple items to compare.")
        
        return "\n".join(output)
    
    def _format_as_generic(self, title: str, prompt: str, data: Any) -> str:
        """Format information in a generic way when no specific format is specified."""
        output = [f"# {title}", "", prompt, "", "## Information", ""]
        
        if isinstance(data, dict):
            for key, value in data.items():
                output.append(f"### {key}")
                output.append("")
                output.append(f"{value}")
                output.append("")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                output.append(f"### Item {i+1}")
                output.append("")
                output.append(f"{item}")
                output.append("")
        else:
            output.append(f"Based on the request: '{prompt}'")
            output.append("")
            output.append("No structured data was provided. Here's a generic presentation of the information.")
        
        return "\n".join(output)
