"""Tests for ConversationMemory."""
import pytest
from webresearch.memory import ConversationMemory


def test_empty_memory_returns_no_context():
    m = ConversationMemory()
    assert m.get_context() == ""
    assert len(m) == 0


def test_build_task_passthrough_when_empty():
    m = ConversationMemory()
    assert m.build_task_with_memory("foo bar") == "foo bar"


def test_add_single_pair():
    m = ConversationMemory()
    m.add("What is Paris?", "Paris is the capital of France.")
    ctx = m.get_context()
    assert "[Q1] What is Paris?" in ctx
    assert "[A1] Paris is the capital of France." in ctx


def test_build_task_injects_context():
    m = ConversationMemory()
    m.add("prev Q", "prev A")
    result = m.build_task_with_memory("follow-up Q")
    assert "PREVIOUS RESEARCH CONTEXT" in result
    assert "CURRENT QUESTION" in result
    assert "follow-up Q" in result
    assert "prev Q" in result


def test_max_pairs_enforced():
    m = ConversationMemory(max_pairs=2)
    queries = [f"question-number-{i}" for i in range(5)]
    answers = [f"answer-number-{i}" for i in range(5)]
    for q, a in zip(queries, answers):
        m.add(q, a)
    assert len(m) == 2
    ctx = m.get_context()
    # Only the two most recent pairs should be present
    assert "question-number-3" in ctx
    assert "answer-number-3" in ctx
    assert "question-number-4" in ctx
    assert "answer-number-4" in ctx
    # Earlier pairs should be evicted
    assert "answer-number-0" not in ctx
    assert "answer-number-1" not in ctx
    assert "answer-number-2" not in ctx


def test_clear_resets_memory():
    m = ConversationMemory()
    m.add("Q", "A")
    m.clear()
    assert len(m) == 0
    assert m.get_context() == ""


def test_long_answer_is_truncated_in_context():
    m = ConversationMemory()
    long_answer = "x" * 1000
    m.add("Q", long_answer)
    ctx = m.get_context()
    # Context should contain the truncation marker
    assert "…" in ctx
    # But the full answer should not be dumped verbatim
    assert len(ctx) < len(long_answer)
