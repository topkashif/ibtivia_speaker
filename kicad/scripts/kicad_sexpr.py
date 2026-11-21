#!/usr/bin/env python3
"""Minimal s-expression parser for KiCad files (stdlib only).

parse(text) -> nested list: atoms are str, quoted values keep their string
content, parens nest. Used by symbol_audit.py and netlist_audit.py.
"""
from __future__ import annotations


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
