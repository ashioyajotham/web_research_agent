"""Tests for Serper API monthly usage tracking."""
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import pytest

import webresearch.tools.search as search_mod


def _make_usage_path(tmp_path: Path) -> Path:
    return tmp_path / "usage.json"


def test_get_monthly_usage_when_no_file(tmp_path):
    with patch.object(search_mod, "_get_usage_path", return_value=_make_usage_path(tmp_path)):
        assert search_mod.get_monthly_usage() == 0


def test_increment_creates_file(tmp_path):
    path = _make_usage_path(tmp_path)
    with patch.object(search_mod, "_get_usage_path", return_value=path):
        count = search_mod._increment_usage()
    assert count == 1
    assert path.exists()


def test_increment_accumulates(tmp_path):
    path = _make_usage_path(tmp_path)
    with patch.object(search_mod, "_get_usage_path", return_value=path):
        search_mod._increment_usage()
        search_mod._increment_usage()
        count = search_mod._increment_usage()
    assert count == 3


def test_get_monthly_usage_matches_increment(tmp_path):
    path = _make_usage_path(tmp_path)
    with patch.object(search_mod, "_get_usage_path", return_value=path):
        search_mod._increment_usage()
        search_mod._increment_usage()
        assert search_mod.get_monthly_usage() == 2


def test_month_rollover_resets_count(tmp_path):
    path = _make_usage_path(tmp_path)
    # Write stale data from a previous month
    path.write_text(json.dumps({"month": "2020-01", "count": 999}), encoding="utf-8")
    with patch.object(search_mod, "_get_usage_path", return_value=path):
        count = search_mod._increment_usage()
    assert count == 1


def test_get_usage_ignores_stale_month(tmp_path):
    path = _make_usage_path(tmp_path)
    path.write_text(json.dumps({"month": "2020-01", "count": 999}), encoding="utf-8")
    with patch.object(search_mod, "_get_usage_path", return_value=path):
        assert search_mod.get_monthly_usage() == 0
