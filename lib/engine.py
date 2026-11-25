#!/usr/bin/env python3
#
# restest engine
#
# written by Fabio Rotondo (fabio.rotondo@gmail.com)
#

import ast
import json
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


class RESTest:
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

        # This is a number used to generate counts
        self._inner_count = 0

        # These are the global headers that will be added to all requests
        self.headers = headers

        # These are the global cookies that will be added to all requests
        self.cookies = {}

        self.stop_on_error = stop_on_error
        self.sections = []

        self._tests = 0
        self._errors = 0

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
        return "\t" * (len(self.sections) + indent)

    def _parse_headers(self, r):
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

        return os.fdopen(fd, mode)

    def _log_write(self, txt):
        if not self.log_file:
            return

        with self._open_log("a") as fout:
            fout.write(txt)

    def _log_start(self, method, endpoint, data):
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
        if not local_cookies:
            local_cookies = {}

        cookies = self.cookies.copy()

        for k, v in local_cookies.items():
            cookies[k] = self._expand_var(str(v))

        return cookies

    def _resolve_url(self, endpoint):
        if endpoint.lower().find("http:") != -1:
            return endpoint
        if endpoint.lower().find("https:") != -1:
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
        if "__direct__" in data:
            return data["__direct__"]

        res = {}

        self._inner_count += 1

        for k, v in data.items():
            k = self._expand_var(k)
            v = self._expand_var(v)
            res[k] = v

        return res

    def _expand_data_list(self, data):
        res = []

        self._inner_count += 1

        for item in data:
            temp = self._expand_data(item)
            res.append(temp)
        return res

    def _parse_object(self, value):
        """Parse a dict given as JSON or as a Python literal, without executing code."""
        if isinstance(value, dict):
            return value

        try:
            return json.loads(value)
        except ValueError:
            return ast.literal_eval(value)

    def _object_compare(self, v1, v2):
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

        if mode == "DELETE":
            m = obj.delete
        elif mode == "GET":
            m = obj.get
        elif mode == "PATCH":
            m = obj.patch
        elif mode == "PUT":
            m = obj.put
        else:
            m = obj.post

        if mode == "GET" and data:
            url_params = self._data_to_url(data)
            url += "?" + url_params if url.find("?") == -1 else "&" + url_params

        files = self._reorder_files(files)
        if files:
            content = "form"

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
            r = m(url, data=encoded, headers=headers, files=files)

        elif content == "form":
            for k, v in data.items():
                if isinstance(v, (list, dict)):
                    data[k] = json.dumps(v)

            r = m(url, data=data, headers=headers, files=files)

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

    def fields(self, resp, fields):
        """
        Extract fields from response and save to globals.

        Supports multiple syntaxes:
        - String: "field_name" (path and save key are the same)
        - List/Tuple: ["json.path", "save_key"] or ["json.path"]
        - Object: {"path": "json.path", "save": "save_key", "mode": "value|length|type|keys"}

        The path can start with '#' for automatic length extraction.

        Args:
            resp: Response object
            fields: List of field specifications
        """
        j = resp.json()

        for k in fields:
            # Object syntax: {"path": "...", "mode": "...", "save": "..."}
            if isinstance(k, dict):
                json_key = k.get("path", "")
                glob_key = k.get("save", json_key)
                mode = k.get("mode", "value").lower()

                # ADD: support for '*' field name (all JSON)
                if json_key == "*":
                    self.globals[glob_key] = j
                    continue

                value = self._expand_value(j, json_key)

                # Apply mode transformation
                if mode == "length":
                    if value is None:
                        value = 0
                    elif hasattr(value, "__len__"):
                        value = len(value)
                    else:
                        self._error(f"Cannot get length of {type(value).__name__} at path: {json_key}")
                        continue
                elif mode == "type":
                    if value is None:
                        value = "null"
                    elif isinstance(value, list):
                        value = "array"
                    elif isinstance(value, dict):
                        value = "object"
                    elif isinstance(value, str):
                        value = "string"
                    elif isinstance(value, bool):
                        value = "boolean"
                    elif isinstance(value, (int, float)):
                        value = "number"
                    else:
                        value = type(value).__name__
                elif mode == "keys":
                    if isinstance(value, dict):
                        value = list(value.keys())
                    else:
                        self._error(f"Cannot get keys of {type(value).__name__} at path: {json_key}")
                        continue
                # mode == "value" is the default, no transformation needed

                self.globals[glob_key] = value

            # List/Tuple syntax: ["json.path", "save_key"] or ["json.path"]
            elif isinstance(k, (list, tuple)):
                if len(k) == 2:
                    json_key = k[0]
                    glob_key = k[1]
                else:
                    json_key = k[0]
                    glob_key = k[0]

                # ADD: support for '*' field name (all JSON)
                if json_key == "*":
                    self.globals[glob_key] = j
                    continue

                self.globals[glob_key] = self._expand_value(j, json_key)

            # String syntax: "field_name"
            else:
                glob_key = k
                json_key = k

                # ADD: support for '*' field name (all JSON)
                if json_key == "*":
                    self.globals[glob_key] = j
                    continue

                self.globals[glob_key] = self._expand_value(j, json_key)

    def dumps(self, resp, fields):
        j = resp.json()

        for k in fields:
            if isinstance(k, (list, tuple)):
                glob_key = k[1]
                json_key = k[0]
            elif isinstance(k, dict):
                json_key = k["field"]
                glob_key = json_key
            else:
                glob_key = k
                json_key = k

            v = self._expand_value(j, json_key)

            print("==== %s: %s\n" % (glob_key, json.dumps(v, indent=4, default=str)))

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
        key = self._expand_var(key)

        res, err = expand_value(key, dct)

        if err:
            print("PATH: %s - Error: %s" % (key, err))
            return "__NOT_FOUND__"

        return res

    def copy_val(self, _from, _to):
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
        _ms = self._expand_var(_ms)
        time.sleep(int(_ms) / 1000)

    def _check(self, chk, field, v):
        current_val = self._expand_var(v)
        expected_val = self._expand_var(chk.get("value"))

        # Evaluate expression in expected_val if present
        if is_expression(expected_val):
            expected_val = evaluate_expr(expected_val, self.globals)

        mode = chk.get("mode", "EQUALS")

        cols = (
            _c(self, field, "white"),
            _c(self, expected_val, "yellow"),
            _c(self, current_val, "red"),
        )

        # mode is now case insensitive
        mode = mode.upper()

        if mode in ("EXISTS", "EXIST", "!!", "NOT_NULL", "IS_NOT_NULL"):
            if (str(v) == "None") or (len(str(v)) == 0):
                return "FIELD: %s is EMPTY" % (_c(self, field, "white"))
        elif mode in (
            "EMPTY",
            "IS_EMPTY",
            "IS_NULL",
            "NULL",
            "NOT_EXISTS",
            "NOT_EXIST",
            "@",
        ):
            if str(v) != "None":
                return "FIELD: %s VALUE mismatch. Expected: Null - got: %s" % (
                    _c(self, field, "white"),
                    _c(self, current_val, "red"),
                )
        elif mode in ("EQUALS", "==", "=", "EQUAL"):
            if (current_val != expected_val) and (
                str(current_val) != str(expected_val)
            ):
                return "FIELD: %s VALUE mismatch. Expected: %s - got: %s" % cols
        elif mode in ("NOT_EQUAL", "!=", "<>"):
            if current_val == expected_val:
                return (
                    "FIELD: %s VALUE mismatch. Expected difference: %s - got: %s" % cols
                )
        elif mode in ("CONTAINS", "->"):
            if expected_val not in current_val:
                return "FIELD: %s DOES NOT contains %s. List: %s" % cols
        elif mode in ("SIZE", "LEN", "LENGTH"):
            if len(current_val) != int(expected_val):
                return "FIELD: %s SIZE mismatch. Expected: %s - got: %s (%s)" % (
                    _c(self, field, "white"),
                    _c(self, expected_val, "yellow"),
                    _c(self, len(current_val), "red"),
                    _c(self, current_val, "yellow"),
                )
        elif mode in ("GT", ">"):
            if isinstance(current_val, str):
                current_val = int(current_val)
            if current_val <= expected_val:
                return "FIELD: %s is SMALLER. Expected: %s got: %s" % cols
        elif mode in ("GTE", ">="):
            if isinstance(current_val, str):
                current_val = int(current_val)
            if current_val < expected_val:
                return "FIELD: %s is SMALLER. Expected: %s got: %s" % cols
        elif mode in ("LT", "<"):
            if isinstance(current_val, str):
                current_val = int(current_val)
            if current_val >= expected_val:
                return "FIELD: %s is BIGGER. Expected: %s got: %s" % cols
        elif mode in ("LTE", "<="):
            if isinstance(current_val, str):
                current_val = int(current_val)
            if current_val > expected_val:
                return "FIELD: %s is BIGGER. Expected: %s got: %s" % cols
        elif mode in ("SIZE-GT", "()>"):
            if len(current_val) <= int(expected_val):
                return "FIELD: %s is SMALLER. Expected: %s got: %s" % cols
        elif mode in ("SIZE-GTE", "()>="):
            if len(current_val) < int(expected_val):
                return "FIELD: %s is SMALLER. Expected: %s got: %s" % cols
        elif mode in ("SIZE-LT", "()<"):
            if len(current_val) >= int(expected_val):
                return "FIELD: %s is BIGGER. Expected: %s got: %s" % cols
        elif mode in ("SIZE-LTE", "()<="):
            if len(current_val) > int(expected_val):
                return "FIELD: %s is BIGGER. Expected: %s got: %s" % cols
        elif mode in ("OBJ", "OBJECT"):
            if not self._object_compare(current_val, expected_val):
                return "FIELD: %s object values mismatch" % (_c(self, field, "white"))
        else:
            return "ERROR: unsupported test mode: %s " % mode

        if "save" in chk:
            self.globals[chk["save"]] = v

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

        # Convert to numbers for comparison if possible
        try:
            if isinstance(left_val, str):
                left_val = float(left_val) if "." in left_val else int(left_val)
        except (ValueError, TypeError):
            pass

        try:
            if isinstance(right_val, str):
                right_val = float(right_val) if "." in right_val else int(right_val)
        except (ValueError, TypeError):
            pass

        # Normalize operator aliases
        op_map = {
            "==": "==", "=": "==", "EQUALS": "==", "EQUAL": "==",
            "!=": "!=", "<>": "!=", "NOT_EQUALS": "!=", "NOT_EQUAL": "!=",
            ">": ">", "GT": ">",
            ">=": ">=", "GTE": ">=",
            "<": "<", "LT": "<",
            "<=": "<=", "LTE": "<=",
        }
        op = op_map.get(op, op)

        # Perform comparison
        result = False
        if op == "==":
            result = left_val == right_val or str(left_val) == str(right_val)
        elif op == "!=":
            result = left_val != right_val and str(left_val) != str(right_val)
        elif op == ">":
            result = left_val > right_val
        elif op == ">=":
            result = left_val >= right_val
        elif op == "<":
            result = left_val < right_val
        elif op == "<=":
            result = left_val <= right_val
        else:
            return f"EXPR test: unsupported operator '{op}'"

        if not result:
            return (
                f"EXPR test failed: {_c(self, key_path, 'white')} ({_c(self, left_val, 'red')}) "
                f"{op} {_c(self, chk.get('expr', ''), 'white')} ({_c(self, right_val, 'yellow')})"
            )

        return None

    def check(self, resp, checks):
        j = resp.json()

        for chk in checks:
            if "title" in chk:
                print("%s%s" % (self._tabs(1), chk["title"]))

            self._tests += 1

            # Check for EXPR mode (uses key/op/expr instead of field/mode/value)
            mode = chk.get("mode", "").upper()
            if mode in ("EXPR", "EXPRESSION"):
                err = self._check_expr(chk, j)
                if err:
                    return self._error(err)
                continue

            # 2.3.0 - checking for 'field' key
            if "field" not in chk:
                return self._error("Tests: missing 'field' key in one of the tests")
            field = self._expand_var(chk["field"])

            # 2.1.0 - added support for rt: prefix and the rt:size field
            if field == "rt:size":
                v = str(resp.size)
            else:
                v = self._expand_value(j, field)

            err = self._check(chk, field, v)

            if v == "__NOT_FOUND__":
                return self._error(
                    "FIELD: %s missing %s"
                    % (field, json.dumps(j, default=str, indent=2))
                )

            if err:
                return self._error(err)

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
            v = self.globals.get(f, "__NOT_FOUND__")

            # Format for log file (with ====)
            if v == "__NOT_FOUND__":
                log_s = "==== %s: <undefined>\n" % f
            else:
                log_s = "==== %s: %s\n" % (f, json.dumps(v, indent=4, default=str))

            self._log_write(log_s)

            # Format for console (colored, without ====)
            if do_print:
                if v == "__NOT_FOUND__":
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
        name = self.sections.pop()
        self._log_write(("=" * 70) + "\n\n")
        self._log_write(
            """%s
END  ----  %s
%s

"""
            % ("*" * 70, name, "*" * 70)
        )
