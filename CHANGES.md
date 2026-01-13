# RESTest Changes

## v2.5.0 - Number Operations Feature

### New Features

#### Expression Parser (`lib/expr_parser.py`)
- New standalone expression parser supporting arithmetic operations
- Supported operators: `+`, `-`, `*`, `/`, `%` (modulo)
- Parentheses for grouping: `${(a + b) * c}`
- Variable references from globals
- Expression syntax: `${expression}`

#### Length Extraction (`lib/path_parser.py`)
- Added `#` prefix for automatic length extraction
- `#path.to.array` returns the length of the array
- Works with arrays, strings, and objects (returns key count)
- Returns 0 for null/missing values

#### Expression Support in Engine (`lib/engine.py`)
- `set` action now evaluates expressions: `{"action": "set", "key": "sum", "value": "${a + b}"}`
- `fields` extraction supports object syntax with modes:
  - `{"path": "...", "mode": "length", "save": "..."}` - extract length
  - `{"path": "...", "mode": "type", "save": "..."}` - extract type name
  - `{"path": "...", "mode": "keys", "save": "..."}` - extract object keys
  - `{"path": "...", "mode": "value", "save": "..."}` - extract value (default)
- Test values can be expressions: `{"field": "items", "mode": "SIZE", "value": "${expected_count}"}`
- New `EXPR` test mode for expression-based comparisons:
  ```json
  {
      "mode": "EXPR",
      "key": "#data.items",
      "op": "==",
      "expr": "${expected_count}"
  }
  ```

### Files Added
- `lib/expr_parser.py` - Expression tokenizer, parser, and evaluator
- `number_operations.md` - Feature specification document
- `test_number_ops.py` - Unit tests for the new features

### Files Modified
- `lib/path_parser.py` - Added `#` prefix handling in `expand_value()`
- `lib/engine.py` - Added expression support in `set_val()`, `fields()`, `_check()`, and new `_check_expr()` method
- `lib/engine.py` - Enhanced `dump()` method: `fields` now optional (dumps all if omitted), `print` defaults to `true`, improved console output with colored formatting (green labels, white values, no "====" prefix)
- `lib/parser.py` - Updated `_method_dump()` to support optional fields and default print behavior

#### Step Mode
- Added `--step` command line flag to execute one action at a time
- When enabled, waits for user to press ENTER before executing the next action
- Automatically dumps all variables in memory before each prompt
- Shows variable names in green and values in white for easy reading
- Useful for debugging and interactive test execution
- Supports Ctrl+C to interrupt execution gracefully
- Files modified: `restest.py`, `lib/parser.py`
