#!/usr/bin/env python3
"""M2a gate: audit kicad/lib/neo_n1.kicad_sym against primary sources.

Checks per symbol:
1. exact pin-number -> pin-name mapping (source: Nordic PS ballout tables /
   pSemi datasheet, transcribed below)
2. all 48 nRF5340 GPIOs present under their Nordic balls
3. pin numbers unique; symbol pin numbers all exist as footprint pads

Exit 0 = zero diffs. Any diff prints and exits 1.

Sources (transcribed 2026-11-21):
- nRF5340 PS, aQFN94 pin assignments (docs.nordicsemi.com ps_nrf5340)
- nPM1300 PS, QFN32 pin assignments (docs.nordicsemi.com ps_npm1300)
- nRF7002 PS QFN reference schematic (pin numbers 1,7,8,9,10 verified;
  full function set matches PS signal names) + SnapEDA pinout
- PE4259 datasheet DOC-03694-5 Table 7
"""
import re
import sys
from pathlib import Path

from kicad_sexpr import parse, find_first, find_all
from symbol_inspect import pins_of

HERE = Path(__file__).resolve().parent
LIB = HERE.parent / "lib" / "neo_n1.kicad_sym"
FP_DIR = HERE.parent / "lib" / "neo_n1_footprints.pretty"

# --- nRF5340-QKxx: GPIO -> ball (Nordic PS aQFN94 table, all 48) ---------
NRF5340_GPIO_BALL = {
    "P0.00": "N1", "P0.01": "R1", "P0.02": "W1", "P0.03": "AA1",
    "P0.04": "V2", "P0.05": "Y2", "P0.06": "AB2", "P0.07": "AD2",
    "P0.08": "AH2", "P0.09": "AJ1", "P0.10": "AK2", "P0.11": "AK4",
    "P0.12": "AK6", "P0.13": "AL5", "P0.14": "AK8", "P0.15": "AK10",
    "P0.16": "AL9", "P0.17": "AK12", "P0.18": "AK14", "P0.19": "AL13",
    "P0.20": "AK16", "P0.21": "AL15", "P0.22": "AK18", "P0.23": "AK20",
    "P0.24": "AL27", "P0.25": "AK28", "P0.26": "AL29", "P0.27": "AK30",
    "P0.28": "AE31", "P0.29": "U31", "P0.30": "B24", "P0.31": "B22",
    "P1.00": "M2", "P1.01": "P2", "P1.02": "AE1", "P1.03": "AF2",
    "P1.04": "AL19", "P1.05": "AK22", "P1.06": "AL21", "P1.07": "AK24",
    "P1.08": "AL23", "P1.09": "AK26", "P1.10": "R31", "P1.11": "B20",
    "P1.12": "B18", "P1.13": "A17", "P1.14": "B16", "P1.15": "B14",
}
NRF5340_EXTRA = {
    "A5": "VBUS", "B2": "D+", "B4": "D-", "B6": "DECUSB",
    "W31": "SWDCLK", "AA31": "SWDIO", "AC31": "RESET",
    "L31": "ANT", "C31": "XC1", "B30": "XC2", "E1": "VDDH",
}

# --- exact pin-number -> name maps ----------------------------------------
NRF7002 = {
    "1": "OTPVDD", "2": "NC", "3": "NC", "4": "NC", "5": "NC", "6": "NC",
    "7": "TXRF1", "8": "PAVDD1", "9": "TXRF0", "10": "PAVDD0",
    "11": "SXLDO", "12": "PALDO", "13": "VBAT", "14": "RFVDD",
    "15": "RFBUCKVDD", "16": "XOLDO", "17": "XOP", "18": "XON",
    "19": "AFELDO", "20": "AFEVBAT", "21": "NC", "22": "NC", "23": "NC",
    "24": "NC", "25": "BUCKVBAT", "26": "BUCKOUT",
    "29": "BUCKVMID", "30": "BUCKEN", "31": "BUCKVBATS", "32": "PWRBUCKVDD",
    "33": "DIGVDD", "34": "PWRIOVDD",
    "35": "QSPI_CLK/SPI_CLK", "36": "QSPI_SS/SPI_SS",
    "37": "QSPI_DATA0/SPI_MOSI", "38": "QSPI_DATA1/SPI_MISO",
    "39": "QSPI_DATA2", "40": "QSPI_DATA3",
    "41": "COEX_STATUS0", "42": "COEX_REQ", "43": "COEX_GRANT",
    "44": "SW_CTRL0", "45": "SW_CTRL1", "46": "HOST_IRQ",
    "48": "IOVDD", "27": "BUCKVSS", "28": "BUCKVSS", "47": "VSS", "49": "VSS",
}
NPM1300 = {
    "1": "VOUT1", "2": "PVSS1", "3": "SW1", "4": "PVDD", "5": "SW2",
    "6": "PVSS2", "7": "GPIO0", "8": "GPIO1", "9": "GPIO2", "10": "GPIO3",
    "11": "GPIO4", "12": "VDDIO", "13": "SDA", "14": "SCL", "15": "SHPHLD",
    "16": "VSET2", "17": "VSET1", "18": "NTC", "19": "VBAT", "20": "VSYS",
    "21": "VBUS", "22": "VBUSOUT", "23": "CC1", "24": "CC2", "25": "LED0",
    "26": "LED1", "27": "LED2", "28": "LSIN1/VINLDO1",
    "29": "LSOUT1/VOUTLDO1", "30": "LSIN2/VINLDO2", "31": "LSOUT2/VOUTLDO2",
    "32": "VOUT2", "33": "AVSS",
}
PE4259 = {
    "1": "RF1", "2": "GND", "3": "RF2", "4": "CTRL", "5": "RFC",
    "6": "CTRL/VDD",
}

FOOTPRINT_FOR = {
    "nRF5340-QKxx": "XCVR_NRF5340-QKAA-R7.kicad_mod",
    "NRF7002-QFAA-R7": "IC_NRF7002-QFAA-R7.kicad_mod",
    "NPM1300-QEAA-R7": "QFN50P500X500X90-33N_NPM1300.kicad_mod",
    "PE4259": "SOT65P215X110-6N_PE4259.kicad_mod",
}


def norm(name: str) -> str:
    """Normalize pin names: strip KiCad overbar markup, case-fold."""
    name = name.replace("~{", "").replace("}", "").replace("~", "")
    return name.strip().upper()


def load_lib(path: Path):
    root = parse(path.read_text(encoding="utf-8", errors="replace"))
    libnode = find_first(root, "kicad_symbol_lib")
    out = {}
    for sym in find_all(libnode or root, "symbol"):
        if len(sym) > 1:
            out[str(sym[1])] = pins_of(sym)
    return out


def fp_pads(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    nums = set()
    for m in re.finditer(r'\(pad (?:\"([^\"]+)\"|([^\s\)]+))', text):
        nums.add(m.group(1) or m.group(2))
    return nums


def main() -> int:
    diffs = []
    syms = load_lib(LIB)
    for expected in ("nRF5340-QKxx", "NRF7002-QFAA-R7", "NPM1300-QEAA-R7", "PE4259"):
        if expected not in syms:
            diffs.append(f"missing symbol {expected}")
    if diffs:
        print("\n".join(diffs))
        return 1

    # 1+2: nRF5340
    pins = {p[0]: p[1] for p in syms["nRF5340-QKxx"]}
    if len(pins) != len(syms["nRF5340-QKxx"]):
        diffs.append("nRF5340: duplicate pin numbers")
    gpio_map = {}
    for pnum, pname in pins.items():
        for g in re.findall(r"P[01]\.\d\d", pname):
            gpio_map.setdefault(g, pnum)
    for gpio, ball in NRF5340_GPIO_BALL.items():
        if gpio not in gpio_map:
            diffs.append(f"nRF5340: GPIO {gpio} missing from symbol")
        elif gpio_map[gpio] != ball:
            diffs.append(f"nRF5340: {gpio} on {gpio_map[gpio]}, Nordic says {ball}")
    for ball, name in NRF5340_EXTRA.items():
        got = pins.get(ball)
        if got is None:
            diffs.append(f"nRF5340: ball {ball} missing")
        elif norm(got) != norm(name):
            diffs.append(f"nRF5340: ball {ball} is {got!r}, expected {name!r}")

    # 1: exact maps for vendor symbols
    for symname, want in (("NRF7002-QFAA-R7", NRF7002),
                          ("NPM1300-QEAA-R7", NPM1300),
                          ("PE4259", PE4259)):
        pins = {p[0]: p[1] for p in syms[symname]}
        if len(pins) != len(syms[symname]):
            diffs.append(f"{symname}: duplicate pin numbers")
        for pnum, name in want.items():
            got = pins.get(pnum)
            if got is None:
                diffs.append(f"{symname}: pin {pnum} missing")
            elif norm(got) != norm(name):
                diffs.append(f"{symname}: pin {pnum} is {got!r}, expected {name!r}")
        extras = set(pins) - set(want)
        if extras:
            diffs.append(f"{symname}: unexpected pins {sorted(extras)}")

    # 3: symbol pins must exist as footprint pads
    for symname, fp in FOOTPRINT_FOR.items():
        pads = fp_pads(FP_DIR / fp)
        sym_nums = {p[0] for p in syms[symname]}
        missing = {n for n in sym_nums if n not in pads}
        if missing:
            diffs.append(f"{symname}: pin numbers absent from {fp}: {sorted(missing)}")
        extra = pads - sym_nums
        if extra:
            print(f"INFO: {symname}: {fp} has {len(extra)} pads not in symbol "
                  f"(GND ring/corners - verify vs datasheet mech drawing at M3): "
                  f"{sorted(extra)[:8]}{'...' if len(extra) > 8 else ''}")

    if diffs:
        print(f"AUDIT FAIL: {len(diffs)} diffs")
        for d in diffs:
            print("  -", d)
        return 1
    print("AUDIT PASS: zero diffs "
          f"({len(syms)} symbols: "
          + ", ".join(f"{k}={len(v)}pins" for k, v in syms.items()) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
