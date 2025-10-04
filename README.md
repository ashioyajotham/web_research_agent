# Web Research Agent

An AI agent that uses the ReAct (Reasoning and Acting) methodology to complete complex research tasks by browsing the web, analyzing information, and writing code.

## Features

- **ReAct Methodology**: Implements the original ReAct paradigm from the paper "ReAct: Synergizing Reasoning and Acting in Language Models"
- **Task-Agnostic Design**: No hardcoded logic for specific tasks - the agent intelligently adapts to any research question
- **Extensible Tool System**: Easy-to-extend architecture for adding new capabilities
- **Multiple Tools**:
  - **Web Search**: Google search via Serper.dev API
  - **Web Scraping**: Fetch and parse content from any URL
  - **Code Execution**: Run Python code for data analysis and processing
  - **File Operations**: Read and write files for data persistence
- **Powered by Gemini 2.0**: Uses Google's Gemini 2.0 Flash model for reasoning and decision-making

## Architecture

The agent follows a simple but powerful loop:

1. **Thought**: The agent reasons about the current state and what action to take next
2. **Action**: The agent selects and executes a tool with specific parameters
3. **Observation**: The agent receives and processes the result
4. **Repeat**: The cycle continues until the task is complete

### Project Structure

```
web_research_agent/
├── agent.py              # Core ReAct agent implementation
├── llm.py               # LLM interface for Gemini
├── config.py            # Configuration management
├── main.py              # Entry point script
├── tools/               # Tool system
│   ├── __init__.py     # Tool manager
│   ├── base.py         # Base tool class
│   ├── search.py       # Web search tool
│   ├── scrape.py       # Web scraping tool
│   ├── code_executor.py # Python code execution
│   └── file_ops.py     # File operations
├── tasks.txt           # Example tasks
├── .env.example        # Environment variables template
└── requirements.txt    # Python dependencies
```

## Installation

### From PyPI (Recommended)

Install directly from PyPI:

```bash
pip install web-research-agent
```

Then run the interactive CLI:

```bash
webresearch
```

The first time you run it, you'll be prompted to enter your API keys. These will be securely stored in `~/.webresearch/config.env`.

### From Source

1. **Clone the repository**:
   ```bash
   git clone https://github.com/victorashioya/web_research_agent.git
   cd web_research_agent
   ```

2. **Install in development mode**:
   ```bash
   pip install -e .
   ```

3. **Run the CLI**:
   ```bash
   webresearch
   ```

### API Keys

You'll need:
- **Gemini API key**: Get yours at [Google AI Studio](https://makersuite.google.com/app/apikey) (free tier available)
- **Serper API key**: Get yours at [Serper.dev](https://serper.dev) (free tier: 2,500 searches/month)

The CLI will prompt you for these on first run.

## Usage

### Interactive CLI (Recommended)

Simply run:

```bash
webresearch
```

You'll see a beautiful interface with options to:
1. **Run a research query** - Ask any research question interactively
2. **Process tasks from file** - Run multiple tasks from a file
3. **View recent logs** - Check execution logs
4. **Reconfigure API keys** - Update your configuration
5. **Exit** - Close the application

### Command-Line Mode

For batch processing, you can still use the traditional mode:

```bash
python main.py tasks.txt
```

Options:
- `-o, --output` - Specify output file (default: results.txt)
- `-v, --verbose` - Enable detailed logging

This will:
- Read tasks from `tasks.txt` (one task per line, separated by blank lines)
- Process each task using the ReAct agent
- Save results to `results.txt`
- Save execution logs to `logs/agent_<timestamp>.log`

### Custom Output File

Specify a custom output file:

```bash
python main.py tasks.txt -o my_results.txt
```

### Verbose Logging

Enable detailed debug logging:

```bash
python main.py tasks.txt -v
```

### Task File Format

Tasks should be separated by blank lines. Multi-line tasks are supported:

```
Find the name of the COO of the organization that mediated secret talks between US and Chinese AI companies in Geneva in 2023.

Compile a list of 10 statements made by Joe Biden regarding US-China relations. Each statement must have been made on a separate occasion. Provide a source for each statement.

By what percentage did Volkswagen reduce the sum of their Scope 1 and Scope 2 greenhouse gas emissions in 2023 compared to 2021?
```

## Configuration

Edit `.env` to customize agent behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_ITERATIONS` | 15 | Maximum reasoning steps before timeout |
| `MAX_TOOL_OUTPUT_LENGTH` | 5000 | Maximum characters from tool outputs |
| `TEMPERATURE` | 0.1 | LLM temperature (0.0-1.0, lower = more focused) |
| `MODEL_NAME` | gemini-2.0-flash-exp | Gemini model to use |
| `WEB_REQUEST_TIMEOUT` | 30 | Timeout for web requests (seconds) |
| `CODE_EXECUTION_TIMEOUT` | 60 | Timeout for code execution (seconds) |

## Example Tasks

The agent can handle a variety of research tasks:

1. **Information Gathering**: Compile statements, find specific facts, locate documents
2. **Data Analysis**: Download datasets, process CSV/JSON files, perform calculations
3. **Multi-Step Research**: Tasks requiring multiple sources and synthesis
4. **Verification**: Cross-reference information from multiple sources

See `tasks.txt` for examples of representative tasks.

## Adding New Tools

The agent is designed to be easily extensible. To add a new tool:

1. **Create a new tool class** in `tools/` inheriting from `Tool`:

```python
from tools.base import Tool

class MyNewTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return """Description of what your tool does and its parameters."""

    def execute(self, **kwargs) -> str:
        # Your tool logic here
        return "Tool result"
```

2. **Register the tool** in `main.py`:

```python
tool_manager.register_tool(MyNewTool())
```

That's it! The agent will automatically discover and use your new tool.

## How It Works

### ReAct Loop

The agent follows this pattern for each iteration:

```
Thought: I need to search for information about X
Action: search
Action Input: {"query": "X"}
Observation: [Search results appear here]

Thought: Now I need to read the first result
Action: scrape
Action Input: {"url": "https://..."}
Observation: [Page content appears here]

Thought: I have enough information to answer
Final Answer: [Complete answer with sources]
```

### Tool Selection

The agent autonomously decides which tools to use based on:
- The task requirements
- Current context and previous observations
- Tool descriptions provided to the LLM

### Error Handling

- Network timeouts and errors are caught and reported
- Failed tool executions return error messages to the agent
- Maximum iteration limit prevents infinite loops
- Best-effort answers provided if task cannot be completed

## Troubleshooting

### Common Issues

**API Key Errors**:
- Ensure `.env` file exists and contains valid API keys
- Check that keys are not wrapped in quotes

**Import Errors**:
- Run `pip install -r requirements.txt` to install all dependencies
- Ensure you're using Python 3.8 or higher

**Timeout Errors**:
- Increase timeout values in `.env`
- Some tasks may require more iterations - adjust `MAX_ITERATIONS`

**Empty Results**:
- Check logs in `logs/` directory for detailed error information
- Verify network connectivity for web requests

### Debug Mode

Run with `-v` flag to see detailed execution logs:

```bash
python main.py tasks.txt -v
```

## Performance Tips

1. **Adjust iterations**: Complex tasks may need more than 15 iterations
2. **Temperature tuning**: Lower temperature (0.0-0.2) for focused research, higher (0.5-0.7) for creative tasks
3. **Output length**: Increase `MAX_TOOL_OUTPUT_LENGTH` for tasks requiring full document analysis
4. **Model selection**: Use `gemini-2.0-flash-exp` for speed or `gemini-1.5-pro` for complex reasoning

## Limitations

- Web content behind paywalls or login walls cannot be accessed
- PDF parsing is limited (URLs are noted for manual download)
- Code execution is sandboxed but runs in the local environment
- Some websites may block scraping attempts
- Rate limits apply to API calls (Serper free tier: 2,500 searches/month)

## Code Quality

The codebase emphasizes:
- **Modularity**: Each component has a single responsibility
- **Extensibility**: New tools can be added without modifying core logic
- **Documentation**: Comprehensive docstrings and comments
- **Error Handling**: Graceful degradation and informative error messages
- **Logging**: Detailed execution traces for debugging
- **Type Hints**: Clear interfaces using Python type annotations

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

For bug reports and feature requests, please open an issue on GitHub.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**TL;DR**: You are free to use, modify, and distribute this software, even for commercial purposes, as long as you include the original copyright notice.

## References

- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [Serper.dev API Documentation](https://serper.dev/docs)
