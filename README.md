# Web Research Agent

[![CI](https://github.com/ashioyajotham/web_research_agent/actions/workflows/ci.yml/badge.svg)](https://github.com/ashioyajotham/web_research_agent/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/web-research-agent)](https://pypi.org/project/web-research-agent/)
[![Python](https://img.shields.io/pypi/pyversions/web-research-agent)](https://pypi.org/project/web-research-agent/)

An AI agent that uses the **ReAct** (Reasoning and Acting) methodology to complete complex research tasks by searching the web, scraping pages, and running code — all visible in real time.

## Features

- **Real-time ReAct streaming** — watch every Thought → Action → Observation step live in your terminal as the agent works
- **Standard & Deep Research modes** — single sequential loop, or parallel fan-out across 4 sub-queries for thorough investigations
- **Session memory** — follow-up queries automatically inherit context from the current session
- **Playwright browser tool** — headless Chromium fallback for JavaScript-rendered pages
- **Code execution sandbox** — AST-based pre-check blocks dangerous imports before running user-generated code
- **Query history** — persistent `~/.webresearch/history.json` with arrow-key navigation and re-run
- **Rate-limit display** — Serper API monthly usage shown after every query
- **Prompt injection protection** — scraped content is sanitised before reaching the LLM
- **Powered by Gemini 2.5 Flash**

## Research Attribution

This project implements the **ReAct** paradigm from:

> **ReAct: Synergizing Reasoning and Acting in Language Models**
> Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, Yuan Cao — *ICLR 2023*
> [Paper](https://arxiv.org/abs/2210.03629) · [Project page](https://react-lm.github.io/)

## Installation

```bash
pip install web-research-agent
```

Optional — Playwright for JS-heavy pages:

```bash
pip install "web-research-agent[browser]"
playwright install chromium
```

### API Keys

You need two keys (both have free tiers):

| Key | Where to get it |
|-----|----------------|
| **Gemini API key** | [Google AI Studio](https://makersuite.google.com/app/apikey) |
| **Serper API key** | [serper.dev](https://serper.dev) — 2,500 searches/month free |

The CLI prompts for these on first run and stores them in `~/.webresearch/config.env`.

### Windows PATH fix

If `webresearch` is not recognised after `pip install`:

```powershell
# Permanent fix
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "User") + ";$env:APPDATA\Python\Python313\Scripts",
    "User"
)
# Then restart your terminal
```

Or run directly without PATH: `python -m cli`

## Quick start

```bash
webresearch
```

The interactive menu:

```
  1.  🔍 Run a research query
  2.  📁 Process tasks from file
  3.  📚 View query history
  4.  📋 View recent logs
  5.  🔧 Reconfigure API keys
  6.  🧹 Clear session memory
  7.  👋 Exit
```

Select **1**, type your question, then choose your research mode:

- **Standard** — sequential ReAct loop, up to 15 iterations (~1 min)
- **Deep Research** — parallel fan-out: 4 sub-queries × 5 iterations each (~3 min, more thorough)

## How it works

### Standard mode (sequential ReAct)

```
Thought: I need to search for current Bitcoin price
Action: search   {"query": "Bitcoin price USD 2025"}
Observation: [search results…]

Thought: I have enough information
Final Answer: Bitcoin is currently trading at $67,709.
```

### Deep Research mode (parallel fan-out)

```
Original question: "What is the state of fusion energy in 2025?"

Sub-query 1: What recent breakthroughs in fusion energy occurred?   ⟳ running
Sub-query 2: Which companies are leading commercial fusion?          ⟳ running
Sub-query 3: What is the current timeline for viable fusion power?  ⟳ running
Sub-query 4: What are the remaining engineering challenges?          ⟳ running

→ All results synthesised into one comprehensive answer
```

### Session memory

```
Q1: "Who is the CEO of OpenAI?"          → Sam Altman
Q2: "What is his background?"            → agent knows "his" = Sam Altman
Q3: "What companies has he co-founded?"  → agent retains full context
```

Type option **6** from the menu to reset the session.

## Architecture

```
webresearch/
├── agent.py          # Sequential ReAct loop (step_callback for live streaming)
├── parallel.py       # Parallel fan-out agent (ThreadPoolExecutor)
├── memory.py         # ConversationMemory for multi-turn sessions
├── llm.py            # Gemini API interface (retry + backoff)
├── config.py         # Configuration from env / ~/.webresearch/config.env
└── tools/
    ├── base.py            # Abstract Tool class
    ├── search.py          # Google search via Serper.dev + usage tracking
    ├── scrape.py          # requests-based HTML scraper + injection sanitizer
    ├── browser.py         # Playwright headless scraper (scrape_js)
    ├── code_executor.py   # Python sandbox (AST check + isolated temp dir)
    └── file_ops.py        # Read / write files
cli.py                # Interactive terminal UI (rich + questionary)
```

## Configuration

Set these in `.env` or `~/.webresearch/config.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Required |
| `SERPER_API_KEY` | — | Required |
| `MODEL_NAME` | `gemini-2.5-flash` | Gemini model |
| `MAX_ITERATIONS` | `15` | ReAct loop cap |
| `TEMPERATURE` | `0.1` | LLM temperature |
| `MAX_TOOL_OUTPUT_LENGTH` | `5000` | Chars fed back to LLM per tool call |
| `WEB_REQUEST_TIMEOUT` | `30` | Scraper timeout (s) |
| `CODE_EXECUTION_TIMEOUT` | `60` | Code sandbox timeout (s) |

## Batch processing

```bash
webresearch   # choose option 2, enter path to tasks file
```

Tasks file format (blank-line separated):

```
Find the name of the COO of the organization that mediated
secret talks between US and Chinese AI companies in Geneva in 2023.

By what percentage did Volkswagen reduce their Scope 1 + Scope 2
greenhouse gas emissions in 2023 compared to 2021?
```

## Programmatic use

```python
from webresearch import ReActAgent, ParallelResearchAgent
from webresearch.config import Config
from webresearch.llm import LLMInterface
from webresearch.tools import ToolManager, SearchTool, ScrapeTool, CodeExecutorTool, FileOpsTool

cfg = Config()
cfg.validate()
llm = LLMInterface(api_key=cfg.gemini_api_key, model_name=cfg.model_name)

tools = ToolManager()
tools.register_tool(SearchTool(cfg.serper_api_key))
tools.register_tool(ScrapeTool())
tools.register_tool(CodeExecutorTool())
tools.register_tool(FileOpsTool())

# Sequential
agent = ReActAgent(llm=llm, tool_manager=tools)
answer = agent.run("What is the capital of France?")

# Parallel fan-out
deep = ParallelResearchAgent(llm=llm, tool_manager=tools)
answer = deep.run("Explain the state of nuclear fusion energy in 2025")
```

## Adding a custom tool

```python
from webresearch.tools.base import Tool

class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return """One-line summary.

Parameters:
- param (str, required): what it does

Use this tool when you need to…"""

    def execute(self, param: str) -> str:
        return f"Result for {param}"

# Register it
tools.register_tool(MyTool())
```

## Security

- **Prompt injection**: 9 regex patterns strip instruction-like content from scraped pages before it reaches the LLM
- **Code sandbox**: AST pre-check blocks `subprocess`, `socket`, `ctypes`, `os.system/fork/exec`, and 10+ other dangerous calls; code runs in an isolated `TemporaryDirectory` with API keys stripped from the subprocess environment
- **API keys**: stored in `~/.webresearch/config.env`, never logged

## Development

```bash
git clone https://github.com/ashioyajotham/web_research_agent.git
cd web_research_agent
pip install -e ".[dev]"
pytest tests/ -v          # 56 tests, no API keys required
```

CI runs on Python 3.9 · 3.10 · 3.11 · 3.12 for every push and pull request.

## Limitations

- Paywalled or login-gated content cannot be accessed (even with Playwright)
- PDF parsing is not supported; URLs are noted for manual download
- Serper free tier: 2,500 searches/month — complex queries can use 5–8 calls each
- Parallel mode fires multiple concurrent Gemini requests; heavy use may hit rate limits

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports and feature requests welcome via GitHub Issues.

## License

MIT — see [LICENSE](LICENSE).

## References

- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- [Google Gemini API](https://ai.google.dev/docs)
- [Serper.dev API](https://serper.dev/docs)
