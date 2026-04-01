"""
Code execution tool for running Python code in a sandboxed environment.
Uses AST analysis to block dangerous operations before execution.
"""

import ast
import logging
import os
import subprocess
import tempfile
from typing import Optional

from .base import Tool

logger = logging.getLogger(__name__)

# Modules that can be used to escape the sandbox or access the network/OS
_BLOCKED_MODULES = frozenset({
    "subprocess", "socket", "socketserver",
    "ftplib", "smtplib", "telnetlib", "imaplib", "poplib", "nntplib",
    "paramiko", "fabric",
    "ctypes", "cffi",
    "winreg", "msilib", "msvcrt",
    "importlib",
})

# os module attributes that can spawn processes or manipulate the system
_BLOCKED_OS_ATTRS = frozenset({
    "system", "popen", "popen2", "popen3", "popen4",
    "execv", "execve", "execvp", "execvpe", "execlp", "execlpe",
    "spawnl", "spawnle", "spawnlp", "spawnlpe",
    "spawnv", "spawnve", "spawnvp", "spawnvpe",
    "fork", "forkpty",
    "kill", "killpg", "abort",
    "putenv", "unsetenv",
})

# Sensitive environment variable prefixes to strip from the subprocess
_SENSITIVE_ENV_PREFIXES = (
    "GEMINI", "SERPER", "OPENAI", "ANTHROPIC", "HUGGING",
    "AWS", "AZURE", "GCP", "GOOGLE_API",
)


def _check_code_safety(code: str) -> Optional[str]:
    """
    Analyse code with AST and return an error string if unsafe, else None.
    Blocks dangerous module imports and os.* shell-escape calls.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        hint = ""
        if "triple-quoted" in str(e) or "unterminated" in str(e):
            hint = " Tip: avoid triple-quoted strings (\"\"\"...\"\"\" or \'\'\'...\'\'\'); use single/double quotes with escaped characters instead."
        return f"Syntax error in code: {e}{hint}"

    for node in ast.walk(tree):
        # Block dangerous top-level imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in _BLOCKED_MODULES:
                    return (
                        f"Sandbox blocked: cannot import '{alias.name}'. "
                        f"Network and process modules are not allowed."
                    )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in _BLOCKED_MODULES:
                    return (
                        f"Sandbox blocked: cannot import from '{node.module}'. "
                        f"Network and process modules are not allowed."
                    )

        # Block dangerous os.* attribute access (e.g. os.system, os.fork)
        elif isinstance(node, ast.Attribute):
            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "os"
                and node.attr in _BLOCKED_OS_ATTRS
            ):
                return (
                    f"Sandbox blocked: 'os.{node.attr}' is not allowed. "
                    f"Use os.path and os.listdir for file operations."
                )

        # Block dynamic execution builtins that bypass import scanning.
        # __import__ skips ast.Import nodes; eval/exec run dynamically
        # constructed strings that were never parsed by this checker.
        elif isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in ("eval", "exec", "__import__", "compile")
            ):
                return (
                    f"Sandbox blocked: '{node.func.id}' is not permitted. "
                    "Dynamic code execution and import bypasses are not allowed."
                )

    return None


class CodeExecutorTool(Tool):
    """Tool for executing Python code in a sandboxed environment."""

    def __init__(self, timeout: int = 60, max_output_length: int = 10000):
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

Use this tool when you need to:
- Process data (CSV, JSON, etc.)
- Perform calculations or data analysis
- Parse and transform information
- Generate formatted output
- Extract specific information from structured data

Example usage:
code: '''
import pandas as pd
df = pd.read_csv('data.csv')
print(df.head())
'''

code: '''
# Calculate percentage change
old_value = 1000
new_value = 850
change = ((new_value - old_value) / old_value) * 100
print(f"Change: {change:.2f}%")
'''

Notes:
- Code runs in an isolated temporary directory
- Network access and process spawning are blocked for security
- Common data libraries (pandas, numpy, json, etc.) are available
- Timeout: 60 seconds
- IMPORTANT: Do NOT use triple-quoted strings (\"\"\"...\"\"\" or \'\'\'...\'\'\'). They cause
  syntax errors when the content contains quotes. Use single or double quoted
  strings with escaped characters, or build strings with concatenation instead.
"""

    def execute(self, code: str) -> str:
        if not code or not code.strip():
            return "Error: Code cannot be empty"

        # Safety check before execution
        safety_error = _check_code_safety(code)
        if safety_error:
            logger.warning(f"Code blocked by sandbox: {safety_error}")
            return f"Sandbox error: {safety_error}"

        try:
            logger.info(f"Executing sandboxed code ({len(code)} chars)")

            # Build a clean environment — strip sensitive API keys
            clean_env = {
                k: v for k, v in os.environ.items()
                if not any(k.upper().startswith(p) for p in _SENSITIVE_ENV_PREFIXES)
            }
            # Keep PATH so Python can find stdlib / site-packages
            clean_env.setdefault("PATH", os.environ.get("PATH", ""))

            with tempfile.TemporaryDirectory() as sandbox_dir:
                code_file = os.path.join(sandbox_dir, "code.py")
                with open(code_file, "w", encoding="utf-8") as f:
                    f.write(code)

                result = subprocess.run(
                    ["python", code_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=sandbox_dir,   # isolated temp dir, not user cwd
                    env=clean_env,
                )

            output = ""
            if result.stdout:
                output += "STDOUT:\n" + result.stdout
            if result.stderr:
                if output:
                    output += "\n\n"
                output += "STDERR:\n" + result.stderr

            if not output:
                output = "Code executed successfully with no output."

            if result.returncode != 0:
                output += f"\n\nReturn code: {result.returncode}"

            return self._truncate_output(output)

        except subprocess.TimeoutExpired:
            logger.error(f"Code execution timed out after {self.timeout}s")
            return f"Error: Code execution timed out after {self.timeout} seconds"
        except FileNotFoundError:
            logger.error("Python interpreter not found")
            return "Error: Python interpreter not found. Make sure Python is installed and in PATH."
        except Exception as e:
            logger.error(f"Unexpected error during code execution: {str(e)}")
            return f"Error: Unexpected error during code execution: {str(e)}"

    def _truncate_output(self, output: str) -> str:
        if len(output) <= self.max_output_length:
            return output
        truncated = output[: self.max_output_length]
        truncated += f"\n\n... [Output truncated. Total length: {len(output)} chars, showing first {self.max_output_length}]"
        return truncated
