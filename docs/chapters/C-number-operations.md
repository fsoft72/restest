# Number Operations and Expressions

This chapter covers RESTest's number operations feature, including arithmetic expressions, length extraction, and expression-based testing.

## Overview

Starting with version 2.5.0, RESTest supports:
- Arithmetic expressions with `+`, `-`, `*`, `/`, `%` operators
- Length extraction from arrays, strings, and objects
- Expression-based comparisons in tests
- Numeric variable operations without using Python's `eval()`

## Expression Syntax

Expressions use the `${...}` syntax to distinguish them from regular variable references.

### Basic Expression Format
```json
{
    "action": "set",
    "key": "result",
    "value": "${a + b}"
}
```

### Supported Operators

| Operator | Description | Example | Result (a=10, b=5) |
|----------|-------------|---------|---------------------|
| `+` | Addition | `${a + b}` | 15 |
| `-` | Subtraction | `${a - b}` | 5 |
| `*` | Multiplication | `${a * b}` | 50 |
| `/` | Division (integer) | `${a / b}` | 2 |
| `%` | Modulo | `${a % b}` | 0 |
| `()` | Grouping | `${(a + b) * 2}` | 30 |

### Operator Precedence

Expressions follow standard mathematical operator precedence:
1. Parentheses `()`
2. Multiplication `*`, Division `/`, Modulo `%`
3. Addition `+`, Subtraction `-`

```json
{
    "action": "set",
    "key": "result1",
    "value": "${a + b * 2}"   // Result: 20 (b*2 first, then +a)
}
```

```json
{
    "action": "set",
    "key": "result2",
    "value": "${(a + b) * 2}" // Result: 30 (a+b first, then *2)
}
```

## Setting Numeric Variables

### Using Expressions in Set Action

```json
{
    "actions": [
        {
            "action": "set",
            "key": "price",
            "value": 100
        },
        {
            "action": "set",
            "key": "quantity",
            "value": 5
        },
        {
            "action": "set",
            "key": "total",
            "value": "${price * quantity}"
        }
    ]
}
```

### Complex Calculations

```json
{
    "actions": [
        {
            "action": "set",
            "key": "subtotal",
            "value": "${price * quantity}"
        },
        {
            "action": "set",
            "key": "tax",
            "value": "${subtotal * 8 / 100}"  // 8% tax
        },
        {
            "action": "set",
            "key": "total",
            "value": "${subtotal + tax}"
        }
    ]
}
```

## Length Extraction

Extract the length of arrays, strings, or object key counts using the `#` prefix.

### Array Length with # Prefix

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

**Response:**
```json
{
    "data": {
        "users": [
            {"name": "Alice", "permissions": ["read", "write"]},
            {"name": "Bob", "permissions": ["read"]}
        ]
    }
}
```

**Result:**
- `user_count` = 2
- `first_user_perms_count` = 2

### String Length

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
        }
    ]
}
```

### Object Key Count

```json
{
    "method": "get",
    "url": "/api/config",
    "fields": [
        ["#settings", "setting_count"]
    ]
}
```

**Response:**
```json
{
    "settings": {
        "timeout": 30,
        "retries": 3,
        "verbose": true
    }
}
```

**Result:** `setting_count` = 3

### Object Syntax for Fields

Use the extended object syntax for more control:

```json
{
    "method": "get",
    "url": "/api/data",
    "fields": [
        {
            "path": "results.items",
            "mode": "length",
            "save": "items_count"
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

**Field Modes:**
- `value` (default): Extract the value as-is
- `length`: Extract `len()` of array/string/object
- `type`: Extract type name ("array", "object", "string", "number", "null")
- `keys`: Extract object keys as array (objects only)

## Expressions in Tests

### Using Expressions in Test Values

Traditional test modes now support expressions in the `value` field:

```json
{
    "method": "get",
    "url": "/api/items",
    "fields": [
        ["#data", "expected_count"]
    ],
    "tests": [
        {
            "field": "data",
            "mode": "SIZE",
            "value": "${expected_count}"
        }
    ]
}
```

### SIZE Mode with Expressions

```json
{
    "actions": [
        {
            "action": "set",
            "key": "page_size",
            "value": 20
        },
        {
            "method": "get",
            "url": "/api/items?limit=%(page_size)s",
            "tests": [
                {
                    "field": "items",
                    "mode": "SIZE-LTE",
                    "value": "${page_size}"
                }
            ]
        }
    ]
}
```

## EXPR Test Mode

The new `EXPR` mode enables expression-based comparisons.

### EXPR Mode Syntax

```json
{
    "mode": "EXPR",
    "key": "path.to.value",
    "op": "==",
    "expr": "${expression_or_value}"
}
```

**Fields:**
- `mode`: Must be "EXPR" or "EXPRESSION"
- `key`: Path to value in response (supports `#` prefix for length)
- `op`: Comparison operator
- `expr`: Expression or literal value to compare against

**Supported Operators:**
- `==`, `=`, `EQUALS`, `EQUAL` - Equal to
- `!=`, `<>`, `NOT_EQUALS`, `NOT_EQUAL` - Not equal to
- `>`, `GT` - Greater than
- `>=`, `GTE` - Greater than or equal
- `<`, `LT` - Less than
- `<=`, `LTE` - Less than or equal

### Basic EXPR Examples

#### Comparing Length to Variable
```json
{
    "method": "get",
    "url": "/api/users",
    "fields": [
        ["data.total", "expected_total"]
    ],
    "tests": [
        {
            "mode": "EXPR",
            "key": "#data.users",
            "op": "==",
            "expr": "${expected_total}"
        }
    ]
}
```

#### Comparing to Literal Value
```json
{
    "tests": [
        {
            "mode": "EXPR",
            "key": "#data.items",
            "op": ">=",
            "expr": 10
        }
    ]
}
```

#### Comparing with Expression
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
            "key": "${available + reserved}",
            "op": "==",
            "expr": "${total}"
        }
    ]
}
```

## Complete Examples

### Pagination with Counts

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
            "method": "get",
            "url": "/api/items?limit=%(page_size)s&offset=%(second_page_offset)s",
            "fields": [
                ["#data.items", "second_page_count"]
            ]
        },
        {
            "action": "set",
            "key": "fetched_total",
            "value": "${first_page_count + second_page_count}"
        }
    ]
}
```

### Creating Items and Verifying Count

```json
{
    "actions": [
        {
            "method": "get",
            "url": "/api/items",
            "fields": [
                ["#data", "initial_count"]
            ]
        },
        {
            "method": "post",
            "url": "/api/items",
            "body": {"name": "Item 1"},
            "repeat": 3
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

### Validating Calculated Totals

```json
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
```

### Percentage Calculations

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

### Boundary Testing

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

### Conditional Logic with Numbers

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
            "method": "post",
            "url": "/api/items",
            "body": {"name": "Auto-created item"},
            "repeat": "${need_more}",
            "skip": "${need_more <= 0}"
        }
    ]
}
```

## Error Handling

### Division by Zero

```json
{
    "action": "set",
    "key": "result",
    "value": "${count / 0}"
}
```

**Error:** `ExpressionError: Division by zero in expression: count / 0`

### Undefined Variable

```json
{
    "action": "set",
    "key": "result",
    "value": "${undefined_var + 5}"
}
```

**Error:** `ExpressionError: Undefined variable 'undefined_var' in expression`

### Non-Numeric Variable

```json
{
    "actions": [
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
    ]
}
```

**Error:** `ExpressionError: Cannot perform arithmetic on non-numeric value 'John' (variable: name)`

### Length of Non-Countable

```json
{
    "fields": [
        ["#data.count", "length_of_number"]
    ]
}
```

Where `data.count` is `42` (a number).

**Error:** `PathError: Cannot get length of int (at path: data.count)`

## Best Practices

### 1. Variable Naming
Use descriptive names that indicate the variable contains a number:

```json
{
    "action": "set",
    "key": "item_count",        // Good
    "value": "${items_length}"
}
```

```json
{
    "action": "set",
    "key": "x",                  // Avoid
    "value": "${y + z}"
}
```

### 2. Extract First, Calculate Second
Extract values from responses before using them in expressions:

```json
{
    "actions": [
        {
            "method": "get",
            "url": "/api/data",
            "fields": [
                ["#items", "count"],
                ["price", "unit_price"]
            ]
        },
        {
            "action": "set",
            "key": "total",
            "value": "${count * unit_price}"
        }
    ]
}
```

### 3. Use Expressions in Tests
Prefer expressions in tests over hardcoded values when possible:

```json
// ✅ Good - Dynamic
{
    "tests": [
        {
            "field": "items",
            "mode": "SIZE",
            "value": "${expected_count}"
        }
    ]
}
```

```json
// ❌ Avoid - Hardcoded
{
    "tests": [
        {
            "field": "items",
            "mode": "SIZE",
            "value": 5
        }
    ]
}
```

### 4. Comment Complex Calculations
Use `"rem"` actions to document complex expressions:

```json
{
    "actions": [
        {
            "rem": "Calculate total with 8% tax and $5 shipping"
        },
        {
            "action": "set",
            "key": "subtotal",
            "value": "${price * quantity}"
        },
        {
            "action": "set",
            "key": "tax",
            "value": "${subtotal * 8 / 100}"
        },
        {
            "action": "set",
            "key": "total",
            "value": "${subtotal + tax + 5}"
        }
    ]
}
```

### 5. Handle Edge Cases
Always consider zero counts and null values:

```json
{
    "method": "get",
    "url": "/api/items",
    "fields": [
        ["#data.items", "count"]
    ],
    "tests": [
        {
            "mode": "EXPR",
            "key": "${count}",
            "op": ">=",
            "expr": 0
        }
    ]
}
```

## Troubleshooting

### Expression Not Evaluating

**Problem:** Variable shows literal expression instead of result
```json
{
    "action": "set",
    "key": "sum",
    "value": "a + b"  // Missing ${}
}
```

**Solution:** Use proper expression syntax
```json
{
    "action": "set",
    "key": "sum",
    "value": "${a + b}"
}
```

### Cannot Use Response Fields Directly in Expressions

**Problem:** Trying to reference response fields in expressions without extraction
```json
{
    "tests": [
        {
            "mode": "EXPR",
            "key": "total",
            "op": "==",
            "expr": "${subtotal + tax}"  // subtotal/tax not extracted yet
        }
    ]
}
```

**Solution:** Extract fields first
```json
{
    "fields": [
        ["subtotal", "subtotal"],
        ["tax", "tax"]
    ],
    "tests": [
        {
            "mode": "EXPR",
            "key": "total",
            "op": "==",
            "expr": "${subtotal + tax}"
        }
    ]
}
```

### Wrong Operator Precedence

**Problem:** Unexpected calculation results
```json
{
    "value": "${10 + 5 * 2}"  // Result: 20, expected 30
}
```

**Solution:** Use parentheses to control order
```json
{
    "value": "${(10 + 5) * 2}"  // Result: 30
}
```

## Technical Details

### Expression Parser
- Custom recursive descent parser (no `eval()`)
- Full operator precedence support
- Safe evaluation with clear error messages
- Supports integers and floating-point numbers

### Type Handling
- Numbers stored as `int` or `float`
- Automatic type conversion for arithmetic
- String-to-number conversion when needed
- Integer division when both operands are integers

### Security
- No use of Python's `eval()` or `exec()`
- Sandboxed expression evaluation
- Only arithmetic operations allowed
- No access to system functions
