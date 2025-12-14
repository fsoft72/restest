# Number Operations Specification for RESTest

## Overview

This document specifies the addition of **number operations** to RESTest, enabling arithmetic expressions, numeric variable manipulation, and enhanced numeric tests without using Python's `eval()`. The implementation will extend the existing variable expansion and test systems with a dedicated expression parser.

---

## Table of Contents

1. [Goals and Non-Goals](#goals-and-non-goals)
2. [Current State Analysis](#current-state-analysis)
3. [Proposed Syntax](#proposed-syntax)
4. [Expression Parser Design](#expression-parser-design)
5. [New Features](#new-features)
   - [Numeric Variable Storage](#51-numeric-variable-storage)
   - [Array Length Extraction](#52-array-length-extraction)
   - [Arithmetic Expressions](#53-arithmetic-expressions)
   - [Expression Tests](#54-expression-tests)
6. [Implementation Plan](#implementation-plan)
7. [Examples](#examples)
8. [Edge Cases and Error Handling](#edge-cases-and-error-handling)

---

## 1. Goals and Non-Goals

### Goals

- Add arithmetic operations (`+`, `-`, `*`, `/`, `%`) on numeric variables
- Enable saving array/string lengths to variables
- Allow expressions in test values (e.g., test if `arr_len == other_len + 1`)
- Support numeric comparisons between variables
- Maintain JSON compatibility (no custom syntax that breaks JSON)
- Provide clear, descriptive error messages
- Create a dedicated expression parser (similar to `path_parser.py`)

### Non-Goals

- **NO use of Python's `eval()` or `exec()`** - security risk, we build our own parser
- No support for complex math functions (sin, cos, sqrt, etc.) - keep it simple
- No floating-point precision guarantees - use integers where possible
- No bitwise operations in the first version
- No support for boolean algebra expressions

---

## 2. Current State Analysis

### Variable Storage (`lib/engine.py`)

```python
self.globals = {}  # All variables stored as strings
```

Variables are currently:
- Stored as **strings** (even numbers: `"123"`)
- Expanded via Python's `%` formatting: `%(variable_name)s`
- Global and persistent across all test files

### Existing Test Modes

| Mode | Description |
|------|-------------|
| `GT`, `>` | Greater than |
| `GTE`, `>=` | Greater than or equal |
| `LT`, `<` | Less than |
| `LTE`, `<=` | Less than or equal |
| `SIZE`, `LEN` | Array/string length equals N |
| `SIZE-GT`, `()>` | Length greater than N |
| `SIZE-GTE`, `()>=` | Length greater than or equal to N |
| `SIZE-LT`, `()<` | Length less than N |
| `SIZE-LTE`, `()<=` | Length less than or equal to N |

**Current Limitation:** Test values must be literals, not expressions or variable references.

### Path Parser Reference (`lib/path_parser.py`)

The path parser demonstrates the pattern we'll follow:
- Regex-based tokenization
- Recursive descent parsing
- Mode-based token interpretation
- Clean separation of parsing and evaluation

---

## 3. Proposed Syntax

### 3.1 Expression Markers

To distinguish expressions from regular strings, we use the `${...}` syntax:

```json
"value": "${my_var + 5}"
"value": "${arr_len * 2}"
"value": "${count - 1}"
```

This syntax:
- Is valid JSON (it's just a string)
- Is clearly distinguishable from regular values
- Is familiar to developers (shell, template languages)
- Won't conflict with existing `%(var)s` syntax

### 3.2 Length Extraction Syntax

For extracting lengths, we use the `#` prefix in field paths:

```json
"fields": [
    ["#response.items", "items_count"],
    ["#users", "user_count"]
]
```

Alternative (explicit mode):
```json
"fields": [
    {"path": "response.items", "mode": "length", "save": "items_count"}
]
```

### 3.3 Variable Reference in Expressions

Variables are referenced by name (no `%()s` needed inside `${}`):

```json
"${my_var}"           // Simple reference
"${my_var + 5}"       // Variable plus literal
"${var1 + var2}"      // Two variables
"${arr_len * 2 + 1}"  // Complex expression
```

---

## 4. Expression Parser Design

### 4.1 New File: `lib/expr_parser.py`

Similar to `path_parser.py`, create a dedicated expression parser.

### 4.2 Tokenization

```python
# Token types
TOKEN_NUMBER = "NUMBER"      # 123, 45.67
TOKEN_IDENT = "IDENT"        # variable names
TOKEN_OP = "OP"              # +, -, *, /, %
TOKEN_LPAREN = "LPAREN"      # (
TOKEN_RPAREN = "RPAREN"      # )

# Regex for tokenization
rx_expr = re.compile(r"""
    (\d+\.?\d*)     |   # Numbers (int or float)
    ([a-zA-Z_]\w*)  |   # Identifiers
    ([+\-*/%])      |   # Operators
    ([()])              # Parentheses
""", re.VERBOSE)
```

### 4.3 Grammar (EBNF)

```
expression  := term (('+' | '-') term)*
term        := factor (('*' | '/' | '%') factor)*
factor      := NUMBER | IDENTIFIER | '(' expression ')'
```

This grammar ensures:
- Correct operator precedence (`*`, `/`, `%` before `+`, `-`)
- Parentheses for grouping
- No `eval()` needed - we control evaluation completely

### 4.4 Evaluation

```python
def evaluate_expr(expr_str: str, variables: dict) -> int | float:
    """
    Parse and evaluate an expression string.

    Args:
        expr_str: Expression like "my_var + 5"
        variables: Dict of variable name -> value

    Returns:
        Numeric result of the expression

    Raises:
        ExpressionError: On syntax or runtime errors
    """
```

---

## 5. New Features

### 5.1 Numeric Variable Storage

#### New Action: `set` with `type: "number"`

```json
{
    "action": "set",
    "key": "count",
    "value": 42,
    "type": "number"
}
```

When `type: "number"` is specified:
- Value is stored as Python `int` or `float`
- Arithmetic operations work directly
- String concatenation will convert back to string

#### Automatic Type Detection

When setting from expressions, type is inferred:

```json
{
    "action": "set",
    "key": "result",
    "value": "${count + 10}"
}
```

Result is automatically numeric.

---

### 5.2 Array Length Extraction

#### Method 1: Hash Prefix in Path

```json
{
    "method": "get",
    "url": "/api/users",
    "fields": [
        ["#data.users", "user_count"],
        ["#data.users[0].permissions", "first_user_perms_count"]
    ]
}
```

The `#` prefix:
- Extracts the value at the path
- Returns `len()` of arrays or strings
- Returns `0` for `null`/missing
- Raises error for non-countable types (objects, numbers)

#### Method 2: Object Syntax

```json
{
    "method": "get",
    "url": "/api/users",
    "fields": [
        {
            "path": "data.users",
            "mode": "length",
            "save": "user_count"
        },
        {
            "path": "data.users",
            "mode": "value",
            "save": "users_array"
        }
    ]
}
```

Supported modes:
- `value` (default): Extract the value as-is
- `length`: Extract `len()` of array/string
- `type`: Extract type name ("array", "object", "string", "number", "null")
- `keys`: Extract object keys as array (for objects only)

---

### 5.3 Arithmetic Expressions

#### Supported Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `+` | Addition | `${a + b}` |
| `-` | Subtraction | `${a - b}` |
| `*` | Multiplication | `${a * b}` |
| `/` | Division (integer) | `${a / b}` |
| `%` | Modulo | `${a % b}` |
| `()` | Grouping | `${(a + b) * c}` |

#### Expression in `set` Action

```json
{
    "action": "set",
    "key": "total",
    "value": "${price * quantity}"
}
```

```json
{
    "action": "set",
    "key": "average",
    "value": "${total / count}"
}
```

```json
{
    "action": "set",
    "key": "next_page",
    "value": "${current_page + 1}"
}
```

#### Expression in URL/Body (After Calculation)

First calculate, then use:

```json
[
    {
        "action": "set",
        "key": "next_offset",
        "value": "${offset + limit}"
    },
    {
        "method": "get",
        "url": "/api/items?offset=%(next_offset)s&limit=%(limit)s"
    }
]
```

---

### 5.4 Expression Tests

#### New Test Syntax: Expression Values

Allow expressions in the `value` field of tests:

```json
{
    "field": "data.items",
    "mode": "SIZE",
    "value": "${expected_count}"
}
```

```json
{
    "field": "data.items",
    "mode": "SIZE",
    "value": "${page_size * page_number}"
}
```

#### New Test Mode: `EXPR` / `EXPRESSION`

For complex comparisons involving expressions:

```json
{
    "mode": "EXPR",
    "key": "data.total",
    "op": "==",
    "expr": "${items_count + extra_items}"
}
```

Supported comparison operators in `EXPR`:
- `==`, `=`, `EQUALS`
- `!=`, `<>`, `NOT_EQUALS`
- `>`, `GT`
- `>=`, `GTE`
- `<`, `LT`
- `<=`, `LTE`

#### Comparing Two Fields

```json
{
    "mode": "EXPR",
    "key": "data.sent_count",
    "op": "==",
    "expr": "data.received_count"
}
```

#### Field Length in Expression

```json
{
    "mode": "EXPR",
    "key": "#data.items",
    "op": ">=",
    "expr": "${min_items}"
}
```

---

## 6. Implementation Plan

### Phase 1: Expression Parser (`lib/expr_parser.py`)

1. Create tokenizer (regex-based)
2. Implement recursive descent parser
3. Implement evaluator with variable substitution
4. Add comprehensive error messages
5. Write unit tests

### Phase 2: Length Extraction

1. Modify `path_parser.py` to handle `#` prefix
2. Add `mode` support to field extraction in `engine.py`
3. Update `fields()` method to support object syntax
4. Write unit tests

### Phase 3: Expression in `set` Action

1. Modify `_method_set()` to detect `${...}` syntax
2. Call expression parser for evaluation
3. Store result with appropriate type
4. Write unit tests

### Phase 4: Expression in Tests

1. Modify `_check()` to detect expressions in `value`
2. Add new `EXPR` test mode
3. Support `#` prefix for length in test fields
4. Write unit tests

### Phase 5: Documentation and Examples

1. Update README with new features
2. Create example test files
3. Document error messages

---

## 7. Examples

### Example 1: Basic Array Length Check

**Scenario:** Fetch users and verify the count matches expected value.

```json
{
    "actions": [
        {
            "action": "set",
            "key": "expected_users",
            "value": 10
        },
        {
            "method": "get",
            "url": "/api/users",
            "fields": [
                ["#data.users", "actual_count"]
            ],
            "tests": [
                {
                    "field": "data.users",
                    "mode": "SIZE",
                    "value": "${expected_users}"
                }
            ]
        }
    ]
}
```

---

### Example 2: Pagination Test

**Scenario:** Test pagination with calculated offsets.

```json
{
    "actions": [
        {
            "action": "set",
            "key": "page_size",
            "value": 20
        },
        {
            "action": "set",
            "key": "current_page",
            "value": 0
        },
        {
            "rem": "First page"
        },
        {
            "method": "get",
            "url": "/api/items?limit=%(page_size)s&offset=0",
            "fields": [
                ["#data.items", "first_page_count"],
                ["meta.total", "total_items"]
            ],
            "tests": [
                {
                    "field": "data.items",
                    "mode": "SIZE-LTE",
                    "value": "${page_size}"
                }
            ]
        },
        {
            "action": "set",
            "key": "second_page_offset",
            "value": "${page_size}"
        },
        {
            "rem": "Second page"
        },
        {
            "method": "get",
            "url": "/api/items?limit=%(page_size)s&offset=%(second_page_offset)s",
            "fields": [
                ["#data.items", "second_page_count"]
            ],
            "tests": [
                {
                    "field": "data.items",
                    "mode": "SIZE-LTE",
                    "value": "${page_size}"
                }
            ]
        },
        {
            "action": "set",
            "key": "fetched_total",
            "value": "${first_page_count + second_page_count}"
        },
        {
            "rem": "Verify we got expected items (assuming 2 pages cover all)"
        },
        {
            "action": "set",
            "key": "expected_total",
            "value": "${total_items}"
        }
    ]
}
```

---

### Example 3: Create and Verify Count

**Scenario:** Create items and verify the list grew by the expected amount.

```json
{
    "actions": [
        {
            "rem": "Get initial count"
        },
        {
            "method": "get",
            "url": "/api/items",
            "fields": [
                ["#data", "initial_count"]
            ]
        },
        {
            "rem": "Create 3 new items"
        },
        {
            "method": "post",
            "url": "/api/items",
            "body": {"name": "Item 1"},
            "repeat": 3
        },
        {
            "rem": "Verify count increased by 3"
        },
        {
            "method": "get",
            "url": "/api/items",
            "tests": [
                {
                    "field": "data",
                    "mode": "SIZE",
                    "value": "${initial_count + 3}"
                }
            ]
        }
    ]
}
```

---

### Example 4: Complex Expression Test

**Scenario:** Verify calculated totals match.

```json
{
    "actions": [
        {
            "method": "get",
            "url": "/api/order/123",
            "fields": [
                ["data.subtotal", "subtotal"],
                ["data.tax", "tax"],
                ["data.shipping", "shipping"]
            ],
            "tests": [
                {
                    "mode": "EXPR",
                    "key": "data.total",
                    "op": "==",
                    "expr": "${subtotal + tax + shipping}"
                }
            ]
        }
    ]
}
```

---

### Example 5: Array Comparison

**Scenario:** Verify two arrays have related sizes.

```json
{
    "actions": [
        {
            "method": "get",
            "url": "/api/users",
            "fields": [
                ["#data.active_users", "active_count"],
                ["#data.inactive_users", "inactive_count"]
            ],
            "tests": [
                {
                    "mode": "EXPR",
                    "key": "#data.all_users",
                    "op": "==",
                    "expr": "${active_count + inactive_count}"
                }
            ]
        }
    ]
}
```

---

### Example 6: Percentage Calculation

**Scenario:** Calculate and verify a percentage.

```json
{
    "actions": [
        {
            "method": "get",
            "url": "/api/stats",
            "fields": [
                ["data.success", "success_count"],
                ["data.total", "total_count"]
            ]
        },
        {
            "action": "set",
            "key": "success_rate",
            "value": "${(success_count * 100) / total_count}"
        },
        {
            "rem": "Verify success rate is at least 80%"
        },
        {
            "method": "get",
            "url": "/api/stats",
            "tests": [
                {
                    "mode": "EXPR",
                    "key": "${success_rate}",
                    "op": ">=",
                    "expr": 80
                }
            ]
        }
    ]
}
```

---

### Example 7: Dynamic Repeat Count

**Scenario:** Delete all items (count determined at runtime).

```json
{
    "actions": [
        {
            "method": "get",
            "url": "/api/items",
            "fields": [
                ["data[*].id", "item_ids"],
                ["#data", "item_count"]
            ]
        },
        {
            "method": "delete",
            "url": "/api/items/%(item_ids[inner_count])s",
            "repeat": "${item_count}"
        }
    ]
}
```

---

### Example 8: Boundary Testing

**Scenario:** Test array boundaries.

```json
{
    "actions": [
        {
            "method": "get",
            "url": "/api/products",
            "fields": [
                ["#data", "product_count"]
            ]
        },
        {
            "action": "set",
            "key": "last_index",
            "value": "${product_count - 1}"
        },
        {
            "rem": "Access last element"
        },
        {
            "method": "get",
            "url": "/api/products",
            "tests": [
                {
                    "field": "data[${last_index}]",
                    "mode": "EXISTS"
                },
                {
                    "field": "data[${product_count}]",
                    "mode": "NOT_EXISTS"
                }
            ]
        }
    ]
}
```

---

### Example 9: Multiple Length Extractions

**Scenario:** Extract multiple lengths in one request.

```json
{
    "method": "get",
    "url": "/api/dashboard",
    "fields": [
        ["#data.notifications", "notification_count"],
        ["#data.messages", "message_count"],
        ["#data.tasks", "task_count"],
        ["#data.alerts", "alert_count"]
    ],
    "tests": [
        {
            "field": "data.notifications",
            "mode": "SIZE-LTE",
            "value": 100
        },
        {
            "mode": "EXPR",
            "key": "${notification_count + message_count}",
            "op": "<=",
            "expr": 200
        }
    ]
}
```

---

### Example 10: Conditional Logic with Numbers

**Scenario:** Different behavior based on count.

```json
{
    "actions": [
        {
            "method": "get",
            "url": "/api/items",
            "fields": [
                ["#data", "count"]
            ]
        },
        {
            "action": "set",
            "key": "need_more",
            "value": "${10 - count}"
        },
        {
            "rem": "Create items to reach minimum of 10"
        },
        {
            "method": "post",
            "url": "/api/items",
            "body": {"name": "Auto-created item"},
            "repeat": "${need_more}",
            "skip": "${need_more <= 0}"
        }
    ]
}
```

---

### Example 11: Object Syntax for Fields

**Scenario:** Using the verbose object syntax for clarity.

```json
{
    "method": "get",
    "url": "/api/data",
    "fields": [
        {
            "path": "results.items",
            "mode": "length",
            "save": "items_length"
        },
        {
            "path": "results.items",
            "mode": "value",
            "save": "items_array"
        },
        {
            "path": "results.metadata",
            "mode": "keys",
            "save": "metadata_keys"
        },
        {
            "path": "results.items[0]",
            "mode": "type",
            "save": "first_item_type"
        }
    ]
}
```

---

### Example 12: Comparing Response Fields

**Scenario:** Verify relationship between two response fields.

```json
{
    "method": "get",
    "url": "/api/inventory",
    "tests": [
        {
            "rem": "Available should never exceed total"
        },
        {
            "mode": "EXPR",
            "key": "data.available",
            "op": "<=",
            "expr": "data.total"
        },
        {
            "rem": "Reserved + available should equal total"
        },
        {
            "mode": "EXPR",
            "key": "${data.reserved + data.available}",
            "op": "==",
            "expr": "data.total"
        }
    ]
}
```

Wait, the above syntax has issues. Let me clarify with correct syntax:

```json
{
    "method": "get",
    "url": "/api/inventory",
    "fields": [
        ["data.available", "available"],
        ["data.reserved", "reserved"],
        ["data.total", "total"]
    ],
    "tests": [
        {
            "mode": "EXPR",
            "key": "${available}",
            "op": "<=",
            "expr": "${total}"
        },
        {
            "mode": "EXPR",
            "key": "${reserved + available}",
            "op": "==",
            "expr": "${total}"
        }
    ]
}
```

---

### Example 13: Nested Array Length

**Scenario:** Check nested array sizes.

```json
{
    "method": "get",
    "url": "/api/categories",
    "fields": [
        ["#data", "category_count"],
        ["#data[0].products", "first_category_products"],
        ["#data[0].products[0].variants", "first_product_variants"]
    ],
    "tests": [
        {
            "mode": "EXPR",
            "key": "${first_category_products}",
            "op": ">",
            "expr": 0
        }
    ]
}
```

---

### Example 14: Modulo Operations

**Scenario:** Verify even distribution.

```json
{
    "actions": [
        {
            "method": "get",
            "url": "/api/teams",
            "fields": [
                ["#data.members", "member_count"],
                ["#data.teams", "team_count"]
            ]
        },
        {
            "action": "set",
            "key": "remainder",
            "value": "${member_count % team_count}"
        },
        {
            "action": "set",
            "key": "members_per_team",
            "value": "${member_count / team_count}"
        }
    ]
}
```

---

### Example 15: String Length

**Scenario:** Check string lengths.

```json
{
    "method": "get",
    "url": "/api/user/123",
    "fields": [
        ["#data.username", "username_length"],
        ["#data.bio", "bio_length"]
    ],
    "tests": [
        {
            "mode": "EXPR",
            "key": "${username_length}",
            "op": ">=",
            "expr": 3
        },
        {
            "mode": "EXPR",
            "key": "${username_length}",
            "op": "<=",
            "expr": 20
        },
        {
            "mode": "EXPR",
            "key": "${bio_length}",
            "op": "<=",
            "expr": 500
        }
    ]
}
```

---

## 8. Edge Cases and Error Handling

### 8.1 Division by Zero

```json
{
    "action": "set",
    "key": "result",
    "value": "${count / 0}"
}
```

**Error:** `ExpressionError: Division by zero in expression: count / 0`

### 8.2 Undefined Variable

```json
{
    "action": "set",
    "key": "result",
    "value": "${undefined_var + 5}"
}
```

**Error:** `ExpressionError: Undefined variable 'undefined_var' in expression`

### 8.3 Non-Numeric Variable

```json
{
    "action": "set",
    "key": "name",
    "value": "John"
},
{
    "action": "set",
    "key": "result",
    "value": "${name + 5}"
}
```

**Error:** `ExpressionError: Cannot perform arithmetic on non-numeric value 'John' (variable: name)`

### 8.4 Invalid Syntax

```json
{
    "action": "set",
    "key": "result",
    "value": "${5 + + 3}"
}
```

**Error:** `ExpressionError: Unexpected operator at position 4 in expression: 5 + + 3`

### 8.5 Unbalanced Parentheses

```json
{
    "action": "set",
    "key": "result",
    "value": "${(5 + 3}"
}
```

**Error:** `ExpressionError: Unbalanced parentheses in expression: (5 + 3`

### 8.6 Length of Non-Countable

```json
{
    "fields": [
        ["#data.count", "length_of_number"]
    ]
}
```

Where `data.count` is `42` (a number).

**Error:** `PathError: Cannot get length of number (at path: data.count)`

### 8.7 Empty Array Length

```json
{
    "fields": [
        ["#data.items", "count"]
    ]
}
```

Where `data.items` is `[]`.

**Result:** `count = 0` (this is valid, not an error)

### 8.8 Null Value Length

```json
{
    "fields": [
        ["#data.items", "count"]
    ]
}
```

Where `data.items` is `null`.

**Result:** `count = 0` (treat null as empty)

---

## 9. File Changes Summary

| File | Changes |
|------|---------|
| `lib/expr_parser.py` | **NEW** - Expression tokenizer, parser, evaluator |
| `lib/path_parser.py` | Add `#` prefix handling for length extraction |
| `lib/engine.py` | Modify `_expand_var()`, `fields()`, `_check()` to support expressions |
| `lib/parser.py` | Update `_method_set()` to handle expression values |
| `tests/test_expr_parser.py` | **NEW** - Unit tests for expression parser |
| `tests/test_number_ops.py` | **NEW** - Integration tests |

---

## 10. Backward Compatibility

All changes are **backward compatible**:

1. `${...}` syntax is opt-in - existing `%(var)s` syntax unchanged
2. `#` prefix is opt-in - regular paths work as before
3. Object syntax for fields is optional - array syntax still works
4. `EXPR` mode is new - existing modes unchanged
5. Literal values in tests still work - expressions are optional

---

## 11. Future Considerations

Features that could be added later (not in initial implementation):

1. **Math functions:** `${max(a, b)}`, `${min(a, b)}`, `${abs(x)}`
2. **String operations:** `${concat(a, b)}`, `${len(str)}`
3. **Conditional expressions:** `${a > b ? a : b}`
4. **Bitwise operations:** `${a & b}`, `${a | b}`
5. **Type coercion functions:** `${int(str)}`, `${str(num)}`
6. **Aggregate functions:** `${sum(array)}`, `${avg(array)}`

---

## 12. Glossary

| Term | Definition |
|------|------------|
| Expression | A string containing arithmetic operations: `${a + b}` |
| Length extraction | Using `#` prefix to get `len()` of array/string |
| EXPR mode | New test mode for expression-based comparisons |
| Variable reference | Referring to a stored variable by name in expression |

---

## Appendix A: Expression Parser Pseudocode

```python
class ExprParser:
    def __init__(self, expr: str, variables: dict):
        self.expr = expr
        self.variables = variables
        self.tokens = self._tokenize(expr)
        self.pos = 0

    def _tokenize(self, expr: str) -> list:
        """Convert expression string to token list."""
        # Returns: [("NUMBER", 5), ("OP", "+"), ("IDENT", "var"), ...]
        pass

    def parse(self) -> float:
        """Parse and evaluate the expression."""
        return self._expression()

    def _expression(self) -> float:
        """expression := term (('+' | '-') term)*"""
        result = self._term()
        while self._current_is("+", "-"):
            op = self._consume()
            right = self._term()
            result = self._apply_op(result, op, right)
        return result

    def _term(self) -> float:
        """term := factor (('*' | '/' | '%') factor)*"""
        result = self._factor()
        while self._current_is("*", "/", "%"):
            op = self._consume()
            right = self._factor()
            result = self._apply_op(result, op, right)
        return result

    def _factor(self) -> float:
        """factor := NUMBER | IDENTIFIER | '(' expression ')'"""
        if self._current_is_number():
            return self._consume_number()
        elif self._current_is_ident():
            var_name = self._consume_ident()
            return self._get_variable(var_name)
        elif self._current_is("("):
            self._consume()  # (
            result = self._expression()
            self._expect(")")
            return result
        else:
            raise ExpressionError(f"Unexpected token: {self._current()}")
```

---

## Appendix B: Quick Reference Card

### Setting Numeric Variables

```json
{"action": "set", "key": "count", "value": 10}
{"action": "set", "key": "sum", "value": "${a + b}"}
{"action": "set", "key": "diff", "value": "${a - b}"}
{"action": "set", "key": "product", "value": "${a * b}"}
{"action": "set", "key": "quotient", "value": "${a / b}"}
{"action": "set", "key": "remainder", "value": "${a % b}"}
{"action": "set", "key": "complex", "value": "${(a + b) * c}"}
```

### Extracting Lengths

```json
["#array_path", "var_name"]
{"path": "array_path", "mode": "length", "save": "var_name"}
```

### Expression Tests

```json
{"field": "path", "mode": "SIZE", "value": "${expected}"}
{"mode": "EXPR", "key": "path", "op": "==", "expr": "${calc}"}
{"mode": "EXPR", "key": "${var1}", "op": ">=", "expr": "${var2}"}
```

### Operators

| Op | Name | Example |
|----|------|---------|
| `+` | Add | `${a + 5}` |
| `-` | Subtract | `${a - 5}` |
| `*` | Multiply | `${a * 5}` |
| `/` | Divide | `${a / 5}` |
| `%` | Modulo | `${a % 5}` |
| `()` | Group | `${(a + b) * c}` |
