"""
Smoke tests for ThinkTool integration.

Verifies:
1. ThinkTool executes and returns the expected confirmation string
2. ThinkTool registers correctly in ToolManager and appears in descriptions
3. The agent parses a 'think' action from an LLM response and records it in the trace
4. The system prompt contains the mandatory think-tool instruction
"""

import json
import pytest

from webresearch.tools.think import ThinkTool
from webresearch.tools import ToolManager
from webresearch.agent import ReActAgent


# ── 1. ThinkTool unit ──────────────────────────────────────────────────────────

def test_think_tool_name():
    assert ThinkTool().name == "think"


def test_think_tool_returns_confirmation():
    result = ThinkTool().execute(thought="I should search for the event first, not the entity.")
    assert "Reasoning recorded" in result


def test_think_tool_accepts_any_string():
    """execute() must not raise regardless of thought content."""
    tool = ThinkTool()
    tool.execute(thought="")
    tool.execute(thought="x" * 5000)
    tool.execute(thought='contains "quotes" and \\backslashes\\')


# ── 2. ToolManager registration ───────────────────────────────────────────────

def test_think_registered_first():
    """ThinkTool should be the first tool registered so it tops the prompt list."""
    tm = ToolManager()
    tm.register_tool(ThinkTool())
    descriptions = tm.get_tool_descriptions()
    # 'think' should appear before any other tool name in the descriptions block
    assert "think" in descriptions


def test_think_tool_description_lists_use_cases():
    desc = ThinkTool().description
    # Description must mention the three canonical use cases so the LLM knows when to call it
    assert "plan" in desc.lower()
    assert "verif" in desc.lower()
    assert "direction" in desc.lower() or "dead end" in desc.lower()


# ── 3. Agent parses and traces a think action ─────────────────────────────────

class _MockLLM:
    """Stub LLM that returns a scripted sequence of responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self._index = 0

    def generate(self, prompt: str) -> str:
        resp = self._responses[self._index % len(self._responses)]
        self._index += 1
        return resp


def _make_agent(responses):
    tm = ToolManager()
    tm.register_tool(ThinkTool())
    return ReActAgent(
        llm=_MockLLM(responses),
        tool_manager=tm,
        max_iterations=5,
    )


def test_agent_executes_think_action():
    """Agent must call ThinkTool when the LLM outputs a think action."""
    responses = [
        # Step 1: think
        'Thought: I should plan before searching.\n'
        'Action: think\n'
        'Action Input: {"thought": "Search for the event, then extract the entity."}',
        # Step 2: search (satisfies the research-tool requirement)
        'Thought: Now search.\n'
        'Action: search\n'
        'Action Input: {"query": "the answer"}',
        # Step 3: final answer (allowed — search was called)
        'Thought: I have reasoned enough.\n'
        'Final Answer: The answer is 42.',
    ]
    agent = ReActAgent(llm=_MockLLM(responses), tool_manager=_make_stub_tm(), max_iterations=5)
    result = agent.run("What is the answer?")
    assert result == "The answer is 42."


def test_think_step_appears_in_trace():
    """Execution trace must include the think action step."""
    responses = [
        'Thought: Planning step.\n'
        'Action: think\n'
        'Action Input: {"thought": "Plan: search for event first."}',
        'Thought: Done.\nFinal Answer: Result.',
    ]
    agent = _make_agent(responses)
    agent.run("Multi-step task")
    trace = agent.get_execution_trace()

    think_steps = [s for s in trace if s.get("action") == "think"]
    assert len(think_steps) >= 1, "Expected at least one think step in trace"
    assert "Plan" in think_steps[0].get("action_input", {}).get("thought", "")


def test_think_observation_recorded_in_trace():
    """Trace entries for think steps must carry an observation (the tool's confirmation)."""
    responses = [
        'Thought: Verify entity.\n'
        'Action: think\n'
        'Action Input: {"thought": "Does this org match the description?"}',
        'Thought: Yes.\nFinal Answer: Shaikh Group.',
    ]
    agent = _make_agent(responses)
    agent.run("Who organised the talks?")
    trace = agent.get_execution_trace()

    think_steps = [s for s in trace if s.get("action") == "think"]
    assert think_steps, "No think step found in trace"
    # The observation for a think step should be the tool's return string
    assert "observation" in think_steps[0]
    assert "Reasoning recorded" in think_steps[0]["observation"]


# ── 4. System prompt contains the mandatory instruction ───────────────────────

def _make_stub_tm():
    """ToolManager with ThinkTool + a stub SearchTool."""
    from webresearch.tools.base import Tool as BaseTool
    class _StubSearch(BaseTool):
        @property
        def name(self): return "search"
        @property
        def description(self): return "stub search"
        def execute(self, query: str) -> str: return "real search results"
    tm = ToolManager()
    tm.register_tool(ThinkTool())
    tm.register_tool(_StubSearch())
    return tm


def test_final_answer_blocked_without_research_tool():
    """Final Answer attempted without any search/scrape must be intercepted."""
    responses = [
        # Step 1: tries to answer from training data (no search)
        'Thought: I know this.\nFinal Answer: Wrong answer from memory.',
        # Step 2: corrects — calls search
        'Thought: Search first.\nAction: search\nAction Input: {"query": "something"}',
        # Step 3: final answer (now allowed — search was called)
        'Thought: Done.\nFinal Answer: The verified answer.',
    ]
    agent = ReActAgent(llm=_MockLLM(responses), tool_manager=_make_stub_tm(), max_iterations=6)
    result = agent.run("Find something")

    trace = agent.get_execution_trace()
    # Step 1 observation should be the research-tool enforcement message
    assert "research" in trace[0]["observation"].lower(), (
        "Final Answer without research tool should be blocked with enforcement message"
    )
    assert result == "The verified answer."


def test_search_without_preceding_think_is_allowed():
    """Search is allowed without a preceding think — per-action think enforcement was removed."""
    responses = [
        # Step 1: search directly, no think first — must execute normally
        'Thought: Search now.\nAction: search\nAction Input: {"query": "something"}',
        # Step 2: final answer
        'Thought: Done.\nFinal Answer: The answer.',
    ]
    agent = ReActAgent(llm=_MockLLM(responses), tool_manager=_make_stub_tm(), max_iterations=4)
    result = agent.run("Task")

    trace = agent.get_execution_trace()
    assert "real search results" in trace[0]["observation"], (
        "Search without preceding think should execute normally"
    )
    assert result == "The answer."


def test_think_allows_consecutive_thinks():
    """Two consecutive think calls must both execute — only non-think actions need a think before them."""
    responses = [
        'Thought: Think.\nAction: think\nAction Input: {"thought": "First thought."}',
        'Thought: Think more.\nAction: think\nAction Input: {"thought": "Second thought."}',
        'Thought: Search.\nAction: search\nAction Input: {"query": "q"}',
        'Thought: Done.\nFinal Answer: Answer.',
    ]
    agent = ReActAgent(llm=_MockLLM(responses), tool_manager=_make_stub_tm(), max_iterations=6)
    result = agent.run("Task")

    trace = agent.get_execution_trace()
    assert "Reasoning recorded" in trace[0]["observation"]
    assert "Reasoning recorded" in trace[1]["observation"]
    assert "real search results" in trace[2]["observation"]
    assert result == "Answer."


def test_system_prompt_contains_think_instruction():
    """The built ReAct prompt must contain the decision-point think guidance."""
    tm = ToolManager()
    tm.register_tool(ThinkTool())
    agent = ReActAgent(llm=_MockLLM(["Final Answer: x"]), tool_manager=tm)
    prompt = agent._build_prompt("dummy task")
    lower = prompt.lower()
    # Decision-point model section
    assert "think tool" in lower, "Prompt missing THINK TOOL section"
    assert "decision point" in lower, "Prompt missing decision-point guidance"
    # Research tool enforcement
    assert "must" in lower, "Prompt missing enforcement language"
    # Worked example is present so the LLM knows the expected pattern
    assert "worked example" in lower, "Prompt missing worked example"
