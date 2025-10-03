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
   git clone https://github.com/YOUR_USERNAME/web_research_agent.git
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

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
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

Register it in `main.py` in the `initialize_agent()` function:

```python
tool_manager.register_tool(MyTool(param1="value"))
```

### 4. Test Your Tool

Create a test task and verify it works:

```bash
echo "Test task that requires my_tool" > test_my_tool.txt
python main.py test_my_tool.txt
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

### Manual Testing

1. **Verify setup**:
   ```bash
   python check_setup.py
   ```

2. **Test with demo**:
   ```bash
   python demo.py
   ```

3. **Test with simple tasks**:
   ```bash
   python main.py example_simple.txt
   ```

4. **Test with full task set**:
   ```bash
   python main.py tasks.txt
   ```

### Testing Checklist

Before submitting a pull request:

- [ ] Code runs without errors
- [ ] All existing functionality still works
- [ ] New features are documented
- [ ] Error handling is comprehensive
- [ ] Logging is appropriate
- [ ] Type hints are present
- [ ] Docstrings are complete
- [ ] No hardcoded values (use config)
- [ ] No API keys in code

### Creating Test Cases

When adding new features, create a test task:

```
# test_new_feature.txt
Task that exercises the new feature.

Another task that tests edge cases.
```

## Pull Request Process

### Before Submitting

1. **Sync with upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run verification**:
   ```bash
   python check_setup.py
   python test_imports.py
   ```

3. **Test thoroughly**: Run the agent on various tasks

4. **Update documentation**: If you changed functionality

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
- [ ] Code follows style guidelines
- [ ] Added/updated documentation
- [ ] Tested thoroughly
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

1. **Open an issue first**: Discuss the approach
2. **Consider impact**: How does it affect existing code?
3. **Maintain modularity**: Don't create tight coupling
4. **Follow patterns**: Use existing design patterns
5. **Document decisions**: Update ARCHITECTURE.md

## Questions?

If you have questions:

1. **Check documentation**: README, ARCHITECTURE, etc.
2. **Search issues**: Someone may have asked before
3. **Open an issue**: Ask your question
4. **Be specific**: Provide context and examples

## Recognition

Contributors will be:
- Listed in the CONTRIBUTORS file (if we create one)
- Mentioned in release notes for significant contributions
- Appreciated in commit messages and PR descriptions

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

---

Thank you for contributing to Web Research Agent! 🎉