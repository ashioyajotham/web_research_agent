"""
File operations tool for reading and writing files.
Allows the agent to persist information and work with local files.
"""

import os
import logging
from pathlib import Path
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
        # All file I/O is constrained to this directory to prevent path traversal.
        self.safe_root = Path.cwd() / "agent_workspace"
        self.safe_root.mkdir(exist_ok=True)
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
            safe_path = self._resolve_safe(path)
            if safe_path is None:
                return "Error: path traversal not permitted — all paths must stay within agent_workspace/"
            if operation == "read":
                return self._read_file(safe_path)
            else:  # write
                if content is None:
                    return "Error: content parameter is required for write operation"
                return self._write_file(safe_path, content)

        except Exception as e:
            logger.error(f"File operation failed: {str(e)}")
            return f"Error: File operation failed: {str(e)}"

    def _resolve_safe(self, path: str) -> Optional[Path]:
        """
        Resolve path relative to safe_root and return it, or None if traversal detected.
        Absolute paths are also remapped under safe_root to prevent escaping.
        """
        try:
            resolved = (self.safe_root / Path(path).name if Path(path).is_absolute()
                        else (self.safe_root / path).resolve())
            if not str(resolved).startswith(str(self.safe_root.resolve())):
                logger.warning(f"Path traversal attempt blocked: {path!r}")
                return None
            return resolved
        except Exception:
            return None

    def _read_file(self, path: Path) -> str:
        try:
            if not path.exists():
                return f"Error: File not found: {path}"

            if not path.is_file():
                return f"Error: Path is not a file: {path}"

            file_size = path.stat().st_size

            content = path.read_text(encoding="utf-8")

            if len(content) > self.max_read_length:
                truncated = content[: self.max_read_length]
                truncated += f"\n\n... [Content truncated. Total size: {file_size} bytes, showing first {self.max_read_length} characters]"
                return truncated

            return f"Content of {path.name}:\n{'=' * 80}\n{content}"

        except UnicodeDecodeError:
            return f"Error: File {path.name} is not a text file or uses an unsupported encoding"
        except PermissionError:
            return f"Error: Permission denied reading file: {path.name}"
        except Exception as e:
            return f"Error reading file {path.name}: {str(e)}"

    def _write_file(self, path: Path, content: str) -> str:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            file_size = len(content.encode("utf-8"))
            return f"Successfully wrote {file_size} bytes to agent_workspace/{path.name}"

        except PermissionError:
            return f"Error: Permission denied writing to file: {path.name}"
        except Exception as e:
            return f"Error writing to file {path.name}: {str(e)}"
