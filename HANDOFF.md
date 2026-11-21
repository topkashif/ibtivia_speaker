# Handoff — read me first

Last updated: 2026-11-21 (M2b done). Project map and rules: `AGENTS.md`.
Milestones: `MILESTONES.md`. Hardware contract: `hardware_reference.md`.

## Current state (30-second version)

Building a pin-compatible clone of the Seeed reSpeaker Clip wearable recorder
**without the OLED**. Firmware builds under NCS v3.3.0 with display compiled
out (M0 done). M1 done (costed BOM, `bom/bom.csv`, now 35 rows). **M2 in
progress: M2.0 skeleton + M2a libraries + M2b radio block DONE** — the radio
sheet is **generated** by `kicad/scripts/make_radio_sheet.py` (do not hand-edit
`radio.kicad_sch`; edit the generator and re-run). Audited by the new
`kicad/scripts/netlist_audit.py --block radio` (zero diffs). Next:
**M2c — power block**. No hardware exists yet.

## Done and verified (M2b — radio sheet, 2026-11-21)

- `kicad/sheets/radio.kicad_sch` (155 KB, generated): U1 nRF5340-QKxx (95
  balls), U2 nRF7002 (49 pins), U5 PE42359 (drawn with the project's PE4259
  symbol; single-pin control mode), X1/X2/X3 crystals, L1/L2 10 µH DCDC +
  L5 3.3 µH nRF7002 buck + L6/L7 RF match, ANT1 + match, full decoupling,
  PWR_FLAGs, wire stub + global label on every pin (global labels carry
  cross-sheet nets).
- **Design decisions** (sources: nRF5340 PS v1.3 §4.7/§9.3 + Table 214/216;
  nRF7002 PS v1.0 Table 11/17/19 + Fig 18; PE42359 DS DOC-13214 Table 5;
  nRF7002 DK hardware files 0.7.2 for the iovdd-load-switch architecture —
  all cited in `netlist_audit.py`'s docstring, raws in %TEMP%\dk7002):
  1. **nRF5340 = normal-voltage config 3** — VDD+VDDH all on MAIN_3V3
     (NOT the DK's high-voltage mode: the Clip has only two 10 µH inductors
     and its DTS never enables `&vregh`). 2× 10 µH: DCCD→DECD (VREGMAIN),
     DCC→DECR (VREGRADIO); DCCH + DECN open; QSPI/coex/RF-switch logic all
     3.3 V. This also keeps the M1 green-LED-on-P1.09 choice valid (1.8 V
     GPIO drive would starve a green LED).
  2. **nRF7002 = PS Fig 18 reference** — VBAT/BUCKVBAT/BUCKVBATS/AFEVBAT on
     MAIN_3V3; internal buck 3.3 µH BUCKOUT→BUCKVMID = VDD_BUCK feeding
     RFVDD/RFBUCKVDD/DIGVDD/PWRBUCKVDD; PWRIOVDD(34)→OTPVDD(1) link; own
     **40 MHz crystal X3 (Cl=8 pF, no load caps)**; TXRF1/PAVDD1 NC
     (2.4 GHz-only antenna; nRF7001-equivalent).
  3. **PE42359 single-pin control** — pin 6 = VDD (RFSW_VDD, switched 3.3 V
     branch of MAIN via P0.29 load switch, M2c), pin 4 = CTRL ← nRF7002
     SW_CTRL0, 100 kΩ pull-down holds the BLE path (RFC–RF2) when SW_CTRL0
     floats. RF1 = nRF7002 TXRF0 (WiFi-active), RF2 = nRF5340 ANT. No
     series DC-blocks (pSemi eval = direct 50 Ω; BOM note corrected).
  4. Antenna: series C40 1.2 pF + shunt L7 2.7 nH at the 2450AT18B0100 pad
     (Johanson); nRF5340 side C9 0.7 pF shunt + L6 2.2 nH series (PS §9.3).
     All RF match values = VNA-tune reserves.
  5. **No external crystal load caps anywhere** (the M2b bullet's "w/ load
     caps" was a slip against the contract — crystals connect direct;
     internal caps tuned in DTS).
- `kicad/scripts/netlist_audit.py` (new): exports the project netlist via
  `kicad-cli sch export netlist --format kicadsexpr` and diffs it against an
  independent transcription of the contract (pin map + PS figures):
  54 expected nets, GND/NC checks, open-pin coverage check (every open pin
  must be in the NC list — this caught the missing X3), U5 control mode,
  encoded values. `--block radio` green: zero diffs.
- ERC 0, DRC 0, symbol_audit still zero diffs, SVG export eyeballed (clean).
- **BOM +8 rows** (X3, L5, L6, L7, C40, C41, R5 100k pulldowns, SW2 load
  switches): RF passives + the two GPIO load switches the firmware expects
  (iovdd-ctrl P0.26, rfsw P0.29) — flagged "price + stock check before M4".

## Done and verified (M2a and earlier)

- M0 (firmware boundary): OLED removal applied across 7 firmware files (board
  DTS, app Kconfig / CMakeLists / display.h stubs / prj.conf, MCUboot conf +
  overlay, app board overlay). Verified: build exit 0, signed artifacts,
  `CONFIG_CLIP_DISPLAY`/`CONFIG_MCUBOOT_DISPLAY` not set, no display objects
  linked. See `MILESTONES.md` M0 and `hardware_reference.md` §5.
- NCS v3.3.0 installed at `C:\ncs\v3.3.0` (toolchain `936afb6332`); the 5
  MCUboot patches applied to `C:\ncs\v3.3.0\bootloader\mcuboot`; ccache copied
  into that toolchain's `opt/bin`. **v3.4.2 does not build this tree** — do
  not "upgrade". Successful build in `build-clip/` (gitignored).

## Done and verified (M1)

- **India re-quote (2026-11-21):** `bom/bom.csv` now carries India
  stock + INR pricing per row (digikey.in / mouser.in / element14 India /
  LCSC / Campus Component Pune / Semikart / Robu checked; raw quotes in
  `bom/bom_india_requote.json` + `bom/india_quotes_2026-11-21.json`).
  Per-board cost @qty-10 ≈ **₹3,700**. digikey.in U1 price verified live
  (5,833 in stock, ₹920.19 @10). India zero-stock rows: T5838 mic
  (backorder Dec-2026/Mar-2027; Knowles sub live 22.6k @ ₹224.69), battery
  (factory-direct only; Robu WLY601235 rejected — wrong size, no NTC),
  magnetic pogo (12-wk backorder). Passives: exact Murata 100 nF/4.7 µF not
  stocked in India — named equivalents (Yageo CC0402 / Murata ME47D) are
  deep-stocked. Note: digikey.in stock ships from global warehouse (duty +
  GST at delivery); element14 India quotes are domestic GST-inclusive.

- **Alternates review applied (2026-11-21, user suggestions):** U1/U2/U3
  orderables switched to **-R7** (7″ reel container code — identical
  silicon, zero fw impact; better MOQ/stock: U1 element14 ₹783.50,
  U2 Mouser ₹364.01, U3 Mouser ₹211.14 @10). Mic primary is now **T5837**
  (user suggestion confirmed drop-in: −37 dBFS vs T5838's −41, same
  footprint/L-R convention, no fw change, Mouser India 16k @ ₹199.68 — far
  better supplied than T5838's zero shelf). Winbond flash alternates decoded
  into BOM row U4A (all EF 40 17 → DTS `jedec-id` + delete `sfdp-bfp`
  override; prefer −Q over −M). WLY 601235 battery alternate logged as BT1A
  with four hard consequences (6.0 mm thick, no NTC → `DISABLENTC=1` + strap
  + driver fix, charge ≤120 mA 0.5 C, OCV re-profile) — HSZ 362123 stays
  primary.
- **Pogo removal (2026-11-21, user decision):** magnetic pogo connector
  deleted from the BOM and from the future schematic entirely — **no DNP
  pads, no reference**. USB-C (J3, USB4105-GF-A) is the sole charge/data
  port; revisit only if a dock product is revived. Consequences applied:
  BOM rows added — R4 (2× ERJ-2GEJ512X 5.1 kΩ Rd on CC1/CC2, *required* for
  any Type-C source to apply VBUS) and D1 (USBLC6-2SC6 ESD on D+/D−,
  digikey.in 129,234 @ ₹21.56, live-verified). Zero firmware impact
  (charging/VBUS/shutdown gating all read the nPM1300; grep of the whole
  tree found no pogo/dock reference). Board cost @qty-10 drops to ~₹2,970.
  M2 checklist item: confirm nPM1300's integrated VBUS input protection in
  PS v1.3 during schematic; add a VBUS TVS only if absent.
- `bom/bom.csv`: per-block MPNs, packages, stock + qty-10 prices at 2+
  distributors (collected 2026-11-21 by three parallel research passes);
  firmware-constrained parts flagged; substitutions carry their firmware
  consequence in-row. nPM1300 Digi-Key row re-verified directly (15,740 in
  stock, $2.519 @10).
- Key selection calls (details in CSV + `hardware_reference.md` §1):
  nRF5340-QKAA-R $9.68/$8.04 @10 · nRF7002-QFAA-R (thin DK stock, incoming
  Dec) · NPM1300-QEAA-R · flash PY25Q64HA-SUH-IR (LCSC-only; ⚠ P25Q64H has
  wrong JEDEC ID) w/ Winbond alt (DTS `jedec-id` edit) · mics TDK MMICT5838
  (0 stock until Dec) w/ Knowles SPH0641LU4H-1 sub (no fw change) · RF switch
  PE42359SCAA-Z · SD Hirose DM3AT · button C&K KMR231NG LFS · antenna Johanson
  2450AT18B0100001E · crystals ECS-320-10-36-CKL-TR (HFXO, CL 10 pF) +
  ECS-.327-7-34B-TR (LFXO, CL 7 pF — matches internal-cap tuning) · inductors
  2×10 µH (nRF5340) + 2×2.2 µH (nPM1300, per PS v1.3 Table 3) · haptic ERM
  VCLP1020B002L (ERM not LRA: PMIC GPIO on/off drive) · USB-C GCT USB4105-GF-A.
- LED decision: **add LED + 1 kΩ on P1.09** (Kingbright APG1005ZGC-5MAV rows
  in BOM); recorded in decisions log. No firmware consequence today.
- Two single-source positions accepted with FLAGs: HSZ 362123 battery and
  Attend 4-pin magnetic pogo (both factory-direct industry-wide, not a
  distributor gap we can buy around).

## Done and verified (M2.0 + M2a)

- **M2a — libraries (2026-11-21):** `kicad/lib/neo_n1.kicad_sym` assembled
  from raw-span copies (nRF5340-QKxx = stock `MCU_Nordic`; nRF7002-QFAA-R7 /
  NPM1300-QEAA-R7 / PE4259 = SnapEDA downloads in `kicad/lib/vendor/`, only
  their KiCad files tracked). Footprints in `kicad/lib/neo_n1_footprints.pretty`
  (SnapEDA nRF5340 die pad renamed `104`→`EP`; regenerating the lib re-applies
  it via `assemble_lib.py`). Project `sym-lib-table`/`fp-lib-table` wired.
  Verified: `symbol_audit.py` zero diffs (48/48 GPIO→ball vs Nordic PS
  aQFN94 table; exact maps for nRF7002/NPM1300/PE4259 vs Nordic PS + pSemi);
  `kicad-cli sym export svg` OK ×4; ERC 0. nPM1300-CAAA zip = BGA variant
  (wrong one — QEAA is our part), reference only.
- **Step 1 — project skeleton (2026-11-21):** `kicad/neo_n1` project; root
  schematic + 6 hierarchical sub-sheets in `kicad/sheets/` (Radio, Power,
  Audio, Memory, USB, Misc — pages 1–7); `kicad/scripts/make_board_skeleton.py`
  creates `neo_n1.kicad_pcb` with 4 copper layers renamed GND/PWR (inner) and
  a placeholder Edge.Cuts outline. Stackup decision + 50 Ω / 90 Ω impedance
  targets in `kicad/stackup.md`; physical stackup numbers deferred to M3
  (fab house undecided). Verified 2026-11-21: `kicad-cli sch erc` 0
  violations; netlist export resolves all 7 sheets; `kicad-cli pcb drc`
  0 violations. Format notes: KiCad 10 writes sch `version 20260306` /
  pcb `version 20260206`; hand-written s-expr files parse fine — validate
  everything with kicad-cli; kicad-cli drops `*-erc.rpt`/`*-drc.rpt` in the
  **cwd** (delete or redirect after runs).

## Next actions (in order)

Sub-milestones with per-step validation live in `MILESTONES.md` §M2
(M2a…M2f). Each ends validated + committed; a fresh session resumes from
this file + the six context docs listed in MILESTONES.md.

1. ~~**M2b — Radio block**~~ **DONE 2026-11-21** (see M2b section above).
2. **M2c — Power block** (`sheets/power.kicad_sch`): nPM1300 power tree
   (2× 2.2 µH BUCK inductors per PS v1.3 Table 3), battery + NTC, all rails
   **incl. the two MAIN-branch load switches** (nRF70_IOVDD P0.26,
   rfsw_vdd P0.29 — BOM row SW2), mic_vdd/flash_vdd gating, LED + 1 kΩ on
   P1.09, I2C1 + PMIC IRQ, haptic→PMIC-GPIO1, VBUS feed. Record the
   nPM1300 integrated VBUS-protection verdict (add VBUS TVS only if
   absent). Netlist-audit expectations for the power nets land with it.
3. **M2d / M2e — Memory+USB, then Audio+Misc.** The radio sheet already
   labels their BUS nets: FLASH_*, SD_*, USB_DP/DN/VBUS, PDM_*, UART_*,
   SWD_*, NRST, BTN_N, LED_ACT, I2C1_*, PMIC_IRQ, HAPTIC_CTRL, MIC_VDD_EN,
   FLASH_VDD_EN — reuse those names verbatim so the full audit connects.
4. **M2f — full netlist audit vs `hardware_reference.md`, zero diffs** —
   M2 acceptance; **also: re-enable the four ERC rules downgraded to
   `ignore` in `neo_n1.kicad_pro` (isolated_pin_label, pin_not_driven,
   multiple_net_names, footprint_link_issues) and require clean ERC**;
   price/stock the 8 new BOM rows.

## Open questions / decisions pending

- ~~LED indicator: add or stay haptic-only? (blocks M2 start)~~ **DECIDED
  2026-11-21: add LED + 0402 series resistor on P1.09.** BOM carries the rows.
- Target fab/assembly house (affects DFM rules in M3 and stencil in M4).
- Battery: keep 240 mAh HSZ 362123 (firmware fuel-gauge model is encoded in
  `battery_model.inc`) or different cell + firmware edit?
- 88×48 CH1115 kept in `display.h`-disabled tree — no action needed unless
  display returns.

## Gotchas that already bit us (do not rediscover)

1. NCS version drift (v3.4.2) breaks DTS compile — use v3.3.0 only.
2. `patches/mcuboot/*.patch` must be applied to the NCS tree before first
   build; they define `CONFIG_MCUBOOT_DISPLAY` etc.
3. Cross-toolchain ccache leak → `CreateProcess failed` on every compile.
4. `west build` pristine takes > 10 min (Opus/Lua/3 images) — background it.
5. `git -C <repo> apply <relative-path>` resolves relative to the repo, not
   the cwd — use absolute patch paths.
6. KiCad s-expr strings must keep literal newlines ESCAPED (`\n`) inside
   quoted strings — a raw newline in a `(text "...")` makes kicad-cli fail
   the whole sheet load with "Failed to load schematic" (silent, rc=3).
7. Never round-trip symbol libs through a custom serializer — embedded
   `lib_symbols` must be RAW text spans of the source lib (quote style
   matters to KiCad's parser). `make_radio_sheet.py::raw_symbol_span` does
   this; reuse it.
8. Components in a sub-sheet need instance paths `"/<root-uuid>/<sheet-uuid>"`
   and placement on the 1.27 mm grid (else 250+ `endpoint_off_grid` ERC
   warnings); SnapEDA symbols' `_0_0` unit sub-symbols are fine with
   `(unit 1)` instances.
9. power:GND/PWR_FLAG pins are `power_in` in KiCad 10 — a net of only
   inputs needs one PWR_FLAG (GND included when no regulator output lands
   on the sheet yet). PWR_FLAG on a Bidirectional pin (BUCKVMID) triggers
   `pin_to_pin` — don't flag self-driven pins.
10. `kicad-cli` runs from the project dir: `cd kicad` first —
    `kicad/neo_n1.kicad_sch` from `try1/` double-prefixes and "fails to
    load". Use `--output` for reports.

## Session-end checklist (for the next agent)

- [ ] `HANDOFF.md` updated (done/next/open)
- [ ] `MILESTONES.md` status boxes updated
- [ ] `hardware_reference.md` still agrees with the firmware tree + design
- [ ] `git status` clean or committed
