# Web Research Agent

A command-line tool for automated web research and content synthesis. Performs web searches, scrapes content, and generates coherent answers from multiple sources.

## Features

- Automated web research with configurable search queries
- Content extraction from web pages via browser automation
- Answer synthesis from multiple sources
- Task-based research workflow
- Configurable search and extraction parameters
- Markdown output format

## Architecture

Core components:

- **Agent**: Main orchestration layer handling task execution flow
- **Search Tool**: Web search integration using configurable search engines  
- **Browser Tool**: Content extraction from web pages via Selenium
- **Presentation Tool**: Answer synthesis and formatting from collected sources
- **Configuration**: Centralized settings for search limits, timeouts, and output options

## Tool Interfaces

- **Search Tool**: Returns search results (title, link, snippet) from web search engines
- **Browser Tool**: Fetches URL content and extracts main text; aggregates search snippets when direct access fails  
- **Presentation Tool**: Synthesizes final answers using appropriate strategy based on question type
- **Code Generator Tool**: Optional component for computational tasks (filtering, plotting)

Implementation files: `agent/agent.py`, `agent/planner.py`, `tools/search.py`, `tools/browser.py`, `tools/presentation_tool.py`

## Installation

### Prerequisites

- Python 3.8+
- Chrome/Chromium browser
- pip (Python package installer)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/ashioyajotham/web_research_agent.git
   cd web_research_agent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure settings in `config/config.py` as needed

## Usage

### Command Line Interface

Run research tasks from a file:
```bash
python main.py tasks.txt
```

Run interactive mode:
```bash
python cli.py
```

### Task File Format

Create a text file with research questions, one per line:
```
What is the current population of Tokyo?
List the top 5 largest companies by revenue in 2024
Who is the current CEO of Microsoft?
```

### Configuration

Edit `config/config.py` to adjust:
- Search result limits
- Browser timeout settings
- Output format preferences
- Logging levels

## Output

Results are saved in the `results/` directory as markdown files with:
- Source attribution
- Structured answers based on question type
- Timestamp and metadata

## Development

### Project Structure

```
web_research_agent/
├── agent/          # Core agent logic
├── config/         # Configuration management
├── tools/          # Research tools (search, browser, presentation)
├── utils/          # Utilities and formatters
├── logs/           # Application logs
├── results/        # Research output files
└── main.py         # Entry point
```

### Key Components

- `agent/agent.py`: Main research orchestration
- `tools/search.py`: Web search integration
- `tools/browser.py`: Content extraction via Selenium
- `tools/presentation_tool.py`: Answer synthesis and formatting

## License

MIT License - see (LICENSE)[LICENSE] file for details

## Contributing

See CONTRIBUTING.md for development setup and contribution guidelines.
