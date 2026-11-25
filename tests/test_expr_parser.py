#!/usr/bin/env python3
"""Unit tests for lib/expr_parser.py (moved from its __main__ block)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.expr_parser import ExpressionError, evaluate_expr

VARS = {
    "a": 10,
    "b": 5,
    "count": "3",
    "price": 100,
}


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("5 + 3", 8),
        ("10 - 4", 6),
        ("3 * 4", 12),
        ("10 / 2", 5),
        ("10 % 3", 1),
        ("a + b", 15),
        ("a - b", 5),
        ("a * b", 50),
        ("a / b", 2),
        ("(a + b) * 2", 30),
        ("a + b * 2", 20),
        ("count + 1", 4),
        ("price * count", 300),
        ("-5 + 10", 5),
        ("-(a + b)", -15),
        ("${a + b}", 15),
    ],
)
def test_evaluate(expr, expected):
    """Valid expressions evaluate to the expected number."""
    assert evaluate_expr(expr, VARS) == expected


@pytest.mark.parametrize(
    "expr",
    [
        "5 / 0",
        "5 + + 3",
        "(5 + 3",
    ],
)
def test_evaluate_errors(expr):
    """Invalid expressions raise ExpressionError."""
    with pytest.raises(ExpressionError):
        evaluate_expr(expr, VARS)


def test_undefined_variable_is_zero():
    """Undefined variables are initialized to 0 (since v2.6.0)."""
    assert evaluate_expr("undefined_var + 5", {}) == 5
