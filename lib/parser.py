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
import time

from .engine import RESTest
from .cols import xcolored as _c


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

        self._paths = []
        self._included = {}

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

    def _actions(self, actions):
        for act in actions:
            if "title" in act:
                print(act["title"])

            action = act.get("method", act.get("action", "")).lower()
            if action:
                meth = getattr(self, "_method_" + action)
                meth(act)

            if "actions" in act:
                self._actions(act["actions"])

    def _parse_files(self, dct):
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

    def _send_req(self, act):
        m = act["method"].upper()

        auth = act.get("auth", True)
        content = act.get("content", "json")

        files = self._parse_files(act.get("files", {}))

        if m == "POST":
            _col = "blue"
        elif m == "GET":
            _col = "green"
        elif m == "DELETE":
            _col = "red"
        else:
            _col = "white"

        params = act.get("params", act.get("data", {}))
        if not self.quiet:
            sys.stdout.write(
                "%s %s %s %s %s %s"
                % (
                    self.rt._tabs(),
                    _c(self, "%-6s" % m, _col),
                    _c(self, "%-35s" % act.get("url", ""), "yellow"),
                    _c(self, params, "green"),
                    "auth:",
                    _c(self, auth, "blue"),
                )
            )
            sys.stdout.flush()

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
                % (_c(self, "WARNING", "yellow"))
            )
            ignore = act["skip_error"]

        # get current time in milliseconds
        start_time = int(round(1000 * time.time()))

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
        )

        # get current time in milliseconds
        end_time = int(round(1000 * time.time()))

        if not self.quiet:
            if res.status_code < 300:
                status = _c(self, "%-3s" % res.status_code, "green")
            elif res.status_code < 500:
                status = _c(
                    self, "%-3s" % res.status_code, "yellow", "on_grey", ["reverse"]
                )
            else:
                status = _c(
                    self,
                    "%-3s" % res.status_code,
                    "red",
                    "on_grey",
                    ["reverse", "blink"],
                )

            sys.stdout.write(
                " - status: %s - t: %s ms / %s s\n"
                % (status, (end_time - start_time), (end_time - start_time) / 1000)
            )

        return res

    def _method_exec(self, act):
        res = self._send_req(act)

        # if 'save_cookies' in act: self.rt.save_cookies ( res, act [ 'save_cookies' ] )
        if "fields" in act:
            self.rt.fields(res, act["fields"])
        if "tests" in act:
            self.rt.check(res, act["tests"])
        if "dumps" in act:
            self.rt.dumps(res, act["dumps"])

    def _method_get(self, act):
        if "method" not in act:
            act["method"] = "get"
        self._method_exec(act)

    def _method_post(self, act):
        if "method" not in act:
            act["method"] = "post"
        self._method_exec(act)

    def _method_delete(self, act):
        if "method" not in act:
            act["method"] = "delete"
        self._method_exec(act)

    def _method_patch(self, act):
        if "method" not in act:
            act["method"] = "patch"
        self._method_exec(act)

    def _method_put(self, act):
        if "method" not in act:
            act["method"] = "put"
        self._method_exec(act)

    def _method_section(self, act):
        title = act.get("title", act.get("name", "SECTION TITLE MISSING"))
        if not self.quiet:
            print("\n%s====== %s" % (self.rt._tabs(), _c(self, title, "green")))

        self.rt.section_start(title)
        self._actions(act["actions"])
        self.rt.section_end()

        if not self.quiet:
            print(
                "%s=========================================== \n" % (self.rt._tabs(),)
            )

    def _method_copy(self, act):
        self.rt.copy_val(act["from"], act["to"])

    def _method_dump(self, act):
        self.rt.dump(act["fields"], act.get("print"))

    def _method_set(self, act):
        self.rt.set_val(act["key"], act["value"])

    def _resolve_fname(self, fname):
        if not fname.startswith("/"):
            path = self._paths[-1]
            fname = os.path.abspath(os.path.join(path, fname))

        if not os.path.exists(fname):
            sys.stderr.write("ERROR: could not open file: %s\n" % fname)
            sys.exit(1)

        return fname

    def _method_include(self, act):
        fname = self._resolve_fname(act["filename"])

        self._paths.append(os.path.dirname(fname))

        script = self._json_load(fname)

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

    def _method_batch_set(self, act):
        name = act["name"].lower()
        actions = act["actions"]
        self._batches[name] = actions

    def _method_batch_exec(self, act):
        name = act["name"].lower()
        actions = self._batches.get(name)
        if not actions:
            sys.stderr.write(
                _c(self, "\nERROR:", "red")
                + " could not execute: %s\n" % _c(self, name, "white")
            )
            self.rt._dump_keys(self._batches, no_values=True)
            sys.exit(1)

        self._actions(actions)

    def _method_rem(self, act):
        pass

    def _method_code(self, act):
        code = ("\n".join(act["code"])) % self.rt.globals
        print("---- CODE: ", code)
        exec(code)

    def _method_if(self, act):
        err = self.rt._check(act, act["field"], act.get("value", 0))

        print("---- IF RES: ", err, act)

        self._actions(act["actions"])

    def _parse_system(self):
        self.rt.sections = []

        system = self.script.get("system")

        if not system:
            return

        for k, v in system.items():
            setattr(self.rt, k, v)

    def _json_load(self, fname):
        # load gzip file
        if fname.endswith(".gz"):
            f = gzip.open(fname, "r")
        elif fname.endswith(".bz2"):
            f = bz2.BZ2File(fname, "r")
        else:
            f = open(fname, "r", encoding="utf-8")

        data = json.load(f)
        f.close()

        return data
