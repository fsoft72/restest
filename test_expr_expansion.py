#!/usr/bin/env python3
"""
Test suite for universal expression expansion in all fields.

Tests the new feature where ${...} expressions are automatically
expanded everywhere in the codebase, not just in specific actions.
"""

import sys
import os

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from lib.engine import RESTest


def test_pure_expressions():
    """Test pure expressions that return numeric values."""
    print("\n=== Testing Pure Expressions ===")

    rt = RESTest()
    rt.globals = {"a": 10, "b": 5, "counter": 3}

    # Test pure expression returns number
    result = rt._expand_expressions("${a + b}")
    assert result == 15, f"Expected 15, got {result}"
    assert isinstance(result, int), f"Expected int, got {type(result)}"
    print("✓ Pure expression ${a + b} = 15")

    # Test with multiplication
    result = rt._expand_expressions("${a * b}")
    assert result == 50, f"Expected 50, got {result}"
    print("✓ Pure expression ${a * b} = 50")

    # Test with parentheses
    result = rt._expand_expressions("${(a + b) * 2}")
    assert result == 30, f"Expected 30, got {result}"
    print("✓ Pure expression ${(a + b) * 2} = 30")

    # Test with division
    result = rt._expand_expressions("${a / b}")
    assert result == 2, f"Expected 2, got {result}"
    print("✓ Pure expression ${a / b} = 2")

    # Test with modulo
    result = rt._expand_expressions("${a % b}")
    assert result == 0, f"Expected 0, got {result}"
    print("✓ Pure expression ${a % b} = 0")


def test_string_interpolation():
    """Test expressions embedded in strings."""
    print("\n=== Testing String Interpolation ===")

    rt = RESTest()
    rt.globals = {"counter": 1, "user_id": 123}

    # Single expression in string
    result = rt._expand_expressions("user_${counter}")
    assert result == "user_1", f"Expected 'user_1', got '{result}'"
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    print("✓ String interpolation 'user_${counter}' = 'user_1'")

    # Expression with prefix and suffix
    result = rt._expand_expressions("prefix_${counter}_suffix")
    assert result == "prefix_1_suffix", f"Expected 'prefix_1_suffix', got '{result}'"
    print("✓ String interpolation 'prefix_${counter}_suffix' = 'prefix_1_suffix'")

    # Multiple expressions
    result = rt._expand_expressions("user_${user_id}_attempt_${counter}")
    assert result == "user_123_attempt_1", f"Expected 'user_123_attempt_1', got '{result}'"
    print("✓ Multiple expressions = 'user_123_attempt_1'")


def test_in_urls():
    """Test expressions in URL paths."""
    print("\n=== Testing Expressions in URLs ===")

    rt = RESTest()
    rt.globals = {"version": 2, "user_id": 456}

    # URL with version
    result = rt._expand_expressions("/api/v${version}/users")
    assert result == "/api/v2/users", f"Expected '/api/v2/users', got '{result}'"
    print("✓ URL with version = '/api/v2/users'")

    # URL with multiple params
    result = rt._expand_expressions("/users/${user_id}/posts/${version}")
    assert result == "/users/456/posts/2", f"Expected '/users/456/posts/2', got '{result}'"
    print("✓ URL with multiple params = '/users/456/posts/2'")


def test_complex_expressions():
    """Test complex arithmetic expressions."""
    print("\n=== Testing Complex Expressions ===")

    rt = RESTest()
    rt.globals = {"base": 100, "increment": 5, "multiplier": 3}

    # Complex calculation
    result = rt._expand_expressions("${(base + increment) * multiplier}")
    assert result == 315, f"Expected 315, got {result}"
    print("✓ Complex expression ${(base + increment) * multiplier} = 315")

    # With string interpolation
    result = rt._expand_expressions("value_${base + increment * multiplier}")
    assert result == "value_115", f"Expected 'value_115', got '{result}'"
    print("✓ Complex in string = 'value_115'")


def test_no_expressions():
    """Test values without expressions pass through unchanged."""
    print("\n=== Testing Values Without Expressions ===")

    rt = RESTest()

    # Plain string
    result = rt._expand_expressions("plain_string")
    assert result == "plain_string", f"Expected 'plain_string', got '{result}'"
    print("✓ Plain string passes through")

    # Number
    result = rt._expand_expressions(123)
    assert result == 123, f"Expected 123, got {result}"
    print("✓ Number passes through")

    # None
    result = rt._expand_expressions(None)
    assert result is None, f"Expected None, got {result}"
    print("✓ None passes through")

    # Dict (should pass through at this level)
    test_dict = {"key": "value"}
    result = rt._expand_expressions(test_dict)
    assert result == test_dict, f"Expected dict, got {result}"
    print("✓ Dict passes through")


def test_in_expand_var():
    """Test that expressions work through _expand_var (the main entry point)."""
    print("\n=== Testing Through _expand_var ===")

    rt = RESTest()
    rt.globals = {"counter": 10, "name": "test"}

    # Pure expression
    result = rt._expand_var("${counter + 5}")
    assert result == 15, f"Expected 15, got {result}"
    print("✓ _expand_var with pure expression = 15")

    # String interpolation
    result = rt._expand_var("user_${counter}")
    assert result == "user_10", f"Expected 'user_10', got '{result}'"
    print("✓ _expand_var with string interpolation = 'user_10'")

    # Combined with % variable substitution
    rt.globals["prefix"] = "api"
    result = rt._expand_var("%(prefix)s_v${counter}")
    assert result == "api_v10", f"Expected 'api_v10', got '{result}'"
    print("✓ Combined expression and % substitution = 'api_v10'")


def test_in_get_v():
    """Test that expressions work through _get_v."""
    print("\n=== Testing Through _get_v ===")

    rt = RESTest()
    rt.globals = {"id": 42}

    # Pure expression via _get_v
    result = rt._get_v("${id * 2}")
    assert result == 84, f"Expected 84, got {result}"
    print("✓ _get_v with pure expression = 84")

    # String interpolation via _get_v
    result = rt._get_v("item_${id}")
    assert result == "item_42", f"Expected 'item_42', got '{result}'"
    print("✓ _get_v with string interpolation = 'item_42'")


def test_whitespace_handling():
    """Test expressions with various whitespace."""
    print("\n=== Testing Whitespace Handling ===")

    rt = RESTest()
    rt.globals = {"a": 5, "b": 3}

    # Spaces in expression
    result = rt._expand_expressions("${ a + b }")
    assert result == 8, f"Expected 8, got {result}"
    print("✓ Expression with spaces = 8")

    # Multiple spaces
    result = rt._expand_expressions("${  a  +  b  }")
    assert result == 8, f"Expected 8, got {result}"
    print("✓ Expression with multiple spaces = 8")


def test_string_variables():
    """Test expressions with string variables that contain numbers."""
    print("\n=== Testing String Variables ===")

    rt = RESTest()
    rt.globals = {"count": "5"}  # String, not int

    # Expression parser should convert string to int
    result = rt._expand_expressions("${count + 3}")
    assert result == 8, f"Expected 8, got {result}"
    print("✓ String variable '5' + 3 = 8")


def test_edge_cases():
    """Test edge cases."""
    print("\n=== Testing Edge Cases ===")

    rt = RESTest()
    rt.globals = {"x": 0}

    # Expression with zero
    result = rt._expand_expressions("${x + 1}")
    assert result == 1, f"Expected 1, got {result}"
    print("✓ Zero in expression = 1")

    # Negative result
    rt.globals["neg"] = -10
    result = rt._expand_expressions("${neg + 5}")
    assert result == -5, f"Expected -5, got {result}"
    print("✓ Negative result = -5")

    # Float result
    rt.globals["f"] = 10.5
    result = rt._expand_expressions("${f + 0.5}")
    assert result == 11.0, f"Expected 11.0, got {result}"
    print("✓ Float result = 11.0")


def test_realistic_scenarios():
    """Test realistic use cases."""
    print("\n=== Testing Realistic Scenarios ===")

    rt = RESTest()
    rt.globals = {
        "user_id": 123,
        "page": 1,
        "per_page": 20,
        "offset": 0,
        "api_version": 3,
    }

    # Pagination calculation
    rt.globals["offset"] = rt._expand_expressions("${(page - 1) * per_page}")
    assert rt.globals["offset"] == 0, f"Expected 0, got {rt.globals['offset']}"
    print("✓ Pagination: offset = ${(page - 1) * per_page} = 0")

    # API path
    result = rt._expand_expressions("/api/v${api_version}/users/${user_id}")
    assert result == "/api/v3/users/123", f"Expected '/api/v3/users/123', got '{result}'"
    print("✓ API path = '/api/v3/users/123'")

    # Request ID
    rt.globals["request_count"] = 42
    result = rt._expand_expressions("req_${request_count}")
    assert result == "req_42", f"Expected 'req_42', got '{result}'"
    print("✓ Request ID = 'req_42'")


def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("Testing Universal Expression Expansion")
    print("=" * 60)

    test_functions = [
        test_pure_expressions,
        test_string_interpolation,
        test_in_urls,
        test_complex_expressions,
        test_no_expressions,
        test_in_expand_var,
        test_in_get_v,
        test_whitespace_handling,
        test_string_variables,
        test_edge_cases,
        test_realistic_scenarios,
    ]

    failed = 0
    for test_func in test_functions:
        try:
            test_func()
        except AssertionError as e:
            print(f"\n✗ FAILED: {test_func.__name__}")
            print(f"  {e}")
            failed += 1
        except Exception as e:
            print(f"\n✗ ERROR: {test_func.__name__}")
            print(f"  {e}")
            failed += 1

    print("\n" + "=" * 60)
    total = len(test_functions)
    passed = total - failed
    print(f"Results: {passed}/{total} test suites passed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
