#!/usr/bin/env python3
#
# restest parser
#
# written by Fabio Rotondo <fabio.rotondo@gmail.com>
#

import sys
import json
import os
import gzip
import bz2

import requests

from .engine import RESTest
from .cols import xcolored
from .errors import RESTestError
from .timings import Timings
from .utils import deepcopy, size2str


# Options accepted in the script "system" section
SYSTEM_KEYS = (
    "base_url",
    "log_file",
    "stop_on_error",
    "headers",
    "global_headers",
    "cookies",
    "authorization_header",
    "authorization_template",
)


class RESTestParser:
    def __init__(
        self,
        base_url=None,
        stop_on_error=None,
        log_file=None,
        quiet=False,
        postman=None,
        curl=False,
        dry=False,
        delay=0,
        no_colors=False,
        prefix="",
        auth_mode="auth",
        log_clean=False,  # 2.2.0 - support for log_clean
        debug_file_name=None,  # 2.4.0 - support for debug_file_name
        step=False,  # 2.5.0 - support for step mode
        no_break=False,  # 2.5.0 - support for no_break flag
        allow_code=False,  # 2.6.0 - "code" actions run only when explicitly allowed
    ):
        self.rt = RESTest(
            quiet=quiet,
            log_file=log_file,
            postman=postman,
            curl=curl,
            dry=dry,
            delay=delay,
            no_colors=no_colors,
            prefix=prefix,
            auth_mode=auth_mode,
            log_clean=log_clean,  # 2.2.0 - support for log_clean
        )

        self._batches = {}

        self.forced_stop_on_error = stop_on_error
        self.forced_log_file = log_file
        self.forced_base_url = base_url
        self.quiet = quiet
        self.delay = delay
        self.no_colors = no_colors
        # API prefix URL  (append to base_url)
        self.prefix = prefix
        self.auth_mode = auth_mode
        # 2.5.0 - support for step mode
        self.step = step
        # 2.5.0 - support for no_break flag
        self.no_break = no_break
        # 2.6.0 - "code" actions execute Python: disabled unless allowed
        self.allow_code = allow_code

        self._paths = []
        self._included = {}

        # New 2.0 - support for recording of timings
        self.timings = Timings()

        # New 2.4.0 - support for debug_file_name
        self.debug_file_name = debug_file_name

    def open(self, fname):
        self.script = self._json_load(fname)

        self._abs_script_path = os.path.dirname(os.path.abspath(fname))

        self._paths.append(self._abs_script_path)

        self._parse_system()

        if self.forced_base_url is not None:
            self.rt.base_url = self.forced_base_url

        if self.forced_stop_on_error is not None:
            self.rt.stop_on_error = self.forced_stop_on_error

        if self.forced_log_file is not None:
            self.rt.log_file = self.forced_log_file

        self._actions(self.script["actions"])

    def close(self):
        """Release the engine resources (log file)."""
        self.rt.close()

    def export_csv(self, fname):
        self.timings.export_csv(fname)

    def _actions(self, actions):
        for act in actions:
            # New 2.6.0 - support for skip flag on all actions (including include, section, etc.)
            if act.get("skip", False):
                if not self.quiet:
                    sys.stdout.write(" - %s\n" % xcolored(self, "SKIP", "yellow"))
                    sys.stdout.flush()
                continue

            if "title" in act:
                print("\n ==", act["title"])

            action = act.get("method", act.get("action", "")).lower()
            if action:
                meth = getattr(self, "_method_" + action, None)
                if meth is None:
                    raise RESTestError("unknown action or method: '%s'" % action)
                res = meth(act)
                if not res:
                    raise RESTestError(
                        "action '%s' failed: stopping on unhandled error" % action
                    )

            # "section" and "if" already recurse into act["actions"] themselves
            # (see _method_section / _method_if); running the generic fallback
            # below for them too would execute the same nested actions twice.
            if "actions" in act and action not in ("section", "if"):
                self._actions(act["actions"])

            # 2.5.0 - step mode or break attribute: wait for user to press ENTER before next action
            # --no-break flag disables break attribute (but not --step mode)
            should_break = self.step or (act.get("break", False) and not self.no_break)
            if should_break:
                # Dump all variables before prompting
                print("\n%s" % xcolored(self, "=== Variables in Memory ===", "yellow"))
                self.rt.dump()
                # Ctrl+C raises KeyboardInterrupt, handled by the CLI
                input(xcolored(self, "\nPress ENTER to continue...", "cyan"))

    def _parse_files(self, dct):
        """Open the files to upload: {field: path | [paths]} -> {field: file | [files]}."""
        files = {}

        for k, v in dct.items():
            if isinstance(v, list):
                _v = []
                for f in v:
                    n = self._resolve_fname(f)
                    _v.append(open(n, "rb"))

                files[k] = _v
            else:
                v = self._resolve_fname(v)
                files[k] = open(v, "rb")

        return files

    def _close_files(self, files):
        """Close the files opened by _parse_files."""
        for v in files.values():
            for f in v if isinstance(v, list) else [v]:
                f.close()

    def _send_req(self, act, counter):
        m = act["method"].upper()

        # 2.0.1 - support for auth_mode flag
        auth = act.get("auth", True if self.rt.auth_mode == "auth" else False)
        content = act.get("content", "json")

        if m == "POST":
            _col = "blue"
        elif m == "GET":
            _col = "green"
        elif m == "DELETE":
            _col = "red"
        else:
            _col = "white"

        # 2.2.0 - support for "body" as alternative to "params" and "data"
        params = act.get("body", act.get("params", act.get("data", {})))

        if not self.quiet:
            sys.stdout.write(
                "%s %s %s %s %s %s"
                % (
                    self.rt._tabs(),
                    xcolored(self, "%-6s" % m, _col),
                    xcolored(self, "%-35s" % act.get("url", ""), "yellow"),
                    xcolored(self, params, "green"),
                    "auth:",
                    xcolored(self, auth, "blue"),
                )
            )
            sys.stdout.flush()

        # 2.2.0 - if params is present, but it is not a dict return an error
        if params and not isinstance(params, dict):
            raise RESTestError("'body' (or 'params') must be a dictionary")

        # New 2.1.0 - support for skip flag
        if act.get("skip", False):
            if not self.quiet:
                sys.stdout.write(" - %s\n" % xcolored(self, "SKIP", "yellow"))
                sys.stdout.flush()
            return None

        # New 1.91 - support for custom headers in single call
        headers = act.get("headers", {})

        # New 1.92 - support for custom cookies in single call
        cookies = act.get("cookies", {})

        ignore = False
        if "ignore_error" in act:
            ignore = act["ignore_error"]
        elif "skip_error" in act:
            sys.stderr.write(
                "%s 'skip_error' is deprecated use 'ignore_error' in actions\n"
                % (xcolored(self, "WARNING", "yellow"))
            )
            ignore = act["skip_error"]

        self.timings.start(m, act["url"], params)

        files = self._parse_files(act.get("files", {}))

        try:
            res = self.rt.do_EXEC(
                m,
                act["url"],
                params,
                auth,
                status_code=act.get("status_code", act.get("status", 200)),
                skip_error=ignore,
                no_cookies=act.get("no_cookies", False),
                max_exec_time=act.get("max_time", 0),
                title=act.get("title", "No title provided"),
                files=files,
                content=content,
                headers=headers,
                cookies=cookies,
                internal_info={
                    "counter": counter + 1,
                },
            )

            # Dry mode: no request was sent, so there is no response to inspect
            if res is None:
                self.timings.end(None)
                if not self.quiet:
                    sys.stdout.write(" - %s\n" % xcolored(self, "DRY", "yellow"))
                    sys.stdout.flush()
                return None

            data = self.timings.end(res.status_code)
            start_time = data["start_time"]
            end_time = data["end_time"]

            # 2.1.0 - support for response_size
            res.size = len(res.content)
            res.str_size = size2str(res.size)

            if not self.quiet:
                if res.status_code < 300:
                    status = xcolored(self, "%-3s" % res.status_code, "green")
                elif res.status_code < 500:
                    status = xcolored(
                        self, "%-3s" % res.status_code, "yellow", "on_grey", ["reverse"]
                    )
                else:
                    status = xcolored(
                        self,
                        "%-3s" % res.status_code,
                        "red",
                        "on_grey",
                        ["reverse", "blink"],
                    )

                sys.stdout.write(
                    " - size: %5s - status: %s - t: %s ms / %s s\n"
                    % (
                        res.str_size,  # 2.1.0 - support for response_size
                        status,
                        (end_time - start_time),
                        (end_time - start_time) / 1000,
                    )
                )

            return res
        except requests.RequestException as e:
            # Network level failure (connection refused, timeout, bad URL, ...)
            if not self.quiet:
                sys.stdout.write(
                    " - status: %s\n"
                    % xcolored(self, "ERROR", "red", "on_white", ["reverse", "blink"])
                )
            raise RESTestError("request failed: %s" % e) from e
        finally:
            self._close_files(files)

    def _method_exec(self, act):
        repeat = act.get("repeat", 1)
        orig_act = deepcopy(act)

        for i in range(repeat):
            act = deepcopy(orig_act)
            res = self._send_req(act, i)

            # No response (dry mode or skipped request): nothing to extract or test
            if res is None:
                continue

            # if 'save_cookies' in act: self.rt.save_cookies ( res, act [ 'save_cookies' ] )
            if "fields" in act:
                self.rt.fields(res, act["fields"])
            if "tests" in act:
                self.rt.check(res, act["tests"])
            if "dumps" in act:
                self.rt.dumps(res, act["dumps"])

        return True

    def _method_get(self, act):
        if "method" not in act:
            act["method"] = "get"
        return self._method_exec(act)

    def _method_post(self, act):
        if "method" not in act:
            act["method"] = "post"
        return self._method_exec(act)

    def _method_delete(self, act):
        if "method" not in act:
            act["method"] = "delete"
        return self._method_exec(act)

    def _method_patch(self, act):
        if "method" not in act:
            act["method"] = "patch"
        return self._method_exec(act)

    def _method_put(self, act):
        if "method" not in act:
            act["method"] = "put"
        return self._method_exec(act)

    def _method_section(self, act):
        title = act.get("title", act.get("name", "SECTION TITLE MISSING"))
        if not self.quiet:
            print("\n%s====== %s" % (self.rt._tabs(), xcolored(self, title, "green")))

        self.rt.section_start(title)
        self._actions(act["actions"])
        self.rt.section_end()

        if not self.quiet:
            print(
                "%s=========================================== \n" % (self.rt._tabs(),)
            )

        return True

    def _method_copy(self, act):
        self.rt.copy_val(act["from"], act["to"])

        return True

    def _method_dump(self, act):
        """
        Dump variable values to console and/or log file.

        Args:
            act: Action dict with optional 'fields' (array of var names)
                 and optional 'print' (bool, defaults to True)
        """
        fields = act.get("fields")  # None if not specified
        do_print = act.get("print", True)  # Default to True

        self.rt.dump(fields, do_print)

        return True

    def _method_set(self, act):
        self.rt.set_val(act["key"], act["value"])

        return True

    def _resolve_fname(self, fname):
        if not fname.startswith("/"):
            path = self._paths[-1]
            fname = os.path.abspath(os.path.join(path, fname))

        if not os.path.exists(fname):
            raise RESTestError("could not open file: %s" % fname)

        return fname

    def _method_include(self, act):
        fname = self._resolve_fname(act["filename"])

        self._paths.append(os.path.dirname(fname))

        script = self._json_load(fname)

        # 2.5.0 - Display included filename in console (only if show_filename is true)
        if act.get("show_filename", False):
            print(
                "\n%s\n%s %s\n%s\n"
                % (
                    xcolored(self, "=" * 80, "cyan"),
                    xcolored(self, "INCLUDING FILE:", "white", "on_blue", ["bold"]),
                    xcolored(self, fname, "yellow", attrs=["bold"]),
                    xcolored(self, "=" * 80, "cyan"),
                )
            )

        skip_include = False
        if script.get("run-once", False) and fname in self._included:
            skip_include = True
        if not skip_include:
            self._included[fname] = 1
            if "name" in act:
                name = act["name"].lower()
                self._batches[name] = script["actions"]

            if "exec" in act and act["exec"] is True:
                self._actions(script["actions"])

        self._paths.pop()

        return True

    def _method_batch_set(self, act):
        name = act["name"].lower()
        actions = act["actions"]
        self._batches[name] = actions

        return True

    def _method_batch_exec(self, act):
        name = act["name"].lower()
        actions = self._batches.get(name)

        # 2.1.0 - support for batch not found
        if not actions:
            sys.stderr.write(
                "%s: batch %s not found\n"
                % (xcolored(self, "ERROR", "red", "on_white", ["reverse"]), name)
            )

            # List all available batches keys
            for k in self._batches.keys():
                print("  - %s\n" % k)

            return False

        self._actions(actions)

        return True

    def _method_rem(self, act):
        return True

    def _method_code(self, act):
        """
        Execute the Python lines in act["code"] (globals interpolated with %(var)s).

        Raises:
            RESTestError: If code execution was not enabled with --allow-code
        """
        if not self.allow_code:
            raise RESTestError(
                "'code' action is disabled: it runs arbitrary Python. "
                "Use --allow-code to enable it"
            )

        code = ("\n".join(act["code"])) % self.rt.globals
        print("---- CODE: ", code)
        exec(code)

        return True

    # 2.0.2 - support for sleep action
    def _method_sleep(self, act):
        self.rt.sleep(act["ms"])

        return True

    def _method_if(self, act):
        """
        Run the nested actions only when the condition passes.

        The condition uses the same 'field' / 'mode' / 'value' keys of a test,
        but 'field' is a variable name (not a response path).

        Args:
            act: Action dict with 'field', optional 'mode' / 'value' and 'actions'

        Returns:
            True (a false condition is not an error)
        """
        field = self.rt._expand_var(act["field"])
        current = self.rt.globals.get(field)
        err = self.rt._check(act, field, current)

        if not err:
            self._actions(act.get("actions", []))

        return True

    def _parse_system(self):
        """
        Apply the script "system" options to the engine.

        Only the options in SYSTEM_KEYS are accepted: unknown ones are ignored
        with a warning, so a script cannot overwrite the engine internals.
        """
        self.rt.sections = []

        system = self.script.get("system")

        if not system:
            return

        global_headers = None
        for k, v in system.items():
            if k not in SYSTEM_KEYS:
                sys.stderr.write(
                    "%s unknown 'system' option ignored: %s\n"
                    % (xcolored(self, "WARNING", "yellow"), k)
                )
                continue

            if k == "global_headers":
                global_headers = v
                continue

            if k == "base_url" and isinstance(v, str):
                v = v.rstrip("/")

            setattr(self.rt, k, v)

        # Headers priority: global_headers < headers < request headers
        if global_headers:
            self.rt.headers = {**global_headers, **self.rt.headers}

    def _open_script(self, fname):
        """Open a script file, transparently handling .gz and .bz2 compression."""
        if fname.endswith(".gz"):
            return gzip.open(fname, "r")
        if fname.endswith(".bz2"):
            return bz2.BZ2File(fname, "r")

        return open(fname, "r", encoding="utf-8")

    def _json_load(self, fname):
        """
        Load and parse a JSON script file.

        Raises:
            RESTestError: If the file cannot be read or is not valid JSON
        """
        try:
            with self._open_script(fname) as f:
                data = json.load(f)
        except (OSError, ValueError, EOFError) as e:
            raise RESTestError("error loading JSON file: %s\n%s" % (fname, e)) from e

        if self.debug_file_name:
            print(
                "\n%s\n%s: executing file %s\n%s\n"
                % (
                    "=" * 70,
                    xcolored(self, "DEBUG", "blue"),
                    xcolored(self, fname, "yellow"),
                    "=" * 70,
                )
            )

        return data
