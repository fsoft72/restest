#!/usr/bin/env python3
#
# restest engine
#
# written by Fabio Rotondo (fabio.rotondo@gmail.com)
#

import copy
import json
import sys
import time
import urllib

import requests

from .path_parser import expand_value
from .cols import xcolored as _c


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
            open(self.log_file, "w").close()

    def _tabs(self, indent=0):
        return "\t" * (len(self.sections) + indent)

    def _parse_headers(self, r):
        heads = {}

        for k, v in r.headers.items():
            hk = k.lower()
            heads[hk] = r.headers[k]

        r._headers = heads

    def _log_write(self, txt):
        if not self.log_file:
            return

        fout = open(self.log_file, "a")
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

    def _log_resp(self, headers, resp):
        if not self.log_file:
            return

        self._log_write(
            """Headers:      %s
Status Code:  %s
Request Time: %s
Raw Response: %s
"""
            % (headers, resp.status_code, resp.elapsed.microseconds / 1000, resp.text)
        )

    def _log_curl(self, req):
        command = "curl -X {method} \\\n -H {headers} \\\n -d '{data}' \\\n '{uri}'"

        method = req.method
        uri = req.url
        # data = str ( req.body ) [ 2 : -1 ]   # quick and dirty way to remove b'...' from string
        try:
            data = req.body.decode("utf-8")
        except:  # noqa
            data = ""

        headers = ['"{0}: {1}"'.format(k, v) for k, v in req.headers.items()]
        headers = " \\\n -H ".join(headers)

        curl = command.format(method=method, headers=headers, data=data, uri=uri)
        self._log_write("\nCURL:         %s\n\n" % curl)

        if self.dump_curl_on_console:
            sys.stderr.write("\n\n%s\n\n" % curl)
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
            except:  # noqa
                sys.stderr.write(
                    _c(self, "ERROR", "red")
                    + " could not create Authorization template: %s"
                    % self.authorization_template
                )
                raise

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

    def _expand_list(self, lst):
        res = []
        for x in lst:
            if isinstance(x, str):
                res.append(self._get_v(x))
            elif isinstance(x, dict):
                res.append(self._expand_dict(x))
            else:
                res.append(x)

        return res

    def _expand_dict(self, dct):
        for k, v in dct.items():
            if isinstance(v, str) and v.find("%(") != -1:
                v = self._get_v(v)
            elif isinstance(v, dict):
                v = self._expand_dict(v)
            elif isinstance(v, list):
                v = self._expand_list(v)

            dct[k] = v

        return dct

    def _get_v(self, x):
        if isinstance(x, dict):
            return self._expand_dict(x)

        n = str(x)
        if n.find("%(") == -1:
            return x

        if n.find("__internal_") != -1:
            n = n.replace("__internal_", "")
            return n % self._internal_info

        return n % self.globals

    def _expand_var(self, v):
        globs = copy.copy(self.globals)
        globs["inner_count"] = self._inner_count

        try:
            if isinstance(v, list):
                v = self._expand_list(v)
            else:
                v = self._get_v(v)
        except:  # noqa
            sys.stderr.write(
                _c(self, "\nERROR:", "red")
                + " could not expand: %s\n" % _c(self, v, "white")
            )
            self._dump_globals()

            sys.exit(0)

        return v

    def _dump_globals(self):
        keys = list(self.globals.keys())
        if not keys:
            return

        keys.sort()

        max_len = max([len(x) for x in keys])

        for k in keys:
            # pad k to max_len
            sk = k.ljust(max_len)

            sys.stderr.write("    %s : %s\n" % (_c(self, sk, "white"), self.globals[k]))

    def _expand_data(self, data):
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

    def _object_compare(self, v1, v2):
        o1 = eval(v1)
        o2 = eval(v2)

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

        if r.status_code != status_code and self.stop_on_error:
            sys.stderr.write(
                """\n\n%s\n%s %s\n%s\n\n"""
                % (
                    "=" * 78,
                    _c(self, "REQUEST ERROR: ", "red"),
                    _c(self, r.text, "white"),
                    "=" * 78,
                )
            )
            sys.exit(1)

        ms = r.elapsed.microseconds / 1000
        if max_exec_time and ms > max_exec_time:
            sys.stderr.write(
                """%s\nTOO MUCH TIME ERROR (res: %s - expected: %s)\n%s\n"""
                % ("*" * 70, ms, max_exec_time, "*" * 70)
            )
            sys.exit(1)

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
            time.sleep(self.delay // 1000)

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
        j = resp.json()

        for k in fields:
            if isinstance(k, (list, tuple)):
                if len(k) == 2:
                    json_key = k[0]
                    glob_key = k[1]
                else:
                    json_key = k[0]
                    glob_key = k[0]
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
        sys.stderr.write(_c(self, "\n\n=== ERROR: ", "red") + "%s\n" % txt)
        self._log_write("\n\n*** ERROR: %s\n" % txt)
        if self.stop_on_error:
            sys.exit(1)
        self._errors += 1
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
        _key = self._expand_var(_key)
        _val = self._expand_var(_val)

        self.globals[_key] = _val

    def sleep(self, _ms):
        _ms = self._expand_var(_ms)
        time.sleep(int(_ms) / 1000)

    def _check(self, chk, field, v):
        current_val = self._expand_var(v)
        expected_val = self._expand_var(chk.get("value"))

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
            if current_val != expected_val:
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
            if current_val <= expected_val:
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
            if len(current_val) <= int(expected_val):
                return "FIELD: %s is BIGGER. Expected: %s got: %s" % cols
        elif mode in ("OBJ", "OBJECT"):
            if not self._object_compare(current_val, expected_val):
                return "FIELD: %s object values mismatch" % (_c(self, field, "white"))
        else:
            return "ERROR: unsupported test mode: %s " % mode

        if "save" in chk:
            self.globals[chk["save"]] = v

    def check(self, resp, checks):
        j = resp.json()

        for chk in checks:
            if "title" in chk:
                print("%s%s" % (self._tabs(1), chk["title"]))

            self._tests += 1

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

    def dump(self, fields, do_print=False):
        for f in fields:
            f = self._expand_var(f)
            v = self.globals[f]

            s = "==== %s: %s\n" % (f, json.dumps(v, indent=4, default=str))
            self._log_write(s)

            if do_print:
                print(s)

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
