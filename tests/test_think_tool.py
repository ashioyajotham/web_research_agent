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
        # Step 2: final answer
        'Thought: I have reasoned enough.\n'
        'Final Answer: The answer is 42.',
    ]
    agent = _make_agent(responses)
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

def test_system_prompt_contains_think_instruction():
    """The built ReAct prompt must instruct the agent to use think on multi-step tasks."""
    tm = ToolManager()
    tm.register_tool(ThinkTool())
    agent = ReActAgent(llm=_MockLLM(["Final Answer: x"]), tool_manager=tm)
    prompt = agent._build_prompt("dummy task")
    assert "think tool" in prompt.lower(), "Prompt missing think tool instruction"
