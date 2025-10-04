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

## [1.1.13] - 2025-01-10

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

## [1.1.12] - 2025-09-17

### Major Improvements

- **Complete Agent Architecture Redesign**: Implemented proper ReAct (Reasoning + Acting) execution loop in WebResearchAgent
- **Centralized Task Execution**: Moved all task orchestration from main.py into the agent's run() method for cleaner architecture
- **Fixed Core Synthesis Pipeline**: Resolved critical issue where final synthesis step was not being executed properly
- **Enhanced Planning Integration**: Fixed parameter passing between comprehension, planning, and execution phases

### Fixed

- Fixed parameter substitution for search result URLs using correct single-brace placeholder format {search_result_N_url}
- Resolved tool registry issues by implementing proper tool registration with explicit names
- Fixed async/sync execution conflicts in tool calling
- Corrected method signature mismatches in planner.create_plan() calls
- Fixed display_completion_message() argument count error
- Enhanced error handling throughout the execution pipeline

### Technical Improvements

- Implemented complete agent.run() method that handles: task analysis → planning → tool execution → synthesis
- Added proper memory management for search results across tool executions
- Improved tool parameter substitution with robust placeholder replacement
- Enhanced execution logging and error reporting for better debugging
- Streamlined main.py to focus purely on task file processing and result saving

### Breaking Changes

- Agent execution now requires calling agent.run(task) instead of manual tool orchestration
- Tool registry now uses explicit registration: register_tool(name, instance) instead of auto-detection

## [1.1.11] - 2025-06-15

### Fixed

- Fixed web page processing in browser tool to correctly process URLs instead of falling back to snippets
- Enhanced statement extraction for "compile a list" tasks, properly identifying and processing quotes
- Fixed task analysis for statement compilation tasks to use the correct synthesis strategy
- Fixed `UnicodeDecodeError` in `setup.py` on Windows by specifying UTF-8 encoding for `README.md`.
- Increased default search result count from 5 to 10 for more comprehensive research

### Enhanced

- Improved statement compilation strategy to extract quotes from both web content and search snippets
- Added better error recovery in URL fetching to attempt processing before falling back to snippets

## [1.1.10] - 2025-06-12

### Fixed

- Fixed unpacking error in browser tool's URL validation method where placeholder patterns were incorrectly treated as tuples
- Enhanced JSON parsing robustness in the comprehension module with improved error recovery for malformed API responses
- Added better fallback mechanisms when JSON extraction fails in task analysis
- Fixed entity extraction methods to properly handle list data structures

### Enhanced

- Improved error handling with detailed logging to aid debugging
- Added more graceful failure modes to maintain workflow progress despite partial errors

## [1.1.9] - 2025-05-30

### Enhanced

- Improved robustness with consistent handling of curly-brace placeholders in browser.py

### Fixed

- Added try/except blocks around response.json() calls in search.py to handle non-JSON responses more gracefully

## [1.1.8] - 2025-05-28

### Added

- **Dynamic Task Analysis System**: Intelligent pattern recognition that analyzes any research question to determine expected answer type and appropriate synthesis strategy without hardcoded rules
- **Multi-Strategy Synthesis Framework**: Four distinct synthesis approaches (extract-and-verify, aggregate-and-filter, collect-and-organize, comprehensive-synthesis) selected based on task characteristics
- **Answer Type Detection**: System automatically identifies whether tasks expect factual answers, comparisons, lists, or comprehensive analysis
- **Information Target Identification**: Dynamic detection of what specific information needs to be gathered from research questions
- **Output Structure Inference**: Predicts appropriate format for presenting answers based on question structure
- **Enhanced URL Resolution**: Multiple fallback strategies for extracting valid URLs from search results with comprehensive validation
- **Robust Parameter Resolution**: Advanced handling of incomplete or ambiguous web search results
- **Source Verification Framework**: Cross-validation of findings across multiple sources with confidence scoring
- **Numerical Data Processing**: Enhanced extraction and formatting of quantitative information
- **Temporal Pattern Recognition**: Improved handling of date ranges and time-based queries

### Enhanced

- **Complete Results Formatting Overhaul**: System now produces direct answers to research questions instead of defaulting to entity tables
- **Task-Adaptive Reasoning**: Agent adapts its approach based on semantic analysis of question structure and intent
- **Dynamic Answer Synthesis**: Flexible synthesis that matches the expected output structure for each specific question type
- **Improved Search Strategy Planning**: Creates targeted search approaches based on identified information targets
- **Enhanced Entity Processing**: Extracts entities while maintaining focus on answering the specific question asked
- **Advanced Error Recovery**: Multiple fallback mechanisms for content access failures and URL resolution issues
- **Comprehensive Logging**: Detailed tracking of reasoning processes and synthesis strategy decisions

### Fixed

- **Critical Answer Format Issue**: Resolved core problem where agent produced entity-focused tables instead of direct answers to research questions
- **Multiple Syntax Errors**: Fixed indentation issues, missing method implementations, and class structure problems in agent.py
- **TypeError in Numerical Processing**: Resolved tuple handling errors in numerical data formatting
- **URL Validation Issues**: Enhanced validation to reject placeholder URLs and invalid formats
- **Parameter Substitution Problems**: Fixed comprehensive placeholder pattern handling and variable resolution
- **Method Scope Issues**: Corrected parameter handling and method accessibility throughout the agent system

### Technical Details

- **New Dynamic Analysis Methods**: `_analyze_task_for_answer_type()`, `_extract_primary_intent()`, `_infer_output_structure()`, `_identify_information_targets()`
- **New Synthesis Strategy Methods**: `_synthesize_extract_and_verify()`, `_synthesize_aggregate_and_filter()`, `_synthesize_collect_and_organize()`, `_synthesize_comprehensive_synthesis()`
- **Enhanced URL Handling**: `_get_search_result_url()`, `_is_valid_url()`, `_extract_all_urls_from_results()` with comprehensive fallback strategies
- **New Utility Methods**: `_format_source_verification()`, `_format_numerical_findings()`, `_extract_content_items()`, and multiple formatting utilities
- **Improved Core Logic**: Enhanced `_format_results()` now calls dynamic analysis and synthesis system instead of defaulting to entity extraction

## [1.1.7] - 2025-05-25

### Added

- Multi-criteria task parser for handling complex, structured tasks
- Task parser utility with intelligent recognition of indentation patterns
- Enhanced documentation focusing on ReAct research implementation
- New methods for extracting criteria from multi-criteria tasks
- Explicit ReAct paradigm cycle in task execution flow

### Enhanced

- Planner now generates better plans for multi-criteria tasks with specific guidance
- Main task processing loop better handles structured tasks with multiple conditions
- README updated to align with research focus on ReAct implementation
- Improved task handling in agent.py with better error recovery strategies
- Better alignment with ReAct (Reasoning + Acting) paradigm throughout code base

### Fixed

- Tasks with indented criteria are now properly processed as a single task
- Fixed parsing issues in tasks.txt for multi-line structured tasks
- Improved handling of JSON parsing in plan generation
- Enhanced error recovery for web scraping failures

## [1.1.5] - 2025-03-15

### Added
- Smart entity extraction from search snippets for early knowledge acquisition
- Intelligent role-person-organization relationship mapping for better context understanding
- Advanced pattern detection for entity placeholders in presentation content
- Dynamic entity replacement system that works with various placeholder formats
- Improved browser tool entity extraction with relationship inference

### Enhanced
- Presentation tool now automatically replaces entity placeholders like [CEO's Name]
- Entity extraction now creates structured relationships between people, roles, and organizations
- Search results are now analyzed immediately for relevant entities
- Memory system now has better support for entity relationships with find_entity_by_role method
- Attribution line with a chef's kiss! 👨‍🍳👌

### Fixed
- Fixed placeholder issues in browser tool URL handling
- Improved error reporting for entity extraction failures
- Enhanced reliability of entity replacement in presentation outputs
- Resolved issues with unprocessed placeholders in search results
- Fixed missing _display_step_result method in WebResearchAgent class

## [1.1.4] - 2025-03-15

### Added
- Enhanced PresentationTool with smart entity placeholder detection and replacement
- Advanced entity matching that automatically identifies placeholder patterns like [CEO's Name]
- Flexible placeholder format support including brackets, braces, and angle brackets

### Fixed
- Resolved ConfigManager ENV_MAPPING attribute access issue
- Improved environment variable handling in configuration system
- Enhanced browser tool placeholder URL detection

## [1.1.2] - 2025-03-14

### Fixed
- Fixed issue with ENV_MAPPING access in ConfigManager class
- Improved _save_to_env_file function to handle different config object types
- Enhanced backward compatibility with older configuration systems

## [1.1.0] - 2025-03-14

### Added
- Updated package version to 1.1.0.
- Improved configuration management and keyring integration.
- Enhanced tool registration and default tool integration.

### Fixed
- Resolved issues with secure credential storage in ConfigManager.
- Fixed various logging and error handling improvements.

## [1.0.9] - 2025-03-12

### Fixed
- Enhanced the update function in config.py and ConfigManager to correctly handle key updates.
- Improved conversion of configuration updates to use the ConfigManager instance.
- Minor improvements in error handling for configuration update operations.

## [1.0.8] - 2025-03-12

### Fixed
- Fixed "update expected at most 1 argument, got 2" error by enhancing the update function in config.py to handle different calling conventions
- Added ConfigManager compatibility class to ensure backward compatibility with both new and old configuration systems
- Improved error handling for configuration updates

## [1.0.7] - 2025-03-12

### Fixed
- Fixed compatibility issue with older versions of the config manager by adding defensive code around the `securely_stored_keys` method
- Improved error handling for different config object types to ensure backward compatibility
- Made credential storage more resilient when handling different versions of the package

## [1.0.6] - 2025-03-12

### Added
- Secure credential management: API keys are now stored securely in the system's keyring
- Interactive consent flow for storing credentials
- Visual indicators showing where credentials are stored
- Fallback to .env file when system keyring is unavailable
- Added keyring as an optional dependency

### Changed
- Key configuration now happens at the earliest point needed in command execution

## [1.0.5] - 2025-03-11

### Added
- Interactive API Key Configuration: The agent now prompts for missing Gemini and Serper API keys during configuration, storing them using the configuration manager.

## [1.0.4] - 2025-03-11

### Fixed

- Refactored the output formatters by converting the "utils/formatters" module into a package. The new __init__.py file now re-exports the format_results function, ensuring consistent imports between editable and installed versions.

## [1.0.3] - 2025-03-10

### Fixed
- Fixed a bug in the search tool that caused incorrect results

## [1.0.2] - 2025-03-09

### Fixed
- Fixed layout issues with the preview section
- Fixed a bug in the search tool that caused incorrect results

### Added
- Added a new tool for generating code snippets from search results

## [1.0.1] - 2025-03-08

### Fixed
- Fixed import issues with relative vs absolute imports
- Fixed filename sanitization to handle quoted queries properly
- Enhanced result preview section to show both plan and results

### Added
- Support for verbose logging mode with `--verbose` flag
- Smart preview extraction to show more relevant content

## [1.0.0] - 2025-03-08

### Added
- Initial release of Web Research Agent
- Support for search, browser, code generation, and presentation tools
- Interactive shell mode
- Configuration management

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
