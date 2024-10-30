#!/usr/bin/env python3
#
# restest
#
# written by Fabio Rotondo <fabio.rotondo@gmail.com>
#

VERSION = "2.2.0"

import argparse
import os
import time
import json

from lib.parser import RESTestParser
from lib.postman_exp import PostmanExporter


def main():
    parser = argparse.ArgumentParser(
        description="RESTest v%s the easy REST test manager - by Fabio Rotondo (fabio.rotondo@gmail.com)"
        % VERSION
    )

    parser.add_argument("file", nargs="+", help="Files containing the tests")
    parser.add_argument(
        "--auth-mode",
        type=str,
        choices=["auth", "no"],
        default="auth",
        help="Authentication mode. Choose between 'auth' or 'no', defaults to 'auth'",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        help="Base URL. This string overrides the 'system' parameter in JSON file",
    )
    parser.add_argument("--csv", type=str, help="Export results to a CSV file")
    parser.add_argument(
        "--curl",
        action="store_true",
        help="Dumps CURL also on console (defaults on log only",
    )
    parser.add_argument(
        "--delay", type=int, help="Delay in milliseconds between requests"
    )
    parser.add_argument(
        "--dont-stop-on-error",
        action="store_true",
        help="Flag to stop RESTest on error. This flag overrides the 'system' parameter in JSON file",
    )
    parser.add_argument(
        "--dry", action="store_true", help="If set, no request is done for real"
    )
    parser.add_argument(
        "--env",
        action="store_true",
        help="If set, global vars will contain also environment variables",
    )
    parser.add_argument(
        "--env-load",
        type=str,
        help="If set, global vars will be loaded from the specified file",
    )
    parser.add_argument(
        "--env-save",
        type=str,
        help="If set, global vars will be saved to specified file",
    )
    parser.add_argument(
        "--key",
        type=str,
        nargs="+",
        help="One or more keys to be added to the globals dict use key:value format",
    )
    parser.add_argument(
        "--log", type=str, help="Custom log file overriding the one in 'system'"
    )
    parser.add_argument(
        "--log-clean",
        action="store_true",
        help="Clean the logfile before starting",
    )
    parser.add_argument(
        "--no-colors",
        action="store_true",
        help="If set, colors in console output are disabled",
    )
    parser.add_argument(
        "--postman", type=str, help="Export activity to a Postman JSON file"
    )
    parser.add_argument(
        "--postman-auth-name", type=str, help="Name of the authorization header name"
    )
    parser.add_argument(
        "--postman-auth-value", type=str, help="Value to use for authorization header"
    )
    parser.add_argument(
        "--postman-base-url",
        type=str,
        help="The base url to use in Postman instead of the real host",
    )
    parser.add_argument("--postman-name", type=str, help="The Postman Collection name")
    parser.add_argument("--prefix", type=str, help="The API prefix URL")
    parser.add_argument(
        "--quiet", action="store_true", help="If set, no output on console"
    )
    parser.add_argument("--version", action="version", version=f"v{VERSION}")

    args = parser.parse_args()

    postman = None
    if args.postman:
        postman = PostmanExporter(
            args.postman,
            args.postman_name,
            args.postman_base_url,
            args.postman_auth_name,
            args.postman_auth_value,
        )

    rt = RESTestParser(
        quiet=args.quiet,
        base_url=args.base_url,
        stop_on_error=not args.dont_stop_on_error,
        log_file=args.log,
        postman=postman,
        curl=args.curl,
        dry=args.dry,
        delay=args.delay,
        no_colors=args.no_colors,
        prefix=args.prefix,
        auth_mode=args.auth_mode,
        log_clean=args.log_clean,  # 2.2.0 - Added log_clean
    )

    args = parser.parse_args()

    postman = None
    if args.postman:
        postman = PostmanExporter(
            args.postman,
            args.postman_name,
            args.postman_base_url,
            args.postman_auth_name,
            args.postman_auth_value,
        )

    rt = RESTestParser(
        quiet=args.quiet,
        base_url=args.base_url,
        stop_on_error=not args.dont_stop_on_error,
        log_file=args.log,
        postman=postman,
        curl=args.curl,
        dry=args.dry,
        delay=args.delay,
        no_colors=args.no_colors,
        prefix=args.prefix,
        auth_mode=args.auth_mode,
    )

    if args.env_load:
        try:
            data = json.loads(open(args.env_load).read())
            for k, v in data.items():
                rt.rt.globals[k.lower()] = v
        except:  # noqa
            pass

    if args.env:
        for k, v in os.environ.items():
            rt.rt.globals[k.lower()] = v

    if args.key:
        for c in args.key:
            k, v = c.split(":")
            rt.rt.globals[k] = v

    start_time = time.time()
    for f in args.file:
        rt.open(f)

    end_time = time.time()
    total_time = int((end_time - start_time) * 1000) / 1000.0

    if postman:
        postman.save()

    print(
        "\n\n===== FINISHED. Total Errors: %s / %s [Total time: %f]"
        % (rt.rt._errors, rt.rt._tests, total_time)
    )

    if args.env_save:
        open(args.env_save, "w").write(json.dumps(rt.rt.globals, indent=4, default=str))

    if args.csv:
        rt.export_csv(args.csv)


if __name__ == "__main__":
    main()
