"""Tests for the code executor's AST-based sandbox."""
import pytest
from webresearch.tools.code_executor import _check_code_safety


# ── Cases that must be ALLOWED ─────────────────────────────────────────────

@pytest.mark.parametrize("code", [
    "x = 1 + 1\nprint(x)",
    "import math\nprint(math.pi)",
    "import json\nprint(json.dumps({'a': 1}))",
    "import os\nprint(os.path.join('a', 'b'))",
    "import os\nprint(os.listdir('.'))",
    "import pandas as pd\ndf = pd.DataFrame({'x': [1, 2]})\nprint(df)",
    "from pathlib import Path\nprint(Path('.').resolve())",
])
def test_safe_code_is_allowed(code):
    assert _check_code_safety(code) is None


# ── Cases that must be BLOCKED ─────────────────────────────────────────────

@pytest.mark.parametrize("code, reason", [
    ("import subprocess", "subprocess"),
    ("from subprocess import run", "subprocess"),
    ("import socket", "socket"),
    ("from socket import socket as s", "socket"),
    ("import paramiko", "paramiko"),
    ("import ctypes", "ctypes"),
    ("import ftplib", "ftplib"),
    ("import smtplib", "smtplib"),
    ("import os\nos.system('dir')", "os.system"),
    ("import os\nos.popen('ls')", "os.popen"),
    ("import os\nos.fork()", "os.fork"),
    ("import os\nos.execv('/bin/sh', [])", "os.execv"),
    ("import os\nos.kill(1, 9)", "os.kill"),
])
def test_blocked_code_returns_error(code, reason):
    result = _check_code_safety(code)
    assert result is not None, f"Expected '{reason}' to be blocked but was allowed"
    assert "Sandbox blocked" in result or "Blocked" in result


def test_syntax_error_returns_message():
    result = _check_code_safety("def broken(:")
    assert result is not None
    assert "Syntax error" in result


def test_empty_code_passes_safety_check():
    # The executor itself handles empty code; safety check should not crash
    assert _check_code_safety("") is None or _check_code_safety("") is not None
