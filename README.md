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
pip install "web-research-agent[all]"        # providers + browser
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

The live research panel shows a spinner, elapsed time, and contextual progress phrases keyed to the current tool in use (searching / scraping / running code / writing file). Phrases rotate every 6 seconds so they're readable without flickering.

**Multi-line queries** are supported in both `[1]` and `[2]` modes. End your first line with `:` to enter continuation mode — subsequent lines are collected until you press Enter on a blank line:

```
❯ Research question: Compile a list of companies matching:
  (continuing — press Enter on a blank line to finish)
  - Based in the EU
  - Revenue > €1B in 2023
  - Motor vehicle sector
  [blank line]
```

Single-line queries work exactly as before — type and press Enter once.

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
├── memory.py          # Conversation memory (within-session Q&A context)
├── parallel.py        # Parallel deep research: decomposes task → fan-out → synthesize
└── tools/
    ├── base.py        # Tool abstract base class
    ├── think.py       # Reasoning scratchpad — no external call, pure planning/verification
    ├── search.py      # Serper.dev web search
    ├── scrape.py      # HTTP + BeautifulSoup; tables → markdown, encoding fix, 5xx retry
    ├── pdf.py         # pdfplumber PDF extraction with table parsing and page targeting
    ├── browser.py     # Playwright JS-rendered scraping
    ├── code_executor.py  # Sandboxed Python subprocess
    └── file_ops.py    # Read/write for cross-step data persistence
```

### The Think Tool and the ReAct Reasoning Gap

The standard ReAct loop has a structural constraint: every `Thought` must be followed by an `Action` that calls an external tool. There is no way to have a reasoning step that *is* the action — thinking is always a preamble to doing something.

This works well on single-hop lookups. It breaks on multi-hop queries where the agent needs to plan before acting, or where it needs to stop and verify whether an entity found in results actually matches the task description before spending more iterations on it.

**The failure mode without `think`:**

```
Task: "Find the COO of the organization that mediated secret AI talks in Geneva in 2023"

Step 1  Thought: I'll search for organizations that mediated AI talks in Geneva.
        Action:  search {"query": "organization mediated US China AI talks Geneva 2023"}
        Obs:     Results mention WEF, UN Geneva offices, diplomatic bodies...

Step 2  Thought: The World Economic Forum is based in Geneva and hosts AI discussions.
        Action:  search {"query": "World Economic Forum COO"}
        Obs:     Sarita Nayyar / Julien Gattoni...

Step 3  Thought: The COO of WEF is [name].
        Final Answer: [wrong]
```

The agent never asked: *does WEF actually match "mediated secret talks between US and Chinese AI companies"?* It anchored on the most prominent Geneva organization in the search results and ran with it. By step 2, recovery requires contradicting its own prior reasoning — something the model resists without an explicit prompt to verify.

**With `think`:**

```
Step 1  Thought: This is a multi-hop question. I need to find the org first, then its COO.
        Action:  think {"thought": "The question describes a specific event — secret talks
                  between US and Chinese AI companies — not a general Geneva forum. I should
                  search for the event itself, not assume WEF or UN."}
        Obs:     Reasoning recorded.

Step 2  Thought: I'll search for the specific event described.
        Action:  search {"query": "secret talks US Chinese AI companies Geneva 2023 mediator"}
        Obs:     Results mention the Shaikh Group...

Step 3  Thought: Before proceeding, I should verify the Shaikh Group actually fits the
                 description — a private advisory firm that arranged AI company meetings.
        Action:  think {"thought": "The Shaikh Group is described as a geopolitical advisory
                  firm that brokered the Geneva meetings. This matches the task: 'mediated
                  secret talks between US and Chinese AI companies'. Not WEF. Proceed."}
        Obs:     Reasoning recorded.

Step 4  Action:  search {"query": "Shaikh Group COO"}
        ...
        Final Answer: Yannis Pallikaris, COO of the Shaikh Group.
```

The `think` tool does three things the bare ReAct loop cannot:

1. **Upfront planning** — the agent can spend a step decomposing the query and choosing a search strategy before any API call is made. On a 15-iteration budget, one planning step spent before three wrong searches is cheaper than recovering from three wrong searches.

2. **Entity verification** — the agent can explicitly check whether an entity from search results matches the task description. This is the critical gate that prevents anchoring on a superficially related but wrong entity.

3. **Mid-run reorientation** — if evidence contradicts the current path, the agent can reason about the contradiction and pivot without the reasoning appearing inconsistent in the next `Thought:` prefix.

The tool itself is a no-op: it accepts a `thought` string and returns a neutral confirmation. Its value is entirely in the reasoning trace it forces into the step history, where subsequent `Thought:` steps can reference it.

### Model Fallback Chain

When a provider hits a quota or rate limit, the agent automatically falls back to the next available provider:

```
Gemini 2.5 Flash → Groq → OpenRouter → Ollama
```

The chain is thread-safe: a `threading.Lock` guards provider rotation and a `Semaphore(1)` per provider serializes concurrent calls to the same endpoint. Retry backoff is `max(10s, 2^(attempt+2))` — generous enough to avoid hammering free-tier rate limits.

### Prompt Injection Defence

All tool observations are sanitised before entering the prompt. Patterns like `ignore all previous instructions`, `<system>`, `[INST]`, etc. are replaced with `[FILTERED]`. The scraper applies a second pass on raw HTML output.

### Scraper Hardening

The scraper handles several failure modes that would otherwise silently waste iterations:

- **HTML tables → markdown**: BeautifulSoup extracts `<table>` elements and converts them to aligned markdown tables before html2text processes the page. Column values and numbers are preserved exactly — critical for emissions data, financial statements, and any structured tabular source.
- **JS-only pages**: large HTML with <400 chars extracted text → returns a `scrape_js` suggestion
- **Paywall teasers**: 200 OK with <600 chars + subscribe/sign-in keywords → skips and suggests alternatives
- **Auth redirects**: raw HTML scanned for login form signatures (`<input type="password">`, sign-in prose) even when the page returns 200 with substantial content
- **5xx retry**: 500/502/503/504 retried twice with 2s/4s backoff before giving up
- **Encoding**: `apparent_encoding` used when server omits charset or defaults to ISO-8859-1 — fixes mangled characters in EU/government filings
- **Content selectors**: 30+ CSS selectors covering common CMS and news-site patterns (`.article-body`, `.post-content`, `.entry-content`, `data-component` attributes, etc.) before falling back to full `<body>`
- **UA rotation**: request headers rotate across a pool of current browser strings per request
- **HTTP 401/403/406/429**: returned as actionable skip messages, not exceptions

### PDF Extraction

The `pdf_extract` tool downloads and parses PDFs using `pdfplumber`:

- Tables extracted as aligned grids with exact cell values (not OCR text)
- `pages="12-18"` parameter lets the agent target specific page ranges once it knows the document structure
- Total page count shown in output header so the agent can navigate large documents
- Handles login-wall redirects (server returns HTML instead of PDF)

The typical pattern for a sustainability report task: `scrape` the report landing page to find the PDF URL → `pdf_extract` with `pages="all"` to see the table of contents → `pdf_extract` with a targeted range to get the GHG table → `execute_code` to compute the percentage change.

### Session Memory

`ConversationMemory` keeps a fixed-capacity FIFO of (query, answer) pairs for the lifetime of the CLI process (up to 5 pairs). Context is injected differently depending on the mode:

- **Single query `[1]`**: prior Q&A pairs are prepended to the task before the ReAct loop starts, so the agent can reference earlier findings directly.
- **Deep research `[2]`**: prior context is passed only to the final *synthesis* step, never to the sub-question decomposer. This prevents unrelated prior queries from polluting the fan-out questions.

Session memory is cleared with `[7]` or when the process exits.

### Benchmarking

Standard NLP benchmarks (MMLU, HellaSwag, BIG-Bench, GPQA) measure a model's parametric knowledge — what it already knows from pre-training. They test the model in isolation: fixed prompt in, fixed answer out. For an agentic web research system, that tests the wrong thing entirely.

What actually breaks in a research agent is different:

- **Multi-hop reasoning chains**: the agent must find fact A, then use A to find fact B. A wrong answer at hop 1 compounds — the agent searches for the wrong thing at hop 2, finds plausible-sounding results, and hallucinates a confident final answer. Static benchmarks have no tool calls, so they never surface this failure mode.
- **Hallucination under rate pressure**: when the primary model is rate-limited and the chain falls back to a weaker model mid-run, reasoning quality drops. The weaker model may anchor on a plausible-sounding entity from a previous step rather than continuing to search. This looks like "the model knows the answer" but is actually "the model stopped researching too early".
- **Context contamination**: session memory from a previous failed query can leak into the next one, steering the agent toward a wrong entity it found earlier. Fixed-prompt benchmarks have no session state, so they never catch this.
- **Scraping failures**: a JS-rendered page returns 80 chars of content; the agent should detect this and switch to the browser tool. Whether it does that correctly is not a knowledge question — it is a tool-use and observation-interpretation question.

The benchmark in `benchmarks/` addresses these directly. Each case is a real-world multi-hop research question with a known ground-truth answer:

```
benchmarks/
├── benchmark.json       # cases: query + expected_contains + expected_not_contains + source
└── run_benchmark.py     # runner: executes each case, checks answer, reports PASS/FAIL
```

Evaluation is keyword-based rather than LLM-as-judge: `expected_contains` lists anchor terms that must appear in the answer (e.g. `"shaikh group"`), and `expected_not_contains` lists known hallucinations to reject (e.g. `"world economic forum"`). This is the same approach used by BioASQ, TriviaQA, and Natural Questions — robust to phrasing variation while still catching wrong entities.

```bash
# Run one case
python benchmarks/run_benchmark.py --ids geneva-ai-talks-coo

# Run all cases
python benchmarks/run_benchmark.py

# Save results to a specific file
python benchmarks/run_benchmark.py --out results/2026-03-29.json
```

Output:
```
[geneva-ai-talks-coo]
  status:  PASS  (215s)
  answer:  The Shaikh Group mediated the talks. Their COO is...

[vw-scope-emissions]
  status:  FAIL
  missing: ['%']
  answer:  Volkswagen reduced Scope 1 and Scope 2 emissions...
```

**Adding a new case**: add an entry to `benchmark.json` with `id`, `query`, `expected_contains`, `expected_not_contains`, `source`, and `notes`. No code changes required. The recommended workflow is: run the query manually in the TUI, verify the answer against the primary source, then record the discriminating anchor terms.

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
| `LOG_LEVEL` | `WARNING` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Set to `DEBUG` or `INFO` to see per-step reasoning and tool calls in the terminal. |
| `QUIET_FALLBACK` | `false` | Set to `true` to suppress the "Rate limit reached… Switching to…" console message when the model fallback chain activates. Useful in scripted or CI contexts where provider churn is expected. |

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

**Anti-bot fingerprinting defeats the scraper on major commercial sites.** UA rotation helps against trivial checks but Cloudflare, Akamai, and Datadome fingerprint TLS handshake, header order, and timing — none of which the requests-based scraper controls. Affected sites return a challenge page or silent 403. The `scrape_js` (Playwright) tool passes these more often but is not immune.

**Observation truncation loses context.** At `MAX_TOOL_OUTPUT_LENGTH=3000`, long scraped pages are cut off. Key facts in the truncated portion are permanently lost. A chunking + retrieval approach would address this but adds latency.

**PDF table extraction degrades on scanned/image PDFs.** `pdfplumber` works on text-layer PDFs (the majority of corporate reports). Scanned documents with no text layer return empty pages. There is no OCR fallback.

**Synthesis strategy is LLM-selected, not validated.** The model chooses a reasoning strategy (factual lookup, list compilation, structured extraction, open synthesis) inside its own reasoning pass. There is no external classifier validating the selection. Ambiguous tasks sometimes get the wrong strategy.

**Free-tier rate limits constrain throughput.** Groq allows ~6,000 tokens/min on the free tier. With `max_tokens=4096` per step, the first rate limit typically hits around step 2-3 of a 15-step run. The fallback chain and 10s+ backoff floor mitigate this but do not eliminate it. The `MAX_TOOL_OUTPUT_LENGTH=3000` cap on observations reduces prompt size and partially offsets the increased response budget.

---

## References

Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. *ICLR 2023*. [arxiv.org/abs/2210.03629](https://arxiv.org/abs/2210.03629)

Wei, J., et al. (2022). Chain-of-Thought Prompting Elicits Reasoning in Large Language Models. *NeurIPS 2022*. [arxiv.org/abs/2201.11903](https://arxiv.org/abs/2201.11903)

Schick, T., et al. (2023). Toolformer: Language Models Can Teach Themselves to Use Tools. *NeurIPS 2023*. [arxiv.org/abs/2302.04761](https://arxiv.org/abs/2302.04761)

Greshake, K., et al. (2023). Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection. [arxiv.org/abs/2302.12173](https://arxiv.org/abs/2302.12173)

---

## License

MIT. See [LICENSE](LICENSE).
