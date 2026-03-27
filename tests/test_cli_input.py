"""Tests for the _read_query multiline input helper in cli.py."""
import sys
import builtins
from unittest.mock import patch, MagicMock
import pytest

# cli.py has display-only deps (pyfiglet, questionary) that may not be
# installed in the test environment — stub them before importing the module.
sys.modules.setdefault("pyfiglet", MagicMock())
sys.modules.setdefault("questionary", MagicMock())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_prompt_ask(return_value: str):
    """Return a mock for rich.prompt.Prompt.ask that returns a fixed value."""
    m = MagicMock(return_value=return_value)
    return m


def _import_read_query():
    """Import _read_query after patching console so no Rich output is emitted."""
    from cli import _read_query
    return _read_query


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_single_line_query_returned_immediately(monkeypatch):
    """A normal query (not ending in ':') is returned as-is after one Enter."""
    monkeypatch.setattr("cli.Prompt.ask", _make_prompt_ask("What is the capital of France?"))
    from cli import _read_query
    result = _read_query("Research question (or 'back')")
    assert result == "What is the capital of France?"


def test_back_returns_immediately(monkeypatch):
    monkeypatch.setattr("cli.Prompt.ask", _make_prompt_ask("back"))
    from cli import _read_query
    result = _read_query("Research question (or 'back')")
    assert result == "back"


def test_empty_input_returns_empty(monkeypatch):
    monkeypatch.setattr("cli.Prompt.ask", _make_prompt_ask(""))
    from cli import _read_query
    result = _read_query("Research question (or 'back')")
    assert result == ""


def test_colon_triggers_multiline_continuation(monkeypatch):
    """First line ending with ':' enters continuation; blank line terminates."""
    monkeypatch.setattr("cli.Prompt.ask", _make_prompt_ask("Compile companies matching:"))
    # Simulate subsequent lines pasted into stdin, terminated by blank
    stdin_lines = iter(["  - Based in the EU", "  - Revenue > 1B EUR", ""])
    monkeypatch.setattr("builtins.input", lambda: next(stdin_lines))
    monkeypatch.setattr("cli.console", MagicMock())  # suppress Rich output

    from cli import _read_query
    result = _read_query("Research question (or 'back')")

    assert result == "Compile companies matching:\n  - Based in the EU\n  - Revenue > 1B EUR"


def test_multiline_eof_handled_gracefully(monkeypatch):
    """EOFError on stdin is swallowed and partial input is returned."""
    monkeypatch.setattr("cli.Prompt.ask", _make_prompt_ask("Criteria:"))
    monkeypatch.setattr("builtins.input", MagicMock(side_effect=EOFError))
    monkeypatch.setattr("cli.console", MagicMock())

    from cli import _read_query
    result = _read_query("Research question (or 'back')")
    assert result == "Criteria:"


def test_multiline_keyboard_interrupt_handled_gracefully(monkeypatch):
    """KeyboardInterrupt on stdin is swallowed and partial input is returned."""
    monkeypatch.setattr("cli.Prompt.ask", _make_prompt_ask("List:"))
    monkeypatch.setattr("builtins.input", MagicMock(side_effect=KeyboardInterrupt))
    monkeypatch.setattr("cli.console", MagicMock())

    from cli import _read_query
    result = _read_query("Research question (or 'back')")
    assert result == "List:"


def test_trailing_whitespace_on_colon_still_triggers(monkeypatch):
    """'Criteria:   ' (trailing spaces) should also trigger continuation."""
    monkeypatch.setattr("cli.Prompt.ask", _make_prompt_ask("Criteria:   "))
    stdin_lines = iter(["line one", ""])
    monkeypatch.setattr("builtins.input", lambda: next(stdin_lines))
    monkeypatch.setattr("cli.console", MagicMock())

    from cli import _read_query
    result = _read_query("Research question (or 'back')")
    assert result.startswith("Criteria:   \nline one")
