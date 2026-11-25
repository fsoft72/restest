#!/usr/bin/env python3
"""Unit tests for lib/path_parser.py (moved from its __main__ block)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.path_parser import expand_value

DATA = {
    "type1": [
        {"name": "hello", "value": "world"},
        {"name": "ciao", "value": "mondo"},
    ],
    "users": [
        {"email": "test01@example.com", "id": 123, "perms": ["admin", "work", "home"]},
        {"email": "test02@example.com", "id": 999, "perms": ["do", "this"]},
    ],
    "nested": {
        "opts": [
            {
                "name": "opt1",
                "children": [
                    {"name": "child1", "value": 1},
                    {"name": "child2", "value": 2},
                ],
            }
        ]
    },
}

COURSE_ID = "course.080ca4b4e3cb4e1e1b6b99776e8fb621.3tk0"

COURSES = {
    "courses": [
        {
            "id": COURSE_ID,
            "slug": "course-test",
            "tot_lessons": 3,
            "tags": [],
        }
    ]
}


@pytest.mark.parametrize(
    "path,expected",
    [
        ("type1.[0].name", "hello"),
        ("type1.[0].value", "world"),
        ("type1.[name=ciao].value", "mondo"),
        ("users.[id=123].perms", ["admin", "work", "home"]),
        ("nested.opts[name=opt1].children[name!=child2].value", 1),
    ],
)
def test_expand_paths(path, expected):
    """Labels, indexes and [key=value] / [key!=value] filters resolve."""
    res, err = expand_value(path, DATA)
    assert not err
    assert res == expected


def test_quoted_value_with_dots():
    """A quoted filter value may contain dots."""
    res, err = expand_value("courses.[id='%s']" % COURSE_ID, COURSES)
    assert not err
    assert res["slug"] == "course-test"


@pytest.mark.parametrize(
    "path,data,expected",
    [
        ("#type1", DATA, 2),
        ("#type1.[0].name", DATA, 5),
        ("#users.[id=123].perms", DATA, 3),
        ("#courses.[0].tags", COURSES, 0),
        ("#nested", DATA, 1),
    ],
)
def test_length_prefix(path, data, expected):
    """A leading '#' returns the length of arrays, strings and objects."""
    res, err = expand_value(path, data)
    assert not err
    assert res == expected


def test_length_of_number_is_an_error():
    """'#' on a number reports an error."""
    res, err = expand_value("#courses.[0].tot_lessons", COURSES)
    assert res is None
    assert err


def test_missing_key_is_an_error():
    """A missing key returns (None, error)."""
    res, err = expand_value("type1.[0].missing", DATA)
    assert res is None
    assert "missing" in err
