"""
ReAct Agent Implementation.

This implements the ReAct (Reasoning and Acting) paradigm from the paper:
"ReAct: Synergizing Reasoning and Acting in Language Models"

The agent follows a loop:
1. Thought: Reason about what to do next
2. Action: Execute a tool with specific parameters
3. Observation: Receive the result
4. Repeat until the task is complete
"""

import json
import re
import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any, Tuple

from .llm import LLMInterface
from .tools import ToolManager

logger = logging.getLogger(__name__)

# Tightened type alias (issue #9)
StepCallback = Callable[[int, "Step"], None]

# Injection patterns applied to observations before they enter the prompt (issue #1)
_OBSERVATION_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?",
    r"(?i)disregard\s+(?:all\s+)?(?:previous|prior|above)",
    r"(?i)(?:new\s+)?system\s*(?:prompt|instructions?)\s*:",
    r"(?i)you\s+are\s+now\s+(?:a\s+)?(?:different|new|an?\s+)",
    r"(?i)<\s*system\s*>",
    r"(?i)<\s*/?(?:human|assistant|user|prompt)\s*>",
    r"(?i)\[\s*(?:SYSTEM|INST|SYS)\s*\]",
    r"(?i)final\s+answer\s*:\s*(?:ignore|the\s+answer\s+is)",
    # NOTE: "Thought:" and "Action:" patterns removed — too broad, stripped
    # legitimate content from news articles (e.g. "Action: The company announced...")
]

# How many recent steps to include in full; older ones are summarised (issue #11)
_FULL_HISTORY_WINDOW = 8


@dataclass
class Step:
    """Represents a single step in the ReAct loop."""

    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    # Iteration metadata (issue #10)
    iteration: int = 0
    timestamp: float = field(default_factory=time.time)
    elapsed_ms: Optional[float] = None


class AgentError(Exception):
    """Raised when the agent encounters an unrecoverable error."""
    pass


class ReActAgent:
    """
    ReAct agent that reasons about and executes tasks using available tools.

    The agent follows the ReAct paradigm:
    - Thought: Reasoning about the current state and what to do next
    - Action: Executing a tool to gather information or perform an operation
    - Observation: Processing the result of the action
    """

    def __init__(
        self,
        llm: LLMInterface,
        tool_manager: ToolManager,
        max_iterations: int = 15,
        max_tool_output_length: int = 5000,
    ):
        self.llm = llm
        self.tool_manager = tool_manager
        self.max_iterations = max_iterations
        self.max_tool_output_length = max_tool_output_length
        self.steps: List[Step] = []
        self._action_cache: Dict[str, str] = {}  # issue #8

    def run(self, task: str, step_callback: Optional[StepCallback] = None) -> str:
        """
        Run the agent on a given task.

        Args:
            task: The task description
            step_callback: Optional callable(iteration, step) called after each step

        Returns:
            The final answer string. Errors are prefixed with "⚠ Error:" so the
            caller can distinguish them from valid answers (issue #12).
        """
        logger.info(f"Starting task: {task[:100]}...")
        self.steps = []
        self._action_cache = {}

        try:
            for iteration in range(self.max_iterations):
                logger.info(f"Iteration {iteration + 1}/{self.max_iterations}")

                prompt = self._build_prompt(task)
                t0 = time.time()
                response = self.llm.generate(prompt)

                thought, action, action_input, final_answer = self._parse_response(response)

                step = Step(thought=thought, iteration=iteration + 1)

                if final_answer:
                    # Enforce at least one real research tool call before accepting the answer.
                    # 'think' is reasoning scaffolding, not a research tool.
                    _RESEARCH_TOOLS = frozenset({"search", "scrape", "scrape_js", "pdf_extract"})
                    used_research = any(s.action in _RESEARCH_TOOLS for s in self.steps)
                    if not used_research:
                        logger.warning("Agent attempted Final Answer without any research tool use — forcing search.")
                        step.observation = (
                            "You provided a Final Answer without calling any research tools. "
                            "This is not permitted — you are a research agent, not a knowledge base. "
                            "Your training data may be outdated or wrong. "
                            "You must call search or scrape at least once before answering. "
                            "Begin with a think step, then search."
                        )
                        step.elapsed_ms = (time.time() - t0) * 1000
                        self.steps.append(step)
                        if step_callback:
                            step_callback(iteration + 1, step)
                        continue

                    logger.info("Agent produced final answer")
                    step.elapsed_ms = (time.time() - t0) * 1000
                    self.steps.append(step)
                    if step_callback:
                        step_callback(iteration + 1, step)
                    return final_answer

                if action and action_input is not None:
                    step.action = action
                    step.action_input = action_input

                    observation = self._execute_action(action, action_input)
                    step.observation = observation
                    step.elapsed_ms = (time.time() - t0) * 1000
                    self.steps.append(step)
                    logger.info(f"Action: {action}, Observation length: {len(observation)}")
                else:
                    step.observation = "No valid action found. Please provide a thought and then an action."
                    step.elapsed_ms = (time.time() - t0) * 1000
                    self.steps.append(step)

                if step_callback:
                    step_callback(iteration + 1, step)

            logger.warning("Max iterations reached without final answer")
            best_effort = self._generate_best_effort_answer(task)
            return f"⚠ Max iterations ({self.max_iterations}) reached — answer may be incomplete.\n\n{best_effort}"

        except Exception as e:
            logger.error(f"Error during agent execution: {str(e)}")
            # Prefix with "⚠ Error:" so callers can render it differently (issue #12)
            return f"⚠ Error: The agent encountered an error: {str(e)}"

    def _sanitize_observation(self, obs: str) -> str:
        """Strip prompt-injection patterns from scraped observations (issue #1)."""
        for pattern in _OBSERVATION_INJECTION_PATTERNS:
            obs = re.sub(pattern, "[FILTERED]", obs)
        return obs

    def _build_prompt(self, task: str) -> str:
        """Build the prompt with a sliding-window history to cap context size (issue #11)."""
        prompt_parts = []

        prompt_parts.append("""You are a research agent that can use tools to complete tasks. You follow the ReAct (Reasoning and Acting) paradigm.

For each step, you should:
1. Think about what you need to do next (Thought)
2. Decide on an action to take using one of the available tools (Action)
3. Specify the parameters for the action (Action Input)
4. Observe the result (Observation - this will be provided to you)

When you have enough information to answer the task, provide your final answer.

FORMAT:
You must use this exact format:

Thought: [your reasoning about what to do next]
Action: [the tool name to use]
Action Input: [the parameters as a JSON object]

OR, when you have the final answer:

Thought: [your reasoning about why you have enough information]
Final Answer: [your complete answer to the task]

IMPORTANT RULES:
- Always start with "Thought:" to explain your reasoning
- Use "Action:" only when you want to use a tool
- Use "Action Input:" with valid JSON for parameters — ensure all string values use escaped characters (\\n, \\", etc.) and never contain raw newlines or unescaped backslashes
- Use "Final Answer:" only when you can fully answer the task
- Be thorough and verify information from multiple sources when needed
- For tasks requiring lists or compilations, gather comprehensive information before concluding
- Always cite sources (URLs) in your final answer
- You must call at least one search or scrape tool before providing a Final Answer.
  Do NOT answer from your training knowledge alone — you are a research tool, not a
  knowledge base. If you believe you know the answer, verify it with a search first.

SEARCH VS SCRAPE — know the difference:
- search: returns a list of 10 results, each with a title, URL, and a short snippet (~20 words).
  Snippets are NOT full articles — they are teasers. Use search to discover which pages exist.
- scrape: fetches the full text of a single URL. Use scrape immediately after search when:
    * the snippet is too short to answer the question
    * the URL looks like a primary source (org website, news article, report)
    * you need to verify a claim that the snippet only hints at
  Pattern: search → pick the best URL → scrape it → extract the answer.
  Do NOT keep searching with rephrased queries when a relevant URL is already in your results.

THINK TOOL — when to use it:
Use think at genuine decision points, not before every action.
Required at four moments:

1. Task start: before your first search. Decompose the task —
   what exactly are you looking for? What intermediate facts
   do you need first? Do not assume you know which entity is
   implied — if the task describes someone by what they did,
   find the event first.

2. After search results: before scraping. Read the snippets.
   Pick the single most promising URL and state why. If no URL
   looks useful, state why and what different query to try.
   Do NOT rephrase and re-search just because a snippet is short.

3. After scraping: before deciding next action. Does the page
   content answer the question? If yes, move to Final Answer.
   If paywalled or empty, pick the next best URL. If the content
   is partial, decide whether to scrape another URL or answer
   with what you have.

4. When stuck: if two consecutive searches returned nothing
   useful, stop and think about why the approach is failing
   before trying again.

Do NOT call think between consecutive actions in the same
phase — for example, do not think between scraping page 1
and scraping page 2 when you already decided to scrape both.
Think is for decisions, not narration.

WORKED EXAMPLE:
Task: "Find the COO of the organization that mediated secret US-China AI talks in Geneva in 2023."

Step 1 — think (task start, required):
Action: think
Action Input: {"thought": "I need two things: (1) which org mediated the talks — I don't know this, (2) that org's COO. I must find the org first. Plan: search for the Geneva event, identify the org, then scrape their team/about page for COO."}

Step 2 — search:
Action: search
Action Input: {"query": "secret US China AI companies talks Geneva 2023 mediator organizer"}

Step 3 — think (after search results, required):
Action: think
Action Input: {"thought": "Results mention [Org X] at [URL]. Snippet is 20 words — not enough to confirm COO. Scraping [URL] next."}

Step 4 — scrape:
Action: scrape
Action Input: {"url": "[URL from step 3]"}

Step 5 — think (after scrape, required):
Action: think
Action Input: {"thought": "Page confirms COO is [Name]. Source is their official team page. Sufficient to answer."}

Final Answer: The COO of [Org X] is [Name]. Source: [URL]
""")

        prompt_parts.append("\n" + self.tool_manager.get_tool_descriptions())
        prompt_parts.append(f"\n\nTASK:\n{task}")

        if self.steps:
            earlier = self.steps[:-_FULL_HISTORY_WINDOW] if len(self.steps) > _FULL_HISTORY_WINDOW else []
            recent = self.steps[-_FULL_HISTORY_WINDOW:]

            if earlier:
                prompt_parts.append(f"\n\n[{len(earlier)} earlier steps — summarised to save context]:")
                for i, step in enumerate(earlier, 1):
                    summary = f"\nStep {i}: Thought: {step.thought}"
                    if step.action:
                        summary += f" → Action: {step.action}"
                    prompt_parts.append(summary)

            prompt_parts.append("\n\nPREVIOUS STEPS (full detail):" if earlier else "\n\nPREVIOUS STEPS:")
            offset = len(earlier)
            for i, step in enumerate(recent, offset + 1):
                prompt_parts.append(f"\nStep {i}:")
                prompt_parts.append(f"Thought: {step.thought}")

                if step.action:
                    prompt_parts.append(f"Action: {step.action}")
                    prompt_parts.append(f"Action Input: {self._format_action_input(step.action_input)}")

                if step.observation:
                    obs = step.observation
                    if len(obs) > self.max_tool_output_length:
                        obs = obs[:self.max_tool_output_length] + f"\n... [truncated from {len(step.observation)} chars]"
                    # Sanitize before injecting into prompt (issue #1)
                    prompt_parts.append(f"Observation: {self._sanitize_observation(obs)}")

        prompt_parts.append("\n\nWhat is your next step?")
        return "\n".join(prompt_parts)

    def _parse_response(
        self, response: str
    ) -> Tuple[str, Optional[str], Optional[Dict], Optional[str]]:
        """Parse the LLM response to extract thought, action, and parameters."""
        thought = ""
        action = None
        action_input = None
        final_answer = None

        thought_match = re.search(
            r"Thought:\s*(.+?)(?=\n(?:Action|Final Answer):|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if thought_match:
            thought = thought_match.group(1).strip()

        # Fixed: non-greedy with stop boundary so subsequent Action blocks are
        # not swallowed into the final answer (issue #3)
        final_answer_match = re.search(
            r"Final Answer:\s*(.+?)(?=\n\n(?:Thought|Action):|\Z)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if final_answer_match:
            final_answer = final_answer_match.group(1).strip()
            return thought, None, None, final_answer

        action_match = re.search(r"Action:\s*(\w+)", response, re.IGNORECASE)
        if action_match:
            action = action_match.group(1).strip()

        action_input_match = re.search(
            r"Action Input:\s*(\{.+?\}|\{.+)", response, re.DOTALL | re.IGNORECASE
        )
        if action_input_match:
            action_input_str = action_input_match.group(1).strip()
            try:
                brace_count = 0
                end_idx = 0
                for i, char in enumerate(action_input_str):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break

                if end_idx > 0:
                    action_input_str = action_input_str[:end_idx]

                action_input = json.loads(action_input_str)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse action input as JSON: {e}")
                action_input = self._parse_action_input_fallback(action_input_str)

        return thought, action, action_input, final_answer

    def _parse_action_input_fallback(self, action_input_str: str) -> Dict[str, Any]:
        """Fallback parser; logs a warning and surfaces raw input on total failure (issue #7)."""
        params = {}

        patterns = [
            r'"(\w+)":\s*"([^"]+)"',
            r"'(\w+)':\s*'([^']+)'",
            r'(\w+):\s*"([^"]+)"',
            r"(\w+)=([^,}\s]+)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, action_input_str):
                key, value = match.groups()
                if key not in params:
                    params[key] = value

        if not params:
            logger.warning(
                f"Action input fallback parser found no key-value pairs in: {action_input_str!r}"
            )
            # Surface the raw string so the LLM can self-correct next iteration
            params = {"_raw_input": action_input_str, "_parse_error": "JSON parse failed"}

        return params

    def _format_action_input(self, action_input: Optional[Dict]) -> str:
        """Format action input for display in the prompt."""
        if not action_input:
            return "{}"
        try:
            return json.dumps(action_input, indent=2)
        except (TypeError, ValueError):  # Fixed: no bare except (issue #2)
            return str(action_input)

    def _execute_action(self, action: str, action_input: Dict[str, Any]) -> str:
        """Execute a tool action, returning a cached result for duplicate calls (issue #8)."""
        try:
            cache_key = f"{action}:{hash(json.dumps(action_input, sort_keys=True))}"
        except (TypeError, ValueError):
            cache_key = f"{action}:{hash(str(action_input))}"

        if cache_key in self._action_cache:
            logger.info(f"Cache hit for action '{action}' — returning cached result")
            return self._action_cache[cache_key]

        try:
            result = self.tool_manager.execute_tool(action, **action_input)
            self._action_cache[cache_key] = result
            return result
        except Exception as e:
            logger.error(f"Error executing action {action}: {str(e)}")
            return f"Error executing action: {str(e)}"

    def _generate_best_effort_answer(self, task: str) -> str:
        """Generate a best-effort answer using a proportional observation budget (issue #5)."""
        n_steps = max(1, len(self.steps))
        per_step_budget = max(200, self.max_tool_output_length // n_steps)

        prompt = f"""The agent reached the maximum number of iterations while working on this task:

TASK:
{task}

Based on the information gathered in these steps, provide the best possible answer:

"""
        for i, step in enumerate(self.steps, 1):
            prompt += f"\nStep {i}:\n"
            prompt += f"Thought: {step.thought}\n"
            if step.observation:
                obs = step.observation[:per_step_budget]
                prompt += f"Observation: {obs}{'...' if len(step.observation) > per_step_budget else ''}\n"

        prompt += "\n\nProvide a final answer based on the information gathered:"

        try:
            return self.llm.generate(prompt)
        except Exception:
            last_thought = self.steps[-1].thought if self.steps and self.steps[-1].thought else "N/A"
            return f"Unable to complete the task within {self.max_iterations} iterations. Last thought: {last_thought}"

    def get_execution_trace(self) -> List[Dict[str, Any]]:
        """Get the execution trace of all steps, including timing metadata."""
        trace = []
        for i, step in enumerate(self.steps, 1):
            step_dict = {
                "step": i,
                "iteration": step.iteration,
                "thought": step.thought,
                "timestamp": step.timestamp,
                "elapsed_ms": step.elapsed_ms,
            }
            if step.action:
                step_dict["action"] = step.action
                step_dict["action_input"] = step.action_input
            if step.observation:
                step_dict["observation"] = (
                    step.observation[:500] + "..."
                    if len(step.observation) > 500
                    else step.observation
                )
            trace.append(step_dict)
        return trace
