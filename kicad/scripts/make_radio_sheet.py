#!/usr/bin/env python3
"""Generate kicad/sheets/radio.kicad_sch (M2b — Radio block).

Places U1 nRF5340-QKxx, U2 nRF7002-QFAA-R7, U5 PE4259 (project lib), the
antenna front end, both crystals, the DCDC inductors and all decoupling, and
attaches a wire stub + global label to every pin (global labels carry nets
across the 6-block sheet hierarchy).

Design decisions encoded here (sources cited in netlist_audit.py):
- nRF5340 normal-voltage config (nRF5340 PS v1.3 Table 214 config 3 /
  section 9.3): VDD+VDDH on MAIN_3V3, 2x 10uH DCDC (DCCD-DECD, DCC-DECR),
  DCCH floating (VREGH stays LDO — the Clip BOM has only two 10uH parts and
  the board DTS never enables vregh).
- nRF7002 per PS Figure 18 reference schematic: VBAT/BUCKVBAT/BUCKVBATS/
  AFEVBAT on MAIN_3V3, internal buck 3.3uH BUCKOUT->BUCKVMID (VDD_BUCK)
  feeding RFVDD/RFBUCKVDD/DIGVDD/PWRBUCKVDD, PWRIOVDD->OTPVDD external link,
  40 MHz crystal (no external load caps), TXRF1/PAVDD1 not connected
  (2.4 GHz-only antenna per BOM; nRF7001-equivalent configuration).
- PE4259/PE42359 single-pin control mode (pSemi DS Table 5): pin 6 = VDD
  (RFSW_VDD, 1.8-3.3 V gated rail), pin 4 = CTRL <- nRF7002 SW_CTRL0.
  CTRL high -> RFC-RF1 (WiFi/TXRF0), low -> RFC-RF2 (BLE/ANT). 100k pull-down
  holds the BLE path while SW_CTRL0 is floating (nRF70 IOVDD off).
- RF match: nRF5340 ANT 0.7 pF shunt + 2.2 nH series (nRF5340 PS 9.3);
  antenna side series 1.2 pF + shunt 2.7 nH at the Johanson 2450AT18B0100
  pad (BOM ANT1 row; VNA-tune reserve, M3 keep-out).
- No external crystal load caps anywhere: firmware tunes internal caps
  (hfxo 9 pF, lfxo 7 pF; tests/clip `lfxo|hfxo` shell commands).

Regenerate with:  python make_radio_sheet.py
(Also regenerate after any neo_n1.kicad_sym edit so embedded copies match.)
"""
from __future__ import annotations

import uuid
import re
from pathlib import Path

from kicad_sexpr import parse, find_first, find_all, dumps

HERE = Path(__file__).resolve().parent
KICAD = HERE.parent
LIB = KICAD / "lib" / "neo_n1.kicad_sym"
STOCK = Path(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
OUT = KICAD / "sheets" / "radio.kicad_sch"

SHEET_UUID = "47b0e3b7-6847-4f23-9317-fd80997304b2"  # matches project root
ROOT_UUID = "9f19b16c-0527-4e52-bc42-a056a6a1ffa7"  # root schematic uuid
# full hierarchical path for components living in the Radio sub-sheet
INST_PATH = f"/{ROOT_UUID}/{SHEET_UUID}"


def det_uuid(*parts) -> str:
    """Deterministic UUID so regeneration is diff-stable."""
    ns = uuid.uuid5(uuid.NAMESPACE_URL,
                    "https://neo_n1.local/kicad/radio")
    return str(uuid.uuid5(ns, "/".join(str(p) for p in parts)))


# ---------------------------------------------------------------------------
# Component placement: ref, lib_id, value, footprint, (x, y), rotation
# ---------------------------------------------------------------------------
IC_FOOTPRINTS = {
    "U1": "neo_n1_footprints:XCVR_NRF5340-QKAA-R7",
    "U2": "neo_n1_footprints:IC_NRF7002-QFAA-R7",
    "U5": "neo_n1_footprints:SOT65P215X110-6N_PE4259",
}
L_FOOT = "Inductor_SMD:L_0805_2012Metric"
L_RF_FOOT = "Inductor_SMD:L_0402_1005Metric"
C_FOOT = "Capacitor_SMD:C_0402_1005Metric"
R_FOOT = "Resistor_SMD:R_0402_1005Metric"

# (ref, lib, value, footprint, x, y)
COMPONENTS = [
    ("U1",  "neo_n1:nRF5340-QKxx",     "nRF5340-QKAA",   IC_FOOTPRINTS["U1"], 100, 165),
    ("U2",  "neo_n1:NRF7002-QFAA-R7",  "nRF7002-QFAA",   IC_FOOTPRINTS["U2"], 258, 128),
    ("U5",  "neo_n1:PE4259",           "PE42359",        IC_FOOTPRINTS["U5"], 330, 210),
    ("X1",  "Device:Crystal",          "32MHz",          "", 100, 268),
    ("X2",  "Device:Crystal",          "32.768kHz",      "", 140, 268),
    ("X3",  "Device:Crystal",          "40MHz",          "", 180, 268),
    ("L1",  "Device:L",                "10uH",           L_FOOT, 55, 130),
    ("L2",  "Device:L",                "10uH",           L_FOOT, 55, 170),
    ("L5",  "Device:L",                "3.3uH",          L_FOOT, 300, 95),
    ("L6",  "Device:L",                "2.2nH",          L_RF_FOOT, 300, 195),
    ("L7",  "Device:L",                "2.7nH",          L_RF_FOOT, 375, 232),
    ("ANT1", "Device:Antenna",         "2450AT18B0100",  "", 395, 205),
    # nRF5340 decoupling (PS 9.3 config 3)
    ("C1",  "Device:C", "1uF",  C_FOOT, 78, 74),
    ("C2",  "Device:C", "1uF",  C_FOOT, 88, 74),
    ("C3",  "Device:C", "100nF", C_FOOT, 98, 74),
    ("C4",  "Device:C", "1uF",  C_FOOT, 42, 108),
    ("C5",  "Device:C", "1uF",  C_FOOT, 42, 148),
    ("C6",  "Device:C", "2.2nF", C_FOOT, 42, 88),
    ("C7",  "Device:C", "1uF",  C_FOOT, 42, 218),
    ("C8",  "Device:C", "100nF", C_FOOT, 42, 238),
    ("C9",  "Device:C", "0.7pF", C_FOOT, 300, 175),
    # nRF7002 decoupling (PS Fig 18)
    ("C20", "Device:C", "4.7uF", C_FOOT, 290, 62),
    ("C21", "Device:C", "2.2uF", C_FOOT, 300, 62),
    ("C22", "Device:C", "2.2uF", C_FOOT, 310, 62),
    ("C23", "Device:C", "1uF",  C_FOOT, 320, 62),
    ("C24", "Device:C", "4.7uF", C_FOOT, 296, 88),
    ("C25", "Device:C", "4.7uF", C_FOOT, 306, 88),
    ("C26", "Device:C", "22nF", C_FOOT, 316, 88),
    ("C27", "Device:C", "0.22uF", C_FOOT, 326, 88),
    ("C28", "Device:C", "2.2uF", C_FOOT, 296, 112),
    ("C29", "Device:C", "1uF",  C_FOOT, 306, 112),
    ("C30", "Device:C", "0.47uF", C_FOOT, 316, 112),
    ("C31", "Device:C", "100nF", C_FOOT, 326, 112),
    ("C32", "Device:C", "100nF", C_FOOT, 296, 136),
    ("C33", "Device:C", "0.47uF", C_FOOT, 306, 136),
    ("C34", "Device:C", "10nF", C_FOOT, 316, 136),
    ("C35", "Device:C", "0.47uF", C_FOOT, 326, 136),
    ("C36", "Device:C", "2.2uF", C_FOOT, 336, 136),
    # RF + control
    ("C40", "Device:C", "1.2pF", C_FOOT, 355, 218),
    ("R1",  "Device:R", "100k", R_FOOT, 258, 175),
    ("R2",  "Device:R", "100k", R_FOOT, 268, 175),
]

GND_SYMS = [(70, 275), (268, 200), (352, 246)]  # power:GND driver symbols
PWR_FLAGS = [  # (x, y, net) — nets whose only drivers are chip-internal
    # or off-sheet (USB VBUS from the connector, M2d)
    (40, 60, "MAIN_3V3"), (352, 130, "NRF70_IOVDD"),
    (352, 140, "RFSW_VDD"), (352, 150, "NRF70_PWRIOVDD"),
    (352, 160, "RFVDD"),
    (362, 170, "RFBUCKVDD"), (372, 170, "DIGVDD"),
    (382, 170, "PWRBUCKVDD"), (392, 170, "NRF70_SXLDO"),
    (402, 170, "NRF70_PALDO"), (412, 170, "NRF70_PAVDD0"),
    (412, 160, "NRF70_XOLDO"), (412, 150, "NRF70_AFELDO"),
    (422, 150, "USB_VBUS"),
    (422, 160, "GND"),
    # no flag on VDD_BUCK: BUCKVMID is a bidirectional pin (self-driven)
]

# ---------------------------------------------------------------------------
# Pin -> net maps
# ---------------------------------------------------------------------------
U1_NETS = {
    # power (15 stacked VDD balls + VDDH) — PS config 3: all on the rail
    "A19": "MAIN_3V3", "B28": "MAIN_3V3", "C1": "MAIN_3V3",
    "E31": "MAIN_3V3", "N31": "MAIN_3V3", "AG1": "MAIN_3V3",
    "AL3": "MAIN_3V3", "AL7": "MAIN_3V3", "AL11": "MAIN_3V3",
    "AL17": "MAIN_3V3", "AL25": "MAIN_3V3", "AC1": "MAIN_3V3",
    "B8": "MAIN_3V3", "L1": "MAIN_3V3", "U1": "MAIN_3V3",
    "AJ31": "MAIN_3V3",
    "E1": "MAIN_3V3",  # VDDH tied to VDD (normal-voltage mode)
    "EP": "GND",
    # DCDC (VREGMAIN + VREGRADIO), PS Fig 15
    "B10": "VREGMAIN_SW", "A15": "VREGMAIN_OUT",
    "A21": "VREGRADIO_SW", "A27": "VREGRADIO_OUT",
    # decoupling pins
    "G31": "DEC_RF", "A13": "DEC_A", "B6": "DEC_USB",
    # crystals (no external load caps)
    "C31": "HFXO_IN", "B30": "HFXO_OUT", "N1": "LFXO_IN", "R1": "LFXO_OUT",
    # RF
    "L31": "NRF53_ANT",
    # USB (sheet: USB, M2d)
    "B2": "USB_DP", "B4": "USB_DN", "A5": "USB_VBUS",
    # SWD (sheet: Misc, M2e)
    "W31": "SWD_CLK", "AA31": "SWD_IO", "AC31": "NRST",
    # UART console (sheet: Misc, M2e)
    "AK22": "UART_TX", "AL19": "UART_RX",
    # I2C1 PMIC (sheet: Power, M2c)
    "V2": "I2C1_SDA", "Y2": "I2C1_SCL",
    # SPI3 flash (sheet: Memory, M2d)
    "AK18": "FLASH_SCK", "AL27": "FLASH_MOSI", "AK20": "FLASH_MISO",
    "AK16": "FLASH_CSN", "AL13": "FLASH_WP", "AL15": "FLASH_HOLD",
    # SPI4 microSD (sheet: Memory, M2d)
    "AB2": "SD_SCK", "AH2": "SD_MOSI", "AD2": "SD_MISO", "AJ1": "SD_CSN",
    # PDM mics (sheet: Audio, M2e)
    "R31": "PDM_CLK", "B20": "PDM_DIN",
    # QSPI nRF7002
    "AK12": "QSPI_SCK", "AK14": "QSPI_CSN", "AL5": "QSPI_IO0",
    "AK8": "QSPI_IO1", "AK10": "QSPI_IO2", "AL9": "QSPI_IO3",
    # nRF7002 control
    "AK4": "NRF70_BUCKEN", "AK6": "NRF70_HOST_IRQ", "AL29": "NRF70_IOVDD_EN",
    # coex PTA
    "AE31": "PTA_REQ", "AK28": "PTA_STATUS0", "B22": "PTA_GRANT",
    "B24": "PTA_SWCTRL1",
    # rail enables / misc consumers
    "U31": "RFSW_EN", "B16": "MIC_VDD_EN", "AK30": "FLASH_VDD_EN",
    "AK2": "PMIC_IRQ", "AL21": "HAPTIC_CTRL", "B14": "BTN_N",
    "AK26": "LED_ACT",
    # J1 (DCCH) / A23 (DECN) / spare GPIOs get no-connect flags below
}

U2_NETS = {
    "1": "NRF70_PWRIOVDD", "34": "NRF70_PWRIOVDD",   # internal OTP link
    "13": "MAIN_3V3", "20": "MAIN_3V3", "25": "MAIN_3V3",
    "31": "MAIN_3V3",                                 # VBAT / AFEVBAT /
                                                      # BUCKVBAT / BUCKVBATS
    "26": "VREG70_SW", "29": "VDD_BUCK",              # buck out -> 3.3uH -> VMID
    "27": "GND", "28": "GND", "47": "GND", "49": "GND",
    "14": "RFVDD", "15": "RFBUCKVDD", "32": "PWRBUCKVDD", "33": "DIGVDD",
    "11": "NRF70_SXLDO", "12": "NRF70_PALDO", "10": "NRF70_PAVDD0",
    "16": "NRF70_XOLDO", "19": "NRF70_AFELDO",
    "48": "NRF70_IOVDD",
    "30": "NRF70_BUCKEN", "46": "NRF70_HOST_IRQ",
    "35": "QSPI_SCK", "36": "QSPI_CSN", "37": "QSPI_IO0", "38": "QSPI_IO1",
    "39": "QSPI_IO2", "40": "QSPI_IO3",
    "41": "PTA_STATUS0", "42": "PTA_REQ", "43": "PTA_GRANT",
    "44": "RFSW_CTRL", "45": "PTA_SWCTRL1",
    "9": "NRF70_TXRF0",
    "17": "NRF70_XOP", "18": "NRF70_XON",   # 40 MHz crystal (PS Table 19)
    # 7 TXRF1 / 8 PAVDD1: NC (2.4 GHz-only antenna; see module docstring)
}

U5_NETS = {
    "1": "NRF70_TXRF0",      # RF1 <- nRF7002 TXRF0 (CTRL high path)
    "3": "NRF53_ANT_FILT",   # RF2 <- nRF5340 ANT match (default/BLE path)
    "5": "RF_ANT_FILT",      # RFC -> series 1.2pF -> shunt L -> ANT1
    "4": "RFSW_CTRL",        # <- nRF7002 SW_CTRL0, 100k pull-down to GND
    "6": "RFSW_VDD",         # VDD (single-pin control mode)
    "2": "GND",
}

TWO_PIN_NETS = {
    "X1":  {"1": "HFXO_IN", "2": "HFXO_OUT"},
    "X2":  {"1": "LFXO_IN", "2": "LFXO_OUT"},
    "X3":  {"1": "NRF70_XOP", "2": "NRF70_XON"},
    "L1":  {"1": "VREGMAIN_SW", "2": "VREGMAIN_OUT"},
    "L2":  {"1": "VREGRADIO_SW", "2": "VREGRADIO_OUT"},
    "L5":  {"1": "VREG70_SW", "2": "VDD_BUCK"},
    "L6":  {"1": "NRF53_ANT", "2": "NRF53_ANT_FILT"},
    "L7":  {"1": "RF_ANT", "2": "GND"},
    "ANT1": {"1": "RF_ANT"},
    "C1":  {"1": "MAIN_3V3", "2": "GND"},
    "C2":  {"1": "MAIN_3V3", "2": "GND"},
    "C3":  {"1": "MAIN_3V3", "2": "GND"},
    "C4":  {"1": "VREGMAIN_OUT", "2": "GND"},
    "C5":  {"1": "VREGRADIO_OUT", "2": "GND"},
    "C6":  {"1": "DEC_RF", "2": "GND"},
    "C7":  {"1": "DEC_A", "2": "GND"},
    "C8":  {"1": "DEC_USB", "2": "GND"},
    "C9":  {"1": "NRF53_ANT", "2": "GND"},
    "C20": {"1": "MAIN_3V3", "2": "GND"},
    "C21": {"1": "MAIN_3V3", "2": "GND"},
    "C22": {"1": "MAIN_3V3", "2": "GND"},
    "C23": {"1": "MAIN_3V3", "2": "GND"},
    "C24": {"1": "VDD_BUCK", "2": "GND"},
    "C25": {"1": "VDD_BUCK", "2": "GND"},
    "C26": {"1": "VDD_BUCK", "2": "GND"},
    "C27": {"1": "RFBUCKVDD", "2": "GND"},
    "C28": {"1": "RFVDD", "2": "GND"},
    "C29": {"1": "DIGVDD", "2": "GND"},
    "C30": {"1": "PWRBUCKVDD", "2": "GND"},
    "C31": {"1": "NRF70_PWRIOVDD", "2": "GND"},
    "C32": {"1": "NRF70_PAVDD0", "2": "GND"},
    "C33": {"1": "NRF70_SXLDO", "2": "GND"},
    "C34": {"1": "NRF70_XOLDO", "2": "GND"},
    "C35": {"1": "NRF70_AFELDO", "2": "GND"},
    "C36": {"1": "NRF70_IOVDD", "2": "GND"},
    "C40": {"1": "RF_ANT_FILT", "2": "RF_ANT"},
    "R1":  {"1": "NRF70_BUCKEN", "2": "GND"},
    "R2":  {"1": "RFSW_CTRL", "2": "GND"},
}

# U1 balls left unconnected (no net): NC balls, NFC pins, DCCH (VREGH stays
# LDO), DECN (NFC regulator decoupling), spare GPIOs (P1.00/01/02/03/07/08/
# 12/13 — breakout candidates for M2e Misc, NC until then).
U1_NC_NOTE = "spare GPIO / NFC off / DCCH unused (VREGH LDO)"

# Wire stub length (mm) from pin to label
STUB = 2.54


# ---------------------------------------------------------------------------
# Symbol extraction / geometry
# ---------------------------------------------------------------------------
def load_lib_symbols():
    root = parse(LIB.read_text(encoding="utf-8", errors="replace"))
    lib = find_first(root, "kicad_symbol_lib")
    out = {}
    for sym in find_all(lib, "symbol"):
        out[str(sym[1])] = sym
    return out


def extract_stock(libfile: str, names: list[str]) -> dict:
    root = parse((STOCK / libfile).read_text(encoding="utf-8",
                                              errors="replace"))
    lib = find_first(root, "kicad_symbol_lib")
    out = {}
    for sym in find_all(lib, "symbol"):
        if str(sym[1]) in names:
            out[str(sym[1])] = sym
    missing = set(names) - set(out)
    if missing:
        raise SystemExit(f"{libfile}: symbols not found: {missing}")
    return out


def pin_list(symnode) -> dict:
    """{pin_number: (x, y, angle, ptype)} — all units merged."""
    out = {}
    direct = find_all(symnode, "pin")
    units = [symnode] if direct else find_all(symnode, "symbol")
    for unit in units:
        for pin in find_all(unit, "pin"):
            at = find_first(pin, "at")
            num = find_first(pin, "number")
            if at is None or num is None:
                continue
            x, y = float(at[1]), float(at[2])
            ang = float(at[3]) if len(at) > 3 else 0.0
            out[str(num[1])] = (x, y, ang, str(pin[1]))
    return out


def pin_offsets(symnode) -> dict:
    """Absolute in-symbol pin geometry already includes the offset from the
    symbol origin — KiCad pin (at) is relative to the symbol origin."""
    return pin_list(symnode)


def raw_symbol_span(text: str, name: str) -> str:
    """Extract the RAW text of `(symbol "NAME" ...)` at lib depth.

    Verbatim text avoids any serializer fidelity risk: what KiCad wrote,
    KiCad reads back. The caller renames the top symbol to the full lib id.
    """
    marker = f'(symbol "{name}"'
    i = text.find(marker)
    if i < 0:
        raise SystemExit(f"symbol {name!r} not found")
    # walk to the matching close paren, respecting quoted strings
    depth = 0
    j = i
    n = len(text)
    while j < n:
        c = text[j]
        if c == '"':  # skip string literal
            j += 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
        j += 1
    raise SystemExit(f"symbol {name!r}: unbalanced parens in source")


def embed_lib_id(lib_id: str, source_text: str, name: str) -> str:
    """Raw lib def with only the TOP symbol renamed to the full lib id
    (KiCad's native embedding pattern)."""
    raw = raw_symbol_span(source_text, name)
    return raw.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1)


def label_node(net: str, x: float, y: float, ang: float) -> str:
    shapes = {0.0: "input", 180.0: "input", 90.0: "input", 270.0: "input"}
    return (f'(global_label "{net}" (shape {shapes.get(ang, "input")}) '
            f'(at {fmt(x)} {fmt(y)} {int(ang)}) '
            f'(fields_autoplaced yes) '
            f'(effects (font (size 1.27 1.27)) (justify left)) '
            f'(uuid "{det_uuid("label", net, x, y, ang)}"))')


def fmt(v: float) -> str:
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return s if s else "0"


def snap(v: float) -> float:
    """Snap a placement coordinate to KiCad's 1.27 mm connection grid."""
    return round(v / 1.27) * 1.27


def main():
    # raw lib texts (verbatim embedding) + parsed copies (pin geometry only)
    proj_text = LIB.read_text(encoding="utf-8", errors="replace")
    dev_text = (STOCK / "Device.kicad_sym").read_text(encoding="utf-8",
                                                      errors="replace")
    pwr_text = (STOCK / "power.kicad_sym").read_text(encoding="utf-8",
                                                     errors="replace")
    proj_syms = load_lib_symbols()
    dev_syms = extract_stock("Device.kicad_sym",
                             ["C", "R", "L", "Crystal", "Antenna"])
    pwr_syms = extract_stock("power.kicad_sym", ["GND", "PWR_FLAG"])

    # ---- embedded lib_symbols section (raw spans, KiCad-faithful) ----
    src_of = {"nRF5340-QKxx": proj_text, "NRF7002-QFAA-R7": proj_text,
              "PE4259": proj_text, "C": dev_text, "R": dev_text,
              "L": dev_text, "Crystal": dev_text, "Antenna": dev_text,
              "GND": pwr_text, "PWR_FLAG": pwr_text}
    geo_of = {**proj_syms, **dev_syms, **pwr_syms}

    lib_syms = []
    for name in src_of:
        if name not in ("nRF5340-QKxx", "NRF7002-QFAA-R7", "PE4259",
                        "C", "R", "L", "Crystal", "Antenna", "GND",
                        "PWR_FLAG"):
            continue
        libid_full = (f"neo_n1:{name}" if name in ("nRF5340-QKxx",
                                                   "NRF7002-QFAA-R7",
                                                   "PE4259")
                      else f"Device:{name}" if name in
                      ("C", "R", "L", "Crystal", "Antenna")
                      else f"power:{name}")
        lib_syms.append(embed_lib_id(libid_full, src_of[name], name))

    # ---- instances, wires, labels ----
    wires, labels, instances = [], [], []

    def attach_pin(comp_ref, comp_xy, pin_geo, net):
        """Wire stub from pin to label at net name."""
        px, py, ang, _ = pin_geo
        sx, sy = comp_xy
        # schematic position of the pin (symbol Y axis is inverted)
        ax, ay = sx + px, sy - py
        # outward direction: into-body angle in schematic = (360 - ang) % 360
        into = (360 - ang) % 360
        outward = (into + 180) % 360
        dx, dy = {0: (1, 0), 180: (-1, 0), 90: (0, 1), 270: (0, -1)}[int(outward)]
        lx, ly = ax + dx * STUB, ay + dy * STUB
        wires.append(
            f'(wire (pts (xy {fmt(ax)} {fmt(ay)}) (xy {fmt(lx)} {fmt(ly)})) '
            f'(stroke (width 0) (type default)) '
            f'(uuid "{det_uuid("wire", comp_ref, pin_geo[0], pin_geo[1])}"))')
        labels.append(label_node(net, lx, ly, outward))

    for ref, libid, value, foot, cx, cy in COMPONENTS:
        libname = libid.split(":")[1]
        cx, cy = snap(cx), snap(cy)
        geo = pin_offsets(geo_of[libname])
        nets = (U1_NETS if ref == "U1" else
                U2_NETS if ref == "U2" else
                U5_NETS if ref == "U5" else TWO_PIN_NETS[ref])
        used = set()
        for pnum, pgeo in geo.items():
            net = nets.get(pnum)
            if net is None:
                continue  # NC pins handled below
            attach_pin(ref, (cx, cy), pgeo, net)
            used.add(pnum)
        # no-connect markers on pins with no net (only where the symbol does
        # not already type them no_connect)
        for pnum, pgeo in geo.items():
            if pnum in used or pgeo[3] == "no_connect":
                continue
            px, py, ang, _ = pgeo
            ax, ay = cx + px, cy - py
            instances.append(
                f'(no_connect (at {fmt(ax)} {fmt(ay)}) '
                f'(uuid "{det_uuid("nc", ref, pnum)}"))')
        inst = [
            f'(lib_id "{libid}")',
            f'(at {cx} {cy} 0)',
            f'(unit 1)',
            f'(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)',
        ]
        props = [
            f'(property "Reference" "{ref}" '
            f'(at {cx} {cy - 4} 0) (effects (font (size 1.27 1.27))))',
            f'(property "Value" "{value}" '
            f'(at {cx} {cy + 4} 0) (effects (font (size 1.27 1.27))))',
        ]
        if foot:
            props.append(f'(property "Footprint" "{foot}" '
                         f'(at {cx} {cy} 0) (effects (font (size 1.27 1.27)) (hide yes)))')
        body = "\n".join(x for x in inst + props if x)
        instances.append(
            f'(symbol\n{body}\n(uuid "{det_uuid("inst", ref)}")\n'
            f'(instances (project "neo_n1" (path "/{ROOT_UUID}/{SHEET_UUID}" '
            f'(reference "{ref}") (unit 1)))))\n')

    # GND power symbols + PWR_FLAGs
    for i, (gx, gy) in enumerate(GND_SYMS):
        gx, gy = snap(gx), snap(gy)
        instances.append(
            f'(symbol (lib_id "power:GND") (at {gx} {gy} 0) (unit 1)\n'
            f'(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n'
            f'(uuid "{det_uuid("gnd", i)}")\n'
            f'(property "Reference" "#PWR0{i+1}" (at {gx} {gy} 0) '
            f'(effects (font (size 1.27 1.27)) (hide yes)))\n'
            f'(property "Value" "GND" (at {gx} {gy - 4} 0) '
            f'(effects (font (size 1.27 1.27))))\n'
            f'(property "Footprint" "" (at {gx} {gy} 0) '
            f'(effects (font (size 1.27 1.27)) (hide yes)))\n'
            f'(instances (project "neo_n1" (path "/{ROOT_UUID}/{SHEET_UUID}" '
            f'(reference "#PWR0{i+1}") (unit 1)))))\n')
        # GND symbols connect by their pin at (0,0); add a label wire stub
        wires.append(
            f'(wire (pts (xy {gx} {gy}) (xy {gx} {gy})) '
            f'(stroke (width 0) (type default)) '
            f'(uuid "{det_uuid("gndwire", i)}"))')
    for i, (fx, fy, net) in enumerate(PWR_FLAGS):
        fx, fy = snap(fx), snap(fy)
        instances.append(
            f'(symbol (lib_id "power:PWR_FLAG") (at {fx} {fy} 0) (unit 1)\n'
            f'(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n'
            f'(uuid "{det_uuid("pwrflag", net)}")\n'
            f'(property "Reference" "#FLG0{i+1}" (at {fx} {fy} 0) '
            f'(effects (font (size 1.27 1.27)) (hide yes)))\n'
            f'(property "Value" "PWR_FLAG" (at {fx} {fy} 4) '
            f'(effects (font (size 1.27 1.27)) (hide yes)))\n'
            f'(instances (project "neo_n1" (path "/{ROOT_UUID}/{SHEET_UUID}" '
            f'(reference "#FLG0{i+1}") (unit 1)))))\n')
        labels.append(label_node(net, fx, fy, 90))

    note = (
        '(text "M3 keep-out: antenna ground clearance per Johanson\\n'
        '2450AT18B0100 (13.5 x 4 mm, all layers). RF match values\\n'
        '(C9 0.7pF, L6 2.2nH, C40 1.2pF, L7 2.7nH) are VNA-tune reserves.\\n'
        'Crystals have NO external load caps: internal caps tuned in DTS\\n'
        '(hfxo 9 pF, lfxo 7 pF)."\n'
        '(exclude_from_sim no)\n'
        '(at 30 32 0)\n'
        '(effects (font (size 1.27 1.27)) (justify left))\n'
        f'(uuid "{det_uuid("note")}")\n)')

    sheet = f'''(kicad_sch
	(version 20260306)
	(generator "eeschema")
	(generator_version "10.0")
	(uuid "{SHEET_UUID}")
	(paper "A3")
	(title_block
		(title "ibtivia Ai Clip")
		(date "2026-11-21")
		(rev "A")
		(comment 1 "Radio: nRF5340 + nRF7002 + antenna switch + antenna + crystals + coex PTA")
	)
	(lib_symbols
{chr(10).join(lib_syms)}
	)
{chr(10).join(instances)}
{chr(10).join(wires)}
{chr(10).join(labels)}
{note}
	(sheet_instances
		(path "/"
			(page "2")
		)
	)
	(embedded_fonts no)
)
'''
    OUT.write_text(sheet, encoding="utf-8")
    print(f"wrote {OUT} ({len(sheet)} bytes)")


if __name__ == "__main__":
    main()
