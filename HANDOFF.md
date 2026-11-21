# Handoff — read me first

Last updated: 2026-11-21. Project map and rules: `AGENTS.md`.
Milestones: `MILESTONES.md`. Hardware contract: `hardware_reference.md`.

## Current state (30-second version)

Building a pin-compatible clone of the Seeed reSpeaker Clip wearable recorder
**without the OLED**. Firmware builds under NCS v3.3.0 with display compiled
out (M0 done). **M1 done: costed BOM with alternates lives in `bom/bom.csv`
(24 rows, priced 2026-11-21)**; hardware contract updated with the BOM
findings. No KiCad project exists yet. No hardware exists yet.

## Done and verified

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

## Next actions (in order)

1. **M2 — KiCad:** create `kicad/` project (4-layer SIG/GND/PWR/SIG); copy
   nRF7002 DK reference schematics for the nRF5340+nRF7002+antenna block
   (antenna: Johanson keep-out + shunt-L/series-C pi pads); then write the
   netlist audit script (KiCad Python) comparing nets to
   `hardware_reference.md` — which now includes the LED on P1.09 and the
   nPM1300 2.2 µH BUCK inductors.

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

## Session-end checklist (for the next agent)

- [ ] `HANDOFF.md` updated (done/next/open)
- [ ] `MILESTONES.md` status boxes updated
- [ ] `hardware_reference.md` still agrees with the firmware tree + design
- [ ] `git status` clean or committed
