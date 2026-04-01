# Quickstart

Get from zero to a working research query in under 5 minutes.

---

## 1. Install

```bash
pip install web-research-agent
```

Optional extras:

```bash
pip install "web-research-agent[providers]"  # Groq / OpenRouter / DeepSeek fallback
pip install "web-research-agent[browser]"    # JS-rendered page scraping via Playwright
pip install "web-research-agent[all]"        # everything
```

Requires Python 3.8+.

---

## 2. Get API keys

Two keys are required, both have a free tier:

| Key | Where to get it | Free tier |
|-----|----------------|-----------|
| `GEMINI_API_KEY` | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) | 1,500 req/day |
| `SERPER_API_KEY` | [serper.dev](https://serper.dev) | 2,500 searches/month |

---

## 3. Run the setup wizard

```bash
webresearch
```

On first run the interactive menu walks you through entering your keys. They are stored in the system keyring — no `.env` file needed. You only do this once.

If you prefer environment variables instead:

```bash
export GEMINI_API_KEY=your_key_here
export SERPER_API_KEY=your_key_here
webresearch
```

---

## 4. Ask a question

From the main menu, press **1** (Single query) and type your question:

```
What were Volkswagen's Scope 1 and Scope 2 emissions in 2023, and by what
percentage did they change compared to 2019?
```

The agent will:
1. **Think** — decompose the task and plan its approach
2. **Search** — query Google via Serper for relevant sources
3. **Scrape** — fetch and parse the most promising pages
4. **Answer** — synthesize findings with source citations

It will not answer from training data alone. If it can't verify something via live search, it says so.

---

## 5. Deep research (parallel mode)

Press **2** (Deep research) for multi-angle queries. The agent decomposes your question into up to 4 sub-questions, researches them in parallel, then synthesizes a comprehensive answer.

Best for: competitive analysis, multi-source fact-checking, topics that span several domains.

---

## 6. Model fallback chain (optional)

If you hit Gemini's free-tier daily limit, add one or more fallback providers. The chain tries them in order:

```bash
# Fast inference fallback
export GROQ_API_KEY=your_key_here

# OpenRouter (access to many models)
export OPENROUTER_API_KEY=your_key_here

# Local model via Ollama
export OLLAMA_BASE_URL=http://localhost:11434
```

Or enter them through **option 6 → Configure API keys** in the menu. The active provider is shown in the status bar; a fallback switch is logged when it happens.

---

## 7. Tune behaviour (optional)

All settings can be overridden with environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `gemini-2.5-flash` | Gemini model to use |
| `MAX_ITERATIONS` | `15` | Max reasoning steps per query |
| `SUB_ITERATIONS` | `8` | Max steps per parallel sub-query |
| `MAX_TOOL_OUTPUT_LENGTH` | `3000` | Max chars per tool observation |
| `TEMPERATURE` | `0.1` | LLM temperature (lower = more deterministic) |
| `WEB_REQUEST_TIMEOUT` | `30` | HTTP timeout in seconds |

---

## 8. Playwright for JS-heavy pages (optional)

Some pages require JavaScript to render. If the `scrape` tool returns thin content:

```bash
pip install playwright
playwright install chromium
```

The `scrape_js` tool will then be available automatically.

---

## Common issues

**"GEMINI_API_KEY not found"** — run `webresearch` and use option 6 to enter your key, or `export GEMINI_API_KEY=...` in your shell.

**"Daily request quota exhausted"** — you've hit Gemini's free-tier daily limit. Add a Groq or OpenRouter key as a fallback, or wait until midnight Pacific time when the quota resets.

**Scrape returns empty / JS page message** — install Playwright (step 8 above) and the agent will automatically use `scrape_js` for those pages.

**Windows PATH issues** — if `webresearch` isn't found after install, run `python -m cli` from the project directory, or add the Python Scripts folder to your PATH.
