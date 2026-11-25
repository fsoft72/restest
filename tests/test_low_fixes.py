#!/usr/bin/env python3
"""Regression tests for the low priority items in OPTIMIZE.md."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.engine import NOT_FOUND, RESTest
from lib.errors import RESTestError
from lib.parser import RESTestParser


class _JsonResponse:
    """Minimal response exposing a JSON body."""

    def __init__(self, body):
        self._body = body

    def json(self):
        """Return the JSON body."""
        return self._body


def _write_script(script):
    """Write a script dict to a temp JSON file and return its path."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(script, f)
    return f.name


def _quiet_engine():
    """Return an engine that counts errors instead of raising."""
    return RESTest(stop_on_error=False, quiet=True)


def test_cli_key_value_may_contain_colons():
    """--key splits on the first ':' only, so URLs and tokens are kept whole."""
    script = _write_script({"actions": [{"action": "rem"}]})
    fd, env_file = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        subprocess.run(
            [
                sys.executable,
                os.path.join(ROOT, "restest.py"),
                "--quiet",
                "--key",
                "url:http://example.com:8080/x",
                "--env-save",
                env_file,
                script,
            ],
            check=True,
            capture_output=True,
        )
        with open(env_file) as f:
            assert json.load(f)["url"] == "http://example.com:8080/x"
    finally:
        os.unlink(script)
        os.unlink(env_file)


def test_cli_key_without_colon_is_a_usage_error():
    """--key without ':' exits with a usage error instead of a traceback."""
    res = subprocess.run(
        [sys.executable, os.path.join(ROOT, "restest.py"), "x.json", "--key", "novalue"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 2
    assert "--key expects key:value" in res.stderr
    assert "Traceback" not in res.stderr


def test_not_found_is_a_sentinel_not_a_string():
    """A response containing the text "__NOT_FOUND__" is not a missing field."""
    rt = RESTest(quiet=True)
    resp = _JsonResponse({"v": "__NOT_FOUND__"})
    assert rt._run_check(resp, resp.json(), {"field": "v", "value": "__NOT_FOUND__"}) is None

    with contextlib.redirect_stdout(io.StringIO()):
        assert rt._expand_value({}, "missing") is NOT_FOUND
    assert str(NOT_FOUND) == "__NOT_FOUND__"


def test_fields_accepts_all_forms():
    """String, list and object forms of 'fields' share one code path."""
    rt = RESTest(quiet=True)
    body = {"a": 1, "items": [1, 2, 3], "obj": {"k": 1}}
    rt.fields(
        _JsonResponse(body),
        [
            "a",
            ["a", "a2"],
            ["items"],
            ["*", "all"],
            {"path": "items", "save": "n", "mode": "length"},
            {"field": "obj", "save": "t", "mode": "type"},
            {"path": "obj", "save": "keys", "mode": "keys"},
            {"path": "*", "save": "all_keys", "mode": "keys"},
        ],
    )
    g = rt.globals
    assert g["a"] == 1 and g["a2"] == 1 and g["items"] == [1, 2, 3]
    assert g["all"] == body
    assert g["n"] == 3 and g["t"] == "object" and g["keys"] == ["k"]
    assert g["all_keys"] == ["a", "items", "obj"]


def test_fields_mode_errors_are_counted():
    """Bad modes and impossible transformations are reported, not saved."""
    rt = _quiet_engine()
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        rt.fields(
            _JsonResponse({"a": 1}),
            [
                {"path": "a", "save": "x", "mode": "bogus"},
                {"path": "a", "save": "y", "mode": "keys"},
                {"path": "missing", "save": "z", "mode": "length"},
            ],
        )
    assert rt._errors == 3
    assert not {"x", "y", "z"} & set(rt.globals)


def test_empty_field_spec_raises():
    """An empty entry is a clear error instead of an IndexError."""
    try:
        RESTest(quiet=True).fields(_JsonResponse({}), [[]])
    except RESTestError:
        return
    raise AssertionError("expected RESTestError")


def test_dumps_accepts_the_same_forms_as_fields():
    """dumps() takes path/save/mode objects and one item lists like fields()."""
    rt = RESTest(quiet=True)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rt.dumps(
            _JsonResponse({"a": [1, 2]}),
            [["a"], {"path": "a", "save": "size", "mode": "length"}, {"field": "a"}],
        )
    text = out.getvalue()
    assert "==== a: [" in text
    assert "==== size: 2" in text


class _RecordingParser(RESTestParser):
    """Parser recording the method of every HTTP action instead of sending it."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.methods = []

    def _method_exec(self, act):
        """Record act["method"]."""
        self.methods.append(act["method"])
        return True


def test_http_verb_actions_default_their_method():
    """'action': 'get' / 'post' / ... run as requests with that method."""
    script = _write_script(
        {
            "actions": [
                {"action": "get", "url": "/a"},
                {"action": "POST", "url": "/b"},
                {"method": "delete", "url": "/c"},
                {"action": "put", "url": "/d"},
                {"action": "patch", "url": "/e"},
            ]
        }
    )
    parser = _RecordingParser(quiet=True)
    try:
        parser.open(script)
    finally:
        parser.close()
        os.unlink(script)
    assert parser.methods == ["get", "post", "delete", "put", "patch"]


if __name__ == "__main__":
    test_cli_key_value_may_contain_colons()
    test_cli_key_without_colon_is_a_usage_error()
    test_not_found_is_a_sentinel_not_a_string()
    test_fields_accepts_all_forms()
    test_fields_mode_errors_are_counted()
    test_empty_field_spec_raises()
    test_dumps_accepts_the_same_forms_as_fields()
    test_http_verb_actions_default_their_method()
    print("OK")
