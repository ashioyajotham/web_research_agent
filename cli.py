"""
Interactive CLI for Web Research Agent.
Provides a beautiful terminal interface with real-time ReAct step streaming,
multi-turn session memory, and query history navigation.
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import random

import pyfiglet
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

try:
    import questionary
    _HAS_QUESTIONARY = True
except ImportError:
    _HAS_QUESTIONARY = False

console = Console()

from webresearch import __version__ as VERSION
TAGLINE = "stay curious, anon.  the web doesn't answer itself."

# ─── Theme ───────────────────────────────────────────────────────────────────
# Single accent colour used for all structural chrome: borders, rules, spinner,
# menu keys, iteration counter, and interactive prompts.
# Change this one constant to retheme the entire agent.
THEME = "cyan"

STARTUP_QUIPS: List[str] = [
    "booting the curiosity engine",
    "calibrating the question accelerator",
    "charging up the search antennae",
    "warming up the research reactor",
    "initialising the knowledge pipeline",
    "loading the mechanistic interpreter (not that kind)",
    "spinning up the inference coils",
    "allocating attention heads",
]

_DONE_FALLBACK: List[str] = [
    "stay curious, anon.",
    "tokens well spent.",
    "sources cited. vibes: immaculate.",
    "no hallucinations detected (that we know of).",
    "the inference chain held.",
    "knowledge acquired. proceed accordingly.",
    "attention heads: vindicated.",
    "the oracle has delivered.",
    "research complete. touch grass.",
    "citations attached. conclusions drawn.",
]

# Words stripped before extracting the {topic} for phrase interpolation.
# Includes stopwords, weak verbs, possessives, quantifiers, and content-free
# nouns so "volkswagen scope" wins over "volkswagen their".
_SKIP: frozenset = frozenset({
    "by","what","how","who","when","where","why",
    "find","get","compile","download","calculate","write",
    "search","look","make","create","build","extract","give",
    "list","show","tell","help","check","identify",
    "a","an","the","for","from","of","in","on","at","to",
    "and","or","that","this","which","with","about","into",
    "did","does","do","is","are","was","were","has","have",
    "had","can","could","would","should","will","please","me",
    "their","its","his","her","our","your","my","these","those",
    "many","much","some","any","all","each","every","both",
    "statements","made","reduce","reduction","amount","total",
    "number","percentage","percent","sum","value","data",
    "information","details","names","companies","company",
    "organizations","organization","person","people","up","set","group",
})

# Action-keyed phrase pools — {topic} is filled at render time by extract_topic().
# Keys are matched with `k in action.lower()` so "execute_code" matches "code",
# "file_ops" matches "file", "scrape_js" and "browser" both match "browser".
PHRASES: Dict[str, List[str]] = {
    # Each pool uses the SPINNER_VERBS style — one verb per step, picked by iteration number.
    # Themed to the action type so the word feels contextually right.
    "search": [
        "Investigating...", "Spelunking...", "Perusing...", "Deciphering...",
        "Scurrying...", "Foraging...", "Scouring...", "Herding...",
        "Outpacing...", "Triangulating...", "Rummaging...", "Sifting...",
        "Pouncing...", "Sniffing...", "Prospecting...", "Hunting...",
    ],
    "scrape": [
        "Unravelling...", "Dissecting...", "Schlepping...", "Swiping...",
        "Perusing...", "Hoovering...", "Harvesting...", "Skimming...",
        "Ingesting...", "Extracting...", "Parsing...", "Devouring...",
        "Absorbing...", "Distilling...",
    ],
    "code": [
        "Computing...", "Calculating...", "Crunching...", "Processing...",
        "Synthesizing...", "Integrating...", "Iterating...", "Executing...",
        "Churning...", "Compiling...", "Quantumizing...", "Transmuting...",
    ],
    "file": [
        "Rustling...", "Checkpointing...", "Archiving...", "Committing...",
        "Stashing...", "Rummaging...", "Filing...", "Cataloguing...",
    ],
    "pdf": [
        "Perusing...", "Dissecting...", "Unravelling...", "Excavating...",
        "Extracting...", "Harvesting...", "Mining...", "Spelunking...",
    ],
    "think": [
        "Cogitating...", "Pondering...", "Ruminating...", "Musing...",
        "Deliberating...", "Reflecting...", "Mulling...", "Philosophising...",
        "Cerebrating...", "Considering...", "Noticing...", "Noodling...",
        "Stewing...", "Puzzling...", "Ideating...", "Hypothesizing...",
    ],
    "browser": [
        "Perambulating...", "Gallivanting...", "Meandering...", "Wandering...",
        "Navigating...", "Venturing...", "Spelunking...", "Exploring...",
    ],
    "default": [
        "Accomplishing...", "Actioning...", "Actualizing...", "Architecting...",
        "Baking...", "Beaming...", "Beboppin'...", "Befuddling...", "Billowing...",
        "Bloviating...", "Boogieing...", "Boondoggling...", "Booping...",
        "Bootstrapping...", "Brewing...", "Burrowing...", "Canoodling...",
        "Caramelizing...", "Cascading...", "Catapulting...", "Channeling...",
        "Choreographing...", "Coalescing...", "Combobulating...", "Composing...",
        "Concocting...", "Contorting...", "Convening...", "Crystallizing...",
        "Cultivating...", "Determining...", "Dilly-dallying...", "Discombobulating...",
        "Doodling...", "Drizzling...", "Elucidating...", "Embellishing...",
        "Enchanting...", "Envisioning...", "Fermenting...", "Fiddling...",
        "Finagling...", "Finetuning...", "Flabbergasting...", "Flummoxing...",
        "Fluttering...", "Forging...", "Frolicking...", "Frosting...",
        "Gallivanting...", "Galloping...", "Garnishing...", "Generating...",
        "Gesticulating...", "Germinating...", "Gitifying...", "Grooving...",
        "Harmonizing...", "Hatching...", "Honking...", "Hullaballooing...",
        "Hyperspacing...", "Imagining...", "Improvising...", "Jitterbugging...",
        "Julienning...", "Kneading...", "Leavening...", "Levitating...",
        "Lollygagging...", "Manifesting...", "Marinating...", "Metamorphosing...",
        "Misting...", "Moonwalking...", "Moseying...", "Mustering...",
        "Nebulizing...", "Orchestrating...", "Percolating...", "Photosynthesizing...",
        "Pollinating...", "Pontificating...", "Precipitating...", "Propagating...",
        "Puttering...", "Quantumizing...", "Razzle-dazzling...", "Razzmatazzing...",
        "Recombobulating...", "Reticulating...", "Sautéing...", "Seasoning...",
        "Shenaniganing...", "Shimmying...", "Simmering...", "Skedaddling...",
        "Sketching...", "Slithering...", "Smooshing...", "Sock-hopping...",
        "Spinning...", "Sprouting...", "Sublimating...", "Swirling...",
        "Tangentializing...", "Tinkering...", "Tip-toeing...", "Tomfoolering...",
        "Topsy-turrying...", "Transfiguring...", "Twisting...", "Undulating...",
        "Unfurling...", "Vibing...", "Waddling...", "Warping...",
        "Whatchamacalliting...", "Whirlpooling...",
    ],
}

logging.getLogger().setLevel(logging.WARNING)

# ─── Session memory (persists for the lifetime of this CLI process) ───────────
from webresearch.memory import ConversationMemory
_session = ConversationMemory(max_pairs=5)


# ─── Live research panel ─────────────────────────────────────────────────────


def extract_topic(query: str) -> str:
    """Extract 1–2 meaningful words from a query for phrase interpolation.

    Skips stopwords, weak verbs, possessives, quantifiers, and content-free
    nouns so "volkswagen scope" wins over "volkswagen their percentage".
    Falls back to "this" for empty input, all-stopwords, or single-char leftovers.
    """
    if not query or not query.strip():
        return "this"
    words = query.strip().lower().split()
    meaningful: List[str] = []
    for w in words:
        clean = re.sub(r"[^a-z0-9\-]", "", w)
        if clean and clean not in _SKIP and not clean.isdigit() and len(clean) > 1:
            meaningful.append(clean)
        if len(meaningful) == 2:
            break
    topic = " ".join(meaningful) if meaningful else "this"
    return (topic[:25] + "…") if len(topic) > 28 else topic


def _phrase(action: Optional[str], step: int, topic: str = "this") -> str:
    """Pick a phrase keyed to the current tool action and step number.

    One phrase per step — picked by step index, not by elapsed time.
    This means the phrase stays stable for the entire duration of a step
    (which can range from 3 s to 30 s) rather than cycling mid-action.
    """
    key = "default"
    if action:
        for k in PHRASES:
            if k in action.lower():
                key = k
                break
    pool = PHRASES[key]
    raw = pool[step % len(pool)]
    return raw.replace("{topic}", topic)


# ─── Session stats (lifetime of this CLI process) ────────────────────────────
_session_queries: int = 0
_session_steps: int = 0


def _exit_quip(n_queries: int, total_steps: int) -> str:
    if n_queries == 0:
        return "you came, you saw, you didn't ask anything."
    if n_queries == 1 and total_steps <= 3:
        return "one question, answered. not bad."
    if total_steps >= 60:
        return f"{total_steps} steps taken. the web has been thoroughly interrogated."
    if total_steps >= 30:
        q_word = "query" if n_queries == 1 else "queries"
        return f"{n_queries} {q_word}, {total_steps} steps deep. that's some serious digging."
    if n_queries >= 5:
        return f"{n_queries} questions answered. the curiosity engine delivered."
    return random.choice(_DONE_FALLBACK)


class ResearchPanel:
    """Dynamic Rich renderable for live ReAct loop — spinner, elapsed, thought/action."""

    def __init__(self, query: str, max_iterations: int, start_time: float):
        self.query = query
        self.topic = extract_topic(query)
        self.max_iterations = max_iterations
        self.start_time = start_time
        self.iteration = 0
        self.current_thought: Optional[str] = None
        self.current_action: Optional[str] = None
        self.current_action_input: Optional[Dict] = None
        self.current_obs_len: int = 0
        self.done = False
        self._spinner = Spinner("arc", style=THEME)

    def update(self, iteration: int, step: Any) -> None:
        self.iteration = iteration
        self.current_thought = step.thought
        self.current_action = step.action
        self.current_action_input = step.action_input
        self.current_obs_len = len(step.observation or "")

    def _action_preview(self) -> str:
        if not self.current_action:
            return "—"
        tool = self.current_action
        inp = self.current_action_input or {}
        # Show the most meaningful input field
        preview = (
            inp.get("url") or inp.get("query") or inp.get("filename")
            or next(iter(inp.values()), None)
        )
        if preview and isinstance(preview, str):
            short = (preview[:50] + "…") if len(preview) > 50 else preview
            return f"[bold yellow]{tool}[/bold yellow]  [dim]→[/dim]  {short}"
        return f"[bold yellow]{tool}[/bold yellow]"

    def __rich__(self) -> Panel:
        elapsed = time.time() - self.start_time
        phrase = _phrase(self.current_action, self.iteration, self.topic)

        grid = Table.grid(padding=(0, 1))
        grid.add_column(style="dim", min_width=11, max_width=11)
        grid.add_column(style="white", ratio=1)

        q = (self.query[:62] + "…") if len(self.query) > 62 else self.query
        grid.add_row("query", f"[bold]{q}[/bold]")

        iter_str = f"[bold {THEME}]{self.iteration}[/bold {THEME}][dim] / {self.max_iterations}[/dim]"
        elapsed_str = f"[yellow]{elapsed:.0f}s[/yellow]"
        grid.add_row("iteration", f"{iter_str}    elapsed  {elapsed_str}")
        grid.add_row("", "")

        if self.done:
            grid.add_row(f"[bold green]✓[/bold green]", "[bold green]complete[/bold green]")
        else:
            spin_frame = self._spinner.render(time.time())
            grid.add_row(spin_frame, f"[dim italic]{phrase}[/dim italic]")

        grid.add_row("", "")

        if self.current_thought:
            t = (self.current_thought[:64] + "…") if len(self.current_thought) > 64 else self.current_thought
            grid.add_row("thought", f"[white]{t}[/white]")

        grid.add_row("action", self._action_preview())

        if self.current_obs_len:
            grid.add_row("status", f"[dim]received {self.current_obs_len:,} chars[/dim]")
        elif self.iteration > 0 and not self.done:
            grid.add_row("status", f"[dim {THEME}]running…[/dim {THEME}]")

        return Panel(
            grid,
            title="[dim]─── research in progress[/dim]",
            border_style=THEME,
            padding=(0, 1),
        )


# ─── Banner ──────────────────────────────────────────────────────────────────

def print_banner() -> None:
    try:
        raw = pyfiglet.figlet_format("WEB RESEARCH", font="small_slant")
    except pyfiglet.FontNotFound:
        raw = pyfiglet.figlet_format("WEB RESEARCH", font="slant")
    lines = [l for l in raw.split("\n") if l.strip()]
    console.print()
    for i, line in enumerate(lines):
        console.print(line, style=f"bold {THEME}")
    console.print(Text(TAGLINE, style=f"italic dim {THEME}"), justify="center")
    console.print()


def print_status_bar(config: dict) -> None:
    """One-line config summary: ✓ config loaded · model · serper · vX.Y.Z"""
    from webresearch.config import Config
    model = Config().model_name

    extras = [k.lower().replace("_api_key", "").replace("_base_url", "")
              for k in ("GROQ_API_KEY", "OPENROUTER_API_KEY", "OLLAMA_BASE_URL")
              if config.get(k)]

    dot = "  ·  "   # plain text separator; styled dim via Text.append(style=)
    line = Text()
    line.append("  ✓  config loaded", style="green")
    line.append(dot, style="dim")
    line.append(model, style=f"bold {THEME}")
    line.append(dot, style="dim")
    line.append("serper", style="green")
    for e in extras:
        line.append(dot, style="dim")
        line.append(e, style="dim")
    line.append(dot, style="dim")
    line.append(f"v{VERSION}", style="dim")

    console.print(line)
    console.print(Rule(style=THEME))
    console.print()


def render_startup(model: str) -> None:
    """Animated boot sequence — shown once at launch after banner."""
    console.print(f"  [dim]{random.choice(STARTUP_QUIPS)}[/dim]", end="")
    for _ in range(3):
        time.sleep(0.18)
        console.print("[dim].[/dim]", end="")
    console.print()
    console.print()

    checks = [
        ("rich",   "terminal ui"),
        ("config", "credentials loaded"),
        ("model",  model),
        ("serper", "search api"),
    ]
    for name, detail in checks:
        time.sleep(0.07)
        t = Text()
        t.append("  ✓  ", style="green")
        t.append(f"{name:<10}", style="dim")
        t.append(detail, style="white")
        console.print(t)
    console.print()


# ─── Config ──────────────────────────────────────────────────────────────────

def get_config_path() -> Path:
    config_dir = Path.home() / ".webresearch"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "config.env"


def load_config() -> dict:
    config_path = get_config_path()
    config = {}
    if config_path.exists():
        with open(config_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
    return config


def save_config(config: dict):
    config_path = get_config_path()
    with open(config_path, "w") as f:
        f.write("# Web Research Agent Configuration\n")
        f.write("# This file is automatically generated\n\n")
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    console.print(f"✓ Configuration saved to {config_path}", style="bold green")


def agent_settings():
    """Interactive sub-screen for toggling LOG_LEVEL and QUIET_FALLBACK."""
    console.print(Rule("[dim]agent settings[/dim]", style=THEME))
    console.print()

    # ── LOG_LEVEL ─────────────────────────────────────────────────────────────
    current_level = os.environ.get("LOG_LEVEL", "WARNING").upper()
    console.print("[bold yellow]1. Log level[/bold yellow]")
    console.print("   Controls how much internal reasoning is printed to the terminal.")
    console.print(f"   [dim]Current: [{THEME}]{current_level}[/{THEME}][/dim]")
    console.print("   [dim]Options: DEBUG  INFO  WARNING  ERROR[/dim]")
    val = Prompt.ask("   [green]New log level[/green] (Enter to keep)", default="").strip().upper()
    if val and val in ("DEBUG", "INFO", "WARNING", "ERROR"):
        os.environ["LOG_LEVEL"] = val
        # re-apply immediately so the rest of this session respects it
        logging.basicConfig(level=getattr(logging, val, logging.WARNING), force=True)
        console.print(f"   [bold green]Log level set to {val}[/bold green]")
    elif val:
        console.print("   [dim yellow]Unrecognised level — keeping current value.[/dim yellow]")

    # ── QUIET_FALLBACK ────────────────────────────────────────────────────────
    console.print()
    current_quiet = os.environ.get("QUIET_FALLBACK", "false").lower() == "true"
    console.print("[bold yellow]2. Quiet fallback[/bold yellow]")
    console.print("   Suppress the 'Rate limit reached... Switching to...' banner.")
    console.print(f"   [dim]Current: [{THEME}]{'on' if current_quiet else 'off'}[/{THEME}][/dim]")
    val = Prompt.ask("   [green]Enable quiet fallback?[/green] (y/n, Enter to keep)", default="").strip().lower()
    if val in ("y", "yes", "true", "1"):
        os.environ["QUIET_FALLBACK"] = "true"
        console.print("   [bold green]Quiet fallback enabled.[/bold green]")
    elif val in ("n", "no", "false", "0"):
        os.environ["QUIET_FALLBACK"] = "false"
        console.print("   [bold green]Quiet fallback disabled.[/bold green]")

    console.print()
    console.print(
        f"[dim]Settings apply for this session. To persist across restarts, add them to your "
        f"[{THEME}].env[/{THEME}] file in the project directory.[/dim]"
    )
    console.print()


def configure() -> dict:
    """Configuration hub — routes to API key setup or agent settings."""
    console.print(Rule("[dim]configuration[/dim]", style=THEME))
    console.print()
    t = Text()
    t.append("  [a]", style=f"bold {THEME}"); t.append("  api keys              ", style="white"); t.append("gemini · serper · fallback providers", style="dim")
    console.print(t)
    t = Text()
    t.append("  [b]", style=f"bold {THEME}"); t.append("  agent settings        ", style="white"); t.append("log level · quiet fallback", style="dim")
    console.print(t)
    t = Text()
    t.append("  [x]", style=f"bold {THEME}"); t.append("  back", style="white")
    console.print(t)
    console.print()

    choice = Prompt.ask("[green]❯[/green]", choices=["a", "b", "x"], show_choices=False)
    console.print()
    if choice == "a":
        return setup_api_keys()
    elif choice == "b":
        agent_settings()
    return {}


def setup_api_keys() -> dict:
    from webresearch.credentials import set_credential, keyring_available, get_credential

    storage_method = "system keyring" if keyring_available() else f"~/.webresearch/config.env"
    console.print(
        Panel.fit(
            f"[bold {THEME}]API Key Setup[/bold {THEME}]\n"
            f"Credentials will be stored in: [green]{storage_method}[/green]",
            border_style=THEME,
        )
    )
    console.print()

    config = {}

    # ── 1. Gemini (required) ──────────────────────────────────────────────────
    console.print("[bold yellow]1. Gemini API Key[/bold yellow]  [red](required)[/red]")
    console.print("   Get yours at: https://aistudio.google.com/app/apikey")
    existing = get_credential("GEMINI_API_KEY")
    if existing:
        console.print(f"   [dim]Current value: {'*' * 8}{existing[-4:]}[/dim]")
    while True:
        prompt_suffix = " (Enter to keep existing)" if existing else ""
        val = Prompt.ask(f"   [green]Enter Gemini API key[/green]{prompt_suffix}", default="").strip()
        if val:
            config["GEMINI_API_KEY"] = val
            break
        if existing:
            config["GEMINI_API_KEY"] = existing
            break
        console.print("   [bold red]Gemini API key is required and cannot be skipped.[/bold red]")

    # ── 2. Serper (required) ──────────────────────────────────────────────────
    console.print("\n[bold yellow]2. Serper API Key[/bold yellow]  [red](required)[/red]")
    console.print("   Get yours at: https://serper.dev  [dim](free tier: 2,500 searches/month)[/dim]")
    existing = get_credential("SERPER_API_KEY")
    if existing:
        console.print(f"   [dim]Current value: {'*' * 8}{existing[-4:]}[/dim]")
    while True:
        prompt_suffix = " (Enter to keep existing)" if existing else ""
        val = Prompt.ask(f"   [green]Enter Serper API key[/green]{prompt_suffix}", default="").strip()
        if val:
            config["SERPER_API_KEY"] = val
            break
        if existing:
            config["SERPER_API_KEY"] = existing
            break
        console.print("   [bold red]Serper API key is required and cannot be skipped.[/bold red]")

    # ── 3. Groq (optional) ────────────────────────────────────────────────────
    console.print("\n[bold yellow]3. Groq API Key[/bold yellow]  [dim](optional — first LLM fallback)[/dim]")
    console.print("   Get yours at: https://console.groq.com  [dim](free tier available)[/dim]")
    console.print("   [dim]Activated automatically when Gemini hits rate limits.[/dim]")
    existing = get_credential("GROQ_API_KEY")
    if existing:
        console.print(f"   [dim]Current value: {'*' * 8}{existing[-4:]}  (Enter to keep, 'clear' to remove)[/dim]")
        val = Prompt.ask("   [green]Enter Groq API key[/green]", default="").strip()
        if val.lower() == "clear":
            pass  # don't add to config — will be missing from save
        elif val:
            config["GROQ_API_KEY"] = val
        else:
            config["GROQ_API_KEY"] = existing
    else:
        val = Prompt.ask("   [green]Enter Groq API key[/green] (or Enter to skip)", default="").strip()
        if val:
            config["GROQ_API_KEY"] = val
        else:
            console.print(
                "   [dim yellow]Skipped. Without a fallback LLM, Gemini rate limits will halt research.[/dim yellow]"
            )

    # ── 4. OpenRouter (optional) ──────────────────────────────────────────────
    console.print("\n[bold yellow]4. OpenRouter API Key[/bold yellow]  [dim](optional — second LLM fallback)[/dim]")
    console.print("   Get yours at: https://openrouter.ai  [dim](free models available)[/dim]")
    existing = get_credential("OPENROUTER_API_KEY")
    if existing:
        console.print(f"   [dim]Current value: {'*' * 8}{existing[-4:]}  (Enter to keep, 'clear' to remove)[/dim]")
        val = Prompt.ask("   [green]Enter OpenRouter API key[/green]", default="").strip()
        if val.lower() == "clear":
            pass
        elif val:
            config["OPENROUTER_API_KEY"] = val
        else:
            config["OPENROUTER_API_KEY"] = existing
    else:
        val = Prompt.ask("   [green]Enter OpenRouter API key[/green] (or Enter to skip)", default="").strip()
        if val:
            config["OPENROUTER_API_KEY"] = val
        else:
            console.print("   [dim yellow]Skipped.[/dim yellow]")

    # ── 5. Ollama (optional) ──────────────────────────────────────────────────
    console.print("\n[bold yellow]5. Ollama Base URL[/bold yellow]  [dim](optional — local LLM fallback)[/dim]")
    console.print("   Default when Ollama is running locally: http://localhost:11434/v1")
    existing = get_credential("OLLAMA_BASE_URL")
    if existing:
        console.print(f"   [dim]Current value: {existing}  (Enter to keep, 'clear' to remove)[/dim]")
        val = Prompt.ask("   [green]Enter Ollama base URL[/green]", default="").strip()
        if val.lower() == "clear":
            pass
        elif val:
            config["OLLAMA_BASE_URL"] = val
        else:
            config["OLLAMA_BASE_URL"] = existing
    else:
        val = Prompt.ask("   [green]Enter Ollama base URL[/green] (or Enter to skip)", default="").strip()
        if val:
            config["OLLAMA_BASE_URL"] = val
        else:
            console.print("   [dim yellow]Skipped.[/dim yellow]")

    console.print()

    # Warn if fallback keys were added but openai package is not installed
    has_fallback_keys = any(k in config for k in ("GROQ_API_KEY", "OPENROUTER_API_KEY"))
    if has_fallback_keys:
        from webresearch.llm_compat import openai_available
        if not openai_available():
            console.print(
                f"[bold yellow]Note:[/bold yellow] Groq/OpenRouter keys saved, but the "
                f"[{THEME}]openai[/{THEME}] package is required to use them.\n"
                "  Install it now: [green]pip install \"web-research-agent[providers]\"[/green]\n"
            )

    # ── Persist ───────────────────────────────────────────────────────────────
    if keyring_available():
        stored_count = 0
        for key, value in config.items():
            if set_credential(key, value):
                stored_count += 1
        console.print(
            f"[bold green]Stored {stored_count} credential(s) in system keyring.[/bold green]"
        )
    else:
        # Fallback: plain-text file (only for environments without keyring support)
        save_config({k: v for k, v in config.items()})

    console.print()
    return config


def check_config() -> dict:
    from webresearch.credentials import get_credential, REQUIRED_CREDENTIALS, OPTIONAL_CREDENTIALS

    # Developer override: .env file in working directory takes top priority.
    if os.path.exists(".env"):
        from dotenv import load_dotenv
        load_dotenv()

    # Read all credentials (keyring > env var fallback happens inside get_credential).
    gemini = get_credential("GEMINI_API_KEY")
    serper = get_credential("SERPER_API_KEY")

    if gemini and serper:
        config: dict = {"GEMINI_API_KEY": gemini, "SERPER_API_KEY": serper}
        for key in OPTIONAL_CREDENTIALS:
            val = get_credential(key)
            if val:
                config[key] = val
        return config

    # Try the legacy plain-text config file (keyring not available path, or
    # user was on an old version that wrote credentials there).
    stored = load_config()
    if stored.get("GEMINI_API_KEY") and stored.get("SERPER_API_KEY"):
        config = {"GEMINI_API_KEY": stored["GEMINI_API_KEY"], "SERPER_API_KEY": stored["SERPER_API_KEY"]}
        for key in OPTIONAL_CREDENTIALS:
            if stored.get(key):
                config[key] = stored[key]
        return config

    # No credentials found anywhere — run first-time interactive setup.
    console.print("[bold yellow]Configuration not found. Starting setup...[/bold yellow]\n")
    return setup_api_keys()


def apply_config_to_env(config: dict):
    for key, value in config.items():
        os.environ[key] = value


# ─── History ─────────────────────────────────────────────────────────────────

def get_history_path() -> Path:
    history_dir = Path.home() / ".webresearch"
    history_dir.mkdir(exist_ok=True)
    return history_dir / "history.json"


def load_history() -> List[Dict]:
    path = get_history_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_to_history(query: str, answer: str, steps: int, duration: float):
    history = load_history()
    history.insert(0, {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "answer_preview": answer[:200],
        "steps": steps,
        "duration": round(duration, 2),
    })
    path = get_history_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history[:50], f, indent=2)


def view_history():
    history = load_history()
    if not history:
        console.print("  no query history yet.", style="dim yellow")
        return

    console.print(Rule("[dim]query history[/dim]", style=THEME))
    console.print()
    shown = history[:15]

    table = Table(show_header=True, border_style="dim", show_lines=False)
    table.add_column("#", style=THEME, width=4, justify="right")
    table.add_column("query", style="white", no_wrap=True, max_width=54)
    table.add_column("iter", style="yellow", width=5, justify="right")
    table.add_column("time", style="dim", width=7, justify="right")
    table.add_column("date", style="dim", width=16)

    for i, entry in enumerate(shown, 1):
        ts = entry.get("timestamp", "")[:16].replace("T", " ")
        q = entry["query"]
        flag = " [bold yellow]⚠[/bold yellow]" if str(entry.get("answer_preview","")).startswith("⚠") else ""
        table.add_row(
            str(i),
            (q[:53] + "…") if len(q) > 53 else q,
            str(entry.get("steps", "?")),
            f"{entry.get('duration', 0):.1f}s",
            ts + flag,
        )

    console.print(table)
    console.print()

    if _HAS_QUESTIONARY:
        choices = [
            questionary.Choice(
                title=f"  [{i+1:2d}]  {e['query'][:60]}",
                value=e["query"],
            )
            for i, e in enumerate(shown)
        ]
        choices.append(questionary.Choice(title="  back", value=""))
        selected = questionary.select(
            "re-run a query:", choices=choices
        ).ask()
        if selected:  # empty string ("back") and None (Ctrl-C) are both falsy
            _run_query(selected)
    else:
        choice = Prompt.ask(
            "[green]❯[/green] enter number to re-run (Enter to go back)", default=""
        )
        if choice.isdigit() and 1 <= int(choice) <= len(shown):
            _run_query(shown[int(choice) - 1]["query"])


# ─── Rate-limit display ───────────────────────────────────────────────────────

def _print_usage_banner():
    """Print Serper API monthly usage after a query completes."""
    try:
        from webresearch.tools.search import get_monthly_usage, _MONTHLY_LIMIT
        count = get_monthly_usage()
        pct = count / _MONTHLY_LIMIT * 100
        if pct < 70:
            style, icon = "dim green", "●"
        elif pct < 90:
            style, icon = "bold yellow", "⚠"
        else:
            style, icon = "bold red", "⛔"
        console.print(
            f"[{style}]{icon} Serper API: {count}/{_MONTHLY_LIMIT} searches this month "
            f"({pct:.0f}%)[/{style}]"
        )
    except Exception:
        pass


# ─── Agent initialization ────────────────────────────────────────────────────

def _build_tool_manager(cfg) -> "ToolManager":
    """Build a ToolManager with all available tools."""
    from webresearch.tools import (
        ToolManager, SearchTool, ScrapeTool, BrowserScrapeTool,
        CodeExecutorTool, FileOpsTool, playwright_available,
        PDFExtractTool, pdf_available, ThinkTool,
    )
    tool_manager = ToolManager()
    tool_manager.register_tool(ThinkTool())
    tool_manager.register_tool(SearchTool(cfg.serper_api_key))
    tool_manager.register_tool(ScrapeTool())
    if playwright_available():
        tool_manager.register_tool(BrowserScrapeTool())
    if pdf_available():
        tool_manager.register_tool(PDFExtractTool())
    tool_manager.register_tool(CodeExecutorTool())
    tool_manager.register_tool(FileOpsTool())
    return tool_manager


def _build_llm_chain(cfg) -> "ModelFallbackChain":
    """
    Build a ModelFallbackChain from the available provider keys in cfg.

    Chain order:
      1. Gemini 2.5 Flash  (primary — always present)
      2. Groq / llama-3.3-70b-versatile  (if GROQ_API_KEY set)
      3. OpenRouter / llama-3.3-70b-instruct:free  (if OPENROUTER_API_KEY set)
      4. Ollama local  (if OLLAMA_BASE_URL set)
    """
    from webresearch.llm import LLMInterface
    from webresearch.llm_compat import OpenAICompatibleLLMInterface, openai_available, PROVIDERS
    from webresearch.llm_chain import ModelFallbackChain

    interfaces = []

    # Primary: Gemini
    gemini = LLMInterface(
        api_key=cfg.gemini_api_key,
        model_name=cfg.model_name,
        temperature=cfg.temperature,
    )
    gemini.provider_name = f"Gemini ({cfg.model_name})"
    interfaces.append(gemini)

    has_optional_keys = any([cfg.groq_api_key, cfg.openrouter_api_key, cfg.ollama_base_url])

    if not openai_available() and has_optional_keys:
        console.print(
            "[bold yellow]Warning:[/bold yellow] Groq/OpenRouter/Ollama API keys are configured "
            f"but the [{THEME}]openai[/{THEME}] package is not installed — fallback providers are disabled.\n"
            "  Fix: [green]pip install \"web-research-agent[providers]\"[/green]",
        )

    if openai_available():
        # Groq fallback
        if cfg.groq_api_key:
            base_url, display, model = PROVIDERS["groq"]
            interfaces.append(OpenAICompatibleLLMInterface(
                api_key=cfg.groq_api_key,
                model_name=model,
                base_url=base_url,
                provider_name=f"Groq ({model})",
                temperature=cfg.temperature,
            ))

        # OpenRouter fallback
        if cfg.openrouter_api_key:
            base_url, display, model = PROVIDERS["openrouter"]
            interfaces.append(OpenAICompatibleLLMInterface(
                api_key=cfg.openrouter_api_key,
                model_name=model,
                base_url=base_url,
                provider_name=f"OpenRouter ({model})",
                temperature=cfg.temperature,
            ))

        # Ollama fallback
        if cfg.ollama_base_url:
            _, _, model = PROVIDERS["ollama"]
            interfaces.append(OpenAICompatibleLLMInterface(
                api_key="ollama",
                model_name=model,
                base_url=cfg.ollama_base_url,
                provider_name=f"Ollama ({model})",
                temperature=cfg.temperature,
            ))

    def _on_switch(from_name: str, to_name: str):
        if not cfg.quiet_fallback:
            console.print(
                f"\n[bold yellow]Rate limit reached on {from_name}. "
                f"Switching to {to_name}...[/bold yellow]\n"
            )

    chain = ModelFallbackChain(interfaces=interfaces, switch_callback=_on_switch)

    if len(interfaces) > 1:
        names = " -> ".join(
            getattr(i, "provider_name", getattr(i, "model_name", "?"))
            for i in interfaces
        )
        console.print(f"[dim]Model chain: {names}[/dim]")

    return chain


def initialize_agent():
    """Initialize the sequential ReAct agent with a model fallback chain."""
    from webresearch.config import Config
    from webresearch.agent import ReActAgent

    cfg = Config()
    cfg.validate()
    return ReActAgent(
        llm=_build_llm_chain(cfg),
        tool_manager=_build_tool_manager(cfg),
        max_iterations=cfg.max_iterations,
        max_tool_output_length=cfg.max_tool_output_length,
    )


def initialize_parallel_agent():
    """Initialize the parallel fan-out research agent with a model fallback chain."""
    from webresearch.config import Config
    from webresearch.parallel import ParallelResearchAgent

    cfg = Config()
    cfg.validate()
    return ParallelResearchAgent(
        llm=_build_llm_chain(cfg),
        tool_manager=_build_tool_manager(cfg),
    )


# ─── Execution trace persistence ─────────────────────────────────────────────

def _save_trace(query: str, answer: str, trace: list, duration: float, mode: str = "query") -> None:
    """Write the full step-by-step execution trace to logs/ as a timestamped JSON file."""
    try:
        logs_dir = Path.home() / ".webresearch" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = logs_dir / f"trace_{ts}_{mode}.json"
        payload = {
            "query": query,
            "answer": answer,
            "mode": mode,
            "duration_s": round(duration, 2),
            "steps": len(trace),
            "trace": trace,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
    except Exception:
        pass  # Trace saving is best-effort — never surface to the user


# ─── Core query runner ────────────────────────────────────────────────────────

def _run_query(query: str):
    """Execute a research query with live step-by-step output and session memory."""
    try:
        agent = initialize_agent()
    except Exception as e:
        console.print(f"✗ Error initializing agent: {str(e)}", style="bold red")
        console.print("Tip: Reconfigure API keys with option 5.", style="yellow")
        return

    # Inject previous session context into the task
    task = _session.build_task_with_memory(query)
    if len(_session) > 0:
        console.print(
            f"[dim]↑ Using {len(_session)} previous Q&A pair(s) as context[/dim]\n"
        )

    wall_start = time.time()
    from webresearch.config import Config as _Cfg
    panel = ResearchPanel(query, _Cfg().max_iterations, wall_start)
    n_steps = 0

    answer: Optional[str] = None

    with Live(panel, console=console, refresh_per_second=12) as live:
        def step_callback(iteration: int, step: Any):
            nonlocal n_steps
            n_steps = iteration
            panel.update(iteration, step)
            live.update(panel)

        answer = agent.run(task, step_callback=step_callback)
        panel.done = True
        live.update(panel)

    duration = time.time() - wall_start

    console.print()
    console.rule("[bold green]RESULT[/bold green]", style="green")
    console.print()

    border = "red" if answer.startswith("⚠ Error:") else ("yellow" if answer.startswith("⚠") else "green")
    console.print(Panel(answer, border_style=border, padding=(1, 2)))
    console.print()
    global _session_queries, _session_steps
    _session_queries += 1
    _session_steps += n_steps

    if not answer.startswith("⚠"):
        console.print(f"  [dim italic]{random.choice(_DONE_FALLBACK)}[/dim italic]")
    console.print(
        f"  [dim]⏱  {duration:.1f}s  ·  {n_steps} steps[/dim]"
    )
    _print_usage_banner()
    console.print()

    # Save execution trace to logs/ for post-run debugging
    _save_trace(query, answer, agent.get_execution_trace(), duration)

    # Save to session memory and persistent history
    # Don't persist error or incomplete answers — they'd poison future queries
    if not answer.startswith("⚠"):
        _session.add(query, answer)
    save_to_history(query, answer, n_steps, duration)

    if Confirm.ask("Save result to file?", default=False):
        filename = Prompt.ask("Filename", default="result.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"Query: {query}\n{'=' * 80}\n\n{answer}\n\n")
            f.write(f"{'─' * 80}\nExecution time: {duration:.2f}s | Steps: {n_steps}\n")
        console.print(f"✓ Saved to [{THEME}]{filename}[/{THEME}]", style="bold green")


# ─── Deep research (parallel fan-out) ────────────────────────────────────────

def _run_deep_research(query: str):
    """Execute a query via the parallel fan-out agent with a live status board."""
    try:
        agent = initialize_parallel_agent()
    except Exception as e:
        console.print(f"✗ Error initializing agent: {str(e)}", style="bold red")
        console.print("Tip: Reconfigure API keys with option 5.", style="yellow")
        return

    # Pass prior context to synthesis only — decomposition always gets the raw
    # query so unrelated Q&A pairs don't pollute sub-question generation.
    context = _session.get_context() if len(_session) > 0 else ""
    if context:
        console.print(f"[dim]↑ Using {len(_session)} previous Q&A pair(s) as context[/dim]\n")

    start_time = datetime.now()
    sub_status: Dict[int, Dict] = {}

    def make_status_board() -> Table:
        t = Table(
            title=f"[bold {THEME}]Deep Research — Parallel Fan-out[/bold {THEME}]",
            border_style=THEME,
            expand=True,
        )
        t.add_column("#", style=THEME, width=4, justify="center")
        t.add_column("Sub-query", style="white", ratio=4)
        t.add_column("Status", width=14)
        for idx in sorted(sub_status):
            s = sub_status[idx]
            state = s["state"]
            icons = {"pending": "○ pending", "running": "⟳ running", "done": "✓ done", "error": "✗ error"}
            styles = {"pending": "dim", "running": "bold cyan", "done": "bold green", "error": "bold red"}
            t.add_row(
                str(idx + 1),
                s.get("question", "…")[:70],
                f"[{styles[state]}]{icons[state]}[/{styles[state]}]",
            )
        return t

    answer: Optional[str] = None

    with Live(make_status_board(), console=console, refresh_per_second=4) as live:
        def cb(idx: int, state: str, question: Optional[str] = None):
            if idx not in sub_status:
                sub_status[idx] = {"question": question or "…", "state": state}
            else:
                sub_status[idx]["state"] = state
                if question:
                    sub_status[idx]["question"] = question
            live.update(make_status_board())

        answer = agent.run(query, sub_status_callback=cb, context=context)

    duration = (datetime.now() - start_time).total_seconds()
    n_sub = len(sub_status)

    console.print()
    console.rule("[bold green]RESULT[/bold green]", style="green")
    console.print()
    border = "red" if answer.startswith("⚠ Error:") else ("yellow" if answer.startswith("⚠") else "green")
    console.print(Panel(answer, border_style=border, padding=(1, 2)))
    console.print()
    console.print(
        f"⏱  [yellow]{duration:.2f}s[/yellow]  [dim]│[/dim]  "
        f"[{THEME}]{n_sub} parallel sub-queries[/{THEME}]"
    )
    _print_usage_banner()
    console.print()

    _save_trace(query, answer, agent.get_execution_trace(), duration, mode="deep")
    if not answer.startswith("⚠"):
        _session.add(query, answer)
    save_to_history(query, answer, n_sub, duration)

    if Confirm.ask("Save result to file?", default=False):
        filename = Prompt.ask("Filename", default="result.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"Query: {query}\n{'=' * 80}\n\n{answer}\n\n")
            f.write(f"{'─' * 80}\nExecution time: {duration:.2f}s | Sub-queries: {n_sub}\n")
        console.print(f"✓ Saved to [{THEME}]{filename}[/{THEME}]", style="bold green")


# ─── Menu actions ─────────────────────────────────────────────────────────────

def _mrow(key: str, label: str, desc: str = "") -> None:
    """Print one menu row — bypasses markup so brackets render literally."""
    t = Text()
    t.append(f"  [{key}]", style=f"bold {THEME}")
    t.append(f"  {label:<24}", style="white")
    if desc:
        t.append(f"  {desc}", style="dim")
    console.print(t)


def show_menu():
    history_count = len(load_history())

    console.print(Rule("[dim]research[/dim]", style="dim"))
    _mrow("1", "run query",         "ask anything  ·  sources included")
    _mrow("2", "run deep research", "parallel fan-out  ·  4 sub-queries")
    _mrow("3", "process task file", "batch mode")
    console.print()
    console.print(Rule("[dim]session[/dim]", style="dim"))
    _mrow("4", "query history",
          f"{history_count} recorded" if history_count else "")
    _mrow("5", "execution logs")
    console.print()
    console.print(Rule("[dim]system[/dim]", style="dim"))
    _mrow("6", "configuration",        "api keys · agent settings")
    _mrow("7", "clear session memory",
          f"{len(_session)} pair(s) in context" if len(_session) > 0 else "")
    _mrow("q", "exit")
    console.print()


def _read_query(prompt_text: str) -> str:
    """
    Prompt for a research question with automatic multiline support.

    Single-line: type query + Enter — done, same as before.
    Multi-line:  first line ends with ':' triggers continuation mode;
                 keep typing lines, then press Enter on a blank line to finish.
    This handles pasted criteria lists like "Compile companies matching:".
    """
    first = Prompt.ask(f"[green]❯[/green] {prompt_text}")
    if not first or first.lower() == "back":
        return first or ""

    if not first.rstrip().endswith(":"):
        return first

    # Continuation mode — consume further lines until blank Enter
    console.print("[dim]  (continuing — press Enter on a blank line to finish)[/dim]")
    lines = [first]
    try:
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
    except (EOFError, KeyboardInterrupt):
        pass
    return "\n".join(lines)


def run_interactive_query():
    console.print(Rule("[dim]run query[/dim]", style=THEME))
    console.print()
    query = _read_query("Research question (or 'back')")
    if not query or query.lower() == "back":
        return
    console.print()
    _run_query(query)


def run_interactive_deep_query():
    console.print(Rule("[dim]run deep research[/dim]", style=THEME))
    console.print()
    query = _read_query("Research question (or 'back')")
    if not query or query.lower() == "back":
        return
    console.print()
    _run_deep_research(query)


def run_tasks_from_file():
    console.print(Rule("[dim]process task file[/dim]", style=THEME))
    console.print()

    filepath = Prompt.ask("[green]❯[/green] Path to tasks file (or 'back' to return)")
    if not filepath or filepath.lower() == "back":
        return

    if not os.path.exists(filepath):
        console.print(f"✗ File not found: {filepath}", style="bold red")
        return

    if not os.path.isfile(filepath):
        console.print(f"✗ That path is a directory, not a file: {filepath}", style="bold red")
        return

    output_file = Prompt.ask("Output file", default="results.txt")
    console.print(f"\n[yellow]Processing tasks from:[/yellow] {filepath}")
    console.print(f"[yellow]Results will be saved to:[/yellow] {output_file}\n")

    def read_tasks(task_file: str) -> List[str]:
        with open(task_file, "r", encoding="utf-8") as f:
            tasks, current = [], []
            for line in f:
                line = line.rstrip()
                if not line:
                    if current:
                        tasks.append("\n".join(current))
                        current = []
                else:
                    current.append(line)
            if current:
                tasks.append("\n".join(current))
        return tasks

    try:
        tasks = read_tasks(filepath)
        agent = initialize_agent()
        results = []

        for i, task in enumerate(tasks, 1):
            console.print(f"[{THEME}][Task {i}/{len(tasks)}][/{THEME}] {task[:60]}…")
            start_time = datetime.now()
            try:
                answer = agent.run(task)
                duration = (datetime.now() - start_time).total_seconds()
                results.append({
                    "task": task,
                    "answer": answer,
                    "execution_time": round(duration, 2),
                    "num_steps": len(agent.get_execution_trace()),
                })
                console.print(f"[green]✓ Completed in {duration:.2f}s[/green]\n")
            except Exception as e:
                console.print(f"[red]✗ Error: {str(e)}[/red]\n")
                results.append({"task": task, "answer": "Error during processing", "error": str(e)})

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 100 + "\nWEB RESEARCH AGENT RESULTS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 100 + "\n\n")
            for i, result in enumerate(results, 1):
                f.write(f"\n{'=' * 100}\nTASK {i}\n{'=' * 100}\n\n")
                f.write(f"TASK DESCRIPTION:\n{result['task']}\n\n{'-' * 100}\n\n")
                f.write(f"ANSWER:\n{result['answer']}\n\n")
                if result.get("error"):
                    f.write(f"ERROR: {result['error']}\n\n")
                f.write(f"Execution time: {result.get('execution_time', 'N/A')} seconds\n")
                f.write(f"Number of steps: {result.get('num_steps', 'N/A')}\n")

        console.print(f"[green]✓ All tasks completed! Results saved to {output_file}[/green]\n")
        _print_usage_banner()

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]\n")


def view_logs():
    logs_dir = Path.home() / ".webresearch" / "logs"
    trace_files = sorted(logs_dir.glob("trace_*.json"), key=lambda x: x.stat().st_mtime, reverse=True) if logs_dir.exists() else []

    if not trace_files:
        console.print("No execution traces found. Run a query first.", style="bold yellow")
        return

    console.print(Rule("[dim]execution logs[/dim]", style=THEME))
    console.print()

    table = Table(show_header=True, box=None)
    table.add_column("#", style=THEME, width=4)
    table.add_column("Query", style="white", ratio=3)
    table.add_column("Steps", style="yellow", justify="right", width=6)
    table.add_column("Duration", style="yellow", justify="right", width=10)
    table.add_column("Status", width=8)
    table.add_column("When", style="dim", width=18)

    recent = trace_files[:10]
    for i, tf in enumerate(recent, 1):
        try:
            with open(tf, encoding="utf-8") as f:
                d = json.load(f)
            status = "[bold red]ERROR[/bold red]" if str(d.get("answer", "")).startswith("⚠") else "[bold green]OK[/bold green]"
            ts = tf.stem.split("_", 1)[1].rsplit("_", 1)[0]  # trace_YYYYMMDD_HHMMSS_mode → YYYYMMDD_HHMMSS
            when = datetime.strptime(ts, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M")
            table.add_row(
                str(i),
                d.get("query", "")[:60],
                str(d.get("steps", "?")),
                f"{d.get('duration_s', 0):.1f}s",
                status,
                when,
            )
        except Exception:
            table.add_row(str(i), tf.name, "?", "?", "?", "?")

    console.print(table)
    console.print()

    choice = Prompt.ask("[green]Enter number to inspect[/green] (or press Enter to skip)", default="")

    if choice.isdigit() and 1 <= int(choice) <= len(recent):
        tf = recent[int(choice) - 1]
        with open(tf, encoding="utf-8") as f:
            d = json.load(f)

        console.print()
        console.rule(f"[bold {THEME}]{d.get('query', '')[:80]}[/bold {THEME}]", style=THEME)
        console.print(f"[dim]Mode: {d.get('mode')}  ·  {d.get('steps')} steps  ·  {d.get('duration_s')}s[/dim]\n")

        for step in d.get("trace", []):
            console.print(f"[bold {THEME}]Step {step['step']}[/bold {THEME}]  [dim]{step.get('elapsed_ms', 0)/1000:.1f}s[/dim]")
            if step.get("thought"):
                console.print(f"  [yellow]Thought:[/yellow] {step['thought'][:200]}")
            if step.get("action"):
                inp = step.get("action_input") or {}
                inp_preview = str(list(inp.values())[0])[:80] if inp else ""
                console.print(f"  [green]Action:[/green]  {step['action']} → {inp_preview}")
            if step.get("observation"):
                console.print(f"  [dim]Obs:[/dim]     {step['observation'][:200]}")
            console.print()

        answer = d.get("answer", "")
        border = "red" if answer.startswith("⚠") else "green"
        console.print(Panel(answer[:600] + ("..." if len(answer) > 600 else ""), title="Answer", border_style=border))
        console.print()
        console.rule(style=THEME)
        console.print()


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    from webresearch.config import Config as _BootCfg
    _log_level = getattr(logging, _BootCfg().log_level, logging.WARNING)
    logging.basicConfig(level=_log_level)
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    logging.getLogger("pdfminer").setLevel(logging.ERROR)

    print_banner()

    config = check_config()
    apply_config_to_env(config)

    from webresearch.config import Config
    model = Config().model_name
    render_startup(model)
    print_status_bar(config)

    while True:
        show_menu()
        choice = Prompt.ask(
            "[green]❯[/green]", choices=["1", "2", "3", "4", "5", "6", "7", "q"],
            show_choices=False,
        )
        console.print()

        if choice == "1":
            run_interactive_query()
        elif choice == "2":
            run_interactive_deep_query()
        elif choice == "3":
            run_tasks_from_file()
        elif choice == "4":
            view_history()
        elif choice == "5":
            view_logs()
        elif choice == "6":
            result = configure()
            if result:
                apply_config_to_env(result)
        elif choice == "7":
            _session.clear()
            console.print("✓ Session memory cleared.", style="bold green")
            console.print()
        elif choice == "q":
            console.print(f"  [dim]{_exit_quip(_session_queries, _session_steps)}[/dim]")
            console.print()
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(f"\n  [dim]{_exit_quip(_session_queries, _session_steps)}[/dim]\n")
        sys.exit(0)
