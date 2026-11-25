# Optimization TODO

> Generated on 2026-11-25. Items sorted by importance.

## Critical

- [ ] **`if` action always aborts the run** - `_method_if` ignores the `_check` result (nested actions run whether the condition passes or not), prints a leftover debug line (`---- IF RES:`), and returns `None`, so `_actions` treats it as failed and calls `sys.exit(1)`. Verified: any script with an `if` action exits with "stopping on unhandled error". Run nested actions only when `err` is falsy, remove the print, return `True`.
  - File(s): `lib/parser.py` (`_method_if`, `_actions`)

- [ ] **`--dry` mode crashes on every request** - `_req` returns `None` in dry mode, then `_send_req` calls `res.status_code` / `len(res.content)`, raising `AttributeError`, which is caught and turned into "status: ERROR" + exit. Verified with `--dry --auth-mode no`. Short-circuit in `_send_req` when `res is None` (end timings with a placeholder status, skip `fields` / `tests` / `dumps` in `_method_exec`).
  - File(s): `lib/parser.py` (`_send_req`, `_method_exec`), `lib/engine.py` (`_req`)

- [ ] **`LTE` and `SIZE-LTE` checks have inverted logic** - `LTE` fails when `current_val <= expected_val` (the passing case) and `SIZE-LTE` fails when `len <= expected`. Both conditions should be `>`. Any test using `<=` / `()<=` currently reports the opposite result.
  - File(s): `lib/engine.py` (`_check`, lines ~882-898)

- [ ] **Response time ignores whole seconds** - `r.elapsed.microseconds / 1000` drops the seconds component, so a 2.3s request is logged as 300ms and `max_time` (`max_exec_time`) never triggers for slow calls. Use `r.elapsed.total_seconds() * 1000`.
  - File(s): `lib/engine.py` (`_req`, `_log_resp`)

## High

- [ ] **`delay` option sleeps 0 seconds for values < 1000ms** - `time.sleep(self.delay // 1000)` uses integer division, so `--delay 500` does nothing and `--delay 1500` sleeps 1s. Use `self.delay / 1000`.
  - File(s): `lib/engine.py` (`do_EXEC`)

- [ ] **Status-code mismatch not counted as error when not stopping** - With `--dont-stop-on-error`, a wrong status code in `_req` is silently accepted (no message, no `_errors += 1`), so the final "Total Errors" line under-reports. Route the mismatch through `self._error(...)`.
  - File(s): `lib/engine.py` (`_req`)

- [ ] **Library code calls `sys.exit` everywhere** - The engine and parser exit the process from ~20 places (`_expand_expressions`, `_expand_var`, `_req`, `_error`, `_resolve_fname`, `_json_load`, ...). This makes the engine impossible to embed or unit-test without catching `SystemExit`, and loses tracebacks. Introduce a `RESTestError` exception hierarchy, raise it in `lib/`, and convert to exit code only in `restest.py:main`.
  - File(s): `lib/engine.py`, `lib/parser.py`, `restest.py`

- [ ] **Nested dict values skip `${...}` expansion** - `_expand_dict` only expands strings containing `%(`, so `{"body": {"user": {"id": "${n + 1}"}}}` is sent literally, while the same expression at top level is evaluated. `_expand_list` also ignores nested lists. Make both delegate every string to `_get_v` and recurse on lists.
  - File(s): `lib/engine.py` (`_expand_dict`, `_expand_list`)

- [ ] **`code` action runs arbitrary Python via `exec`** - `_method_code` interpolates globals (which may come from HTTP responses) into a string and `exec`s it with full access. A malicious API response saved via `fields` can inject code. Either remove the action, gate it behind an explicit `--allow-code` flag, or at minimum pass the values as locals instead of string-formatting them into source.
  - File(s): `lib/parser.py` (`_method_code`)

- [ ] **Postman export breaks on form content and leaks debug output** - `PostmanExporterItem` calls `json.loads(data)` but `data` is a `dict` for `content: "form"` requests (TypeError). `_parse_headers` prints a `***** HEADERS *****` debug block on every request, and `save()` never closes the file. Accept dicts, drop the print, use `with open(...)`.
  - File(s): `lib/postman_exp.py`

## Medium

- [ ] **Duplicated comparison logic in `_check` and `_check_expr`** - Two separate implementations of `==`, `!=`, `>`, `>=`, `<`, `<=` with different numeric coercion rules (`_check` uses `int()` and crashes on `"3.5"`, `_check_expr` handles floats). Extract a single `OPERATORS` table (alias -> callable) plus one `_to_number` helper used by both; this also eliminates the class of bug in the `LTE` item above.
  - File(s): `lib/engine.py` (`_check`, `_check_expr`)

- [ ] **`_check` runs before the "not found" guard** - `check()` calls `_check(chk, field, v)` before testing `v == "__NOT_FOUND__"`, so numeric modes try `int("__NOT_FOUND__")` and raise `ValueError` instead of the clear "FIELD missing" message. Move the guard above the call.
  - File(s): `lib/engine.py` (`check`)

- [ ] **`check()` stops at the first failing test even when not stopping on error** - `return self._error(...)` exits the loop, so with `--dont-stop-on-error` the remaining tests of that action are never run or counted. Use `self._error(...); continue`.
  - File(s): `lib/engine.py` (`check`)

- [ ] **Uploaded files are never closed** - `_parse_files` opens every file with `open(..., "rb")` and nothing closes them; with `repeat` this leaks a descriptor per iteration. It also runs before the per-request skip check. Close them in a `finally` in `_method_exec` (or use `contextlib.ExitStack`).
  - File(s): `lib/parser.py` (`_parse_files`, `_send_req`)

- [ ] **Failed requests in quiet mode crash later** - In `_send_req` the `except Exception` block exits only when `not self.quiet`; in quiet mode it returns `None`, and `_method_exec` then calls `self.rt.fields(None, ...)` -> `AttributeError`. The broad `except` also hides real bugs as "status: ERROR". Catch `requests.RequestException` only and always fail the same way regardless of `quiet`.
  - File(s): `lib/parser.py` (`_send_req`, `_method_exec`)

- [ ] **Absolute URL detection matches anywhere in the string** - `_resolve_url` uses `endpoint.lower().find("http:") != -1`, so `/redirect?to=http://x` is treated as absolute and the base URL is dropped. Use `startswith(("http://", "https://"))`.
  - File(s): `lib/engine.py` (`_resolve_url`)

- [ ] **Unknown HTTP methods silently become POST** - The `if/elif` chain in `_req` falls back to `obj.post` for anything else (`HEAD`, `OPTIONS`, typos). Use `obj.request(mode, ...)` and validate the method name. Likewise `_actions` uses `getattr(self, "_method_" + action)`, which raises a raw `AttributeError` on an unknown action; report a clear "unknown action 'xxx'" error instead.
  - File(s): `lib/engine.py` (`_req`), `lib/parser.py` (`_actions`)

- [ ] **`system` block can overwrite any engine attribute** - `_parse_system` does `setattr(self.rt, k, v)` for every key, so a script with `"system": {"session": 1}` or `"globals": ...` silently breaks the engine. Whitelist the supported keys (`base_url`, `log_file`, `stop_on_error`, `authorization_header`, `authorization_template`, `headers`, ...) and warn on the rest.
  - File(s): `lib/parser.py` (`_parse_system`)

- [ ] **Log file reopened and chmod'ed on every write** - `_log_write` opens, chmods and closes the log for each fragment; a single request triggers 4+ open/close cycles. Open the handle once (lazily) and close it at the end of the run.
  - File(s): `lib/engine.py` (`_log_write`, `_open_log`)

- [ ] **`_expand_expressions` duplicates its error handling and re-imports inline** - The pure-expression branch and `replace_expr` contain identical error blocks; `import re` and `from .expr_parser import ...` are done inside the function although `evaluate_expr` is already imported at the top. Compile the `${...}` regex once as a module constant and extract a single `_eval_or_die(expr, value)` helper.
  - File(s): `lib/engine.py` (`_expand_expressions`)

## Low / Nice to have

- [ ] **Dead and duplicated code in `restest.py`** - `parser.parse_args()` is called twice, a commented-out copy of the setup block lives in a stray string literal, and `--key` uses `c.split(":")`, which crashes on values containing `:` (URLs, tokens). Remove the dead code and use `split(":", 1)`.
  - File(s): `restest.py` (`main`)

- [ ] **Repeated `fields()` branches and inconsistent `dumps()` keys** - The `"*"` handling is copy-pasted three times; `fields()` uses `path`/`save` for the object form while `dumps()` uses `field`. Normalize each spec to `(json_key, glob_key, mode)` first, then run one code path; accept the same keys in both.
  - File(s): `lib/engine.py` (`fields`, `dumps`)

- [ ] **Magic sentinel string `"__NOT_FOUND__"`** - Used in four places across `fields`, `check`, `dump`, `_expand_value`. Replace with a module-level `NOT_FOUND = object()` sentinel (or a constant) to avoid collisions with real data.
  - File(s): `lib/engine.py`

- [ ] **Unused / trivial helpers and dead variables** - `_expand_var` builds a `globs` copy with `inner_count` that is never used; `utils.deepcopy` just wraps `copy.deepcopy`; `_send_req` re-checks `skip` already handled in `_actions`; five `_method_get/post/put/patch/delete` methods are identical apart from the default. Remove dead code and register the HTTP verbs from one loop or a dict.
  - File(s): `lib/engine.py`, `lib/parser.py`, `lib/utils.py`

- [ ] **Tests scattered and partly inside `__main__` blocks** - `test_*.py` live at the repo root, and the expression / path-parser tests exist only as `print("PASS"/"FAIL")` scripts in `__main__`. Move everything to a `tests/` folder under pytest so regressions like the `LTE` and `if` bugs above get caught automatically.
  - File(s): `lib/expr_parser.py`, `lib/path_parser.py`, `test_*.py`

- [ ] **Missing docstrings on public engine/parser methods** - `RESTest.__init__`, `do_EXEC`, `check`, `dumps`, `copy_val`, `sleep`, `section_start`, `RESTestParser.open`, all `_method_*` handlers, and every function in `path_parser.py` lack docstrings, while newer code is documented.
  - File(s): `lib/engine.py`, `lib/parser.py`, `lib/path_parser.py`
