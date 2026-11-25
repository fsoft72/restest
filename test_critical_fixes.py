#!/usr/bin/env python3
"""Regression tests for the critical items in OPTIMIZE.md."""

import datetime
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.engine import RESTest
from lib.parser import RESTestParser


def _run(script, **kwargs):
    """Run a script dict through the parser and return the parser."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(script, f)
    try:
        parser = RESTestParser(quiet=True, **kwargs)
        parser.open(f.name)
    finally:
        os.unlink(f.name)
    return parser


def test_if_runs_actions_when_condition_true():
    """Nested actions of a passing 'if' run once and the script continues."""
    parser = _run(
        {
            "actions": [
                {"action": "set", "key": "a", "value": 1},
                {
                    "action": "if",
                    "field": "a",
                    "value": 1,
                    "actions": [{"action": "set", "key": "hit", "value": "${hit + 1}"}],
                },
                {"action": "set", "key": "after", "value": 1},
            ]
        }
    )
    assert parser.rt.globals["hit"] == 1, parser.rt.globals
    assert parser.rt.globals["after"] == 1, parser.rt.globals


def test_if_skips_actions_when_condition_false():
    """Nested actions of a failing 'if' do not run and the script continues."""
    parser = _run(
        {
            "actions": [
                {"action": "set", "key": "a", "value": 2},
                {
                    "action": "if",
                    "field": "a",
                    "value": 1,
                    "actions": [{"action": "set", "key": "hit", "value": 1}],
                },
                {"action": "set", "key": "after", "value": 1},
            ]
        }
    )
    assert "hit" not in parser.rt.globals, parser.rt.globals
    assert parser.rt.globals["after"] == 1, parser.rt.globals


def test_dry_mode_does_not_crash():
    """In dry mode requests are not sent and fields/tests are skipped."""
    parser = _run(
        {
            "system": {"base_url": "http://localhost:9"},
            "actions": [
                {
                    "method": "get",
                    "url": "/x",
                    "fields": ["id"],
                    "tests": [{"field": "id", "value": 1}],
                },
                {"action": "set", "key": "after", "value": 1},
            ],
        },
        dry=True,
        auth_mode="no",
    )
    assert parser.rt.globals["after"] == 1, parser.rt.globals


def _check_ok(rt, mode, current, expected):
    """Return True when the given check mode passes."""
    rt.globals["v"] = current
    return rt._check({"mode": mode, "value": expected}, "v", current) is None


def test_lte_check():
    """LTE passes for smaller or equal values and fails for bigger ones."""
    rt = RESTest()
    assert _check_ok(rt, "LTE", 3, 5)
    assert _check_ok(rt, "<=", 5, 5)
    assert not _check_ok(rt, "<=", 6, 5)


def test_size_lte_check():
    """SIZE-LTE passes for smaller or equal sizes and fails for bigger ones."""
    rt = RESTest()
    assert _check_ok(rt, "SIZE-LTE", [1, 2], 3)
    assert _check_ok(rt, "()<=", [1, 2, 3], 3)
    assert not _check_ok(rt, "()<=", [1, 2, 3, 4], 3)


class _FakeResponse:
    """Minimal stand-in for requests.Response with only 'elapsed'."""

    def __init__(self, seconds):
        self.elapsed = datetime.timedelta(seconds=seconds)


def test_elapsed_ms_includes_seconds():
    """Elapsed time must include the whole seconds, not only microseconds."""
    rt = RESTest()
    assert rt._elapsed_ms(_FakeResponse(2.3)) == 2300
    assert rt._elapsed_ms(_FakeResponse(0.25)) == 250


if __name__ == "__main__":
    test_if_runs_actions_when_condition_true()
    test_if_skips_actions_when_condition_false()
    test_dry_mode_does_not_crash()
    test_lte_check()
    test_size_lte_check()
    test_elapsed_ms_includes_seconds()
    print("OK")
