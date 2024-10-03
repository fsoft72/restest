#!/usr/bin/env python3

import copy


def deepcopy(o):
    return copy.deepcopy(o)


def size2str(size):
    size = int(size)
    if size < 1024:
        return str(size) + "B"
    elif size < 1024 * 1024:
        return str(size // 1024) + "KB"
    elif size < 1024 * 1024 * 1024:
        return str(size // 1024 // 1024) + "MB"
    else:
        return str(size // 1024 // 1024 // 1024) + "GB"
