# RESTest v2.5.0 - Number Operations, Interactive Debugging, and Documentation Overhaul

This release introduces powerful new features for arithmetic expressions,
interactive debugging, and significantly improved documentation coverage.

## New Features

### Number Operations & Expression Parser
- New expression syntax `${...}` for arithmetic operations
- Supported operators: +, -, *, /, % (modulo) with proper precedence
- Parentheses support for grouping: `${(a + b) * 2}`
- Length extraction with `#` prefix: `#data.items` returns array length
- New EXPR test mode for expression-based comparisons
- Field extraction modes: value, length, type, keys
- Safe evaluation without Python's eval()

### Interactive Debugging
- `--step` flag: execute one action at a time, wait for ENTER
- `break` attribute: set breakpoints on individual actions
- `--no-break` flag: ignore all break attributes (for CI/CD)
- Automatic variable dump at each breakpoint/step
- Colored output: yellow headers, green variable names, white values

### Environment & Configuration
- `--env-cf` flag: load variables from Cloudflare .dev.vars format
- `--debug-file-name` flag: log executing JSON file names
- `show_filename` attribute for include action (opt-in filename display)

### Request Enhancements
- `__direct__` key: send raw arrays/values as request body
- Enhanced dump action: optional fields, default print=true
- Colored console output for dump action

## Documentation

### Newly Documented Features
- `copy` action for variable duplication
- `rem`/`remark` action for inline comments
- `if` action with all conditional modes (EQUALS, GT, LT, CONTAINS, etc.)
- `skip` attribute to conditionally skip requests
- `no_cookies` attribute to disable session cookies
- `dumps` attribute for debugging response fields
- `data`/`params` as aliases for `body`
- `status` as alias for `status_code`
- `save` field in tests to capture values
- `title` field in tests for descriptions
- `%(counter)s` variable for repeat loops
- System `cookies` configuration
- `authorization_header` and `authorization_template` options
- Compressed file support (.gz, .bz2)

### Updated Documentation
- New Appendix C: Number Operations (comprehensive guide)
- Updated command-line reference with all new flags
- Updated test modes reference with EXPR mode
- Version number updated to v2.5.0

## Files Changed
- lib/expr_parser.py (new): Expression tokenizer, parser, evaluator
- lib/path_parser.py: Added # prefix handling
- lib/engine.py: Expression support, enhanced dump, field modes
- lib/parser.py: Step mode, break attribute, show_filename
- restest.py: New CLI flags (--step, --no-break, --env-cf, --debug-file-name)
- docs/chapters/*.md: Comprehensive documentation updates

## Breaking Changes
None - all changes are backwards compatible.
