#!/usr/bin/env python3
"""Inspect a KiCad .kicad_sym: list symbols with pin number/name/type/unit.

Usage: python symbol_inspect.py <lib1.kicad_sym> [lib2...]
KiCad-bundled python or any python3 with this dir on sys.path.
"""
from __future__ import annotations

import sys
from pathlib import Path

from kicad_sexpr import find_all, find_first, parse


def pins_of(symbol):
    """Yield (number, name, type, unit) for every pin in a symbol node.

    Pins sit either directly on the symbol (single-unit SamacSys style) or
    inside unit sub-symbols named <sym>_<unit>_<style> (KiCad stock style).
    Deduped by (number, name, type): repeated pins across units appear once.
    """
    out: list[tuple[str, str, str, str]] = []
    direct = find_all(symbol, "pin")
    if direct:
        for pin in direct:
            out.append(_pin_tuple(pin, "1"))
    for unit in find_all(symbol, "symbol"):
        unit_name = str(unit[1]) if len(unit) > 1 else "?"
        for pin in find_all(unit, "pin"):
            out.append(_pin_tuple(pin, unit_name))
    seen, deduped = set(), []
    for item in out:
        key = item[:3]
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def _pin_tuple(pin, unit_name):
    ptype = pin[1] if len(pin) > 1 else "?"
    pname = pnum = ""
    for key in ("name", "number"):
        node = find_first(pin, key)
        if node and len(node) > 1:
            if key == "name":
                pname = node[1]
            else:
                pnum = node[1]
    return (pnum, pname, ptype, unit_name)


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    for lib_path in argv:
        text = Path(lib_path).read_text(encoding="utf-8", errors="replace")
        root = parse(text)
        libnode = find_first(root, "kicad_symbol_lib") or root
        syms = find_all(libnode, "symbol")
        # top-level symbols only (units are nested 'symbol' inside)
        for sym in syms:
            name = sym[1] if len(sym) > 1 else "?"
            pins = pins_of(sym)
            print(f"== {Path(lib_path).name} :: {name} :: {len(pins)} pins")
            for pnum, pname, ptype, unit in sorted(
                pins, key=lambda p: (p[0].zfill(6), p[1])
            ):
                print(f"   {pnum:>4}  {pname:<24} {ptype}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
