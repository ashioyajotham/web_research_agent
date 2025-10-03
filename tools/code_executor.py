"""
Code execution tool for running Python code safely.
Allows the agent to write and execute Python scripts for data processing and analysis.
"""

import subprocess
import tempfile
import os
import logging
from typing import Optional
from .base import Tool

logger = logging.getLogger(__name__)


class CodeExecutorTool(Tool):
    """Tool for executing Python code in a safe environment."""

    def __init__(self, timeout: int = 60, max_output_length: int = 10000):
        """
        Initialize the code executor tool.

        Args:
            timeout: Execution timeout in seconds
            max_output_length: Maximum length of output to return
        """
        self.timeout = timeout
        self.max_output_length = max_output_length
        super().__init__()

    @property
    def name(self) -> str:
        return "execute_code"

    @property
    def description(self) -> str:
        return """Execute Python code and return the output.

Parameters:
- code (str, required): The Python code to execute

Returns:
The output (stdout and stderr) from executing the code.
If the code produces files, information about those files will be included.

Use this tool when you need to:
- Process data (CSV, JSON, etc.)
- Perform calculations or data analysis
- Parse and transform information
- Generate formatted output
- Work with downloaded files or datasets
- Extract specific information from structured data

Example usage:
code: '''
import pandas as pd
df = pd.read_csv('data.csv')
print(df.head())
'''

code: '''
import json
with open('data.json', 'r') as f:
    data = json.load(f)
print(f"Found {len(data)} items")
'''

code: '''
# Calculate percentage change
old_value = 1000
new_value = 850
change = ((new_value - old_value) / old_value) * 100
print(f"Change: {change:.2f}%")
'''

Notes:
- The code runs in a temporary directory
- Common libraries (pandas, numpy, requests, etc.) are available
- Files created during execution are accessible in subsequent code executions
- The working directory persists across executions within the same task
"""

    def execute(self, code: str) -> str:
        """
        Execute Python code and return the output.

        Args:
            code: The Python code to execute

        Returns:
            The output from executing the code

        Raises:
            Exception: If execution fails
        """
        if not code or not code.strip():
            return "Error: Code cannot be empty"

        try:
            logger.info(f"Executing code (length: {len(code)} chars)")

            # Create a temporary file for the code
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                temp_file = f.name

            try:
                # Execute the code
                result = subprocess.run(
                    ["python", temp_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=os.getcwd(),  # Use current working directory
                )

                # Combine stdout and stderr
                output = ""
                if result.stdout:
                    output += "STDOUT:\n" + result.stdout
                if result.stderr:
                    if output:
                        output += "\n\n"
                    output += "STDERR:\n" + result.stderr

                if not output:
                    output = "Code executed successfully with no output."

                # Add return code if non-zero
                if result.returncode != 0:
                    output += f"\n\nReturn code: {result.returncode}"

                return self._truncate_output(output)

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file: {e}")

        except subprocess.TimeoutExpired:
            logger.error(f"Code execution timed out after {self.timeout} seconds")
            return f"Error: Code execution timed out after {self.timeout} seconds"
        except FileNotFoundError:
            logger.error("Python interpreter not found")
            return "Error: Python interpreter not found. Make sure Python is installed and in PATH."
        except Exception as e:
            logger.error(f"Unexpected error during code execution: {str(e)}")
            return f"Error: Unexpected error during code execution: {str(e)}"

    def _truncate_output(self, output: str) -> str:
        """
        Truncate output to maximum length.

        Args:
            output: The output to truncate

        Returns:
            Truncated output
        """
        if len(output) <= self.max_output_length:
            return output

        truncated = output[: self.max_output_length]
        truncated += f"\n\n... [Output truncated. Total length: {len(output)} characters, showing first {self.max_output_length}]"
        return truncated
