# Changelog

All notable changes to the Web Research Agent project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Function calling API integration for more reliable parsing
- Caching system for search results and web pages
- Parallel tool execution
- Memory system for cross-task knowledge persistence
- PDF parsing support
- Automated evaluation suite

## [1.2.0] - 2025-01-10

### Added
- **Interactive CLI** - Beautiful terminal interface with ASCII art banner
  - Gradient colored ASCII art with version display
  - Interactive menu system with 5 options
  - First-run API key setup wizard
  - Configuration stored in `~/.webresearch/config.env`
  - Development mode support (uses local `.env` if available)
- **Enhanced User Experience**
  - Single query mode - Ask questions interactively
  - Batch mode - Process tasks from file
  - Log viewer - View recent execution logs directly in CLI
  - Configuration management - Reconfigure API keys anytime
  - Clean output without info overload
  - Progress indicators and colored output
  - Save results to file with custom names
- **Console Script Entry Point**
  - `webresearch` command for global CLI access
  - Works after `pip install web-research-agent`
- **PyPI Distribution**
  - Clean `requirements.txt` with core dependencies only
  - `setup.py` for package distribution
  - `pyproject.toml` for modern Python packaging
  - `MANIFEST.in` for package file inclusion
  - Package metadata and classifiers
- **Documentation Organization**
  - Moved technical docs to `/docs` folder
  - ARCHITECTURE.md → docs/
  - EVALUATION_GUIDE.md → docs/
  - IMPLEMENTATION_NOTES.md → docs/
  - SOLUTION_SUMMARY.md → docs/
  - QUICK_REFERENCE.md → docs/
- **Package Structure**
  - `__init__.py` for proper package imports
  - Version consistency across all files
  - Console scripts configuration

### Changed
- Simplified requirements.txt to essential dependencies only
- Updated version to 1.2.0 across all files
- CLI now checks for local .env before prompting for API keys
- Logging output suppressed by default in interactive mode
- `initialize_agent()` now accepts `verbose` parameter
- Main menu provides cleaner user experience

### Fixed
- UTF-8 encoding issues in requirements.txt
- Configuration handling in development vs production mode
- Log output not overwhelming terminal in interactive mode

### Technical Details
- Colorama for cross-platform colored terminal output
- Configuration stored in user home directory
- Fallback to local .env for development
- Entry point: `webresearch` command via console_scripts

## [1.0.0] - 2025-01-10

### Added
- **Interactive CLI Interface** with beautiful ASCII art banner and gradient colors
- **First-time setup wizard** for API key configuration
- **Config file management** - API keys stored securely in `~/.webresearch/config.env`
- **Interactive query mode** - Ask research questions directly in the CLI
- **Batch processing mode** - Process multiple tasks from files
- **Log viewer** - View recent execution logs from within the CLI
- **Console command** - Install via `pip install web-research-agent` and run with `webresearch`
- **Colorama integration** for cross-platform colored terminal output
- **Clean console output** - Reduced info overload with optional verbose mode
- **Documentation organization** - Moved detailed docs to `/docs` folder
- **PyPI packaging** - Complete setup for distribution via PyPI

### Changed
- **Improved main.py** - Added verbose flag to control logging output
- **Enhanced initialize_agent()** - Now accepts verbose parameter
- **Cleaner requirements.txt** - Minimal dependencies only
- **Updated README** - Added CLI installation and usage instructions
- **Version bump** - Updated to 1.2.0 across all files

### Improved
- **User experience** - Interactive menus and prompts
- **Configuration

### Added
- Initial release of Web Research Agent
- Core ReAct (Reasoning and Acting) agent implementation
- LLM interface for Google Gemini 2.0 Flash
- Extensible tool system with abstract base class
- Web search tool using Serper.dev API
- Web scraping tool with HTML parsing and content extraction
- Python code execution tool with timeout protection
- File operations tool for reading and writing files
- Tool manager with dynamic registration system
- Configuration management via environment variables
- Comprehensive error handling and retry logic
- Structured logging system with file and console output
- Command-line interface for task processing
- Task file parsing (one task per line, blank line separated)
- Results output with execution metadata
- Setup verification script (`check_setup.py`)
- Interactive demo script (`demo.py`)
- Comprehensive documentation suite:
  - README.md - Main documentation
  - QUICKSTART.md - 5-minute setup guide
  - ARCHITECTURE.md - Design and architecture details
  - IMPLEMENTATION_NOTES.md - Design decisions and rationale
  - SOLUTION_SUMMARY.md - Overview for evaluators
  - EVALUATION_GUIDE.md - Guide for assessing the agent
  - QUICK_REFERENCE.md - Command reference card
  - CONTRIBUTING.md - Contribution guidelines
  - CONTRIBUTORS.md - Recognition of contributors
  - CHANGELOG.md - Version history
- Example tasks file with representative research questions
- Environment configuration template (`.env.example`)
- MIT License
- Complete type hints throughout codebase
- Google-style docstrings for all public methods

### Features
- Task-agnostic design (no hardcoded logic for specific tasks)
- Maximum iteration limit to prevent infinite loops
- Best-effort answer generation when timeout occurs
- Context truncation to manage token limits
- Configurable temperature, model, and timeout settings
- Full execution trace for debugging
- Graceful error handling (errors become observations)
- Support for multi-line tasks in input files
- Verbose logging mode for detailed debugging
- Custom output file specification

### Technical Details
- Python 3.8+ compatibility
- Built from scratch without agent frameworks (no LangChain, etc.)
- Clean separation of concerns (agent, LLM, tools, config)
- Strategy pattern for tool implementations
- Registry pattern for tool management
- Abstract base class for tool interface
- Dependency injection for testability
- Environment-based configuration (12-factor app)
- Structured logging with multiple levels
- Exponential backoff for API retries
- Subprocess-based code execution (not eval)
- BeautifulSoup for HTML parsing
- html2text for content conversion
- Regex-based response parsing with fallback logic

### Documentation
- 7 comprehensive markdown documentation files
- ~3,000 lines of documentation
- Architecture diagrams and data flow illustrations
- Code examples and usage patterns
- Troubleshooting guides and common issues
- Configuration reference
- API key setup instructions
- Tool development guide
- Testing guidelines

## Version History

### Version Numbering Scheme

We use Semantic Versioning:
- **Major version** (X.0.0): Breaking changes or major architectural updates
- **Minor version** (0.X.0): New features, backward compatible
- **Patch version** (0.0.X): Bug fixes, backward compatible

### Release Notes Format

Each release includes:
- **Added**: New features and capabilities
- **Changed**: Changes to existing functionality
- **Deprecated**: Features to be removed in future versions
- **Removed**: Features removed in this version
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes

---

## How to Update This Changelog

When contributing:

1. Add your changes under `[Unreleased]` section
2. Use the appropriate category (Added, Changed, Fixed, etc.)
3. Write clear, concise descriptions
4. Include issue/PR references if applicable
5. Keep entries in chronological order within each category

Example:
```markdown
## [Unreleased]

### Added
- New database query tool for SQL operations (#123)

### Fixed
- Fixed timeout issue in web scraping tool (#456)
```

When releasing a new version:
1. Move unreleased changes to a new version section
2. Add the version number and date
3. Update the version comparison links at the bottom
4. Tag the release in Git

---

## Links

- [Repository](https://github.com/victorashioya/web_research_agent)
- [Issues](https://github.com/victorashioya/web_research_agent/issues)
- [Pull Requests](https://github.com/victorashioya/web_research_agent/pulls)
- [Releases](https://github.com/victorashioya/web_research_agent/releases)

---

**Note**: For detailed technical changes, see the Git commit history.