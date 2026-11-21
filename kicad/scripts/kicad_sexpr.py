#!/usr/bin/env python3
"""Minimal s-expression parser for KiCad files (stdlib only).

parse(text) -> nested list: atoms are str, quoted values keep their string
content, parens nest. Used by symbol_audit.py and netlist_audit.py.
"""
from __future__ import annotations

import re


def parse(text: str):
    """Parse KiCad s-expression text into nested Python lists."""
    pos, n = 0, len(text)
    stack = []
    # start with an implicit top-level list holder
    root: list = []
    stack.append(root)
    cur = root
    while pos < n:
        c = text[pos]
        if c in " \t\r\n":
            pos += 1
            continue
        if c == "(":
            new: list = []
            cur.append(new)
            stack.append(new)
            cur = new
            pos += 1
            continue
        if c == ")":
            stack.pop()
            if not stack:
                break  # malformed input: stop at unbalanced close
            cur = stack[-1]
            pos += 1
            continue
        if c == '"':
            j = pos + 1
            buf = []
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                    continue
                if text[j] == '"':
                    break
                buf.append(text[j])
                j += 1
            cur.append("".join(buf))
            pos = j + 1
            continue
        # bare atom: read until whitespace or paren
        j = pos
        while j < n and text[j] not in ' \t\r\n()"':
            j += 1
        cur.append(text[pos:j])
        pos = j
    return root


def find_all(node, key: str):
    """All direct children lists whose head == key."""
    if not isinstance(node, list):
        return []
    return [ch for ch in node if isinstance(ch, list) and ch and ch[0] == key]


def find_first(node, key: str):
    hits = find_all(node, key)
    return hits[0] if hits else None


_SAFE = re.compile(r"^[A-Za-z0-9_.+\-/][A-Za-z0-9_.+\-/]*$")


def _atom(s: str) -> str:
    if s and _SAFE.match(s):
        return s
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def dumps(node, indent=0) -> str:
    """Serialize a parsed node back to KiCad s-expr text.

    Top-level children get one line each; nested nodes stay inline. Strings
    are quoted only when they are not safe bare atoms, so output is stable
    for git diffs and re-parseable by parse().
    """
    if not isinstance(node, list):
        return _atom(str(node))
    head = node[0] if node and isinstance(node[0], str) else ""
    body = []
    for ch in node:
        if isinstance(ch, list):
            body.append(dumps(ch, indent + 1))
        else:
            body.append(_atom(str(ch)))
    pad = "\t" * indent
    if len(body) <= 1:
        return f"({' '.join(body)})"
    # long nodes: put children on their own indented lines
    inner = " ".join(body[:1])  # head atom first
    rest = "\n" + "\n".join(pad + "\t" + b for b in body[1:])
    return f"({inner}{rest}\n{pad})"
