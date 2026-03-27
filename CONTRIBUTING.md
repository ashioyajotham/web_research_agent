# Contributing to Web Research Agent

Thank you for your interest in contributing to the Web Research Agent! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Adding New Tools](#adding-new-tools)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive experience for everyone. We expect all contributors to:

- Be respectful and considerate
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Publishing others' private information
- Any conduct that would be inappropriate in a professional setting

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git for version control
- A Gemini API key (for testing)
- A Serper API key (for testing)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/ashioyajotham/web_research_agent.git
   cd web_research_agent
   ```

3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/web_research_agent.git
   ```

## Development Setup

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install in editable mode with all extras**:
   ```bash
   pip install -e ".[providers,browser]"
   ```
   Or just core + test dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest
   ```

3. **Configure API keys** — the agent uses the OS system keyring (no `.env` file needed). On first run it walks you through setup interactively:
   ```bash
   webresearch
   # → follow the setup wizard on first launch
   ```
   To reconfigure at any time: choose `[6] reconfigure api keys` from the menu.

   For CI or headless environments, set environment variables directly:
   ```bash
   export GEMINI_API_KEY=...
   export SERPER_API_KEY=...
   ```

4. **Verify setup**:
   ```bash
   python check_setup.py
   ```

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

1. **Bug Fixes**: Fix issues in existing code
2. **New Features**: Add new tools or capabilities
3. **Documentation**: Improve or add documentation
4. **Tests**: Add or improve test coverage
5. **Performance**: Optimize existing code
6. **Examples**: Add example tasks or use cases

### Contribution Workflow

1. **Check existing issues**: Look for existing issues or create a new one
2. **Create a branch**: Use a descriptive name
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

3. **Make your changes**: Follow the code style guidelines
4. **Test your changes**: Ensure everything works
5. **Commit your changes**: Write clear commit messages
6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Submit a pull request**: Describe your changes clearly

## Adding New Tools

Adding new tools is a primary way to extend the agent's capabilities. Here's how:

### 1. Create a New Tool Class

Create a new file in `tools/` directory (e.g., `tools/my_tool.py`):

```python
"""
Description of what your tool does.
"""

from typing import Optional
import logging
from .base import Tool

logger = logging.getLogger(__name__)


class MyTool(Tool):
    """Tool for doing something specific."""

    def __init__(self, param1: Optional[str] = None):
        """
        Initialize the tool.

        Args:
            param1: Description of parameter
        """
        self.param1 = param1
        super().__init__()

    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return """Brief description of what the tool does.

Parameters:
- param1 (type, required/optional): Description
- param2 (type, required/optional): Description

Returns:
Description of what the tool returns.

Use this tool when you need to:
- Use case 1
- Use case 2

Example usage:
param1: "example value"
param2: "another example"
"""

    def execute(self, **kwargs) -> str:
        """
        Execute the tool.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            The result as a string

        Raises:
            Exception: If execution fails
        """
        try:
            # Validate parameters
            param1 = kwargs.get("param1")
            if not param1:
                return "Error: param1 is required"

            # Your tool logic here
            result = self._do_something(param1)

            return result

        except Exception as e:
            logger.error(f"Error in MyTool: {str(e)}")
            return f"Error: {str(e)}"

    def _do_something(self, param1: str) -> str:
        """Private helper method."""
        # Implementation
        return f"Result for {param1}"
```

### 2. Export the Tool

Add your tool to `tools/__init__.py`:

```python
from .my_tool import MyTool

__all__ = [
    "Tool",
    "ToolManager",
    "SearchTool",
    "ScrapeTool",
    "CodeExecutorTool",
    "FileOpsTool",
    "MyTool",  # Add this line
]
```

### 3. Register the Tool

Register it in `cli.py` inside `_build_tool_manager()`:

```python
# cli.py — _build_tool_manager()
from webresearch.tools.my_tool import MyTool
tool_manager.register_tool(MyTool(param1="value"))
```

### 4. Test Your Tool

Write a unit test in `tests/` (see [Testing Guidelines](#testing-guidelines)), then do a live smoke test via batch mode:

```bash
# tasks.txt
Task that requires my_tool to answer correctly.

python main.py tasks.txt
```

### 5. Document Your Tool

Add documentation to the README.md explaining:
- What the tool does
- When to use it
- Example usage
- Any limitations

## Code Style Guidelines

### Python Style

We follow PEP 8 with some specific conventions:

1. **Type Hints**: Always use type hints
   ```python
   def function_name(param: str, optional: Optional[int] = None) -> str:
       pass
   ```

2. **Docstrings**: Use Google-style docstrings
   ```python
   def function_name(param: str) -> str:
       """
       Brief description.

       Longer description if needed.

       Args:
           param: Description of parameter

       Returns:
           Description of return value

       Raises:
           ValueError: When something is wrong
       """
   ```

3. **Naming Conventions**:
   - Classes: `PascalCase`
   - Functions/methods: `snake_case`
   - Constants: `UPPER_SNAKE_CASE`
   - Private methods: `_leading_underscore`

4. **Line Length**: Max 88 characters (Black default)

5. **Imports**: Organize in three groups
   ```python
   # Standard library
   import os
   import sys

   # Third-party
   import requests
   from bs4 import BeautifulSoup

   # Local
   from .base import Tool
   from config import config
   ```

### Error Handling

- Always use try-except blocks for external operations
- Return error messages as strings (don't raise)
- Log errors with appropriate severity
- Provide actionable error messages

```python
try:
    result = risky_operation()
    return result
except SpecificError as e:
    logger.error(f"Operation failed: {str(e)}")
    return f"Error: {str(e)}. Try doing X instead."
```

### Logging

Use appropriate log levels:

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Detailed information for debugging")
logger.info("General information about progress")
logger.warning("Something unexpected but handled")
logger.error("Something failed")
```

## Testing Guidelines

### Running the Test Suite

The project uses `pytest`. All tests live in `tests/` and run without API keys — external calls are mocked.

```bash
# Run all tests
pytest

# Run a specific file
pytest tests/test_parallel.py -v

# Run a specific test
pytest tests/test_parallel.py::test_decompose_parses_numbered_list -v
```

No API keys or network access required for the unit tests.

### Test Files

| File | What it covers |
|------|----------------|
| `tests/test_agent_parsing.py` | ReAct response parsing, JSON fallback |
| `tests/test_cli_input.py` | `_read_query` multiline input helper |
| `tests/test_memory.py` | `ConversationMemory` FIFO, context injection |
| `tests/test_parallel.py` | Decompose/synthesize/context scoping |
| `tests/test_sandbox.py` | Code executor AST sandboxing |
| `tests/test_scraper.py` | Scraper hardening (paywall, 5xx, encoding) |
| `tests/test_search_usage.py` | Serper monthly usage tracking |

### Writing New Tests

- Use `unittest.mock.MagicMock` for LLM interfaces and tool managers — no real API calls.
- If your test file imports `cli.py`, stub the display-only deps (`pyfiglet`, `questionary`) at the top before the import:
  ```python
  import sys
  from unittest.mock import MagicMock
  sys.modules.setdefault("pyfiglet", MagicMock())
  sys.modules.setdefault("questionary", MagicMock())
  ```
- Test the smallest unit that can fail independently. Integration smoke tests belong in a separate `tasks.txt` run, not in the pytest suite.

### Pre-submission Checklist

- [ ] `pytest` passes with no failures
- [ ] New behaviour has at least one new test
- [ ] No API keys in code or test fixtures
- [ ] No hardcoded values — use config or constructor args
- [ ] Type hints present on new functions
- [ ] Logging uses `logger.*` not `print()`

## Pull Request Process

### Before Submitting

1. **Sync with upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run the test suite**:
   ```bash
   pytest
   ```

3. **Verify the CLI boots cleanly** (optional, requires API keys):
   ```bash
   python check_setup.py
   webresearch
   ```

4. **Update documentation**: If you changed user-visible behaviour, update `README.md` and this guide where relevant

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
Describe how you tested your changes

## Checklist
- [ ] `pytest` passes
- [ ] New behaviour has a test
- [ ] Code follows style guidelines
- [ ] Added/updated documentation
- [ ] No breaking changes (or documented)
- [ ] Updated CHANGELOG if applicable

## Screenshots/Examples
If applicable, add examples of usage
```

### Review Process

1. **Automated checks**: Must pass (if configured)
2. **Code review**: At least one maintainer will review
3. **Feedback**: Address any requested changes
4. **Approval**: Once approved, will be merged

### After Merge

1. **Delete your branch**:
   ```bash
   git branch -d feature/your-feature-name
   git push origin --delete feature/your-feature-name
   ```

2. **Sync your fork**:
   ```bash
   git checkout main
   git pull upstream main
   git push origin main
   ```

## Reporting Issues

### Bug Reports

When reporting bugs, include:

1. **Description**: Clear description of the bug
2. **Steps to reproduce**: Exact steps to trigger the bug
3. **Expected behavior**: What should happen
4. **Actual behavior**: What actually happens
5. **Environment**:
   - Python version
   - Operating system
   - Relevant package versions
6. **Logs**: Relevant log excerpts
7. **Task**: The task that caused the issue (if applicable)

### Feature Requests

When requesting features, include:

1. **Description**: What feature you'd like
2. **Use case**: Why this feature is needed
3. **Proposed solution**: How you envision it working
4. **Alternatives**: Other solutions you've considered
5. **Examples**: Similar features in other tools

### Issue Template

```markdown
## Type
- [ ] Bug Report
- [ ] Feature Request
- [ ] Documentation Issue
- [ ] Question

## Description
Clear description of the issue

## Environment (for bugs)
- Python version:
- OS:
- Installation method:

## Steps to Reproduce (for bugs)
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior


## Actual Behavior


## Logs/Screenshots
```

## Architecture Decisions

When proposing significant changes:

1. **Open an issue first**: Discuss the approach before writing code
2. **Consider impact**: How does it affect the ReAct loop, prompt structure, or tool contracts?
3. **Maintain modularity**: The agent, LLM, tools, and CLI are deliberately decoupled — avoid introducing tight coupling
4. **Follow patterns**: New tools extend `Tool`; new LLM providers implement `LLMInterface`; CLI wiring goes in `cli.py`
5. **Document decisions**: Update README.md and this guide to reflect any user-visible or contributor-visible changes

## Questions?

If you have questions:

1. **Check documentation**: README.md and this guide cover setup, architecture, and contribution workflow
2. **Search issues**: Someone may have asked before
3. **Open an issue**: Ask your question with enough context to reproduce or understand the situation
4. **Be specific**: Provide Python version, OS, and the exact command or code that triggered the problem

## Recognition

Contributors will be:
- Listed in the CONTRIBUTORS file (if we create one)
- Mentioned in release notes for significant contributions
- Appreciated in commit messages and PR descriptions

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

---

Thank you for contributing to Web Research Agent! 🎉
