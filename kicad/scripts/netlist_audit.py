#!/usr/bin/env python3
"""Netlist audit: exported KiCad netlist vs the hardware pin-map contract.

Per-block mode (default): audit one sheet's nets against an expected netlist
transcribed from `hardware_reference.md` §3 (pin map) + the datasheet-verified
design decisions recorded there. Full mode (--full): audit every sheet
(M2f acceptance).

Usage:
  python netlist_audit.py --block radio
  python netlist_audit.py --full

Exit 0 = zero diffs. Any diff prints and exits 1.

Sources:
- `hardware_reference.md` §3 pin map (firmware-extracted contract)
- nRF7002 PS v1.0 Figure 18 reference schematic (nRF7002 power/buck wiring)
- nRF5340 PS v1.3 §9.3 circuit configuration no. 3 (normal-voltage, QKAA,
  2x DCDC inductor, no NFC) + Table 214 config summary
- nRF7002 DK hardware files 0.7.2 (PCA10143) sheets 2/7 for topology
  cross-check (iovdd load switch, SW_CTRL0 -> antenna switch CTRL)
- pSemi PE42359 DS (DOC-13214) Table 5 single-pin control truth table
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from kicad_sexpr import parse, find_all, find_first

HERE = Path(__file__).resolve().parent
KICAD = HERE.parent  # kicad/ project dir
PROJ = KICAD / "neo_n1.kicad_sch"


# --------------------------------------------------------------------------
# Expected nets for the RADIO block (sheet sheets/radio.kicad_sch).
# Format: net name -> {ref: [pin numbers]}  ("EP" = exposed pad).
# Every entry traces to hardware_reference.md §3 or a PS/datasheet figure
# cited in the module docstring. Nets marked (BUS) leave the sheet; their
# far end is audited by the block that owns it.
# --------------------------------------------------------------------------
RADIO_EXPECTED = {
    # --- nRF5340 QSPI to nRF7002 (pin map: QSPI SCK/CSN P0.17/P0.18,
    #     IO0-IO3 P0.13-P0.16) ---
    "QSPI_SCK":   {"U1": ["AK12"], "U2": ["35"]},   # P0.17
    "QSPI_CSN":   {"U1": ["AK14"], "U2": ["36"]},   # P0.18
    "QSPI_IO0":   {"U1": ["AL5"],  "U2": ["37"]},   # P0.13
    "QSPI_IO1":   {"U1": ["AK8"],  "U2": ["38"]},   # P0.14
    "QSPI_IO2":   {"U1": ["AK10"], "U2": ["39"]},   # P0.15
    "QSPI_IO3":   {"U1": ["AL9"],  "U2": ["40"]},   # P0.16
    # --- nRF7002 control (pin map: iovdd-ctrl P0.26, BUCKEN P0.11,
    #     HOST_IRQ P0.12) ---
    "NRF70_BUCKEN":   {"U1": ["AK4"], "U2": ["30"]},   # P0.11
    "NRF70_HOST_IRQ": {"U1": ["AK6"], "U2": ["46"]},   # P0.12
    "NRF70_IOVDD_EN": {"U1": ["AL29"]},                # P0.26 -> iovdd LSW (M2c)
    # --- coex PTA (pin map: REQ P0.28, STATUS0 P0.25, GRANT P0.31,
    #     SWCTRL1 P0.30; nRF7002 PS Table 6 directions) ---
    "PTA_REQ":     {"U1": ["AE31"], "U2": ["42"]},  # P0.28 -> COEX_REQ in
    "PTA_STATUS0": {"U1": ["AK28"], "U2": ["41"]},  # P0.25 -> COEX_STATUS0 in
    "PTA_GRANT":   {"U1": ["B22"],  "U2": ["43"]},  # P0.31 <- COEX_GRANT out
    "PTA_SWCTRL1": {"U1": ["B24"],  "U2": ["45"]},  # P0.30 <- SW_CTRL1
    # --- RF front end: nRF7002 TXRF0 -> PE42359 RF1 (WiFi-active path),
    #     nRF5340 ANT -> shunt 0.7pF -> series 2.2nH -> RF2 (default/BLE
    #     path), RFC -> series 1.2pF -> shunt 2.7nH -> antenna.
    #     pSemi DS Table 5: CTRL high -> RFC-RF1; SW_CTRL0 asserts on
    #     nRF70 radio activity. Single-pin control (pin 6 = VDD).
    "NRF70_TXRF0":    {"U2": ["9"], "U5": ["1"]},
    "NRF53_ANT":      {"U1": ["L31"], },
    "NRF53_ANT_FILT": {"U5": ["3"]},
    "RF_ANT_FILT":    {"U5": ["5"]},
    "RF_ANT":         {},
    "RFSW_CTRL":      {"U2": ["44"]},
    # --- RF switch U5 PE42359 ---
    #     (U5 pins checked separately below: RF1/RF2/RFC join via series
    #     elements, so they get their own nets, not direct net equality.)
    # --- crystals: NO external load caps (firmware DTS tunes internal
    #     caps: hfxo 9 pF, lfxo 7 pF; tests/clip lfxo|hfxo shell commands) ---
    "HFXO_IN":  {"U1": ["C31"]},
    "HFXO_OUT": {"U1": ["B30"]},
    "LFXO_IN":  {"U1": ["N1"]},
    "LFXO_OUT": {"U1": ["R1"]},
    # --- nRF7002 own 40 MHz crystal (PS Table 19: Cl=8pF, ESR<=100 ohm;
    #     no external load caps; X3 pins merged from RADIO_PASSIVES) ---
    # --- nRF5340 power: PS v1.3 Table 214 config 3 (normal voltage):
    #     VDD and VDDH ALL tied to the external 3V3 rail (BUCK2 MAIN);
    #     VREGMAIN + VREGRADIO in DCDC mode (2x 10uH), VREGH unused
    #     (DCCH J1 left floating per PS 4.7.1/9.3 config 3). ---
    "MAIN_3V3": {"U1": ["E1", "B8", "C1", "L1", "U1", "A19", "B28", "E31",
                        "N31", "AJ31", "AG1", "AL3", "AL7", "AL11", "AL17",
                        "AL25", "AC1"]},
    # DCCD-DECD and DCC-DECR bridge through 10uH inductors: separate nets.
    "VREGMAIN_SW":  {"U1": ["B10"]},  # DCCD
    "VREGMAIN_OUT": {"U1": ["A15"]},  # DECD
    "VREGRADIO_SW": {"U1": ["A21"]},  # DCC
    "VREGRADIO_OUT": {"U1": ["A27"]},  # DECR
    "DEC_RF":  {"U1": ["G31"]},  # DECRF
    "DEC_A":   {"U1": ["A13"]},  # DECA
    "DEC_USB": {"U1": ["B6"]},   # DECUSB
    # DECN (A23) unconnected: NFC regulator decoupling, NFC disabled
    # (hardware_reference.md: NFC pins unused on the no-OLED clone).
    "RFSW_EN":     {"U1": ["U31"]},  # P0.29 -> rfsw_vdd LSW (M2c)
    "RFSW_VDD":    {},
    # --- nRF7002 power (nRF7002 PS Figure 18 reference schematic) ---
    #     VBAT/BUCKVBAT/BUCKVBATS/AFEVBAT on MAIN_3V3 (same net as VDDH).
    #     BUCKOUT-3.3uH-BUCKVMID = VDD_BUCK; VDD_BUCK feeds
    #     RFVDD/RFBUCKVDD/DIGVDD/PWRBUCKVDD (PS 14.3.2: RFVDD not in the
    #     externally-supplied sequencing list -> buck-fed).
    #     BUCKVSS (27/28) is the buck power ground return -> GND.
    "VDD_BUCK":       {"U2": ["29"]},
    "VREG70_SW":      {"U2": ["26"]},              # BUCKOUT
    "NRF70_PWRIOVDD": {"U2": ["34", "1"]},         # PWRIOVDD -> OTPVDD link
    "NRF70_SXLDO":    {"U2": ["11"]},
    "NRF70_PALDO":    {"U2": ["12"]},
    "NRF70_PAVDD0":   {"U2": ["10"]},
    "NRF70_XOLDO":    {"U2": ["16"]},
    "NRF70_AFELDO":   {"U2": ["19"]},
    "NRF70_IOVDD":    {"U2": ["48"]},
    "RFVDD":          {"U2": ["14"]},
    "RFBUCKVDD":      {"U2": ["15"]},
    "DIGVDD":         {"U2": ["33"]},
    "PWRBUCKVDD":     {"U2": ["32"]},
    # --- cross-sheet nets leaving this block (BUS): owned by their
    #     consumer sheets, here only checked present-with-pins ---
    "USB_DP": {"U1": ["B2"]},    # -> USB sheet (M2d)
    "USB_DN": {"U1": ["B4"]},
    "USB_VBUS": {"U1": ["A5"]},  # -> USB sheet / PMIC (M2c/M2d)
    "PDM_CLK": {"U1": ["R31"]},  # P1.10 -> Audio sheet (M2e)
    "PDM_DIN": {"U1": ["B20"]},  # P1.11
    # GND: EP + every GND-return pin lands on the GND net (checked below).
}

# Passives/oscillators drawn on this sheet: ref -> {pin: net}.
# Refs are per-sheet facts (values checked in RADIO_VALUES); the net side
# of every entry traces to the datasheet figure named in the comment.
RADIO_PASSIVES = {
    "X1":  {"1": "HFXO_IN", "2": "HFXO_OUT"},      # 32 MHz, no load caps
    "X2":  {"1": "LFXO_IN", "2": "LFXO_OUT"},      # 32.768 kHz, no load caps
    "X3":  {"1": "NRF70_XOP", "2": "NRF70_XON"},   # nRF7002 40 MHz, no caps
    "L1":  {"1": "VREGMAIN_SW", "2": "VREGMAIN_OUT"},   # DCCD -> DECD
    "L2":  {"1": "VREGRADIO_SW", "2": "VREGRADIO_OUT"}, # DCC -> DECR
    "L5":  {"1": "VREG70_SW", "2": "VDD_BUCK"},    # BUCKOUT -> BUCKVMID
    "L6":  {"1": "NRF53_ANT", "2": "NRF53_ANT_FILT"},   # ANT series match
    "L7":  {"1": "RF_ANT", "2": "GND"},            # antenna shunt match
    "ANT1": {"1": "RF_ANT"},                       # 2450AT18B0100
    # nRF5340 decoupling (PS 9.3 config 3: 2x 1uF bulk + 100nF per ball group)
    "C1": {"1": "MAIN_3V3", "2": "GND"},
    "C2": {"1": "MAIN_3V3", "2": "GND"},
    "C3": {"1": "MAIN_3V3", "2": "GND"},
    "C4": {"1": "VREGMAIN_OUT", "2": "GND"},       # 1uF on DECD
    "C5": {"1": "VREGRADIO_OUT", "2": "GND"},      # 1uF on DECR
    "C6": {"1": "DEC_RF", "2": "GND"},             # 2.2nF on DECRF
    "C7": {"1": "DEC_A", "2": "GND"},              # 1uF on DECA
    "C8": {"1": "DEC_USB", "2": "GND"},            # 100nF on DECUSB
    "C9": {"1": "NRF53_ANT", "2": "GND"},          # 0.7pF shunt at ANT
    # nRF7002 decoupling (PS Fig 18 / Table 19 placement notes)
    "C20": {"1": "MAIN_3V3", "2": "GND"},          # 4.7uF BUCKVBAT
    "C21": {"1": "MAIN_3V3", "2": "GND"},          # 2.2uF BUCKVBATS
    "C22": {"1": "MAIN_3V3", "2": "GND"},          # 2.2uF VBAT
    "C23": {"1": "MAIN_3V3", "2": "GND"},          # 1uF AFEVBAT
    "C24": {"1": "VDD_BUCK", "2": "GND"},          # 4.7uF close to L5
    "C25": {"1": "VDD_BUCK", "2": "GND"},          # 4.7uF bulk
    "C26": {"1": "VDD_BUCK", "2": "GND"},          # 22nF HF
    "C27": {"1": "RFBUCKVDD", "2": "GND"},         # 0.22uF
    "C28": {"1": "RFVDD", "2": "GND"},             # 2.2uF
    "C29": {"1": "DIGVDD", "2": "GND"},            # 1uF
    "C30": {"1": "PWRBUCKVDD", "2": "GND"},        # 0.47uF
    "C31": {"1": "NRF70_PWRIOVDD", "2": "GND"},    # 100nF OTPVDD
    "C32": {"1": "NRF70_PAVDD0", "2": "GND"},      # 100nF close to PAVDD0
    "C33": {"1": "NRF70_SXLDO", "2": "GND"},       # 0.47uF
    "C34": {"1": "NRF70_XOLDO", "2": "GND"},       # 10nF
    "C35": {"1": "NRF70_AFELDO", "2": "GND"},      # 0.47uF
    "C36": {"1": "NRF70_IOVDD", "2": "GND"},       # 2.2uF host rail
    "C40": {"1": "RF_ANT_FILT", "2": "RF_ANT"},    # 1.2pF series match
    "R1":  {"1": "NRF70_BUCKEN", "2": "GND"},      # 100k pull-down
    "R2":  {"1": "RFSW_CTRL", "2": "GND"},         # 100k pull-down
}
for _ref, _pinmap in RADIO_PASSIVES.items():
    for _pin, _netname in _pinmap.items():
        RADIO_EXPECTED.setdefault(_netname, {}).setdefault(_ref, []).append(_pin)

# Pins that MUST join the GND net on this sheet.
RADIO_GND_PINS = {
    "U1": ["EP"],            # die pad
    "U2": ["27", "28", "47", "49"],  # BUCKVSS + VSS (+ die pad 49)
    "U5": ["2"],             # PE42359 GND
}

# Pins that MUST be unconnected on this sheet (they may be KiCad-typed
# no_connect or simply absent from every real net).
RADIO_NC_PINS = {
    "U1": ["A23",   # DECN: NFC regulator decoupling, NFC off
           "J1",    # DCCH: VREGH stays LDO (normal-voltage config 3)
           "W1", "AA1",   # NFC1/NFC2: no NFC antenna
           "M2", "P2",          # P1.00/P1.01 spare
           "AE1", "AF2",        # P1.02/P1.03 spare (was OLED I2C2)
           "AK24", "AL23",      # P1.07/P1.08 spare
           "B18", "A17",        # P1.12/P1.13 spare
           # aQFN94 no-connect balls (per Nordic PS ballout)
           "D2", "F2", "G1", "H2", "K2", "T2", "B12", "B26", "A25",
           "J31", "AG31"],
    "U2": ["2", "3", "4", "5", "6", "21", "22", "23", "24",
           "7", "8"],   # TXRF1/PAVDD1: 2.4 GHz-only antenna (nRF7001-equiv)
}

# PE42359 (U5) pin-to-net expectations (single-pin control mode, pSemi
# DS Table 5 + our port assignment: RF1 = WiFi (SW_CTRL0 assert), RF2 = BLE).
RADIO_U5 = {
    "1": "NRF70_TXRF0",     # RF1 <- nRF7002 TXRF0 (CTRL-high path)
    "3": "NRF53_ANT_FILT",  # RF2 <- nRF5340 ANT match (default/BLE path)
    "5": "RF_ANT_FILT",     # RFC -> series 1.2pF -> shunt L -> ANT1
    "4": "RFSW_CTRL",       # CTRL <- nRF7002 SW_CTRL0 (+100k pull-down)
    "6": "RFSW_VDD",        # VDD <- rfsw rail (gated by P0.29)
}

# Component values that encode datasheet decisions (checked when present).
RADIO_VALUES = {
    "L1": "10uH",     # nRF5340 VREGMAIN DCDC (PS 9.3 config 3: 10uH 0603)
    "L2": "10uH",     # nRF5340 VREGRADIO DCDC
    "L5": "3.3uH",    # nRF7002 buck (PS Fig 18: 3.3uH)
    "L6": "2.2nH",    # nRF5340 ANT series (PS 9.3: 2.2nH)
    "L7": "2.7nH",    # antenna shunt (Johanson match, VNA-tune reserve)
    "C9": "0.7pF",    # nRF5340 ANT shunt (PS 9.3: 0.7pF)
    "C40": "1.2pF",   # antenna series (Johanson match, VNA-tune reserve)
    "X1": "32MHz",    # HFXO (BOM: ECS-320 CL=10pF, internal-cap tuning)
    "X2": "32.768kHz",  # LFXO (BOM: ECS-.327-7 CL=7pF)
    "X3": "40MHz",    # nRF7002 crystal (PS Table 19: Cl=8pF, ESR<=100 ohm)
}


KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"


def run_netlist_export() -> str:
    """Export the project netlist with kicad-cli and return its text."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "neo_n1.net"
        cmd = [KICAD_CLI, "sch", "export", "netlist",
               "--format", "kicadsexpr", "-o", str(out), str(PROJ)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not out.exists():
            raise RuntimeError(
                f"kicad-cli netlist export failed: {r.stdout}\n{r.stderr}")
        return out.read_text(encoding="utf-8", errors="replace")


def parse_netlist(text: str):
    """-> {netname: {ref: [pin, ...]}}, {ref: value}."""
    root = parse(text)
    exp = find_first(root, "export") or root
    nets_node = find_first(exp, "nets")
    nets = {}
    for net in find_all(nets_node if nets_node else exp, "net"):
        name_node = find_first(net, "net_name") or find_first(net, "name")
        name = str(name_node[1]) if name_node else "?"
        pins = {}
        for node in find_all(net, "node"):
            ref_n = find_first(node, "ref")
            pin_n = find_first(node, "pin")
            if not ref_n or not pin_n or len(ref_n) < 2 or len(pin_n) < 2:
                continue
            ref = str(ref_n[1])
            pin = str(pin_n[1])
            pins.setdefault(ref, []).append(pin)
        nets[name] = pins
    values = {}
    comps_node = find_first(exp, "components")
    for comp in find_all(comps_node if comps_node else exp, "comp"):
        ref_n = find_first(comp, "ref")
        if not ref_n or len(ref_n) < 2:
            continue
        ref = str(ref_n[1])
        val = find_first(comp, "value")
        if val:
            values[ref] = str(val[1])
    return nets, values


def norm_pin(p: str) -> str:
    return p.strip().strip('"').upper()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", default="radio", choices=["radio"])
    ap.add_argument("--full", action="store_true",
                    help="audit all sheets (M2f acceptance)")
    args = ap.parse_args()

    text = run_netlist_export()
    nets, values = parse_netlist(text)

    diffs = []
    expected = RADIO_EXPECTED if not args.full else RADIO_EXPECTED  # full in M2f

    if args.block != "radio":
        print("no expectations defined for this block yet")
        return 2

    # 1. every expected net exists with exactly the expected pins
    for net, want in expected.items():
        got = nets.get(net)
        if got is None:
            if any(want.values()):
                diffs.append(f"net {net}: MISSING (expected {want})")
            continue
        for ref, pins in want.items():
            g = sorted(norm_pin(p) for p in got.get(ref, []))
            w = sorted(norm_pin(p) for p in pins)
            if g != w:
                extra = sorted(set(g) - set(w))
                missing = sorted(set(w) - set(g))
                diffs.append(
                    f"net {net}/{ref}: got {g}, expected {w}"
                    + (f" (extra {extra})" if extra else "")
                    + (f" (missing {missing})" if missing else ""))

    # 2. GND connectivity
    gnd = None
    for name in nets:
        if name.upper() in ("GND", "GNDA", "GNDPWR"):
            gnd = nets[name]
            break
    if gnd is None:
        diffs.append("GND net missing")
    else:
        for ref, pins in RADIO_GND_PINS.items():
            g = {norm_pin(p) for p in gnd.get(ref, [])}
            for p in pins:
                if norm_pin(p) not in g:
                    diffs.append(f"GND: {ref} pin {p} not on GND net")

    # 3. NC pins: they must not appear on any REAL net. KiCad auto-generates
    #    nets named "unconnected-(<ref>-<pin>-Pad<pin>)" for open pins —
    #    those are fine and skipped. Coverage: every open pin must ALSO be
    #    in RADIO_NC_PINS (catches silently-forgotten pins, e.g. a missed
    #    crystal connection).
    nc = {(ref, norm_pin(p))
          for ref, pins in RADIO_NC_PINS.items() for p in pins}
    for name, pins in nets.items():
        if not name.startswith("unconnected-("):
            continue
        for ref, plist in pins.items():
            for p in plist:
                if (ref, norm_pin(p)) not in nc:
                    diffs.append(
                        f"pin {ref}.{p} is open but not in the NC list "
                        f"(net {name})")

    # 4. U5 PE4259 pin map (port assignment + control mode)
    for pnum, netname in RADIO_U5.items():
        got = nets.get(netname, {}).get("U5", [])
        if norm_pin(pnum) not in {norm_pin(g) for g in got}:
            diffs.append(f"U5 pin {pnum}: expected on net {netname}, "
                         f"on {[g for g in got]}")

    # 5. encoded component values, when the component exists
    for ref, want in RADIO_VALUES.items():
        got = values.get(ref)
        if got is None:
            diffs.append(f"component {ref} missing from netlist")
        elif re.sub(r"[\s]", "", got).lower() != re.sub(r"[\s]", "", want).lower():
            diffs.append(f"component {ref}: value {got!r}, expected {want!r}")

    if diffs:
        print(f"NETLIST AUDIT FAIL: {len(diffs)} diffs")
        for d in diffs:
            print("  -", d)
        return 1
    n_nets = len(expected)
    print(f"NETLIST AUDIT PASS: zero diffs ({n_nets} expected nets, "
          f"{sum(len(v) for v in RADIO_GND_PINS.values())} GND pins, "
          f"{sum(len(v) for v in RADIO_NC_PINS.values())} NC pins, "
          f"U5 control mode + values checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
