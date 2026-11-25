#!/usr/bin/env python3
"""Regression tests for the high priority items in OPTIMIZE.md."""

import contextlib
import datetime
import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lib.engine as engine_module
from lib.engine import RESTest
from lib.errors import RESTestError
from lib.parser import RESTestParser
from lib.postman_exp import PostmanExporter, PostmanExporterItem


class _FakeRequest:
    """Minimal stand-in for requests.PreparedRequest."""

    method = "GET"
    url = "http://localhost/x"
    body = None
    headers = {}


class _FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, status_code):
        self.status_code = status_code
        self.headers = {}
        self.text = ""
        self.content = b""
        self.elapsed = datetime.timedelta(0)
        self.request = _FakeRequest()


class _FakeSession:
    """Session that answers every GET with a fixed status code."""

    def __init__(self, status_code):
        self.status_code = status_code
        self.cookies = {}

    def get(self, url, **kwargs):
        """Return a fake response with the configured status code."""
        return _FakeResponse(self.status_code)


def _write_script(script):
    """Write a script dict to a temp JSON file and return its path."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(script, f)
    return f.name


def _run(script, **kwargs):
    """Run a script dict through the parser and return the parser."""
    fname = _write_script(script)
    try:
        parser = RESTestParser(quiet=True, **kwargs)
        parser.open(fname)
    finally:
        os.unlink(fname)
    return parser


def _raises_restest_error(func):
    """Return the RESTestError raised by func, or None (stderr is silenced)."""
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            func()
        except RESTestError as e:
            return e
    return None


def test_delay_is_in_milliseconds():
    """A 500ms delay must sleep 0.5s, not 0s."""
    slept = []
    orig_sleep = engine_module.time.sleep
    engine_module.time.sleep = slept.append
    try:
        rt = RESTest(dry=True, delay=500)
        rt.do_EXEC("GET", "/x", {}, authenticated=False)
    finally:
        engine_module.time.sleep = orig_sleep
    assert slept == [0.5], slept


def test_status_mismatch_counted_when_not_stopping():
    """A wrong status code is an error even with stop_on_error disabled."""
    rt = RESTest(stop_on_error=False)
    rt.session = _FakeSession(500)
    with contextlib.redirect_stderr(io.StringIO()):
        res = rt.do_EXEC("GET", "/x", {}, authenticated=False, status_code=200)
    assert res.status_code == 500
    assert rt._errors == 1, rt._errors


def test_status_mismatch_raises_when_stopping():
    """A wrong status code raises RESTestError when stop_on_error is on."""
    rt = RESTest(stop_on_error=True)
    rt.session = _FakeSession(500)
    err = _raises_restest_error(
        lambda: rt.do_EXEC("GET", "/x", {}, authenticated=False, status_code=200)
    )
    assert err is not None
    assert "500" in str(err), str(err)


def test_nested_expressions_are_expanded():
    """${...} and %(var)s are expanded inside nested dicts and lists."""
    rt = RESTest()
    rt.globals = {"n": 1, "name": "bob"}
    res = rt._expand_data(
        {
            "user": {"id": "${n + 1}", "name": "%(name)s", "tags": ["${n}", ["${n * 3}"]]},
            "list": [["x_${n}"]],
        }
    )
    assert res["user"]["id"] == 2, res
    assert res["user"]["name"] == "bob", res
    assert res["user"]["tags"] == [1, [3]], res
    assert res["list"] == [["x_1"]], res


_CODE_SCRIPT = {
    "actions": [{"action": "code", "code": ["self.rt.globals['ran'] = 1"]}]
}


def test_code_action_disabled_by_default():
    """The code action must not run without allow_code."""
    holder = {}

    def _go():
        holder["parser"] = _run(_CODE_SCRIPT)

    err = _raises_restest_error(_go)
    assert err is not None
    assert "--allow-code" in str(err), str(err)


def test_code_action_runs_with_allow_code():
    """The code action runs when allow_code is set."""
    with contextlib.redirect_stdout(io.StringIO()):
        parser = _run(_CODE_SCRIPT, allow_code=True)
    assert parser.rt.globals["ran"] == 1, parser.rt.globals


def test_missing_file_raises():
    """Library code raises RESTestError instead of exiting the process."""
    parser = RESTestParser(quiet=True)
    assert _raises_restest_error(lambda: parser.open("/nonexistent/file.json"))


def test_expression_error_raises():
    """A bad ${...} expression raises RESTestError instead of exiting."""
    rt = RESTest()
    assert _raises_restest_error(lambda: rt._expand_var("${1 +}"))


def test_postman_accepts_dict_and_list_data():
    """Postman items accept dict data (form) and JSON lists without crashing."""
    item = PostmanExporterItem(
        "t", "POST", "http://h/a", {"a": 1}, None, {}, None, None
    )
    assert json.loads(item.obj()["request"]["body"]["raw"]) == {"a": 1}

    item = PostmanExporterItem(
        "t", "POST", "http://h/a", '[{"a": 1}]', None, {}, None, None
    )
    assert json.loads(item.obj()["request"]["body"]["raw"]) == [{"a": 1}]


def test_postman_headers_no_debug_print():
    """Building a Postman item must not print debug output."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        PostmanExporterItem(
            "t", "GET", "http://h/a", "{}", None, {"X-A": "1"}, None, None
        )
    assert out.getvalue() == "", out.getvalue()


def test_postman_save_writes_file():
    """Postman save writes a valid JSON collection."""
    fd, fname = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        exp = PostmanExporter(fname, "coll", None, None, None)
        exp.add("t", "GET", "http://h/a", "{}", {}, None)
        exp.save()
        with open(fname) as f:
            data = json.load(f)
        assert data["info"]["name"] == "coll"
        assert len(data["item"]) == 1
    finally:
        os.unlink(fname)


if __name__ == "__main__":
    test_delay_is_in_milliseconds()
    test_status_mismatch_counted_when_not_stopping()
    test_status_mismatch_raises_when_stopping()
    test_nested_expressions_are_expanded()
    test_code_action_disabled_by_default()
    test_code_action_runs_with_allow_code()
    test_missing_file_raises()
    test_expression_error_raises()
    test_postman_accepts_dict_and_list_data()
    test_postman_headers_no_debug_print()
    test_postman_save_writes_file()
    print("OK")
