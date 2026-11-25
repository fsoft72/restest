#!/usr/bin/env python3
"""Regression tests for the low-risk security fixes."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.engine import RESTest


def test_object_compare_json_and_literal():
    """Objects are parsed from JSON or Python literals, never executed."""
    rt = RESTest()
    assert rt._object_compare('{"a": 1, "b": true}', "{'b': True, 'a': 1}")
    assert not rt._object_compare('{"a": 1}', '{"a": 2}')


def test_object_compare_rejects_code():
    """Code injected in a value must raise instead of running."""
    rt = RESTest()
    marker = "/tmp/restest_eval_marker"
    if os.path.exists(marker):
        os.unlink(marker)
    payload = "__import__('os').system('touch %s')" % marker
    try:
        rt._object_compare(payload, "{}")
    except (ValueError, SyntaxError):
        pass
    assert not os.path.exists(marker), "payload was executed"


if __name__ == "__main__":
    test_object_compare_json_and_literal()
    test_object_compare_rejects_code()
    print("OK")
