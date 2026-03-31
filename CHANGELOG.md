# Changelog

All notable changes to the Web Research Agent project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.4.15] - 2026-03-31

### Changed
- `think` is now a mandatory first action, not an optional one. Two-layer enforcement based on Anthropic's τ-bench findings (prompt-only gives 22% lift; prompt + worked example + parser enforcement gives 76%):
  1. **Prompt rewrite** (`agent.py`): advisory "use the think tool when..." replaced with `MANDATORY REASONING — THIS IS NOT OPTIONAL` block. Unconditional language ("your very first action MUST be think"), explicit trigger events (before first action, after any significant observation), and a worked example showing the exact think → search → think → answer pattern.
  2. **Parser-level enforcement** (`agent.py` `run()`): `_think_called` flag tracks whether think has been used. If the agent tries to call search or any other tool before calling think, the observation is replaced with a corrective error message ("Error: you must use the think tool before calling any other tool.") — no API call is made. The agent self-corrects on the next iteration.
- `tests/test_think_tool.py` updated: added `test_parser_blocks_action_before_think` and `test_think_called_flag_satisfied_allows_search` to structurally verify both enforcement layers. All 11 tests pass.

## [2.4.14] - 2026-03-31

### Added
- `tests/test_think_tool.py`: 9 smoke tests covering the full ThinkTool integration path — tool unit behaviour, ToolManager registration, agent parsing a think action from a mock LLM response, trace capture of think steps and their observations, and presence of the think-tool instruction in the built system prompt.

## [2.4.13] - 2026-03-31

### Fixed
- Execution trace files now write to `~/.webresearch/logs/` (absolute, user-home-relative) instead of `./logs/` (relative to CWD). When `webresearch` is launched from any directory other than the project root, traces were being written to a `logs/` folder in that working directory — meaning `[5] execution logs` would find nothing because it read a different relative path. Both `_save_trace()` and `view_logs()` now use the same `~/.webresearch/logs/` path.
- `webresearch/__init__.py` version string was stuck at `2.4.6` — it was never updated when `pyproject.toml` was bumped. Status bar now shows the correct version.

## [2.4.12] - 2026-03-30

### Fixed
- Timeout errors from fallback providers (Groq, OpenRouter) no longer crash the query. Previously `APITimeoutError` ("Request timed out.") was not matched by `_is_quota_error()` in `llm_chain.py`, so the fallback chain re-raised immediately instead of advancing to the next provider. Added `_is_transient_error()` covering `timed out`, `timeout`, `connection`, `502/503/504` signals — these now trigger the same provider-advance logic as quota errors.
- `llm_compat.py` `generate()` now retries on timeout errors (with a fixed 5 s delay) in addition to rate-limit errors. Timeouts on free-tier providers are infrastructure hiccups that often resolve on a second attempt within the same provider before escalating to the chain fallback.

## [2.4.11] - 2026-03-30

### Changed
- Menu option `[6]` renamed from "reconfigure api keys" to "configuration" and expanded into a sub-menu with two routes: `[a] api keys` (unchanged key setup wizard) and `[b] agent settings` (new interactive screen for `LOG_LEVEL` and `QUIET_FALLBACK`). Settings take effect immediately for the current session; a note directs users to `.env` for persistence across restarts.

## [2.4.10] - 2026-03-29

### Added
- Per-run execution trace logging: every query and deep-research run now writes a JSON file to `logs/trace_YYYYMMDD_HHMMSS_mode.json` containing the full Thought → Action → Observation sequence, final answer, duration, and step count. Viewable from the `[5] view logs` menu option, which lists recent runs and lets you step through each trace interactively.
- `LOG_LEVEL` env var (default `WARNING`): controls the Python logging level. Set to `DEBUG` or `INFO` to print per-step reasoning and tool calls to the terminal — useful for diagnosing multi-hop failures without reading raw JSON trace files.
- `QUIET_FALLBACK` env var (default `false`): set to `true` to suppress the yellow "Rate limit reached on X. Switching to Y…" banner when the model fallback chain activates. Useful in scripted or CI contexts where provider churn is expected and the message is noise.

## [2.4.9] - 2026-03-30

### Added
- `ThinkTool` (`webresearch/tools/think.py`): a no-op reasoning tool that gives the agent an explicit planning and verification slot without making any external calls. The agent uses it to plan search strategy on multi-step questions and to verify that an entity found in results genuinely matches the task description before committing to it. Registered first in the tool manager so it appears at the top of the tool list in the prompt.

### Changed
- ReAct system prompt: two new instructions — (1) for entity-from-description questions, search for the described event first then extract the entity from results rather than assuming a known entity; (2) use the think tool on multi-step questions and to verify entity matches before proceeding. These directly address the failure mode where the agent anchored on WEF/UN due to Geneva's prior weight in training data instead of finding the Shaikh Group.
- `benchmark.json`: confirmed COO name `yannis pallikaris` added to `expected_contains` for the Geneva AI talks case, verified against source.

## [2.4.8] - 2026-03-29

### Added
- `benchmarks/benchmark.json`: structured benchmark suite with three real-world multi-hop research cases (Geneva AI talks COO, VW Scope 1+2 emissions reduction, EU automotive GHG companies). Each case carries `expected_contains` anchor terms and `expected_not_contains` known-hallucination guards.
- `benchmarks/run_benchmark.py`: benchmark runner that executes cases through `initialize_agent()`, checks answers against ground-truth keywords, and reports `PASS`/`FAIL` per case with specifics on missing terms and detected hallucinations. Timestamped JSON results file saved after each run. Supports `--ids` to run a subset and `--out` to redirect the results file.

### Fixed
- `initialize_agent()` in `cli.py` now passes `max_tool_output_length=cfg.max_tool_output_length` to `ReActAgent`. Previously the agent silently used its constructor default of 5000 chars, ignoring the configured value of 3000 — causing each observation to be up to 1.7× larger than intended and bloating multi-step prompts.
- Fallback provider `max_tokens` raised from 2048 → 4096 in `llm_compat.py`. On complex multi-hop tasks, 2048 was insufficient for the model to complete a full Thought + Action + Action Input at later iterations when the prompt already carried several thousand tokens of ReAct history. The truncation caused JSON parse failures and premature Final Answers. 4096 restores reasoning headroom without materially increasing Groq token/min consumption given the smaller observation budget from the fix above.

## [2.4.7] - 2026-03-29

### Fixed
- Session memory no longer saves error or incomplete answers (responses prefixed `⚠`) to `ConversationMemory`. Previously every result — including rate-limit errors and max-iteration failures — was stored and injected as authoritative context into subsequent queries, causing the LLM to anchor on hallucinated facts from failed runs.
- Deep research sub-question decomposition prompt now requires each sub-question to be fully self-contained, using the framing "an independent researcher who sees only that sub-question". Removes the prior domain-specific examples in favour of a general constraint that applies to any query type. Eliminates forward-reference sub-questions (e.g. "who is the COO of this organization?") that failed because parallel mini-agents share no state.
- Scrape JS-detection threshold: very thin responses (< 100 chars of extracted text) now always return a `scrape_js` suggestion, regardless of HTML body size. The prior condition required `html_content > 3000` chars, which was not met by SPAs that return a tiny HTML skeleton — causing the agent to silently receive 80–100 chars of useless content instead of being redirected to the browser scraper.

## [2.4.6] - 2026-03-27

### Added
- `_read_query()` multiline input helper in `cli.py`: first line ending with `:` enters continuation mode; subsequent lines are collected until a blank Enter. Single-line queries are unaffected — they return on the first Enter as before. Fixes silent truncation when pasting multi-criteria research questions.
- `test_cli_input.py`: 7 unit tests covering single-line passthrough, `back` sentinel, blank input, colon trigger with continuation, EOFError/KeyboardInterrupt handling, and trailing-whitespace colon detection.

### Changed
- `ParallelResearchAgent.run()` now accepts an optional `context: str = ""` parameter. Context is forwarded to `_synthesize()` only — `_decompose()` always receives the raw task. Prevents prior Q&A pairs from contaminating sub-question generation in deep research mode.
- `_synthesize()` includes a `SESSION CONTEXT` block in the prompt when context is non-empty, with an instruction to reference it only if directly relevant.
- `_run_deep_research()` in `cli.py` no longer overwrites the query with memory; passes `_session.get_context()` as the separate `context=` kwarg instead.
- Phrase rotation interval: `2.5 s → 6.0 s`. Each status phrase now holds for 6 seconds — readable without flickering on fast queries.
- `test_parallel.py`: 5 new tests covering context isolation in decompose, context presence in synthesize, empty-context omission, run-level clean decompose, and run-level synthesize forwarding.

## [2.4.5] - 2026-03-26

### Fixed
- Suppressed noisy `pdfplumber` warnings (`Cannot set gray stroke color because /'P0' is an invalid float value`) that were leaking to the terminal during PDF extraction. Redirected the underlying `pdfminer` logger to `WARNING` before parsing and restored it after.
- Hardened the ReAct prompt: `Action Input` description now explicitly forbids raw newlines and unescaped backslashes inside JSON string values, reducing `Unterminated string` JSON parse failures on multi-line LLM outputs.

## [2.4.4] - 2026-03-25

### Changed
- Phrase engine overhauled to match the CLAUDE.md spec: action-keyed pools (`search`, `scrape`, `code`, `file`, `pdf`, `think`, `browser`, `default`) each hold 12–14 distinct phrases; `{topic}` interpolation replaced static strings.
- `_SKIP` stopword set expanded with content-free nouns (`percentage`, `statements`, `reduction`, `companies`, `organization`, etc.) so `extract_topic()` reliably surfaces entity words over filler.
- Startup quips pool expanded to 8 options.

## [2.4.3] - 2026-03-25

### Added
- `extract_topic(query)`: extracts 1–2 meaningful words from the query for phrase interpolation, skipping stopwords, weak verbs, possessives, quantifiers, and digits. Falls back to `"this"` for empty or all-stopword input.
- `_phrase(action, elapsed, topic)`: picks a rotating phrase from the action-keyed pool; phrase advances every 2.5 s of elapsed time.
- `_exit_quip(n_queries, total_steps)`: session-aware exit message with tiered logic (zero queries, heavy research, high step count, many queries).
- `_session_queries` and `_session_steps` module-level counters; updated after each query and used by `_exit_quip` on `[q]` exit.

## [2.4.2] - 2026-03-25

### Fixed
- `view_history()`: `questionary.select()` returned the choice's `title` string (e.g. `"  [1]  ..."`) instead of its `value` (the raw query) when the user picked a history entry, causing a crash on re-run. Fixed by setting `value=e["query"]` on each `questionary.Choice`.

## [2.4.1] - 2026-03-25

### Fixed
- **Scraper — HTML tables → markdown**: `<table>` elements are now extracted with BeautifulSoup and converted to aligned markdown grids before `html2text` processes the page. Column values and numbers are preserved verbatim — critical for emissions tables, financial statements, and structured regulatory filings.
- **Scraper — encoding**: switched to `apparent_encoding` (chardet) when the server omits `charset` or defaults to ISO-8859-1, fixing mangled characters in EU government PDFs and older corporate filings.
- **Scraper — 5xx retry**: 500/502/503/504 responses are retried twice with 2 s / 4 s backoff before returning an error.
- **Scraper — content selectors**: 30+ CSS selectors covering common CMS patterns (`.article-body`, `.post-content`, `[data-component]`, etc.) tried before falling back to full `<body>`.
- **Scraper — JS-only detection**: pages with >400 chars raw HTML but <400 chars extracted text now return a `scrape_js` suggestion instead of empty content.
- **Scraper — paywall teaser**: 200 OK responses with <600 chars + subscribe/sign-in keywords are skipped with an alternative-source suggestion.
- **Scraper — auth redirect**: raw HTML is scanned for `<input type="password">` and sign-in prose even when the page returns 200 with substantial content.
- **Scraper — UA rotation**: request headers rotate across a pool of current browser UA strings per request.

## [2.4.0] - 2026-03-25

### Added
- `PDFExtractTool` (`webresearch/tools/pdf.py`): downloads and parses PDFs via `pdfplumber`. Tables are extracted as aligned grids with exact cell values (not OCR text). `pages="12-18"` parameter lets the agent target specific ranges once it knows the document layout. Total page count shown in output header. Handles login-wall redirects (server returns HTML instead of a PDF). Registered automatically if `pdfplumber` is installed.
- `pdfplumber>=0.10.0` added to core dependencies in `pyproject.toml`.
- `pdf_available()` helper in `webresearch/tools/__init__.py` for conditional registration.

## [2.3.4] - 2026-03-25

### Fixed
- `view_history()` crash on re-run: after selecting a history entry the agent was re-invoked with the raw questionary choice object instead of the query string. Fixed by extracting `.value` before passing to `_run_query()`.

## [2.3.3] - 2026-03-25

### Fixed
- `ModelFallbackChain`: added `threading.Lock` around provider rotation and a `Semaphore(1)` per provider to serialise concurrent calls to the same endpoint, preventing race conditions during parallel deep research.
- Status bar markup: menu rows with brackets (e.g. `[dim]`) were being parsed as Rich markup. Switched to `rich.text.Text` with explicit `.append()` calls so brackets always render as literal characters.

## [2.3.2] - 2026-03-25

### Fixed
- `ModelFallbackChain` retry backoff formula changed to `max(10, 2^(attempt+2))` seconds — prevents hammering free-tier rate limits while still recovering promptly after temporary 429s.
- Prompt injection sanitization: `Thought:` and `Action:` filter patterns removed from `_OBSERVATION_INJECTION_PATTERNS` — too broad, they were stripping legitimate content from news articles (e.g. `"Action: The company announced..."`).
- Paywall detection: threshold tightened to 600 chars + explicit subscribe/sign-in keywords to reduce false positives on short but legitimate pages.

## [2.3.1] - 2026-03-25

### Added
- Full TUI implementation: animated startup boot sequence (`render_startup`), `print_status_bar()` one-line config summary, `_print_usage_banner()` Serper monthly usage display with colour-coded thresholds (green / yellow / red).
- `_DONE_FALLBACK` quips list displayed after each successful query.
- Session memory display in menu: `[7] clear session memory · N pair(s) in context`.
- Query history table with step count, duration, and ⚠ flag for error results; `questionary` arrow-key navigation for history re-run.
- Deep research status board (`make_status_board`): live `rich.Table` showing per-sub-query state (pending → running → done/error).

## [2.3.0] - 2026-03-25

### Added
- `ResearchPanel`: `rich.Live`-powered live display for the single-query ReAct loop. Shows query (truncated), iteration counter, elapsed time, spinner, current thought (truncated), action + input preview, and observation byte count. Updates at 12 fps via `step_callback`.
- `_action_preview()`: formats action name + most meaningful input field (`url`, `query`, `filename`, or first value) into a single readable line.
- `_spin(elapsed)`: braille spinner cycling at 12 fps from a 10-char sequence.

## [2.2.1] - 2026-03-11

### Fixed
- `_build_llm_chain`: when Groq/OpenRouter/Ollama keys are configured but the `openai` package is not installed, the agent now prints a clear warning and the install command instead of silently running with only Gemini in the chain
- `setup_api_keys`: same warning printed immediately after entering Groq or OpenRouter keys if `openai` is missing

## [2.2.0] - 2026-03-11

### Added
- `webresearch/credentials.py`: secure credential storage using the OS system keyring (Windows Credential Manager, macOS Keychain, Linux libsecret) via the `keyring` library. Falls back to plain-text `~/.webresearch/config.env` on headless servers and CI environments where no keyring backend is available.
- Interactive multi-provider setup flow covering all five credentials:
  - `GEMINI_API_KEY` and `SERPER_API_KEY` — required, loops until provided
  - `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `OLLAMA_BASE_URL` — optional, skip with rate-limit warning; existing values shown masked and preserved on Enter; type `clear` to remove
- `keyring>=24.0.0` added to core dependencies

### Changed
- `Config` now resolves all five credentials through `get_credential()` (keyring → env var) instead of raw `os.getenv()`
- `check_config()` reads keyring/env first, then the legacy `config.env` file, then prompts first-time setup — upgrading users are not asked to reconfigure
- README: added design-decision sections for fallback chain and secure credential storage; updated installation instructions, API key table, and configuration reference

## [2.1.0] - 2026-03-11

### Added
- Model fallback chain (`webresearch/llm_chain.py`): `ModelFallbackChain` wraps an ordered list of LLM interfaces and automatically advances to the next provider on any 429 / quota error, notifying the user in the terminal
- `webresearch/llm_compat.py`: `OpenAICompatibleLLMInterface` covers any provider that exposes the OpenAI chat-completions API shape — Groq, OpenRouter, DeepSeek, Ollama
- Default chain order: Gemini 2.5 Flash → Groq (llama-3.3-70b-versatile) → OpenRouter (llama-3.3-70b:free) → Ollama (local)
- Optional `[providers]` and `[all]` extras in `pyproject.toml` for `openai` and `playwright` packages
- `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `OLLAMA_BASE_URL` config fields

### Changed
- `_build_llm_chain()` in `cli.py` constructs the fallback chain from whichever provider keys are configured; prints the active chain on startup

## [2.0.7] - 2026-03-11

### Fixed
- Version banner in CLI now auto-syncs from the package (`from webresearch import __version__ as VERSION`) instead of a hardcoded string

## [2.0.6] - 2026-03-11

### Fixed
- Gemini daily quota (`PerDay` limit) now raises immediately with a human-readable message instead of retrying
- Per-minute 429 responses: retry delay is parsed from the `retry_delay { seconds: N }` proto field and honoured exactly instead of using fixed exponential backoff
- Friendly quota error messages display the limit type, wait time, and billing link rather than the raw proto error string

## [2.0.5] - 2026-03-11

### Fixed
- Sandbox: LLM-generated code using triple-quoted strings caused `SyntaxError: unterminated triple-quoted string literal`; tool description now warns against them and the error message includes a fix hint
- HTTP scraper: 401/403 returns "Skipped (requires login)" with instruction to find an alternative source; 406 returns "Skipped (406 Not Acceptable)"; 429 returns "Skipped (rate limited)" — agent no longer halts on paywalled or blocked URLs

## [2.0.4] - 2026-03-11

### Fixed (red-team hardening — all 12 items)
- Prompt injection sanitization: scraped observations are filtered through regex patterns before entering the LLM prompt (`ignore all previous instructions`, `Final Answer:`, `Action:`, `Thought:`, `system:`, `[INST]`, etc.)
- Sliding window prompt: last 8 steps kept in full; earlier steps condensed to one-line summaries to prevent context overflow at high iteration counts
- Action deduplication cache: repeated identical tool calls return cached observations without consuming API quota
- `Final Answer` regex: changed to non-greedy with stop boundary to prevent capturing subsequent `Action:` blocks
- `_format_action_input`: bare `except:` replaced with `except (TypeError, ValueError)`
- `_parse_action_input_fallback`: returns `{"_raw_input": ..., "_parse_error": ...}` on total failure instead of silent `{}`
- `_generate_best_effort_answer`: per-step budget scales with `max_tool_output_length // n_steps` instead of hardcoded 1000 chars
- `run()` errors prefixed `"⚠ Error:"` so CLI renders a red panel instead of a green result panel
- `Step` dataclass: added `iteration`, `timestamp`, `elapsed_ms` fields
- `StepCallback` type alias: `Callable[[int, Step], None]`
- `AgentError` custom exception class
- `import json` moved to module top level

## [2.0.3] - 2026-03-11

### Fixed
- Tasks file: `os.path.isfile()` check added before processing; passing a directory path now shows a clear error instead of `PermissionError`
- `setup_api_keys()` no longer writes `MODEL_NAME`, `MAX_ITERATIONS`, or other settings to `config.env`; only credentials are persisted so they remain current across package upgrades

## [2.0.2] - 2026-03-11

### Fixed
- Stale `MODEL_NAME` in `~/.webresearch/config.env` from previous installs no longer overrides the package default; `check_config()` now returns only `{GEMINI_API_KEY, SERPER_API_KEY}` from the stored file

## [2.0.1] - 2026-03-10

### Fixed
- Initial PyPI publish (v2.0.0 tag already existed on the index)

## [2.0.0] - 2026-03-10

### Added
- Complete rewrite of the agent and CLI
- `ReActAgent`: Thought-Action-Observation loop with configurable iteration cap and best-effort answer on timeout
- `ParallelResearchAgent`: LLM-driven decomposition into sub-questions, concurrent execution via `ThreadPoolExecutor`, synthesis pass
- `ConversationMemory`: fixed-capacity FIFO of (query, answer) pairs injected as context into subsequent queries
- Rich terminal UI: live `rich.Live` streaming of the ReAct step table, deep-research status board, query history with arrow-key navigation (questionary), session memory display
- `ModelFallbackChain`, `OpenAICompatibleLLMInterface` (added in 2.1.0 — see above)
- AST-based code sandbox: blocks dangerous imports and `os.*` calls before code reaches the interpreter; runs in an isolated `TemporaryDirectory` with API keys stripped
- Prompt injection sanitization, sliding-window prompt, action deduplication (hardened in 2.0.4)
- `SearchTool` monthly usage tracker with colour-coded usage banner
- `BrowserScrapeTool` (Playwright) as optional JS-rendering fallback
- `FileOpsTool` for reading and writing local files

### Changed
- Package name remains `web-research-agent`; CLI entry point `webresearch`
- All v1.x tool and agent implementations replaced

## [1.2.1] - 2025-01-10

### Added
- Script for PATH management

### Fixed
- Import issues across multiple modules
- UX improvements on color scheme
- UX improvements on command line interface

### Removed
- Replaced Colorama with Rich

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

- [Repository](https://github.com/ashioyajotham/web_research_agent)
- [Issues](https://github.com/ashioyajotham/web_research_agent/issues)
- [Pull Requests](https://github.com/ashioyajotham/web_research_agent/pulls)
- [Releases](https://github.com/ashioyajotham/web_research_agent/releases)

---

**Note**: For detailed technical changes, see the Git commit history.
