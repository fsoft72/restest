#!/usr/bin/env python3
#
# restest engine
#
# written by Fabio Rotondo (fabio.rotondo@gmail.com)
#

import ast
import json
import operator
import os
import re
import sys
import time
import urllib

import requests

from .path_parser import expand_value
from .cols import xcolored as _c
from .errors import RESTestError
from .expr_parser import evaluate_expr, is_expression, ExpressionError

# Matches a ${...} expression inside a string
RX_EXPRESSION = re.compile(r"\$\{([^}]+)\}")

# HTTP methods accepted by _req
HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")

class _NotFound:
    """Type of the NOT_FOUND sentinel: prints as before, never equals real data."""

    def __repr__(self):
        return "__NOT_FOUND__"

    __str__ = __repr__


# Sentinel returned by _expand_value when a path is not found in the response.
# Always compare it with "is": a response may legitimately contain "__NOT_FOUND__"
NOT_FOUND = _NotFound()

# Modes accepted by the object form of "fields" / "dumps"
FIELD_MODES = ("value", "length", "type", "keys")

# Test modes checking that a field has a value
EXISTS_MODES = ("EXISTS", "EXIST", "!!", "NOT_NULL", "IS_NOT_NULL")

# Test modes checking that a field is null (a missing field counts as null)
NULL_MODES = ("EMPTY", "IS_EMPTY", "IS_NULL", "NULL", "NOT_EXISTS", "NOT_EXIST", "@")

# Test modes / EXPR operators (any case) -> canonical comparison operator
OPERATOR_ALIASES = {
    "==": "==", "=": "==", "EQUALS": "==", "EQUAL": "==",
    "!=": "!=", "<>": "!=", "NOT_EQUALS": "!=", "NOT_EQUAL": "!=",
    ">": ">", "GT": ">",
    ">=": ">=", "GTE": ">=",
    "<": "<", "LT": "<",
    "<=": "<=", "LTE": "<=",
}

# Size test modes -> comparison operator applied to len(field)
SIZE_MODES = {
    "SIZE": "==", "LEN": "==", "LENGTH": "==",
    "SIZE-GT": ">", "()>": ">",
    "SIZE-GTE": ">=", "()>=": ">=",
    "SIZE-LT": "<", "()<": "<",
    "SIZE-LTE": "<=", "()<=": "<=",
}

# Ordering operators: both sides are converted to numbers when possible
ORDERING_OPERATORS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}

# Failure message for each canonical operator: (field, expected, got)
CHECK_FAIL_MESSAGES = {
    "==": "FIELD: %s VALUE mismatch. Expected: %s - got: %s",
    "!=": "FIELD: %s VALUE mismatch. Expected difference: %s - got: %s",
    ">": "FIELD: %s is SMALLER. Expected: > %s got: %s",
    ">=": "FIELD: %s is SMALLER. Expected: >= %s got: %s",
    "<": "FIELD: %s is BIGGER. Expected: < %s got: %s",
    "<=": "FIELD: %s is BIGGER. Expected: <= %s got: %s",
}


def _to_number(value):
    """Convert a numeric string to int / float; return any other value unchanged."""
    if not isinstance(value, str):
        return value

    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value


def _compare(op, left, right):
    """
    Compare two values with a canonical operator (see OPERATOR_ALIASES).

    "==" and "!=" also match on the string form (1 == "1").
    Ordering operators convert numeric strings to numbers first.

    Raises:
        TypeError: If the values cannot be ordered (e.g. "abc" > 3)
    """
    if op == "==":
        return left == right or str(left) == str(right)
    if op == "!=":
        return left != right and str(left) != str(right)

    return ORDERING_OPERATORS[op](_to_number(left), _to_number(right))


class RESTest:
    """HTTP test engine: sends requests, runs tests and keeps the global variables."""

    def __init__(
        self,
        base_url="",
        log_file="",
        stop_on_error=True,
        quiet=False,
        postman=None,
        curl=False,
        dry=False,
        delay=0,
        headers=None,
        no_colors=False,
        prefix="",
        auth_mode="auth",
        log_clean=False,  # 2.2.0 - Added log_clean
    ):
        """Create the engine.

        Args:
            base_url: Base URL joined to relative endpoints
            log_file: Path of the log file ("" disables logging)
            stop_on_error: Raise RESTestError on the first test error
            quiet: Disable console output
            postman: Optional PostmanExporter recording every request
            curl: Also print the curl command of each request on the console
            dry: Do not send requests for real
            delay: Milliseconds to wait before each request
            headers: Global headers added to all requests
            no_colors: Disable colors in console output
            prefix: API prefix appended to base_url
            auth_mode: Default authentication mode ("auth" or "no")
            log_clean: Truncate the log file before starting
        """
        if not headers:
            headers = {}

        self.quiet = quiet
        self.base_url = base_url
        self.log_file = log_file
        self.postman = postman
        self.dry = dry
        self.dump_curl_on_console = curl
        self.delay = delay
        self.no_colors = no_colors
        self.prefix = prefix
        self.auth_mode = auth_mode

        self.globals = {}  # Global var / values for requests

        self.authorization_header = "Authorization"
        self.authorization_template = "Bearer %(token)s"

        # These are the global headers that will be added to all requests
        self.headers = headers

        # These are the global cookies that will be added to all requests
        self.cookies = {}

        self.stop_on_error = stop_on_error
        self.sections = []

        self._tests = 0
        self._errors = 0

        # Log file handle, opened lazily by _log_write and closed by close()
        self._log_handle = None
        self._log_handle_path = None

        self.session = requests.Session()

        # Base URL and Prefix
        if not self.prefix:
            self.prefix = ""
        if self.prefix.startswith("/"):
            self.prefix = self.prefix[1:]
        if self.prefix.endswith("/"):
            self.prefix = self.prefix[:-1]
        if self.base_url.endswith("/"):
            self.base_url = self.base_url[:-1]

        # 2.2.0 - Added log_clean
        if self.log_file and log_clean:
            self._open_log("w").close()

    def _tabs(self, indent=0):
        """Return the indentation for the current section depth (plus indent)."""
        return "\t" * (len(self.sections) + indent)

    def _parse_headers(self, r):
        """Store the response headers with lower case names in r._headers."""
        heads = {}

        for k, v in r.headers.items():
            hk = k.lower()
            heads[hk] = r.headers[k]

        r._headers = heads

    def _mask_secret(self, value):
        """Hide a secret value, keeping only the first and last 4 chars when long enough."""
        value = str(value)
        if len(value) <= 12:
            return "****"

        return value[:4] + "****" + value[-4:]

    def _mask_headers(self, headers):
        """Return a copy of headers with the Authorization values masked (for logs)."""
        secret_names = {
            "authorization",
            "proxy-authorization",
            str(self.authorization_header).lower(),
        }

        return {
            k: (self._mask_secret(v) if str(k).lower() in secret_names else v)
            for k, v in headers.items()
        }

    def _open_log(self, mode):
        """Open the log file for "w" or "a", creating it readable by the owner only (0o600)."""
        flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if mode == "w" else os.O_APPEND)
        fd = os.open(self.log_file, flags, 0o600)
        os.chmod(self.log_file, 0o600)

        return os.fdopen(fd, mode, encoding="utf-8")

    def _log_write(self, txt):
        """Append txt to the log file, keeping the file open between writes."""
        if not self.log_file:
            return

        # (Re)open when first used or when log_file changed (e.g. from "system")
        if self._log_handle is None or self._log_handle_path != self.log_file:
            self.close()
            self._log_handle = self._open_log("a")
            self._log_handle_path = self.log_file

        self._log_handle.write(txt)
        self._log_handle.flush()

    def close(self):
        """Close the log file, if open. Safe to call more than once."""
        if self._log_handle is None:
            return

        self._log_handle.close()
        self._log_handle = None
        self._log_handle_path = None

    def _log_start(self, method, endpoint, data):
        """Count a new request and log its method, endpoint and data."""
        self._tests += 1
        if not self.log_file:
            return

        self._log_write("=" * 70)
        self._log_write(
            """
Endpoint:     %s %s
Data:         %s
"""
            % (method, endpoint, json.dumps(data, default=str))
        )

    def _elapsed_ms(self, resp):
        """Return the request duration in milliseconds, whole seconds included."""
        return resp.elapsed.total_seconds() * 1000

    def _log_resp(self, headers, resp):
        """Log the request headers (secrets masked) and the response."""
        if not self.log_file:
            return

        self._log_write(
            """Headers:      %s
Status Code:  %s
Request Time: %s
Raw Response: %s
"""
            % (
                self._mask_headers(headers),
                resp.status_code,
                self._elapsed_ms(resp),
                resp.text,
            )
        )

    def _log_curl(self, req):
        """Log the curl command of a request (and print it when curl dump is enabled)."""
        command = "curl -X {method} \\\n -H {headers} \\\n -d '{data}' \\\n '{uri}'"

        method = req.method
        uri = req.url
        # data = str ( req.body ) [ 2 : -1 ]   # quick and dirty way to remove b'...' from string
        try:
            data = req.body.decode("utf-8")
        except (AttributeError, UnicodeDecodeError):
            data = ""

        def _build(hdrs):
            hdrs = " \\\n -H ".join(['"{0}: {1}"'.format(k, v) for k, v in hdrs.items()])
            return command.format(method=method, headers=hdrs, data=data, uri=uri)

        # Log file gets masked secrets; the console curl stays copy-pastable
        self._log_write("\nCURL:         %s\n\n" % _build(self._mask_headers(req.headers)))

        if self.dump_curl_on_console:
            sys.stderr.write("\n\n%s\n\n" % _build(req.headers))
            sys.stderr.flush()

    def _mk_headers(self, authenticated, local_headers):
        """Build the request headers: global + local, Authorization when authenticated, all expanded."""
        if not local_headers:
            local_headers = {}

        headers = self.headers.copy()
        headers.update(local_headers)

        if authenticated:
            hv = ""
            try:
                hv = self._expand_var(self.authorization_template)
            except RESTestError as e:
                raise RESTestError(
                    "could not create Authorization template: %s\n%s"
                    % (self.authorization_template, e)
                ) from e

            if hv:
                headers[self.authorization_header] = hv

        for k, v in headers.items():
            headers[k] = self._expand_var(str(v))

        return headers

    def _mk_cookies(self, local_cookies):
        """Build the request cookies: global + local, all expanded."""
        if not local_cookies:
            local_cookies = {}

        cookies = self.cookies.copy()

        for k, v in local_cookies.items():
            cookies[k] = self._expand_var(str(v))

        return cookies

    def _resolve_url(self, endpoint):
        """Return endpoint as is when absolute, else join it to base_url / prefix."""
        if endpoint.lower().startswith(("http://", "https://")):
            return endpoint

        base_url = self.base_url + "/" + self.prefix

        if endpoint.startswith("/"):
            return self.base_url + endpoint

        return base_url + "/" + endpoint

    def _expand_any(self, value):
        """Expand ${...} and %(var)s in a value, recursing into dicts and lists."""
        if isinstance(value, dict):
            return self._expand_dict(value)
        if isinstance(value, list):
            return self._expand_list(value)

        return self._get_v(value)

    def _expand_list(self, lst):
        """Return a new list with every item expanded (nested lists included)."""
        return [self._expand_any(x) for x in lst]

    def _expand_dict(self, dct):
        """Expand every value of dct in place (nested dicts and lists included)."""
        for k, v in dct.items():
            dct[k] = self._expand_any(v)

        return dct

    def _expand_expressions(self, value):
        """
        Expand all ${...} expressions in a value.

        Supports:
        - Pure expressions: "${a + b}" returns numeric value
        - String interpolation: "user_${counter}" returns "user_1"
        - Multiple expressions: "id_${a}_${b}" returns "id_10_5"

        Args:
            value: Value to expand (any type)

        Returns:
            Expanded value (preserves type if no expressions found)
        """
        # Only process strings
        if not isinstance(value, str):
            return value

        # Quick check: if no ${ pattern, return as-is
        if "${" not in value:
            return value

        # Value is EXACTLY a single expression (no prefix/suffix): keep numeric result
        full_match = RX_EXPRESSION.fullmatch(value)
        if full_match:
            return self._eval_expression(full_match.group(1), value)

        # String with embedded expressions: replace all occurrences as strings
        return RX_EXPRESSION.sub(
            lambda match: str(self._eval_expression(match.group(1), value)), value
        )

    def _eval_expression(self, expr, value):
        """
        Evaluate the content of one ${...} expression against the globals.

        Args:
            expr: Expression content (without the ${ } wrapper)
            value: Full original value, used in error messages

        Returns:
            Numeric result of the expression

        Raises:
            RESTestError: If the expression is empty or cannot be evaluated
        """
        expr = expr.strip()
        if not expr:
            raise RESTestError(
                "Empty expression '{}' in value: %s" % _c(self, value, "white")
            )

        try:
            return evaluate_expr(expr, self.globals)
        except ExpressionError as e:
            raise RESTestError(
                "Failed to evaluate expression\n"
                "  Value:      %s\n"
                "  Expression: %s\n"
                "  Error:      %s"
                % (
                    _c(self, value, "white"),
                    _c(self, expr, "yellow"),
                    _c(self, str(e), "red"),
                )
            ) from e

    def _get_v(self, x):
        """Expand ${...} expressions and %(var)s placeholders in a single value."""
        if isinstance(x, dict):
            return self._expand_dict(x)

        # Preserve non-string types (bool, int, float, None) as-is
        if not isinstance(x, str):
            return x

        # New 2.6.0 - Expand ${expr} expressions first
        n = self._expand_expressions(x)

        # Handle the case where expression returned a number
        if not isinstance(n, str):
            return n

        # If no %(var)s pattern, return the expression-expanded value
        if n.find("%(") == -1:
            return n

        if n.find("__internal_") != -1:
            n = n.replace("__internal_", "")
            return n % self._internal_info

        return n % self.globals

    def _expand_var(self, v):
        """
        Expand ${...} expressions and %(var)s placeholders in a value.

        Raises:
            RESTestError: If the value cannot be expanded (the message lists the globals)
        """
        try:
            if isinstance(v, list):
                v = self._expand_list(v)
            else:
                v = self._get_v(v)
        except RESTestError:
            raise
        except Exception as e:
            raise RESTestError(
                "could not expand: %s (%s: %s)\n%s"
                % (_c(self, v, "white"), type(e).__name__, e, self._format_globals())
            ) from e

        return v

    def _format_globals(self):
        """Return the global variables as aligned "name : value" lines."""
        keys = sorted(self.globals.keys())
        if not keys:
            return ""

        max_len = max(len(x) for x in keys)

        return "".join(
            "    %s : %s\n" % (_c(self, k.ljust(max_len), "white"), self.globals[k])
            for k in keys
        )

    def _expand_data(self, data):
        """Expand keys and values of a request body ("__direct__" sends a value as is)."""
        if "__direct__" in data:
            return data["__direct__"]

        res = {}

        for k, v in data.items():
            k = self._expand_var(k)
            v = self._expand_var(v)
            res[k] = v

        return res

    def _expand_data_list(self, data):
        """Expand every dict of a list body (see _expand_data)."""
        return [self._expand_data(item) for item in data]

    def _parse_object(self, value):
        """Parse a dict given as JSON or as a Python literal, without executing code."""
        if isinstance(value, dict):
            return value

        try:
            return json.loads(value)
        except ValueError:
            return ast.literal_eval(value)

    def _object_compare(self, v1, v2):
        """Return True when two dicts (or their JSON / literal form) have the same keys and values."""
        o1 = self._parse_object(v1)
        o2 = self._parse_object(v2)

        k1 = list(o1.keys())
        k2 = list(o2.keys())
        k1.sort()
        k2.sort()
        if k1 != k2:
            return False

        for k in k1:
            if o1[k] != o2[k]:
                return False

        return True

    def _data_to_url(self, dct):
        """Encode a dict as an URL query string."""
        elems = []
        for k, v in dct.items():
            v = json.dumps(v)
            if v.startswith('"'):
                v = v[1:-1]
            elems.append(f"{k}={urllib.parse.quote(v)}")

        if not elems:
            return ""

        return "&".join(elems)

    def _reorder_files(self, files):
        """Flatten multi-file fields into (name, file) tuples for requests."""
        if not files:
            return files

        has_multi = False
        for k, v in files.items():
            if isinstance(v, list):
                has_multi = True
                break

        if not has_multi:
            return files

        res = []
        for k, v in files.items():
            if isinstance(v, list):
                for el in v:
                    res.append((k, el))
            else:
                res.append((k, v))

        return res

    def _req(
        self,
        mode,
        endpoint,
        data={},
        authenticated=True,
        status_code=200,
        skip_error=False,
        no_cookies=False,
        max_exec_time=0,
        files=None,
        title="",
        content="json",
        headers=None,
        cookies=None,
    ):
        """Send one HTTP request and validate status code and execution time.

        Returns:
            The response, or None in dry mode

        Raises:
            RESTestError: On unsupported method / content, or on a test error with stop_on_error
        """
        if mode not in HTTP_METHODS:
            raise RESTestError(
                "unsupported HTTP method: %s (supported: %s)"
                % (mode, ", ".join(HTTP_METHODS))
            )

        endpoint = self._expand_data({"endpoint": endpoint})["endpoint"]

        url = self._resolve_url(endpoint)
        headers = self._mk_headers(authenticated=authenticated, local_headers=headers)
        cookies = self._mk_cookies(local_cookies=cookies)

        if type(data) is list:
            data = self._expand_data_list(data)
        else:
            data = self._expand_data(data)

        if no_cookies:
            obj = requests
        else:
            obj = self.session

            # set cookies
            for k, v in cookies.items():
                self.session.cookies.set(k, v)

        if mode == "GET" and data:
            url_params = self._data_to_url(data)
            url += "?" + url_params if url.find("?") == -1 else "&" + url_params

        files = self._reorder_files(files)
        if files:
            content = "form"

        if content not in ("json", "form"):
            raise RESTestError("unsupported content: %s (use 'json' or 'form')" % content)

        if self.dry:
            self._log_start(mode, url, data)
            return None

        if content == "json":
            # v1.90 - changing the json = data to data = encoded
            # 		  to better support UTF-8 strings

            # r = m ( url, json = data, headers = headers, files = files )
            data = json.dumps(data, ensure_ascii=False, default=str)
            encoded = data.encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
            r = obj.request(mode, url, data=encoded, headers=headers, files=files)

        elif content == "form":
            for k, v in data.items():
                if isinstance(v, (list, dict)):
                    data[k] = json.dumps(v)

            r = obj.request(mode, url, data=data, headers=headers, files=files)

        self._parse_headers(r)

        if self.postman:
            self.postman.add(title, mode, url, data, headers, r)

        self._log_start(mode, url, data)
        self._log_resp(headers, r)
        self._log_curl(r.request)

        # If skip_error is set, we don't have to check for the status code
        if skip_error:
            return r

        if r.status_code != status_code:
            self._error(
                "%s %s - Status: %s (expected: %s)"
                % (
                    _c(self, "REQUEST ERROR:", "red"),
                    _c(self, r.text, "white"),
                    r.status_code,
                    status_code,
                )
            )

        ms = self._elapsed_ms(r)
        if max_exec_time and ms > max_exec_time:
            self._error(
                "TOO MUCH TIME ERROR (res: %s ms - expected: %s ms)" % (ms, max_exec_time)
            )

        return r

    def do_EXEC(
        self,
        meth,
        endpoint,
        data={},
        authenticated=True,
        status_code=200,
        skip_error=False,
        no_cookies=False,
        max_exec_time=0,
        files=None,
        title="",
        content="json",
        headers=None,
        cookies=None,
        internal_info=None,
    ):
        """Wait the configured delay, then send a request (see _req).

        Args:
            meth: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: Endpoint, absolute or relative to base_url
            data: Request body (dict or list) or GET parameters
            authenticated: Add the Authorization header
            status_code: Expected status code
            skip_error: Do not check status code and execution time
            no_cookies: Send the request outside the session (no cookies)
            max_exec_time: Max execution time in ms (0 disables the check)
            files: Files to upload (forces "form" content)
            title: Request title (used by the Postman export)
            content: "json" or "form"
            headers: Request specific headers
            cookies: Request specific cookies
            internal_info: Values available as %(__internal_name)s

        Returns:
            The response, or None in dry mode
        """
        # v2.0 - added internal_info dict to the Engine class
        self._internal_info = internal_info

        if self.delay:
            time.sleep(self.delay / 1000)

        return self._req(
            meth,
            endpoint,
            data,
            authenticated,
            status_code,
            skip_error=skip_error,
            no_cookies=no_cookies,
            max_exec_time=max_exec_time,
            files=files,
            title=title,
            content=content,
            headers=headers,
            cookies=cookies,
        )

    def _field_spec(self, spec):
        """
        Normalize one "fields" / "dumps" entry to (json_key, glob_key, mode).

        Accepted forms (the same for "fields" and "dumps"):
        - String: "json.path" (path and save key are the same)
        - List/Tuple: ["json.path", "save_key"] or ["json.path"]
        - Object: {"path": "json.path", "save": "save_key", "mode": "value|length|type|keys"}
          ("field" is accepted as an alias of "path")

        Raises:
            RESTestError: If the entry is empty
        """
        if not spec:
            raise RESTestError("empty entry in 'fields' / 'dumps'")

        if isinstance(spec, dict):
            json_key = spec.get("path", spec.get("field", ""))
            return json_key, spec.get("save", json_key), spec.get("mode", "value").lower()

        if isinstance(spec, (list, tuple)):
            return spec[0], spec[-1], "value"

        return spec, spec, "value"

    def _json_type_name(self, value):
        """Return the JSON type name of a value (null, array, object, string, boolean, number)."""
        if value is None:
            return "null"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        if isinstance(value, str):
            return "string"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, (int, float)):
            return "number"

        return type(value).__name__

    def _field_value(self, j, json_key, mode):
        """
        Extract json_key from the response JSON and apply a field mode.

        Args:
            j: Response JSON
            json_key: Path to extract ("*" is the whole JSON, "#path" its length)
            mode: One of FIELD_MODES

        Returns:
            Tuple (value, error): error is a message string when the value cannot be computed.
            A missing path in "value" mode returns NOT_FOUND (no error, as before).
        """
        if mode not in FIELD_MODES:
            return None, "unsupported field mode: %s (supported: %s)" % (
                mode,
                ", ".join(FIELD_MODES),
            )

        value = j if json_key == "*" else self._expand_value(j, json_key)

        if mode == "value":
            return value, None
        if value is NOT_FOUND:
            return None, "Cannot get %s: path not found: %s" % (mode, json_key)
        if mode == "type":
            return self._json_type_name(value), None

        if mode == "length":
            if value is None:
                return 0, None
            if hasattr(value, "__len__"):
                return len(value), None
            return None, "Cannot get length of %s at path: %s" % (type(value).__name__, json_key)

        # mode == "keys"
        if isinstance(value, dict):
            return list(value.keys()), None
        return None, "Cannot get keys of %s at path: %s" % (type(value).__name__, json_key)

    def fields(self, resp, fields):
        """
        Extract fields from the response and save them to globals.

        See _field_spec for the accepted entry forms. A path can start with '#'
        for automatic length extraction, and "*" saves the whole JSON.

        Args:
            resp: Response object
            fields: List of field specifications
        """
        j = resp.json()

        for spec in fields:
            json_key, glob_key, mode = self._field_spec(spec)
            value, err = self._field_value(j, json_key, mode)
            if err:
                self._error(err)
                continue

            self.globals[glob_key] = value

    def dumps(self, resp, fields):
        """
        Print fields of the response on the console.

        Accepts the same entry forms as fields(): the save key is used as label.

        Args:
            resp: Response object
            fields: List of field specifications
        """
        j = resp.json()

        for spec in fields:
            json_key, label, mode = self._field_spec(spec)
            value, err = self._field_value(j, json_key, mode)
            if err:
                self._error(err)
                continue

            print("==== %s: %s\n" % (label, json.dumps(value, indent=4, default=str)))

    def _error(self, txt):
        """
        Record a test error: log it, then stop or count it.

        Raises:
            RESTestError: If stop_on_error is set
        """
        self._log_write("\n\n*** ERROR: %s\n" % txt)
        self._errors += 1
        if self.stop_on_error:
            raise RESTestError(txt)

        sys.stderr.write(_c(self, "\n\n=== ERROR: ", "red") + "%s\n" % txt)
        return None

    def _expand_value(self, dct, key):
        """Return the value at path key in dct, or NOT_FOUND (with a console message)."""
        key = self._expand_var(key)

        res, err = expand_value(key, dct)

        if err:
            print("PATH: %s - Error: %s" % (key, err))
            return NOT_FOUND

        return res

    def copy_val(self, _from, _to):
        """Copy the global variable _from into _to (both names are expanded)."""
        _from = self._expand_var(_from)
        _to = self._expand_var(_to)

        self.globals[_to] = self.globals[_from]

    def set_val(self, _key, _val):
        """
        Set a global variable value.

        If _val is an expression (${...}), it will be evaluated and the
        numeric result will be stored.

        Args:
            _key: Variable name
            _val: Value to set (can be literal or expression)
        """
        _key = self._expand_var(_key)
        _val = self._expand_var(_val)

        # Check if value is an expression and evaluate it
        if is_expression(_val):
            _val = evaluate_expr(_val, self.globals)

        self.globals[_key] = _val

    def sleep(self, _ms):
        """Pause the run for _ms milliseconds (the value is expanded)."""
        _ms = self._expand_var(_ms)
        time.sleep(int(_ms) / 1000)

    def _check(self, chk, field, v):
        """
        Run one test on a value and save it when the test passes and 'save' is set.

        Args:
            chk: Test definition with optional 'mode' (default EQUALS), 'value', 'save'
            field: Field name, used in error messages
            v: Value to test

        Returns:
            Error message string if the test fails, None if it passes
        """
        current_val = self._expand_var(v)
        expected_val = self._expand_var(chk.get("value"))

        # Evaluate expression in expected_val if present
        if is_expression(expected_val):
            expected_val = evaluate_expr(expected_val, self.globals)

        # mode is case insensitive
        mode = chk.get("mode", "EQUALS").upper()

        try:
            err = self._check_mode(mode, field, v, current_val, expected_val)
        except TypeError as e:
            err = "FIELD: %s cannot be tested with %s %s (%s)" % (
                _c(self, field, "white"),
                mode,
                _c(self, expected_val, "yellow"),
                e,
            )

        if err:
            return err

        if "save" in chk:
            self.globals[chk["save"]] = v

        return None

    def _check_mode(self, mode, field, v, current_val, expected_val):
        """
        Apply a test mode to an already expanded value.

        Args:
            mode: Upper case test mode (EQUALS, GT, SIZE-LT, EXISTS, ...)
            field: Field name, used in error messages
            v: Raw value (used by the null checks)
            current_val: Expanded value to test
            expected_val: Expanded expected value

        Returns:
            Error message string if the test fails, None if it passes

        Raises:
            TypeError: If the values cannot be compared with the given mode
        """
        cols = (
            _c(self, field, "white"),
            _c(self, expected_val, "yellow"),
            _c(self, current_val, "red"),
        )

        if mode in EXISTS_MODES:
            if (str(v) == "None") or (len(str(v)) == 0):
                return "FIELD: %s is EMPTY" % (_c(self, field, "white"))
            return None

        if mode in NULL_MODES:
            if str(v) != "None":
                return "FIELD: %s VALUE mismatch. Expected: Null - got: %s" % (
                    _c(self, field, "white"),
                    _c(self, current_val, "red"),
                )
            return None

        if mode in ("CONTAINS", "->"):
            if expected_val not in current_val:
                return "FIELD: %s DOES NOT contains %s. List: %s" % cols
            return None

        if mode in ("OBJ", "OBJECT"):
            if not self._object_compare(current_val, expected_val):
                return "FIELD: %s object values mismatch" % (_c(self, field, "white"))
            return None

        if mode in SIZE_MODES:
            op = SIZE_MODES[mode]
            size = len(current_val)
            if not _compare(op, size, int(expected_val)):
                return "FIELD: %s SIZE mismatch. Expected: %s %s - got: %s (%s)" % (
                    _c(self, field, "white"),
                    op,
                    _c(self, expected_val, "yellow"),
                    _c(self, size, "red"),
                    _c(self, current_val, "yellow"),
                )
            return None

        op = OPERATOR_ALIASES.get(mode)
        if not op:
            return "ERROR: unsupported test mode: %s " % mode

        if not _compare(op, current_val, expected_val):
            return CHECK_FAIL_MESSAGES[op] % cols

        return None

    def _check_expr(self, chk, j):
        """
        Handle EXPR mode test.

        EXPR mode compares a key value against an expression using an operator.

        Args:
            chk: Check definition with 'key', 'op', 'expr' fields
            j: JSON response data

        Returns:
            Error message string if test fails, None if passes
        """
        key_path = chk.get("key", "")
        op = chk.get("op", "==").upper()
        expr_val = chk.get("expr", "")

        # Expand variables in key_path
        key_path = self._expand_var(key_path)

        # Get left-hand value
        # If key_path is an expression, evaluate it
        if is_expression(key_path):
            left_val = evaluate_expr(key_path, self.globals)
        else:
            # Extract from response (supports # prefix for length)
            left_val, err = expand_value(key_path, j)
            if err:
                return f"EXPR test: error getting key '{key_path}': {err}"

        # Get right-hand value
        expr_val = self._expand_var(expr_val)

        # If expr_val is an expression, evaluate it
        if is_expression(expr_val):
            right_val = evaluate_expr(expr_val, self.globals)
        elif isinstance(expr_val, (int, float)):
            right_val = expr_val
        elif isinstance(expr_val, str):
            # Try to parse as number, otherwise treat as path
            try:
                if "." in expr_val and not expr_val.startswith("#"):
                    # Might be a float or a path
                    try:
                        right_val = float(expr_val)
                    except ValueError:
                        # Treat as path
                        right_val, err = expand_value(expr_val, j)
                        if err:
                            return f"EXPR test: error getting expr '{expr_val}': {err}"
                else:
                    right_val = int(expr_val) if expr_val.isdigit() else expr_val
                    # If it's a string that looks like a path, extract it
                    if isinstance(right_val, str) and not right_val.isdigit():
                        right_val, err = expand_value(right_val, j)
                        if err:
                            # Not a path, use as literal
                            right_val = expr_val
            except (ValueError, TypeError):
                right_val = expr_val
        else:
            right_val = expr_val

        # EXPR compares numbers when possible, also for == and !=
        left_val = _to_number(left_val)
        right_val = _to_number(right_val)

        canonical_op = OPERATOR_ALIASES.get(op)
        if not canonical_op:
            return f"EXPR test: unsupported operator '{op}'"
        op = canonical_op

        try:
            result = _compare(op, left_val, right_val)
        except TypeError as e:
            return f"EXPR test: cannot compare {left_val!r} {op} {right_val!r} ({e})"

        if not result:
            return (
                f"EXPR test failed: {_c(self, key_path, 'white')} ({_c(self, left_val, 'red')}) "
                f"{op} {_c(self, chk.get('expr', ''), 'white')} ({_c(self, right_val, 'yellow')})"
            )

        return None

    def check(self, resp, checks):
        """
        Run all the tests of an action against the response.

        Every failing test is reported through _error(): with stop_on_error
        the first failure raises, otherwise all the tests run and are counted.

        Args:
            resp: Response object
            checks: List of test definitions
        """
        j = resp.json()

        for chk in checks:
            if "title" in chk:
                print("%s%s" % (self._tabs(1), chk["title"]))

            self._tests += 1

            err = self._run_check(resp, j, chk)
            if err:
                self._error(err)

    def _run_check(self, resp, j, chk):
        """
        Run a single test definition.

        Returns:
            Error message string if the test fails, None if it passes
        """
        mode = chk.get("mode", "EQUALS").upper()

        # EXPR mode uses key/op/expr instead of field/mode/value
        if mode in ("EXPR", "EXPRESSION"):
            return self._check_expr(chk, j)

        # 2.3.0 - checking for 'field' key
        if "field" not in chk:
            return "Tests: missing 'field' key in one of the tests"

        field = self._expand_var(chk["field"])

        # 2.1.0 - added support for rt: prefix and the rt:size field
        if field == "rt:size":
            v = str(resp.size)
        else:
            v = self._expand_value(j, field)

        if v is NOT_FOUND:
            # A missing field is what the null modes (e.g. NOT_EXISTS) expect
            if mode not in NULL_MODES:
                return "FIELD: %s missing %s" % (
                    field,
                    json.dumps(j, default=str, indent=2),
                )
            v = None

        return self._check(chk, field, v)

    def dump(self, fields=None, do_print=True):
        """
        Dump variable values to console and/or log file.

        Args:
            fields: List of variable names to dump, or None to dump all variables
            do_print: If True, print to console; if False, only write to log file
        """
        # If no fields specified, dump all variables
        if fields is None:
            fields = list(self.globals.keys())

        for f in fields:
            f = self._expand_var(f)
            v = self.globals.get(f, NOT_FOUND)

            # Format for log file (with ====)
            if v is NOT_FOUND:
                log_s = "==== %s: <undefined>\n" % f
            else:
                log_s = "==== %s: %s\n" % (f, json.dumps(v, indent=4, default=str))

            self._log_write(log_s)

            # Format for console (colored, without ====)
            if do_print:
                if v is NOT_FOUND:
                    console_s = "%s: %s" % (
                        _c(self, f, "green"),
                        _c(self, "<undefined>", "white")
                    )
                else:
                    value_str = json.dumps(v, indent=4, default=str)
                    console_s = "%s: %s" % (
                        _c(self, f, "green"),
                        _c(self, value_str, "white")
                    )
                print(console_s)

    def section_start(self, name):
        """Open a named section: indent the console output and log its start."""
        self.sections.append(name)

        self._log_write(
            """
%s
START  ---->  %s
%s
"""
            % ("*" * 70, name, "*" * 70)
        )

    def section_end(self):
        """Close the current section and log its end."""
        name = self.sections.pop()
        self._log_write(("=" * 70) + "\n\n")
        self._log_write(
            """%s
END  ----  %s
%s

"""
            % ("*" * 70, name, "*" * 70)
        )
