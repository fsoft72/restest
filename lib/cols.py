#!/usr/bin/env python3

from termcolor import colored
import io


def sprint(*args, **kwargs):
    sio = io.StringIO()
    print(*args, **kwargs, file=sio)
    return sio.getvalue().strip()


def xcolored(rt, *args, **kwargs):
    if rt.no_colors:
        return sprint(*args[:-1], **kwargs)
    return colored(*args, **kwargs)
