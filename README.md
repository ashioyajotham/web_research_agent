# Web Research Agent

An AI agent that can browse the web, conduct research, and write code.

## Configuration

The agent requires API keys to function properly:

1. **Gemini API key**: For LLM services
2. **Serper API key**: For Google search results

### Setting up your API keys

#### Option 1: .env file (Recommended)

Create a `.env` file in the project root:

```bash
GEMINI_API_KEY=your_gemini_api_key
SERPER_API_KEY=your_serper_api_key
```

The agent will automatically load this file.

#### Option 2: Environment Variables

```bash
export GEMINI_API_KEY=your_gemini_api_key
export SERPER_API_KEY=your_serper_api_key
```

#### Option 3: Programmatically

```python
from config.config_manager import init_config

config = init_config()
config.update('gemini_api_key', 'your_gemini_api_key')
config.update('serper_api_key', 'your_serper_api_key')
```

## Additional Configuration Options

| Config Key | Environment Variable | Description | Default |
|------------|---------------------|-------------|---------|
| gemini_api_key | GEMINI_API_KEY | API key for Google's Gemini LLM | - |
| serper_api_key | SERPER_API_KEY | API key for Serper.dev search | - |
| log_level | LOG_LEVEL | Logging level | INFO |
| max_search_results | MAX_SEARCH_RESULTS | Maximum number of search results | 5 |
| memory_limit | MEMORY_LIMIT | Number of items to keep in memory | 100 |
| output_format | OUTPUT_FORMAT | Format for output (markdown, text, html) | markdown |
| timeout | REQUEST_TIMEOUT | Default timeout for web requests (seconds) | 30 |

You can set any of these options in your `.env` file or as environment variables.
