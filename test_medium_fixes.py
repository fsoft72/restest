#!/usr/bin/env python3
"""Regression tests for the medium priority items in OPTIMIZE.md."""

import contextlib
import io
import json
import os
import stat
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests

from lib.engine import RESTest
from lib.errors import RESTestError
from lib.parser import RESTestParser


class _JsonResponse:
    """Minimal response exposing a JSON body and a size."""

    def __init__(self, body):
        self._body = body
        self.size = len(json.dumps(body))

    def json(self):
        """Return the JSON body."""
        return self._body


def _write_script(script):
    """Write a script dict to a temp JSON file and return its path."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(script, f)
    return f.name


def _run(script, parser_class=RESTestParser, **kwargs):
    """Run a script dict through the parser and return the parser."""
    fname = _write_script(script)
    parser = parser_class(quiet=True, **kwargs)
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            parser.open(fname)
    finally:
        parser.close()
        os.unlink(fname)
    return parser


def _check_ok(mode, current, expected):
    """Return True when the given test mode passes."""
    return RESTest()._check({"mode": mode, "value": expected}, "v", current) is None


def test_ordering_modes_accept_numeric_strings():
    """GT / LTE convert numeric strings (also floats) on both sides."""
    assert _check_ok("GT", "3.5", 3)
    assert _check_ok("GT", 3, "2")
    assert _check_ok("LTE", "10", "10")
    assert not _check_ok("LT", "10", 2)


def test_ordering_mode_on_text_is_a_failure_not_a_crash():
    """Comparing text with a number reports a failure instead of raising."""
    assert not _check_ok("GT", "abc", 3)


def test_not_equal_is_the_negation_of_equals():
    """NOT_EQUAL fails whenever EQUALS passes (also for 1 vs "1")."""
    assert _check_ok("EQUALS", "1", 1)
    assert not _check_ok("NOT_EQUAL", "1", 1)
    assert _check_ok("NOT_EQUAL", "1", 2)


def test_size_modes():
    """SIZE modes compare the length of the value."""
    assert _check_ok("SIZE", [1, 2], 2)
    assert _check_ok("()>", [1, 2], 1)
    assert not _check_ok("()<", [1, 2], 2)


def test_expr_check_still_works():
    """EXPR tests keep comparing numbers parsed from strings."""
    rt = RESTest()
    assert rt._check_expr({"key": "a", "op": ">", "expr": "2"}, {"a": "3"}) is None
    assert rt._check_expr({"key": "a", "op": "LTE", "expr": "2.5"}, {"a": 2}) is None
    assert rt._check_expr({"key": "a", "op": "==", "expr": "4"}, {"a": 3}) is not None
    assert "unsupported" in rt._check_expr({"key": "a", "op": "~", "expr": "1"}, {"a": 1})


def test_missing_field_reports_missing_not_crash():
    """A missing field with a numeric mode is reported as missing."""
    rt = RESTest(stop_on_error=True)
    resp = _JsonResponse({"a": 1})
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            rt.check(resp, [{"field": "b", "mode": "GT", "value": 1}])
        except RESTestError as e:
            assert "missing" in str(e), str(e)
        else:
            raise AssertionError("expected RESTestError")


def test_missing_field_passes_not_exists():
    """NOT_EXISTS passes when the field is absent from the response."""
    rt = RESTest(stop_on_error=True)
    resp = _JsonResponse({"a": 1})
    with contextlib.redirect_stdout(io.StringIO()):
        rt.check(resp, [{"field": "password", "mode": "NOT_EXISTS"}])
    assert rt._errors == 0


def test_all_failing_tests_are_counted_when_not_stopping():
    """Without stop_on_error every failing test runs and is counted."""
    rt = RESTest(stop_on_error=False)
    resp = _JsonResponse({"a": 1, "b": 2})
    with contextlib.redirect_stderr(io.StringIO()):
        rt.check(
            resp,
            [
                {"field": "a", "value": 5},
                {"field": "b", "value": 5},
                {"field": "a", "value": 1},
            ],
        )
    assert rt._tests == 3, rt._tests
    assert rt._errors == 2, rt._errors


class _TrackingParser(RESTestParser):
    """Parser that remembers every file opened for upload."""

    opened = []

    def _parse_files(self, dct):
        """Open the files and keep a reference to them."""
        files = super()._parse_files(dct)
        for v in files.values():
            _TrackingParser.opened.extend(v if isinstance(v, list) else [v])
        return files


def test_upload_files_are_closed():
    """Files opened for upload are closed after each request."""
    fd, upload = tempfile.mkstemp()
    os.close(fd)
    _TrackingParser.opened = []
    try:
        _run(
            {
                "actions": [
                    {
                        "method": "post",
                        "url": "/x",
                        "files": {"one": upload, "many": [upload, upload]},
                        "repeat": 2,
                    }
                ]
            },
            parser_class=_TrackingParser,
            dry=True,
            auth_mode="no",
        )
    finally:
        os.unlink(upload)
    assert len(_TrackingParser.opened) == 6, _TrackingParser.opened
    assert all(f.closed for f in _TrackingParser.opened)


def test_resolve_url_absolute_only_at_start():
    """Only URLs starting with http(s):// are treated as absolute."""
    rt = RESTest(base_url="http://h")
    assert rt._resolve_url("/r?to=http://x") == "http://h/r?to=http://x"
    assert rt._resolve_url("https://other/a") == "https://other/a"
    assert rt._resolve_url("HTTP://other/a") == "HTTP://other/a"


def test_unsupported_http_method_raises():
    """An unknown HTTP method is an error, not a silent POST."""
    rt = RESTest(dry=True)
    try:
        rt.do_EXEC("FOO", "/x", {}, authenticated=False)
    except RESTestError as e:
        assert "FOO" in str(e)
    else:
        raise AssertionError("expected RESTestError")


def test_unknown_action_raises():
    """An unknown action is reported by name."""
    try:
        _run({"actions": [{"action": "nope"}]})
    except RESTestError as e:
        assert "nope" in str(e)
    else:
        raise AssertionError("expected RESTestError")


def test_system_rejects_unknown_keys_and_merges_global_headers():
    """Unknown system keys are ignored; global_headers go under headers."""
    parser = _run(
        {
            "system": {
                "session": 1,
                "base_url": "http://h/",
                "global_headers": {"X-A": "global", "X-B": "global"},
                "headers": {"X-B": "local"},
            },
            "actions": [],
        }
    )
    assert isinstance(parser.rt.session, requests.Session)
    assert parser.rt.base_url == "http://h"
    assert parser.rt.headers == {"X-A": "global", "X-B": "local"}, parser.rt.headers


def test_log_file_kept_open_and_private():
    """The log handle is reused, flushed after each write and owner only."""
    fd, log = tempfile.mkstemp(suffix=".log")
    os.close(fd)
    os.unlink(log)
    rt = RESTest(log_file=log)
    try:
        rt._log_write("a")
        handle = rt._log_handle
        rt._log_write("b\n")
        assert rt._log_handle is handle
        with open(log) as f:
            assert f.read() == "ab\n"
        assert stat.S_IMODE(os.stat(log).st_mode) == 0o600
    finally:
        rt.close()
        os.unlink(log)
    assert rt._log_handle is None


if __name__ == "__main__":
    test_ordering_modes_accept_numeric_strings()
    test_ordering_mode_on_text_is_a_failure_not_a_crash()
    test_not_equal_is_the_negation_of_equals()
    test_size_modes()
    test_expr_check_still_works()
    test_missing_field_reports_missing_not_crash()
    test_missing_field_passes_not_exists()
    test_all_failing_tests_are_counted_when_not_stopping()
    test_upload_files_are_closed()
    test_resolve_url_absolute_only_at_start()
    test_unsupported_http_method_raises()
    test_unknown_action_raises()
    test_system_rejects_unknown_keys_and_merges_global_headers()
    test_log_file_kept_open_and_private()
    print("OK")
