#!/usr/bin/env python3
"""Assemble kicad/lib/neo_n1.kicad_sym + footprints + lib tables (M2a).

Strategy: copy each symbol node's RAW TEXT out of its source library
(balanced-paren scan, quote-aware) and concatenate into the project lib.
No s-expr re-serialization — KiCad's strict tokenizer rejects unquoted
string atoms, so re-emitting parsed trees is unsafe.

Sources:
- nRF5340-QKxx   : KiCad stock MCU_Nordic (94 balls + EP, Nordic ball names)
- NRF7002-QFAA-R7: kicad/lib/vendor (SnapEDA), numbering verified vs Nordic
                   PS QFN reference schematic (1=OTPVDD, 7=TXRF1, ...)
- NPM1300-QEAA-R7: kicad/lib/vendor (SnapEDA), 33 pins verified vs Nordic
                   PS QFN32 pin table (incl. EP=AVSS)
- PE4259         : kicad/lib/vendor, verified vs pSemi DOC-03694-5 Table 7
"""
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
KICAD = HERE.parent
LIB = KICAD / "lib"
VENDOR = LIB / "vendor"
STOCK = Path("C:/Program Files/KiCad/10.0/share/kicad/symbols")

VENDOR_7002 = VENDOR / "NRF7002-QFAA-R7" / "NRF7002-QFAA-R7.kicad_sym"
VENDOR_NPM = (VENDOR / "LIB_NPM1300-QEAA-R7" / "NPM1300-QEAA-R7" / "KiCad"
              / "NPM1300-QEAA-R7.kicad_sym")
VENDOR_PE = VENDOR / "PE4259" / "PE4259.kicad_sym"

FOOTPRINTS = [
    (VENDOR / "NRF5340-QKAA-R7" / "XCVR_NRF5340-QKAA-R7.kicad_mod",
     "XCVR_NRF5340-QKAA-R7.kicad_mod"),
    (VENDOR / "NRF7002-QFAA-R7" / "IC_NRF7002-QFAA-R7.kicad_mod",
     "IC_NRF7002-QFAA-R7.kicad_mod"),
    (VENDOR / "LIB_NPM1300-QEAA-R7" / "NPM1300-QEAA-R7" / "KiCad"
     / "QFN50P500X500X90-33N.kicad_mod", "QFN50P500X500X90-33N_NPM1300.kicad_mod"),
    (VENDOR / "PE4259" / "SOT65P215X110-6N.kicad_mod", "SOT65P215X110-6N_PE4259.kicad_mod"),
]


def extract_raw_symbol(text: str, name: str) -> str:
    """Return the raw source of top-level (symbol "name" ...) in a lib."""
    for m in re.finditer(r'\(symbol\s+"([^"]+)"', text):
        if m.group(1) != name:
            continue
        depth, i, n = 0, m.start(), len(text)
        in_str = False
        while i < n:
            c = text[i]
            if in_str:
                if c == "\\":
                    i += 2
                    continue
                if c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return text[m.start():i + 1]
            i += 1
    raise SystemExit(f"symbol {name!r} not found")


def lib_version(path: Path) -> str:
    m = re.search(r"\(version\s+(\d+)\)",
                  path.read_text(encoding="utf-8", errors="replace"))
    return m.group(1)


parts = [f"(kicad_symbol_lib\n\t(version {lib_version(STOCK / 'MCU_Nordic.kicad_sym')})\n"
         '\t(generator "neo_n1_project")\n'
         '\t(generator_version "10.0")\n']
parts.append("\t" + extract_raw_symbol(
    (STOCK / "MCU_Nordic.kicad_sym").read_text(encoding="utf-8", errors="replace"),
    "nRF5340-QKxx") + "\n")
for p in (VENDOR_7002, VENDOR_NPM, VENDOR_PE):
    parts.append("\t" + extract_raw_symbol(
        p.read_text(encoding="utf-8", errors="replace"), p.stem) + "\n")
parts.append(")\n")

out = LIB / "neo_n1.kicad_sym"
out.write_text("".join(parts), encoding="utf-8")
print("wrote", out)

fp_dir = LIB / "neo_n1_footprints.pretty"
fp_dir.mkdir(exist_ok=True)
for src, dst in FOOTPRINTS:
    data = src.read_text(encoding="utf-8", errors="replace")
    if dst.startswith("XCVR_NRF5340"):
        # SnapEDA numbered the die pad "104"; the stock symbol (and KiCad
        # convention) name it "EP" - rename so symbol pins map to pads.
        data = data.replace("(pad 104 smd rect", "(pad EP smd rect", 1)
    (fp_dir / dst).write_text(data, encoding="utf-8")
    print("copied", dst)

(KICAD / "sym-lib-table").write_text(
    '(sym_lib_table\n'
    '\t(version 7)\n'
    '\t(lib (name "neo_n1")(type "KiCad")(uri "${KIPRJMOD}/lib/neo_n1.kicad_sym")'
    '(options "")(descr "Neo N1 pinned symbols (datasheet-verified)"))\n'
    ')\n', encoding="utf-8")
(KICAD / "fp-lib-table").write_text(
    '(fp_lib_table\n'
    '\t(version 7)\n'
    '\t(lib (name "neo_n1_footprints")(type "KiCad")'
    '(uri "${KIPRJMOD}/lib/neo_n1_footprints.pretty")(options "")'
    '(descr "Neo N1 part-specific footprints"))\n'
    ')\n', encoding="utf-8")
print("wrote sym-lib-table, fp-lib-table")
