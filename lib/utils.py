#!/usr/bin/env python3


def size2str(size):
    """Return a human readable size (B, KB, MB, GB) for a number of bytes."""
    size = int(size)
    if size < 1024:
        return str(size) + "B"
    elif size < 1024 * 1024:
        return str(size // 1024) + "KB"
    elif size < 1024 * 1024 * 1024:
        return str(size // 1024 // 1024) + "MB"
    else:
        return str(size // 1024 // 1024 // 1024) + "GB"
