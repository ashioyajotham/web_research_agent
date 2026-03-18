# Web Research Agent

A from-scratch implementation of the ReAct (Reasoning and Acting) paradigm for autonomous web research. Built in January 2025 as a take-home coding challenge — before "deep research" became a named product category — with no use of LangChain or agent frameworks. The goal was to understand how far a minimal, well-structured ReAct loop could get on real-world multi-hop research tasks, and where it fundamentally breaks.

---

## Background and Motivation

In late 2024, most publicly available agent implementations were either framework-wrapped (LangChain, AutoGPT derivatives) or academically toy-sized. The FutureSearch coding challenge — a two-hour constraint, Python only, no frameworks, Serper + OpenAI — forced a question: what is the minimum viable architecture for a research agent that handles real tasks?

The representative tasks in the challenge are not trivial:

- Multi-hop factual lookup (*"COO of the org that mediated secret US-China AI talks in Geneva, 2023"*)
- Compilation with sourcing requirements (*"10 Biden statements on US-China relations, each from a distinct occasion, with sources"*)
- Structured data extraction from external datasets (*"Epoch AI large-scale models dataset → time series of record-setting compute runs"*)
- PDF-level numerical retrieval (*"VW Scope 1+2 GHG emissions: percentage reduction 2021→2023"*)
- Multi-criteria entity filtering (*EU motor vehicle companies, EFRAG-defined sector, GHG data for 2021-2023, >€1B revenue, non-subsidiary"*)

These tasks span at least three distinct failure modes for naive agents: single-source trust, inability to parse structured documents, and conflation of entity lookup with numerical reasoning. The architecture here was designed with those failure modes as the primary constraint.

---

## Research Questions

This implementation is an exploratory engineering artefact, not a finished system. The open questions it was built around:

**1. How much of agent performance is model vs. scaffold?**
The ReAct loop is a prompt structure. The synthesis strategies are also prompts. At what point does improving the scaffold stop mattering relative to just using a stronger reasoning model?

**2. Can answer-type detection be made reliable without task-specific heuristics?**
The comprehension module infers whether a task expects a factual answer, a ranked list, a comparison, or a comprehensive analysis — without hardcoded rules. This works on obvious cases and degrades on ambiguous ones. It is unclear whether the failure mode is the classifier or the downstream strategy selection.

**3. What is the actual failure distribution of a ReAct loop on multi-hop tasks?**
Anecdotally: most failures are not in reasoning but in content access (scraping blocked, PDF not parseable, rate limits) and in observation length truncation causing the model to lose key facts from earlier steps. This suggests the bottleneck is infrastructure, not intelligence.

**4. Does observation sanitisation materially affect answer quality on adversarial web content?**
The current implementation does not sanitise observations before feeding them back into the prompt. Prompt injection via scraped content is a known attack vector. The extent to which this affects real-world performance on non-adversarial tasks is an open empirical question.

---

## Architecture

The agent implements the ReAct paradigm as described in Yao et al. (2023):

```
Thought → Action → Observation → [repeat] → Final Answer
```

The loop is single-threaded and synchronous. This is a deliberate constraint — parallelism would have made the two-hour challenge harder to reason about and debug — but it is the primary architectural limitation relative to production systems.

```
WebResearchAgent
├── LLMInterface          # Gemini 2.0 Flash (configurable)
├── ToolManager           # Registry pattern; add tools without touching core logic
│   ├── SearchTool        # Serper.dev API → Google search results
│   ├── ScrapeTool        # HTTP + BeautifulSoup → cleaned text
│   ├── CodeExecutor      # Local Python subprocess with timeout
│   └── FileOps           # Read/write for data persistence across steps
├── Comprehension         # Task analysis: answer type, information targets, output structure
├── Planner               # Adaptive plan: search → browse → present (± code)
└── Memory                # In-session step history; no cross-session persistence
```

### Synthesis Strategies

The agent selects one of four synthesis strategies based on task structure:

| Strategy | Trigger | Description |
|---|---|---|
| `extract-and-verify` | Factual lookup | Target information sought across multiple sources; cross-referenced |
| `aggregate-and-filter` | List/compilation | Multiple items gathered, filtered by stated criteria |
| `collect-and-organize` | Structured output | Items collected with associated metadata, organised by schema |
| `comprehensive-synthesis` | Open analysis | Multiple perspectives gathered, synthesised into a coherent account |

Strategy selection happens inside the LLM's reasoning pass, not via a separate classifier. This makes it interpretable but fragile — the model can select a strategy inconsistent with the task structure, and there is no validation step.

### Fallback Chain

When primary content access fails:

1. Full scrape → cleaned text
2. Scrape blocked → search snippet analysis
3. Snippet insufficient → re-query with modified search terms
4. Re-query fails → flag in observation, continue with partial information

The fallback chain means the agent rarely hard-fails, but it does degrade silently — partial information enters the context without being flagged as lower-confidence than full scrapes.

---

## Known Limitations

These are structural, not incidental bugs:

**Single-threaded execution.** Each search, scrape, and LLM call is sequential. A 15-iteration run with network I/O takes 3-5 minutes. Parallelising sub-queries would reduce this substantially but requires rethinking the observation assembly step.

**No PDF parsing.** Tasks requiring numerical extraction from sustainability reports, academic papers, or datasets in PDF form hit a hard wall. URLs to PDFs are noted in observations but not fetched. This was the primary failure mode on the VW emissions and Epoch AI tasks.

**Observation truncation loses context.** At `MAX_TOOL_OUTPUT_LENGTH=5000`, long scraped pages are truncated. Crucial information in the truncated portion is permanently lost from the agent's context. A chunking + retrieval strategy (embedding the observation and querying relevant chunks) would address this.

**No prompt injection defence.** Scraped web content is injected raw into the prompt. A page containing `Final Answer: [attacker content]` would short-circuit the loop. This has not been exploited in practice on normal research tasks but is a real attack surface.

**Synthesis strategy is LLM-selected, not validated.** There is no check that the selected strategy matches what the task actually requires. A rule-based pre-classifier would make this more robust and debuggable.

**No cross-session memory.** Each task starts with an empty step history. There is no mechanism for the agent to reuse knowledge from a previous related query.

---

## Installation

```bash
pip install web-research-agent
```

Requires two API keys on first run:

- **Gemini API key** — [Google AI Studio](https://makersuite.google.com/app/apikey) (free tier)
- **Serper API key** — [Serper.dev](https://serper.dev) (free tier: 2,500 searches/month)

Keys are stored at `~/.webresearch/config.env` after first-run setup.

```bash
webresearch          # interactive CLI
```

### From Source

```bash
git clone https://github.com/ashioyajotham/web_research_agent.git
cd web_research_agent
pip install -e .
webresearch
```

---

## Usage

### Interactive CLI

```bash
webresearch
```

Options: run a single query, process a task file, view execution logs, reconfigure keys.

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

### Adding a Tool

The `ToolManager` uses a registration pattern. To add a new tool:

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
        # implementation
        return result
```

```python
# main.py
tool_manager.register_tool(MyTool())
```

No changes to core agent logic required.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `MAX_ITERATIONS` | 15 | ReAct loop iterations before forced termination |
| `MAX_TOOL_OUTPUT_LENGTH` | 5000 | Characters of observation fed back to LLM |
| `TEMPERATURE` | 0.1 | LLM temperature; lower = more deterministic |
| `MODEL_NAME` | gemini-2.0-flash-exp | Model identifier |
| `WEB_REQUEST_TIMEOUT` | 30 | Seconds before HTTP request timeout |
| `CODE_EXECUTION_TIMEOUT` | 60 | Seconds before subprocess kill |

---

## Project Structure

```
web_research_agent/
├── webresearch/
│   ├── agent.py           # ReAct loop, step parsing, prompt construction
│   ├── llm.py             # LLM interface (Gemini)
│   ├── config.py          # Configuration management
│   └── tools/
│       ├── base.py        # Tool abstract base class
│       ├── search.py      # Serper.dev search
│       ├── scrape.py      # HTTP scraping + cleaning
│       ├── code_executor.py
│       └── file_ops.py
├── cli.py                 # Interactive CLI entry point
├── main.py                # Batch processing entry point
├── pyproject.toml
└── requirements.txt
```

---

## References

**Core paradigm**

Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. *ICLR 2023*. [arxiv.org/abs/2210.03629](https://arxiv.org/abs/2210.03629)

**Related work and context**

Wei, J., et al. (2022). Chain-of-Thought Prompting Elicits Reasoning in Large Language Models. *NeurIPS 2022*. [arxiv.org/abs/2201.11903](https://arxiv.org/abs/2201.11903)

Huang, W., et al. (2022). Language Models as Zero-Shot Planners: Extracting Actionable Knowledge for Embodied Agents. *ICML 2022*. [arxiv.org/abs/2201.07207](https://arxiv.org/abs/2201.07207)

Schick, T., et al. (2023). Toolformer: Language Models Can Teach Themselves to Use Tools. *NeurIPS 2023*. [arxiv.org/abs/2302.04761](https://arxiv.org/abs/2302.04761)

Creswell, A., et al. (2022). Faithful Reasoning Using Large Language Models. [arxiv.org/abs/2208.14271](https://arxiv.org/abs/2208.14271)

**On agent failure modes**

Greshake, K., et al. (2023). Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection. [arxiv.org/abs/2302.12173](https://arxiv.org/abs/2302.12173) — directly relevant to the observation sanitisation gap noted above.

---

## License

MIT. See [LICENSE](LICENSE).

---

## Origin

This project began as a two-hour take-home coding challenge from FutureSearch (January 2025). The brief: build an LLM agent that can browse the web and write code, from scratch, in Python, no frameworks. The challenge tasks were deliberately adversarial — designed so that no one fully solves all of them in two hours. The agent architecture here was the result of that constraint. The project has been extended and published as an open-source research artefact.
