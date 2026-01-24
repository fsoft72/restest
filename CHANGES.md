# RESTest Changes

## v2.6.0 - Skip Attribute Enhancement & Universal Expression Expansion

### New Features

#### Universal Expression Expansion
- **All fields** now support `${...}` expression syntax, not just `set` and test actions
- Expressions are automatically expanded everywhere: URLs, headers, cookies, POST data, field values, etc.
- Works in string interpolation: `"user_${counter}"` → `"user_1"`
- Works with multiple expressions: `"/users/${user_id}/posts/${post_id}"` → `"/users/123/posts/456"`
- Works as pure expressions: `"${a + b}"` → `15` (returns numeric value)
- Combines seamlessly with variable substitution: `"%(prefix)s_v${version}"` → `"api_v2"`
- Supported operations: `+`, `-`, `*`, `/`, `%` (modulo), parentheses
- Examples:
  ```json
  {
    "action": "set",
    "key": "offset",
    "value": "${(page - 1) * per_page}"
  }
  ```
  ```json
  {
    "method": "get",
    "url": "/api/v${version}/users/${user_id}",
    "headers": {
      "X-Request-ID": "req_${counter}"
    }
  }
  ```
  ```json
  {
    "method": "post",
    "url": "/users",
    "data": {
      "username": "user_${counter}",
      "age": "${base_age + years}"
    }
  }
  ```
- Files modified: `lib/engine.py`
- Test files added: `test_expr_expansion.py`, `test_expr_integration.json`

### Enhancements

#### Skip Attribute for All Actions
- The `skip` attribute now works for ALL action types, not just HTTP requests
- Previously only worked for GET, POST, PUT, PATCH, DELETE actions
- Now also skips: `include`, `section`, `batch_exec`, `copy`, `dump`, `set`, `code`, `sleep`, `if`, `rem`, etc.
- Skip check is performed at the top level before any action processing
- Displays yellow "SKIP" message in console (unless `--quiet` flag is used)
- Example:
  ```json
  {
    "action": "include",
    "filename": "./optional-tests.json",
    "exec": true,
    "skip": true
  }
  ```
- File modified: `lib/parser.py`

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

#### Break Attribute
- Added optional `break` attribute for individual actions
- When `break: true` is set on an action, execution pauses after that action
- Dumps all variables in memory and waits for ENTER to continue
- Works independently of `--step` flag (can be used without it)
- Useful for setting breakpoints at specific actions during debugging
- Added `--no-break` flag to ignore all `break` attributes in actions
  - Useful when running tests in CI/CD or automated environments
  - Does not affect `--step` mode (step mode always pauses)
- Example:
  ```json
  {
    "title": "Check this action",
    "method": "get",
    "url": "/endpoint",
    "break": true
  }
  ```
- Files modified: `restest.py`, `lib/parser.py`

#### Include Action Enhancement
- `include` action can now display the included filename in console
- New `show_filename` attribute: set to `true` to enable filename display
- By default, filenames are not displayed (silent include)
- Very visible output with colored borders when enabled:
  - Cyan borders (80 characters wide)
  - "INCLUDING FILE:" header in white on blue background (bold)
  - Filename in yellow (bold)
- Helps identify which files are being loaded during test execution
- Example:
  ```json
  {
    "action": "include",
    "filename": "./auth/login.json",
    "exec": true,
    "show_filename": true
  }
  ```
- File modified: `lib/parser.py`

#### LLM Documentation
- Added `docs/llm.md` - Comprehensive but concise reference for LLMs
- Covers all RESTest features in a format optimized for AI assistants
- Includes quick reference tables, syntax examples, and a complete test example
