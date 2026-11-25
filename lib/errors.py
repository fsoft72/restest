#!/usr/bin/env python3
#
# restest errors
#


class RESTestError(Exception):
    """
    Fatal error that stops the test run.

    Library code raises it instead of calling sys.exit(), so the engine can be
    embedded and tested. The CLI (restest.py) prints the message and exits 1.
    The message may already contain console colors.
    """
