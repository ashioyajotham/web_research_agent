# Web Research Agent

A from-scratch implementation of the ReAct (Reasoning and Acting) paradigm for autonomous web research. No LangChain, no agent frameworks — just a minimal, well-structured reasoning loop with real tool use.

Originally built as a take-home coding challenge before "deep research" became a product category. The focus was on understanding where the ReAct loop actually breaks on adversarial research tasks, and fixing those failure modes one by one.

---

## Install

```bash
pip install web-research-agent
```

Optional extras:

```bash
pip install "web-research-agent[providers]"  # Groq / OpenRouter fallback via openai package
pip install "web-research-agent[browser]"    # JS-rendered page scraping via Playwright
pip install "web-research-agent[all]"        # Everything
```

Requires Python 3.8+.

---

## Setup

```bash
webresearch
```

On first run, an interactive setup wizard prompts for API keys and stores them securely in the system keyring (no `.env` files needed):

- **Gemini API key** — [Google AI Studio](https://aistudio.google.com/app/apikey) (free tier)
- **Serper API key** — [Serper.dev](https://serper.dev) (free tier: 2,500 searches/month)

Optional fallback providers (used if Gemini quota is exhausted):

- **Groq API key** — fast inference, free tier
- **OpenRouter API key** — multi-model routing
- **Ollama base URL** — local model serving

Keys can be reconfigured at any time from the `[6] reconfigure keys` menu option.

---

## Usage

### Interactive TUI

```bash
webresearch
```

Menu options:

| Key | Action |
|-----|--------|
| `[1]` | Run a single research query |
| `[2]` | Deep research (parallel sub-queries) |
| `[3]` | Process a task file (batch) |
| `[4]` | View query history |
| `[5]` | View execution logs |
| `[6]` | Reconfigure API keys |
| `[7]` | Clear conversation memory |
| `[q]` | Exit |

The live research panel shows a spinner, elapsed time, and contextual progress phrases keyed to the current tool in use (searching / scraping / running code / writing file).

### Batch Mode

```bash
python main.py tasks.txt -o results.txt -v
```

Task file format — one task per block, separated by blank lines:

```
Find the name of the COO of the organization that mediated secret talks
between US and Chinese AI companies in Geneva in 2023.

By what percentage did Volkswagen reduce the sum of their Scope 1 and
Scope 2 greenhouse gas emissions in 2023 compared to 2021?
```

### Python API

```python
from webresearch import initialize_agent

agent = initialize_agent()
result = agent.run("Your research question here")
print(result)
```

---

## Architecture

The agent implements the ReAct paradigm (Yao et al., 2023):

```
Thought → Action → Observation → [repeat] → Final Answer
```

```
webresearch/
├── agent.py           # ReAct loop, step parsing, sliding-window prompt history
├── llm.py             # Gemini LLM interface
├── llm_compat.py      # OpenAI-compatible interface (Groq, OpenRouter, Ollama)
├── llm_chain.py       # Model fallback chain with thread-safe provider rotation
├── config.py          # Configuration (env vars + keyring)
├── credentials.py     # Keyring-backed secure credential storage
├── memory.py          # Conversation memory (cross-session)
├── parallel.py        # Parallel deep research (ThreadPoolExecutor)
└── tools/
    ├── base.py        # Tool abstract base class
    ├── search.py      # Serper.dev web search
    ├── scrape.py      # HTTP + BeautifulSoup text extraction
    ├── browser.py     # Playwright JS-rendered scraping
    ├── code_executor.py  # Sandboxed Python subprocess
    └── file_ops.py    # Read/write for cross-step data persistence
```

### Model Fallback Chain

When a provider hits a quota or rate limit, the agent automatically falls back to the next available provider:

```
Gemini 2.5 Flash → Groq → OpenRouter → Ollama
```

The chain is thread-safe: a `threading.Lock` guards provider rotation and a `Semaphore(1)` per provider serializes concurrent calls to the same endpoint. Retry backoff is `max(10s, 2^(attempt+2))` — generous enough to avoid hammering free-tier rate limits.

### Prompt Injection Defence

All tool observations are sanitised before entering the prompt. Patterns like `ignore all previous instructions`, `<system>`, `[INST]`, etc. are replaced with `[FILTERED]`. The scraper applies a second pass on raw HTML output.

### Paywall and JS Detection

The scraper detects and short-circuits two common failure modes rather than wasting iterations:

- **JS-only pages**: large HTML with <400 chars extracted text → returns a `scrape_js` suggestion
- **Paywall teasers**: 200 OK with <600 chars + subscribe/sign-in keywords → skips and tells the agent to find another source
- **HTTP 401/403/406/429**: returned as actionable skip messages, not exceptions

### Context Window Management

The prompt uses a sliding window: the 8 most recent steps are included in full; earlier steps are condensed to one-line summaries. Tool output is truncated at `MAX_TOOL_OUTPUT_LENGTH` characters before entering the prompt.

---

## Configuration

All settings can be overridden with environment variables:

| Variable | Default | Description |
|---|---|---|
| `MAX_ITERATIONS` | `15` | ReAct loop iterations before forced termination |
| `MAX_TOOL_OUTPUT_LENGTH` | `3000` | Characters of observation fed back to LLM |
| `TEMPERATURE` | `0.1` | LLM temperature; lower = more deterministic |
| `MODEL_NAME` | `gemini-2.5-flash` | Primary model identifier |
| `WEB_REQUEST_TIMEOUT` | `30` | Seconds before HTTP request timeout |
| `CODE_EXECUTION_TIMEOUT` | `60` | Seconds before subprocess kill |

---

## Adding a Tool

The `ToolManager` uses a registration pattern. No changes to core agent logic required:

```python
# webresearch/tools/my_tool.py
from .base import Tool

class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return """Use this tool to [description].
Parameters:
  - param1 (str): Description of param1"""

    def execute(self, param1: str) -> str:
        return result
```

```python
from webresearch import ToolManager
from webresearch.tools.my_tool import MyTool

tool_manager = ToolManager()
tool_manager.register_tool(MyTool())
```

---

## From Source

```bash
git clone https://github.com/ashioyajotham/web_research_agent.git
cd web_research_agent
pip install -e .
webresearch
```

---

## Known Limitations

**PDF parsing is absent.** URLs pointing to PDFs are noted in observations but the content is not extracted. Tasks requiring numerical retrieval from sustainability reports or academic papers hit a ceiling here.

**Observation truncation loses context.** At `MAX_TOOL_OUTPUT_LENGTH=3000`, long scraped pages are cut off. Key facts in the truncated portion are permanently lost. A chunking + retrieval approach would address this but adds latency.

**Synthesis strategy is LLM-selected, not validated.** The model chooses a reasoning strategy (factual lookup, list compilation, structured extraction, open synthesis) inside its own reasoning pass. There is no external classifier validating the selection. Ambiguous tasks sometimes get the wrong strategy.

**Free-tier rate limits constrain throughput.** Groq allows ~6,000 tokens/min on the free tier. With `max_tokens=2048`, the first rate limit usually hits around step 3-4 of a 15-step run. The fallback chain and 10s+ backoff floor mitigate this but do not eliminate it.

---

## References

Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. *ICLR 2023*. [arxiv.org/abs/2210.03629](https://arxiv.org/abs/2210.03629)

Wei, J., et al. (2022). Chain-of-Thought Prompting Elicits Reasoning in Large Language Models. *NeurIPS 2022*. [arxiv.org/abs/2201.11903](https://arxiv.org/abs/2201.11903)

Schick, T., et al. (2023). Toolformer: Language Models Can Teach Themselves to Use Tools. *NeurIPS 2023*. [arxiv.org/abs/2302.04761](https://arxiv.org/abs/2302.04761)

Greshake, K., et al. (2023). Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection. [arxiv.org/abs/2302.12173](https://arxiv.org/abs/2302.12173)

---

## License

MIT. See [LICENSE](LICENSE).
