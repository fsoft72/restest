#!/usr/bin/env python3
"""
Test script for number operations feature.

This script tests the expression parser, path parser with # prefix,
and engine integration without requiring an HTTP server.
"""

import sys
import json
from unittest.mock import MagicMock

# Add lib to path
sys.path.insert(0, ".")

from lib.expr_parser import evaluate_expr, is_expression, ExpressionError
from lib.path_parser import expand_value
from lib.engine import RESTest


def test_expression_parser():
    """Test the expression parser."""
    print("\n=== Testing Expression Parser ===")

    test_vars = {
        "a": 10,
        "b": 5,
        "count": "3",
        "price": 100,
    }

    test_cases = [
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
        ("a + b * 2", 20),  # Tests operator precedence
        ("count + 1", 4),
        ("price * count", 300),
        ("-5 + 10", 5),
        ("-(a + b)", -15),
        ("${a + b}", 15),  # With wrapper
    ]

    passed = 0
    failed = 0

    for expr, expected in test_cases:
        try:
            result = evaluate_expr(expr, test_vars)
            if result == expected:
                print(f"  PASS: '{expr}' = {result}")
                passed += 1
            else:
                print(f"  FAIL: '{expr}' = {result} (expected {expected})")
                failed += 1
        except ExpressionError as e:
            print(f"  FAIL: '{expr}' raised {e}")
            failed += 1

    print(f"\nExpression Parser: {passed} passed, {failed} failed")
    return failed == 0


def test_is_expression():
    """Test is_expression() function."""
    print("\n=== Testing is_expression() ===")

    test_cases = [
        ("${a + b}", True),
        ("${count}", True),
        ("$a + b}", False),  # Missing opening {
        ("{a + b}", False),  # Missing $
        ("a + b", False),
        ("5", False),
        ("", False),
        (123, False),  # Not a string
    ]

    passed = 0
    failed = 0

    for val, expected in test_cases:
        result = is_expression(val)
        if result == expected:
            print(f"  PASS: is_expression({repr(val)}) = {result}")
            passed += 1
        else:
            print(f"  FAIL: is_expression({repr(val)}) = {result} (expected {expected})")
            failed += 1

    print(f"\nis_expression: {passed} passed, {failed} failed")
    return failed == 0


def test_length_extraction():
    """Test path parser with # prefix for length extraction."""
    print("\n=== Testing Length Extraction (# prefix) ===")

    test_data = {
        "users": [
            {"name": "Alice", "roles": ["admin", "user"]},
            {"name": "Bob", "roles": ["user"]},
            {"name": "Charlie", "roles": ["guest"]},
        ],
        "config": {
            "timeout": 30,
            "retries": 3,
        },
        "message": "Hello World",
        "empty_list": [],
        "null_value": None,
    }

    test_cases = [
        ("#users", 3),  # Array length
        ("#users.[0].roles", 2),  # Nested array length
        ("#message", 11),  # String length
        ("#empty_list", 0),  # Empty array
        ("#config", 2),  # Object key count
        # Normal paths (without #) should still work
        ("users.[0].name", "Alice"),
        ("config.timeout", 30),
    ]

    passed = 0
    failed = 0

    for path, expected in test_cases:
        result, err = expand_value(path, test_data)
        if err:
            print(f"  FAIL: '{path}' - error: {err}")
            failed += 1
        elif result == expected:
            print(f"  PASS: '{path}' = {result}")
            passed += 1
        else:
            print(f"  FAIL: '{path}' = {result} (expected {expected})")
            failed += 1

    # Test error case: length of number
    result, err = expand_value("#config.timeout", test_data)
    if err and "Cannot get length" in err:
        print(f"  PASS: '#config.timeout' correctly raised error: {err}")
        passed += 1
    else:
        print(f"  FAIL: '#config.timeout' should have raised error, got: {result}")
        failed += 1

    print(f"\nLength Extraction: {passed} passed, {failed} failed")
    return failed == 0


def test_engine_set_val():
    """Test engine.set_val() with expressions."""
    print("\n=== Testing Engine set_val() with Expressions ===")

    rt = RESTest(base_url="http://localhost", quiet=True)

    # Set initial values
    rt.set_val("a", 10)
    rt.set_val("b", 5)

    test_cases = [
        # (key, value, expected_result)
        ("sum", "${a + b}", 15),
        ("diff", "${a - b}", 5),
        ("product", "${a * b}", 50),
        ("quotient", "${a / b}", 2),
        ("complex", "${(a + b) * 2}", 30),
        ("literal", 42, 42),  # Non-expression should work too
        ("string", "hello", "hello"),
    ]

    passed = 0
    failed = 0

    for key, value, expected in test_cases:
        rt.set_val(key, value)
        result = rt.globals.get(key)
        if result == expected:
            print(f"  PASS: set_val('{key}', {repr(value)}) -> {result}")
            passed += 1
        else:
            print(f"  FAIL: set_val('{key}', {repr(value)}) -> {result} (expected {expected})")
            failed += 1

    print(f"\nEngine set_val: {passed} passed, {failed} failed")
    return failed == 0


def test_engine_fields():
    """Test engine.fields() with # prefix and object syntax."""
    print("\n=== Testing Engine fields() with New Syntax ===")

    rt = RESTest(base_url="http://localhost", quiet=True)

    # Create mock response
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": {
            "items": [1, 2, 3, 4, 5],
            "users": [
                {"name": "Alice"},
                {"name": "Bob"},
            ],
            "metadata": {
                "version": "1.0",
                "count": 100,
            },
        },
    }

    # Test various field extraction syntaxes
    fields_config = [
        # Tuple syntax with # prefix
        ["#data.items", "items_count"],
        ["#data.users", "users_count"],
        # Object syntax with mode
        {"path": "data.items", "mode": "length", "save": "items_len_obj"},
        {"path": "data.metadata", "mode": "keys", "save": "meta_keys"},
        {"path": "data.items", "mode": "type", "save": "items_type"},
        {"path": "data.metadata.count", "mode": "value", "save": "count_val"},
    ]

    rt.fields(mock_resp, fields_config)

    test_cases = [
        ("items_count", 5),
        ("users_count", 2),
        ("items_len_obj", 5),
        ("meta_keys", ["version", "count"]),
        ("items_type", "array"),
        ("count_val", 100),
    ]

    passed = 0
    failed = 0

    for key, expected in test_cases:
        result = rt.globals.get(key)
        if result == expected:
            print(f"  PASS: globals['{key}'] = {result}")
            passed += 1
        else:
            print(f"  FAIL: globals['{key}'] = {result} (expected {expected})")
            failed += 1

    print(f"\nEngine fields: {passed} passed, {failed} failed")
    return failed == 0


def test_engine_check_expr():
    """Test engine.check() with EXPR mode."""
    print("\n=== Testing Engine check() with EXPR Mode ===")

    rt = RESTest(base_url="http://localhost", quiet=True, stop_on_error=False)

    # Set some globals for expression evaluation
    rt.globals["expected_count"] = 5
    rt.globals["min_users"] = 2
    # These would normally be extracted via fields(), but we set them directly for testing
    rt.globals["available"] = 80
    rt.globals["reserved"] = 20

    # Create mock response
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": {
            "items": [1, 2, 3, 4, 5],
            "users": [
                {"name": "Alice"},
                {"name": "Bob"},
            ],
            "total": 100,
            "available": 80,
            "reserved": 20,
        },
    }
    mock_resp.size = 1000

    # Tests that should pass
    passing_tests = [
        # EXPR mode with variable
        {"mode": "EXPR", "key": "#data.items", "op": "==", "expr": "${expected_count}"},
        # EXPR mode with literal
        {"mode": "EXPR", "key": "#data.users", "op": ">=", "expr": 2},
        # EXPR mode with expression (using globals that were extracted via fields)
        {"mode": "EXPR", "key": "data.total", "op": "==", "expr": "${available + reserved}"},
        # Traditional SIZE mode with expression in value
        {"field": "data.items", "mode": "SIZE", "value": "${expected_count}"},
    ]

    passed = 0
    failed = 0

    # Reset error count before each test batch
    for i, test in enumerate(passing_tests):
        rt._errors = 0
        rt._tests = 0

        rt.check(mock_resp, [test])

        if rt._errors == 0:
            print(f"  PASS: Test {i+1} passed as expected")
            passed += 1
        else:
            print(f"  FAIL: Test {i+1} should have passed: {test}")
            failed += 1

    # Tests that should fail
    failing_tests = [
        # Wrong count
        {"mode": "EXPR", "key": "#data.items", "op": "==", "expr": 10},
        # Wrong comparison
        {"mode": "EXPR", "key": "data.total", "op": "<", "expr": 50},
    ]

    for i, test in enumerate(failing_tests):
        rt._errors = 0
        rt._tests = 0

        rt.check(mock_resp, [test])

        if rt._errors > 0:
            print(f"  PASS: Failing test {i+1} correctly failed")
            passed += 1
        else:
            print(f"  FAIL: Failing test {i+1} should have failed: {test}")
            failed += 1

    print(f"\nEngine check EXPR: {passed} passed, {failed} failed")
    return failed == 0


def test_expression_in_check_value():
    """Test that expressions work in regular test mode values."""
    print("\n=== Testing Expressions in Test Values ===")

    rt = RESTest(base_url="http://localhost", quiet=True, stop_on_error=False)

    # Set globals
    rt.globals["expected_size"] = 3
    rt.globals["max_count"] = 10

    # Create mock response
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "items": [1, 2, 3],
        "count": 5,
    }
    mock_resp.size = 100

    test_cases = [
        # SIZE with expression
        ({"field": "items", "mode": "SIZE", "value": "${expected_size}"}, True),
        # GT with expression
        ({"field": "count", "mode": "GT", "value": "${expected_size}"}, True),  # 5 > 3
        # LT with expression
        ({"field": "count", "mode": "LT", "value": "${max_count}"}, True),  # 5 < 10
        # Should fail: count is not > 10
        ({"field": "count", "mode": "GT", "value": "${max_count}"}, False),
    ]

    passed = 0
    failed = 0

    for test, should_pass in test_cases:
        rt._errors = 0
        rt._tests = 0

        rt.check(mock_resp, [test])

        if should_pass:
            if rt._errors == 0:
                print(f"  PASS: {test['field']} {test['mode']} {test['value']}")
                passed += 1
            else:
                print(f"  FAIL: {test['field']} {test['mode']} {test['value']} - should have passed")
                failed += 1
        else:
            if rt._errors > 0:
                print(f"  PASS: {test['field']} {test['mode']} {test['value']} - correctly failed")
                passed += 1
            else:
                print(f"  FAIL: {test['field']} {test['mode']} {test['value']} - should have failed")
                failed += 1

    print(f"\nExpressions in Test Values: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all tests."""
    print("=" * 60)
    print("Number Operations Feature Tests")
    print("=" * 60)

    all_passed = True

    all_passed &= test_expression_parser()
    all_passed &= test_is_expression()
    all_passed &= test_length_extraction()
    all_passed &= test_engine_set_val()
    all_passed &= test_engine_fields()
    all_passed &= test_engine_check_expr()
    all_passed &= test_expression_in_check_value()

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
