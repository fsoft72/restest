#!/usr/bin/env python3

import re

# s = "[id='course.080ca4b4e3cb4e1e1b6b99776e8fb621.3tk0']"
# a regex that splits s on "[", "]", "=", ".", "!" and keeps the content of single and double quotes in one piece
# so that the result is: ["[", "id", "=", "'course.080ca4b4e3cb4e1e1b6b99776e8fb621.3tk0'", "]"]

rx_split = re.compile(r"""(\[|\]|=|!|\.|'.*?'|".*?")""")


def _is_int(txt):
    try:
        int(str(txt), 10)
        return True
    except:  # noqa
        return False


def _parse_square(tokens, pos):
    tok = tokens[pos]

    if _is_int(tok):
        return {"mode": "pos", "value": int(str(tok), 10)}, pos + 2

    return _parser(tokens, pos, is_pattern=True)


def _extract_value(tokens, pos, equal=False):
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
    tokens = [t for t in rx_split.split(path) if t]

    return _parser(tokens, 0)[0]


def _find_in_list(field_name, tok, elem: list):
    equal = tok["mode"] == "equal"
    val = str(tok["value"])

    pos = 0
    found = False
    el = None
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


def expand_value(path, dct):
    parsed_path = path_parser(path)

    res, err = _expand(parsed_path, 0, dct)

    return res, err


if __name__ == "__main__":
    # print ( path_parser ( "first.second.[0].third" ) )
    # print ( json.dumps ( path_parser ( "first.second.[user.key=5].third" ), indent = 4 ) )
    # print ( path_parser ( "first.second.[user.email!=example@gmail.com].third" ) )
    # print ( json.dumps ( path_parser ( "first.[3].[user.key=23].second.[1].name" ), indent = 4 ) )
    # print ( json.dumps ( path_parser ( "first.[sub[user.key=3]].second" ), indent=4 ) )
    x = {
        "type1": [
            {"name": "hello", "value": "world"},
            {"name": "ciao", "value": "mondo"},
        ],
        "users": [
            {
                "email": "test01@example.com",
                "id": 123,
                "perms": ["admin", "work", "home"],
            },
            {"email": "test02@example.com", "id": 999, "perms": ["do", "this"]},
        ],
        "nested": {
            "opts": [
                {
                    "name": "opt1",
                    "children": [
                        {"name": "child1", "value": 1},
                        {"name": "child2", "value": 2},
                    ],
                }
            ]
        },
    }
    dct = {
        "courses": [
            {
                "id": "course.080ca4b4e3cb4e1e1b6b99776e8fb621.3tk0",
                "slug": "course-test",
                "code": "course001",
                "id_owner": "user.8edb2cf662f639dcd3ac9e0c0c5a1816.bq2n",
                "visible": True,
                "tot_sections": 1,
                "tot_time": 600,
                "tot_lessons": 3,
                "type": "default",
                "max_students": 0,
                "num_students": 0,
                "revenue_platform": 30,
                "revenue_trainer": 70,
                "title": "Course Test",
                "id_product": "product.7aa9e1a1a3d39b7d09bd9d71f4e3d09d.ek75",
                "id_trainers": ["user.8edb2cf662f639dcd3ac9e0c0c5a1816.bq2n"],
                "description": "This is the updated description",
                "tags": [],
            }
        ]
    }
    # dct = json.loads(x)
    # print ( expand_value ( "type1.[0].name", dct ) )
    # print ( expand_value ( "type1.[0].value", dct ) )
    # print(expand_value("type1.[name=ciao].value", dct))
    # print ( expand_value ( "users.[id=123].perms", dct ) )
    # print(expand_value("nested.opts[name=opt1].children[name!=child2].value", dct))
    print(
        expand_value("courses.[id='course.080ca4b4e3cb4e1e1b6b99776e8fb621.3tk0']", dct)
    )
