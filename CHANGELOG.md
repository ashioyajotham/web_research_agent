# Changelog

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
