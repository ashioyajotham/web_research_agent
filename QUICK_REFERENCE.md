# Quick Reference Card

## Essential Commands

### Setup
```bash
pip install -r requirements.txt              # Install dependencies
cp .env.example .env                         # Create config file
# Edit .env and add API keys
python check_setup.py                        # Verify installation
```

### Running the Agent
```bash
python main.py tasks.txt                     # Process tasks
python main.py tasks.txt -o output.txt       # Custom output file
python main.py tasks.txt -v                  # Verbose mode
python demo.py                               # Quick demo
```

### Testing
```bash
python check_setup.py                        # Verify setup
python test_imports.py                       # Check dependencies
python main.py example_simple.txt            # Simple test
```

## Configuration (.env)

```ini
GEMINI_API_KEY=your_key                      # Required: Gemini API key
SERPER_API_KEY=your_key                      # Required: Serper API key
MAX_ITERATIONS=15                            # Max reasoning steps
TEMPERATURE=0.1                              # LLM temperature (0.0-1.0)
MAX_TOOL_OUTPUT_LENGTH=5000                  # Truncate tool outputs
```

## Project Structure

```
main.py              Entry point
agent.py             ReAct agent core
llm.py               Gemini interface
config.py            Configuration
tools/
  ├── base.py        Tool interface
  ├── search.py      Web search
  ├── scrape.py      Web scraping
  ├── code_executor.py  Python execution
  └── file_ops.py    File operations
```

## Available Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `search` | Google search | `query` (str) |
| `scrape` | Fetch webpage | `url` (str) |
| `execute_code` | Run Python | `code` (str) |
| `file_ops` | Read/write files | `operation`, `path`, `content` |

## Task File Format

```
Task 1 on one or multiple lines.

Task 2 on one or multiple lines.
Can span multiple lines.

Task 3...
```

Tasks are separated by blank lines.

## Common Issues

| Problem | Solution |
|---------|----------|
| API key error | Add keys to `.env` file |
| Import error | Run `pip install -r requirements.txt` |
| Task timeout | Increase `MAX_ITERATIONS` in `.env` |
| Empty results | Check `logs/` directory for errors |

## Output Files

```
results.txt                                  # Final answers
logs/agent_<timestamp>.log                   # Detailed logs
```

## API Keys

Get keys from:
- Gemini: https://makersuite.google.com/app/apikey
- Serper: https://serper.dev (free tier: 2,500 searches/month)

## Adding a New Tool

1. Create `tools/my_tool.py`:
```python
from tools.base import Tool

class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "What it does..."
    
    def execute(self, **kwargs) -> str:
        return result
```

2. Register in `main.py`:
```python
tool_manager.register_tool(MyTool())
```

## Debugging

```bash
python main.py tasks.txt -v                  # Verbose output
cat logs/agent_<timestamp>.log               # View logs
python demo.py                               # Test single task
```

## Performance Tips

- Complex tasks: Increase `MAX_ITERATIONS` to 20-25
- Slow execution: Already using fastest model (Flash)
- Context bloat: Decrease `MAX_TOOL_OUTPUT_LENGTH`
- Focus needed: Lower `TEMPERATURE` to 0.0

## Documentation

| File | Purpose |
|------|---------|
| `README.md` | Full documentation |
| `QUICKSTART.md` | 5-minute setup guide |
| `ARCHITECTURE.md` | Design details |
| `IMPLEMENTATION_NOTES.md` | Design decisions |
| `SOLUTION_SUMMARY.md` | Overview for evaluators |
| `EVALUATION_GUIDE.md` | Assessment guide |

## ReAct Loop

```
1. Thought: "I need to do X"
2. Action: tool_name
3. Action Input: {"param": "value"}
4. Observation: [tool result]
5. Repeat or Final Answer
```

## Example Session

```bash
$ python main.py example_simple.txt

Processing Task 1: What is the capital of France?

Step 1:
  Thought: I need to search for this information
  Action: search
  Observation: [Search results showing Paris]

Step 2:
  Thought: I have the answer
  Final Answer: The capital of France is Paris.

✓ Completed in 15.3 seconds
```

## Key Features

✓ ReAct methodology (Thought → Action → Observation)
✓ Task-agnostic (no hardcoded logic)
✓ Extensible tool system
✓ Web search & scraping
✓ Python code execution
✓ File operations
✓ Comprehensive error handling
✓ Full execution traces

## Limits

- Serper free tier: 2,500 searches/month
- Gemini free tier: 60 requests/minute
- Code execution: 60 second timeout
- Web requests: 30 second timeout

## Support

1. Run `python check_setup.py`
2. Check `logs/` directory
3. Review `README.md`
4. Use `-v` flag for verbose output

---

**Quick Start**: `python check_setup.py` → `python demo.py` → `python main.py tasks.txt`
