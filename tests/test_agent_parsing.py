"""Tests for ReActAgent response parsing — no API keys needed."""
from unittest.mock import MagicMock
import pytest
from webresearch.agent import ReActAgent


def make_agent():
    llm = MagicMock()
    tool_manager = MagicMock()
    tool_manager.get_tool_descriptions.return_value = "No tools"
    return ReActAgent(llm=llm, tool_manager=tool_manager)


# ── Final answer parsing ────────────────────────────────────────────────────

def test_parse_final_answer():
    agent = make_agent()
    response = "Thought: I have enough info.\nFinal Answer: Paris is the capital of France."
    thought, action, action_input, final = agent._parse_response(response)
    assert final == "Paris is the capital of France."
    assert action is None
    assert action_input is None


def test_parse_multiline_final_answer():
    agent = make_agent()
    response = "Thought: Done.\nFinal Answer: Line one.\nLine two.\nLine three."
    _, _, _, final = agent._parse_response(response)
    assert "Line one" in final
    assert "Line two" in final


# ── Action parsing ──────────────────────────────────────────────────────────

def test_parse_action_with_json_input():
    agent = make_agent()
    response = 'Thought: Need to search.\nAction: search\nAction Input: {"query": "AI news"}'
    thought, action, action_input, final = agent._parse_response(response)
    assert action == "search"
    assert action_input == {"query": "AI news"}
    assert final is None


def test_parse_action_with_complex_json():
    agent = make_agent()
    response = (
        'Thought: Scrape it.\nAction: scrape\n'
        'Action Input: {"url": "https://example.com/page?q=1&p=2"}'
    )
    _, action, action_input, _ = agent._parse_response(response)
    assert action == "scrape"
    assert action_input["url"] == "https://example.com/page?q=1&p=2"


# ── Thought parsing ─────────────────────────────────────────────────────────

def test_parse_thought():
    agent = make_agent()
    response = 'Thought: I need to find more data.\nAction: search\nAction Input: {"query": "x"}'
    thought, _, _, _ = agent._parse_response(response)
    assert "I need to find more data" in thought


def test_parse_empty_response_does_not_crash():
    agent = make_agent()
    thought, action, action_input, final = agent._parse_response("")
    assert thought == ""
    assert action is None
    assert final is None


# ── Prompt building ─────────────────────────────────────────────────────────

def test_build_prompt_contains_task():
    agent = make_agent()
    prompt = agent._build_prompt("What is the GDP of France?")
    assert "What is the GDP of France?" in prompt


def test_build_prompt_contains_tool_descriptions():
    agent = make_agent()
    prompt = agent._build_prompt("test task")
    agent.tool_manager.get_tool_descriptions.assert_called_once()
