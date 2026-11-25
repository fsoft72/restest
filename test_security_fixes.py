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


def test_authorization_masked_in_log(tmp_path="/tmp/restest_log_mask.log"):
    """The log file must not contain the full Authorization value."""
    import requests

    secret = "Bearer SUPERSECRETTOKEN1234567890"
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)
    rt = RESTest(log_file=tmp_path)
    req = requests.Request(
        "POST", "http://x.test/a", headers={"Authorization": secret}, data="{}"
    ).prepare()
    rt._log_curl(req)

    class Resp:
        status_code = 200
        text = ""

        class elapsed:
            microseconds = 0

    rt._log_resp({"Authorization": secret, "X-Other": "keep"}, Resp)
    log = open(tmp_path).read()
    os.unlink(tmp_path)
    assert "SUPERSECRET" not in log, log
    assert "Bear****7890" in log, log
    assert "X-Other" in log and "keep" in log


def test_short_secret_fully_masked():
    """Short secrets must not leak any character."""
    rt = RESTest()
    assert rt._mask_headers({"Authorization": "abc"})["Authorization"] == "****"


if __name__ == "__main__":
    test_object_compare_json_and_literal()
    test_object_compare_rejects_code()
    test_authorization_masked_in_log()
    test_short_secret_fully_masked()
    print("OK")
