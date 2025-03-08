# Contributing to Web Research Agent

First off, thank you for considering contributing to Web Research Agent! It's people like you that make this tool better for everyone.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- A Gemini API key
- A Serper API key for web searches

### Setup for Development

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/web_research_agent.git
   cd web_research_agent
   ```

3. Set up a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

4. Install the package in development mode:
   ```bash
   pip install -e .
   ```

5. Create a `.env` file in the root directory with your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   SERPER_API_KEY=your_serper_key_here
   ```

## Development Workflow

1. Create a branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes, adding tests if applicable.

3. Run the tests to ensure your changes don't break existing functionality.

4. Commit your changes:
   ```bash
   git commit -m "Add your meaningful commit message here"
   ```

5. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Submit a pull request from your forked repo to the main repository.

## Code Style Guidelines

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code style.
- Use meaningful variable and function names.
- Include docstrings for all functions, classes, and modules.
- Keep line length to a maximum of 100 characters.
- Use type hints where possible.

Example function with proper documentation and type hints:
```python
def process_query(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Process a search query and return the results.
    
    Args:
        query: The search query to process
        max_results: Maximum number of results to return
        
    Returns:
        A dictionary containing search results and metadata
    """
    # Implementation here
    return results
```

## Testing

- Write tests for new functionality using pytest.
- Ensure all tests pass before submitting a pull request.
- Run tests with: `pytest`

## Pull Request Process

1. Update the README.md with details of changes if applicable.
2. Update the CHANGELOG.md to describe your changes.
3. The PR should work on the main branch.
4. Include a description of what your changes do and why they should be included.
5. Reference any related issues in your PR description.

## Reporting Issues

- Use the GitHub issue tracker to report bugs.
- Check existing issues before opening a new one.
- Include detailed steps to reproduce the bug.
- Include information about your environment (Python version, OS, etc.).

## Feature Requests

We welcome feature requests! Please provide:
- A clear description of the feature
- Why it would be valuable
- Any implementation ideas you have

## Code of Conduct

- Be respectful and inclusive.
- Focus on the issue, not the person.
- Welcome newcomers and help them learn.
- Ensure your contributions align with the project's goals.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## Questions?

Feel free to reach out if you have any questions about contributing!

Thank you for making Web Research Agent better!
