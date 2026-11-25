#!/usr/bin/env python3

import re
import sys

# s = "[id='course.080ca4b4e3cb4e1e1b6b99776e8fb621.3tk0']"
# a regex that splits s on "[", "]", "=", ".", "!" and keeps the content of single and double quotes in one piece
# so that the result is: ["[", "id", "=", "'course.080ca4b4e3cb4e1e1b6b99776e8fb621.3tk0'", "]"]

rx_split = re.compile(r"""(\[|\]|=|!|\.|'.*?'|".*?")""")


def _is_int(txt):
    """Return True when txt is a base 10 integer."""
    try:
        int(str(txt), 10)
        return True
    except (ValueError, TypeError):
        return False


def _parse_square(tokens, pos):
    """Parse the content of [...]: an index or a nested pattern. Returns (node, next_pos)."""
    tok = tokens[pos]

    if _is_int(tok):
        return {"mode": "pos", "value": int(str(tok), 10)}, pos + 2

    return _parser(tokens, pos, is_pattern=True)


def _extract_value(tokens, pos, equal=False):
    """Parse the value after '=' or '!=' into an equal / not_equal node. Returns (node, next_pos)."""
    mode = "equal"
    if not equal:
        mode = "not_equal"
        pos = pos + 1

    tok = tokens[pos]

    # if tok starts with a quote or double quote, then we remove them
    if tok[0] in ("'", '"'):
        tok = tok[1:-1]

    pos = pos + 1

    return {"mode": mode, "value": tok}, pos


def _parser(tokens, pos, is_pattern=False):
    """Turn tokens into a list of path nodes, starting at pos. Returns (nodes, next_pos)."""
    res = []
    while pos < len(tokens):
        tok = tokens[pos]
        pos += 1
        if not tok:
            continue

        if tok not in (".", "!", "=", "[", "]"):
            if not is_pattern:
                res.append({"mode": "label", "value": tok})
            else:
                res.append({"mode": "pattern", "value": tok})

        elif tok == "[":
            parsed, pos = _parse_square(tokens, pos)
            res.append(parsed)
        elif tok == "]":
            return res, pos
        elif tok == "=":
            parsed, pos = _extract_value(tokens, pos, equal=True)
            res.append(parsed)
        elif tok == "!":
            parsed, pos = _extract_value(tokens, pos, equal=False)
            res.append(parsed)

    return res, pos


def path_parser(path):
    """Parse a path like 'users.[id=3].name' into a list of nodes (see _parser)."""
    tokens = [t for t in rx_split.split(path) if t]

    return _parser(tokens, 0)[0]


def _find_in_list(field_name, tok, elem: list):
    """Find the first element of a list whose field_name matches the equal / not_equal node.

    Returns:
        Tuple (element or None, error or None)
    """
    equal = tok["mode"] == "equal"
    val = str(tok["value"])

    pos = 0
    found = False
    el = None

    if not isinstance(elem, list):
        return None, "Expected a list, got: %s" % type(elem)

    while pos < len(elem):
        el = elem[pos]

        if field_name not in el:
            return None, "Could not find key: %s" % field_name

        if str(el[field_name]) == val:
            found = True

        if not equal:
            found = not found

        if found:
            break

        pos += 1

    if not found:
        return None, None
    return el, None


def _expand(parsed_path, pos, dct):
    """Walk dct following the parsed path nodes from pos.

    Returns:
        Tuple (value or None, error message or "")
    """
    elem = dct
    field_name = ""
    err = ""

    while pos < len(parsed_path):
        tok = parsed_path[pos]
        pos += 1

        if isinstance(tok, list):
            elem, err = _expand(tok, 0, elem)
        elif tok["mode"] == "label":
            n = tok["value"]
            if not elem:
                elem = {}
            if n in elem:
                elem = elem[n]  # tok [ 'value' ] ]
            else:
                err = "Could not find key: '%s'" % n
        elif tok["mode"] == "pos":
            _pos = tok["value"]
            if len(elem) > _pos:
                elem = elem[_pos]
            else:
                err = "Index out of bounds: %s (max: %s) [%s]" % (
                    _pos,
                    len(elem) - 1,
                    elem,
                )
        elif tok["mode"] == "pattern":
            field_name = tok["value"]
        elif tok["mode"] in ("equal", "not_equal"):
            elem, err = _find_in_list(field_name, tok, elem)

        if err:
            return None, err

    return elem, err


def _check_path_quotes(path):
    """
    if a path is similar to [email=aaab.bbb@gmail.com] we need to warn the user
    that the email should be enclosed in single quotes

    In general, path with   =xxx.yyyy.xxx  (a dot or more after the =) should be enclosed in single quotes
    """
    pos = path.find("=")

    # if there is no = in the path, then we are good
    if pos == -1:
        return True

    # if there is a ' after the =, then we are good
    if path[pos + 1] == "'":
        return True

    # if there is at least one "." before the "]" then we should warn the user
    end_pos = path.find("]", pos)

    if path.find(".", pos, end_pos) != -1:
        sys.stdout.write(
            "WARNING: in path '%s', value after \"=\" should be enclosed in single quotes.\n"
            % path
        )

        return False


def expand_value(path, dct):
    """
    Expand a path expression against a dictionary/JSON structure.

    If path starts with '#', returns the length of the value at that path.
    For arrays and strings, returns len(). For None, returns 0.
    For other types (numbers, objects), raises an error.

    Args:
        path: Path expression (e.g., "data.items" or "#data.items" for length)
        dct: Dictionary to expand against

    Returns:
        Tuple of (value, error_message)
    """
    # Check for length extraction prefix
    get_length = path.startswith("#")
    if get_length:
        path = path[1:]

    _check_path_quotes(path)

    parsed_path = path_parser(path)

    res, err = _expand(parsed_path, 0, dct)

    # Handle length extraction
    if get_length and not err:
        if res is None:
            res = 0
        elif isinstance(res, (list, str)):
            res = len(res)
        elif isinstance(res, dict):
            # For objects, return number of keys
            res = len(res)
        elif isinstance(res, (int, float, bool)):
            err = f"Cannot get length of {type(res).__name__} (at path: {path})"
            res = None
        else:
            # Fallback: try to get length if object has __len__
            try:
                res = len(res)
            except TypeError:
                err = f"Cannot get length of {type(res).__name__} (at path: {path})"
                res = None

    return res, err
