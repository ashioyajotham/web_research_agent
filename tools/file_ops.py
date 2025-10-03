"""
File operations tool for reading and writing files.
Allows the agent to persist information and work with local files.
"""

import os
import logging
from typing import Optional
from .base import Tool

logger = logging.getLogger(__name__)


class FileOpsTool(Tool):
    """Tool for reading and writing files."""

    def __init__(self, max_read_length: int = 50000):
        """
        Initialize the file operations tool.

        Args:
            max_read_length: Maximum length of content to return when reading
        """
        self.max_read_length = max_read_length
        super().__init__()

    @property
    def name(self) -> str:
        return "file_ops"

    @property
    def description(self) -> str:
        return """Read from or write to files on the local filesystem.

Parameters:
- operation (str, required): Either "read" or "write"
- path (str, required): The file path (relative or absolute)
- content (str, optional): The content to write (required if operation is "write")

Returns:
For "read": The content of the file
For "write": Confirmation message

Use this tool when you need to:
- Save data, results, or information to a file
- Read previously saved data
- Store intermediate results during analysis
- Create output files with findings
- Work with downloaded files or datasets

Example usage:
operation: "write", path: "results.txt", content: "My findings..."
operation: "read", path: "data.csv"
operation: "write", path: "output.json", content: '{"key": "value"}'

Notes:
- Creates directories as needed when writing
- Supports text files (txt, csv, json, md, etc.)
- Use relative paths for files in the working directory
"""

    def execute(self, operation: str, path: str, content: Optional[str] = None) -> str:
        """
        Perform file operations.

        Args:
            operation: "read" or "write"
            path: The file path
            content: Content to write (for write operations)

        Returns:
            Result message or file content

        Raises:
            Exception: If the operation fails
        """
        if not operation or operation not in ["read", "write"]:
            return 'Error: operation must be either "read" or "write"'

        if not path or not path.strip():
            return "Error: path cannot be empty"

        try:
            if operation == "read":
                return self._read_file(path)
            else:  # write
                if content is None:
                    return "Error: content parameter is required for write operation"
                return self._write_file(path, content)

        except Exception as e:
            logger.error(f"File operation failed: {str(e)}")
            return f"Error: File operation failed: {str(e)}"

    def _read_file(self, path: str) -> str:
        """
        Read content from a file.

        Args:
            path: The file path

        Returns:
            The file content
        """
        try:
            if not os.path.exists(path):
                return f"Error: File not found: {path}"

            if not os.path.isfile(path):
                return f"Error: Path is not a file: {path}"

            # Get file size
            file_size = os.path.getsize(path)

            # Read the file
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Truncate if necessary
            if len(content) > self.max_read_length:
                truncated = content[: self.max_read_length]
                truncated += f"\n\n... [Content truncated. Total size: {file_size} bytes, showing first {self.max_read_length} characters]"
                return truncated

            return f"Content of {path}:\n{'=' * 80}\n{content}"

        except UnicodeDecodeError:
            return (
                f"Error: File {path} is not a text file or uses an unsupported encoding"
            )
        except PermissionError:
            return f"Error: Permission denied reading file: {path}"
        except Exception as e:
            return f"Error reading file {path}: {str(e)}"

    def _write_file(self, path: str, content: str) -> str:
        """
        Write content to a file.

        Args:
            path: The file path
            content: The content to write

        Returns:
            Success message
        """
        try:
            # Create directory if it doesn't exist
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            # Write the file
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            file_size = len(content.encode("utf-8"))
            return f"Successfully wrote {file_size} bytes to {path}"

        except PermissionError:
            return f"Error: Permission denied writing to file: {path}"
        except Exception as e:
            return f"Error writing to file {path}: {str(e)}"
