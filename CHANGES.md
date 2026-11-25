# RESTest Changes

## v2.6.0 - Skip Attribute Enhancement & Universal Expression Expansion

### Documentation

#### Code review TODO list
- Added `OPTIMIZE.md`: prioritized list of 26 bugs, refactors and quality improvements found during a full code review (no code changed)

### Bug Fixes

#### Low priority fixes from OPTIMIZE.md
- `restest.py`: removed the duplicated `parse_args()` call and the dead commented-out setup block; `--key` splits on the first `:` only (`--key url:http://x:8080` works) and a value without `:` is a usage error instead of a traceback
- `fields` and `dumps` share one code path (`_field_spec()` normalizes every entry to `(path, save key, mode)`, `_field_value()` extracts it):
  - `dumps` now accepts the same forms as `fields`: one item lists (crashed), `"*"`, objects with `path` / `save` / `mode`
  - `fields` objects also accept `field` as an alias of `path`; `"*"` honors `mode`
  - An unknown `mode`, or `length` / `type` / `keys` on a missing path, is reported as an error (unknown modes were silently treated as `value`; `length` of a missing path returned 13)
- `NOT_FOUND` is now a sentinel object compared with `is`: a response field holding the text `"__NOT_FOUND__"` is no longer treated as missing (it still prints as `__NOT_FOUND__`)
- Dead code removed: `_inner_count`, `utils.deepcopy` (uses `copy.deepcopy`), the second `skip` check in `_send_req` (already handled in `_actions`); the five identical `_method_get/post/put/patch/delete` are replaced by one dispatch on `HTTP_METHODS` in `_actions`
- Tests moved to `tests/` and run with pytest (`pytest.ini`, `requirements-dev.txt`); the `__main__` self-tests of `lib/expr_parser.py` and `lib/path_parser.py` became `tests/test_expr_parser.py` and `tests/test_path_parser.py`. Run: `python -m pytest`
- Docstrings added to the public engine / parser methods, the `_method_*` handlers and the `path_parser.py` functions
- Docs: `dumps` entry forms in chapter 03
- Files modified: `restest.py`, `lib/engine.py`, `lib/parser.py`, `lib/path_parser.py`, `lib/expr_parser.py`, `lib/utils.py`, `docs/chapters/03-making-requests.md`; files added: `pytest.ini`, `requirements-dev.txt`, `tests/test_low_fixes.py`, `tests/test_expr_parser.py`, `tests/test_path_parser.py`; `test_*.py` / `test_*.json` moved to `tests/`

#### Medium priority fixes from OPTIMIZE.md
- Test comparisons share one implementation (`OPERATOR_ALIASES`, `SIZE_MODES`, `_compare()`, `_to_number()`) for normal tests and `EXPR` tests
  - `GT` / `GTE` / `LT` / `LTE` now accept float strings (`"3.5"`) and numeric strings on the expected side; comparing text with a number is a test failure instead of a crash
  - `NOT_EQUAL` is now the exact negation of `EQUALS`: `"1"` vs `1` counts as equal (it passed `NOT_EQUAL` before)
- A missing field is reported as "FIELD: x missing" before the test runs (numeric modes crashed with `ValueError`); `NOT_EXISTS` / `NULL` modes now pass when the field is absent, as documented
- With `--dont-stop-on-error`, every test of an action runs and every failure is counted (it stopped at the first failure)
- Files opened for upload (`files`) are closed after each request
- Only endpoints starting with `http://` / `https://` are absolute: `/r?to=http://x` keeps the base URL
- Requests use `requests.request()`; unsupported HTTP methods and `content` values raise a clear error (unknown methods were sent as POST); unknown actions report their name instead of an `AttributeError`
- `system` accepts only documented options (unknown ones are ignored with a warning) so scripts cannot overwrite engine internals; `system.global_headers`, documented but silently ignored before, now works (`headers` override it); trailing `/` in `system.base_url` is removed
- The log file is opened once and kept open (flushed after each write, UTF-8), instead of being opened and chmod'ed for every fragment; `RESTest.close()` / `RESTestParser.close()` release it
- Files modified: `lib/engine.py`, `lib/parser.py`, `restest.py`, `test_high_fixes.py`, `docs/chapters/02-test-structure.md`; test added: `test_medium_fixes.py`

#### High priority fixes from OPTIMIZE.md
- **New `--allow-code` flag**: `code` actions (which `exec` arbitrary Python) are now disabled by default and stop the run with an explicit error unless `--allow-code` is given (BREAKING for scripts using `code`)
- `--delay` now sleeps the right amount: `500` was rounded down to 0s, `1500` to 1s
- A wrong status code is now an error also with `--dont-stop-on-error`: it is printed and counted in "Total Errors" (it was silently accepted); `max_time` violations go through the same path
- `${...}` and `%(var)s` are now expanded at any depth inside `body` / `params` (nested dicts and lists of lists were skipped or only half expanded)
- Library code no longer calls `sys.exit()`: errors raise `RESTestError` (new `lib/errors.py`) and `restest.py` prints them and exits with code 1; Ctrl+C exits with code 130 (it was 0 in `--step` mode)
- Network failures (`requests.RequestException`) always stop the run, also in `--quiet` mode (they crashed later with `AttributeError`); other unexpected exceptions are no longer hidden behind a generic "status: ERROR"
- Expression evaluation errors are built by a single `_eval_expression()` helper; the `${...}` regex is compiled once (`RX_EXPRESSION`)
- `_json_load` now reports a missing script file as a clean error (it was a raw traceback) and always closes the file
- `do_EXEC` no longer crashes when called without `files`
- Postman export: form requests (dict data) and JSON list bodies no longer crash, the `HEADERS` debug print is gone, the output file is properly closed
- Docs: `--allow-code` documented in chapters 06, 08 and `docs/llm.md`
- Files modified: `lib/engine.py`, `lib/parser.py`, `lib/postman_exp.py`, `restest.py`, docs; files added: `lib/errors.py`, `test_high_fixes.py`

#### Critical fixes from OPTIMIZE.md
- `if` action: the condition is now evaluated against the variable named in `field` and nested actions run only when it passes; removed the `---- IF RES:` debug print; it no longer aborts the whole run ("stopping on unhandled error")
- `--dry` mode no longer crashes with `'NoneType' object has no attribute 'status_code'`: requests print `DRY`, and `fields` / `tests` / `dumps` are skipped (variables from responses stay undefined in dry runs)
- `LTE` (`<=`) and `SIZE-LTE` (`()<=`) checks had inverted logic and failed on passing values
- Response time now uses `elapsed.total_seconds()`: before, whole seconds were dropped (2.3s logged as 300ms) and `max_time` never fired for slow requests
- Files modified: `lib/engine.py`, `lib/parser.py`, `test_security_fixes.py` (fake response uses a real `timedelta`); test added: `test_critical_fixes.py`

#### Log file permissions
- The log file is now created and truncated with `0o600` permissions (owner read/write only), also when it already existed
- The log file handle is now closed after every write (it was leaked before)
- Request and response bodies in the log are unchanged
- File modified: `lib/engine.py`; test added in `test_security_fixes.py`

#### Authorization masked in log files
- `Authorization`, `Proxy-Authorization` and the configured authorization header are masked in the log file (request headers and CURL line): first and last 4 chars kept, short values fully hidden
- The curl dumped on the console (`dump_curl_on_console`) is left unmasked so it can be copy-pasted
- File modified: `lib/engine.py`; tests added in `test_security_fixes.py`

#### Low-risk security fixes
- `OBJECT` check mode no longer uses `eval()`: values are parsed with `json.loads()` or `ast.literal_eval()` (no code execution)
- `--env-save` now writes the file with `0o600` permissions
- Bare `except:` replaced with specific exceptions in `_log_curl`, `_is_int`, `--env-load` (which now prints a warning) and the Authorization template
- `_expand_var` failures now exit with code 1 instead of 0
- `.gitignore` now excludes `.env`, `*.env` and `.dev.vars`
- Files modified: `lib/engine.py`, `lib/path_parser.py`, `restest.py`, `.gitignore`; test added: `test_security_fixes.py`

#### Actions inside a section executed twice
- Fixed a bug where actions nested in a `section` were run twice
- Root cause: `_method_section` ran its own `actions`, then the generic loop in `_actions` ran them again
- Fix (commit 3e20827): nested `actions` are no longer re-run for actions that handle them themselves (`section`, `if`)
- Regression test added: `test_section_once.py`

#### Boolean and numeric type preservation in request data
- Fixed a bug where boolean values (`true`/`false`) in JSON request data were being sent as Python-style strings (`"True"`/`"False"`) instead of proper JSON booleans
- Root cause: `_get_v()` unconditionally called `str()` on all non-dict values, converting `False` → `"False"` and `True` → `"True"`
- Fix: non-string primitive types (bool, int, float, None) are now returned as-is without string conversion
- This also prevents unnecessary conversion of numeric values to strings when no variable expansion is needed
- File modified: `lib/engine.py`

### New Features

#### Universal Expression Expansion
- **All fields** now support `${...}` expression syntax, not just `set` and test actions
- Expressions are automatically expanded everywhere: URLs, headers, cookies, POST data, field values, etc.
- **Undefined variables auto-initialize to 0**: No need to pre-initialize counters or numeric variables
- Works in string interpolation: `"user_${counter}"` → `"user_0"` (counter auto-initialized)
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
- Files modified: `lib/engine.py`, `lib/expr_parser.py`
- Test files added: `test_expr_expansion.py`, `test_expr_integration.json`, `test_undefined_counter.json`

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
