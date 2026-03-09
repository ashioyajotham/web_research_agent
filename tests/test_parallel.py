"""Tests for ParallelResearchAgent decomposition and synthesis logic."""
import re
from unittest.mock import MagicMock, call
import pytest
from webresearch.parallel import ParallelResearchAgent


def make_parallel_agent(llm_responses=None):
    llm = MagicMock()
    if llm_responses:
        llm.generate.side_effect = llm_responses
    tool_manager = MagicMock()
    tool_manager.get_tool_descriptions.return_value = "No tools"
    return ParallelResearchAgent(
        llm=llm,
        tool_manager=tool_manager,
        max_sub_queries=3,
        sub_iterations=1,
        max_workers=2,
    )


def test_decompose_parses_numbered_list():
    agent = make_parallel_agent()
    agent.llm.generate.return_value = (
        "1. What are the main causes?\n"
        "2. What is the current status?\n"
        "3. What are the projected impacts?"
    )
    questions = agent._decompose("Tell me about climate change")
    assert len(questions) == 3
    assert "What are the main causes?" in questions[0]


def test_decompose_falls_back_on_bad_llm_output():
    agent = make_parallel_agent()
    agent.llm.generate.return_value = "I cannot break this down."
    questions = agent._decompose("Some task")
    # Should fall back to the original task
    assert questions == ["Some task"]


def test_decompose_falls_back_on_exception():
    agent = make_parallel_agent()
    agent.llm.generate.side_effect = Exception("API error")
    questions = agent._decompose("Some task")
    assert questions == ["Some task"]


def test_decompose_respects_max_sub_queries():
    agent = make_parallel_agent()
    agent.llm.generate.return_value = (
        "1. Q1\n2. Q2\n3. Q3\n4. Q4\n5. Q5\n6. Q6"
    )
    questions = agent._decompose("Big question")
    assert len(questions) <= agent.max_sub_queries


def test_run_calls_synthesize(monkeypatch):
    """End-to-end run with mocked sub-research."""
    responses = [
        # decompose call
        "1. Sub-Q1\n2. Sub-Q2\n3. Sub-Q3",
        # synthesis call
        "Comprehensive answer.",
    ]
    agent = make_parallel_agent()
    call_count = [0]

    def mock_generate(prompt):
        idx = call_count[0]
        call_count[0] += 1
        if idx == 0:
            return responses[0]
        return responses[1]

    agent.llm.generate.side_effect = mock_generate

    # Mock _research_sub_question to avoid real ReAct loops
    monkeypatch.setattr(
        agent, "_research_sub_question",
        lambda q, idx, cb=None: f"Answer to: {q}"
    )

    result = agent.run("What is the state of AI?")
    assert "Comprehensive answer." in result


def test_status_callbacks_are_fired(monkeypatch):
    agent = make_parallel_agent()
    agent.llm.generate.return_value = "1. Q1\n2. Q2"

    statuses = []

    def cb(idx, state, question=None):
        statuses.append((idx, state))

    monkeypatch.setattr(
        agent, "_research_sub_question",
        lambda q, idx, cb=None: "answer"
    )

    agent.run("test", sub_status_callback=cb)

    # Both sub-queries should have been signalled as pending
    pending = [(i, s) for i, s in statuses if s == "pending"]
    assert len(pending) == 2
