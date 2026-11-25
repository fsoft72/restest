#!/usr/bin/env python3
"""Regression test: actions inside a section must run exactly once."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.parser import RESTestParser


def _run(script):
    """Run a script dict through the parser and return the parser."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(script, f)
    try:
        parser = RESTestParser(quiet=True)
        parser.open(f.name)
    finally:
        os.unlink(f.name)
    return parser


def test_section_runs_once():
    """A counter incremented inside a section must end at 1."""
    parser = _run(
        {
            "actions": [
                {"action": "set", "key": "counter", "value": 0},
                {
                    "action": "section",
                    "title": "S",
                    "actions": [
                        {"action": "set", "key": "counter", "value": "${counter + 1}"}
                    ],
                },
            ]
        }
    )
    assert parser.rt.globals["counter"] == 1, parser.rt.globals["counter"]


def test_plain_container_still_runs():
    """An action without method but with nested actions still runs them once."""
    parser = _run(
        {
            "actions": [
                {"action": "set", "key": "counter", "value": 0},
                {
                    "title": "plain",
                    "actions": [
                        {"action": "set", "key": "counter", "value": "${counter + 1}"}
                    ],
                },
            ]
        }
    )
    assert parser.rt.globals["counter"] == 1, parser.rt.globals["counter"]


if __name__ == "__main__":
    test_section_runs_once()
    test_plain_container_still_runs()
    print("OK")
