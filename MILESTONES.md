# Milestones — reSpeaker Clip clone (no OLED)

Status: ☐ open · ◐ in progress · ✅ done. Update this file whenever status
changes; put detail in `HANDOFF.md`.

## M0 — Firmware boundary locked ✅
Clone boots the upstream firmware minus the OLED, pin-compatible.
- [x] Hardware contract extracted from BSP into `hardware_reference.md`
- [x] OLED removed: board DTS (`chosen`, `ch1115`, `oled_reg`, `&i2c2`), app
      overlay, MCUboot overlay + conf
- [x] `CONFIG_CLIP_DISPLAY` Kconfig guard + no-op `display.h` stubs; 9 callers
      verified covered
- [x] NCS v3.3.0 installed (v3.4.2 incompatible); MCUboot patches applied to
      NCS tree; ccache fixed
- [x] **Acceptance met:** pristine build exit 0; signed artifacts
      (`merged.hex`, `dfu_application.zip`, `signed_by_*.hex/bin`); no
      `display.c.obj`/`icons.c.obj`; `CONFIG_CLIP_DISPLAY`/`CONFIG_MCUBOOT_DISPLAY`
      not set in image configs

## M1 — Costed BOM with alternates ✅
- [x] Per-block component list from `hardware_reference.md` §1 with exact
      MPNs, packages, distributor stock (2+), unit price at qty 10
- [x] Firmware-encoded specs cross-checked against datasheets (nPM1300 charger
      220 mA / NTC β 3380 / flash JEDEC `85 20 17` / PDM L-R / 240 mAh cell w/
      NTC) — non-substitutable parts flagged
- [x] Passives standardized (0402, stock values)
- **Acceptance:** `bom/bom.csv` complete — 24 rows, every line has a 2nd
  source or an explicit FLAG (battery + magnetic pogo: factory-direct only;
  T5838 + exact Puya: single-distis until Dec-2026). Open substitutions with
  firmware edits: flash swap → `jedec-id` DTS edit; different cell →
  `battery_model.inc` OCV re-characterization; Knowles mic → gain-table
  revisit. Datasheet verdicts: all 4 firmware-encoded nPM1300 values
  supported (PS v1.3) — note reset defaults VTERM 3.60 V / VBUS 100 mA are
  host-configured (our firmware does this); nPM1300 BUCKs need **2.2 µH**
  inductors (not 1.5 µH); nRF5340 QKAA is **aQFN-94** (not aQFN73).

## M2 — KiCad schematic ◐

Each sub-milestone below is session-sized and ends with its own validation
commands passing, `HANDOFF.md` updated, and a commit. A fresh session picks
up from `HANDOFF.md` → first unchecked sub-milestone; it never needs context
beyond `AGENTS.md` + `HANDOFF.md` + `MILESTONES.md` + `hardware_reference.md`
+ `bom/bom.csv` + `kicad/stackup.md`.

- [x] **M2.0 — Project skeleton, 4-layer stackup decided** — `kicad/` project
      (`neo_n1`), 6-block sheet hierarchy (Radio/Power/Audio/Memory/USB/Misc,
      pages 1–7), SIG/GND/PWR/SIG in `kicad/stackup.md`.
      *Validated 2026-11-21:* ERC 0, netlist export resolves all 7 sheets,
      DRC 0 (placeholder Edge.Cuts outline).
- [x] **M2a — Libraries.** Project symbol lib `kicad/lib/neo_n1.kicad_sym`
      (nRF5340-QKxx from stock `MCU_Nordic`; nRF7002-QFAA-R7, NPM1300-QEAA-R7,
      PE4259 from user-fetched SnapEDA vendor downloads in
      `kicad/lib/vendor/`) + 4 footprints in
      `kicad/lib/neo_n1_footprints.pretty` + project `sym-lib-table` /
      `fp-lib-table`. Symbol↔footprint fixes: SnapEDA nRF5340 die pad
      renumbered `104`→`EP`. nPM1300-CAAA (BGA) zip = wrong variant, kept as
      reference only.
      *Validated 2026-11-21:* `symbol_audit.py` — zero diffs: all 48
      nRF5340 GPIO→ball mappings match the Nordic PS aQFN94 table, exact
      pin maps verified for nRF7002 (49, vs Nordic QFN ref schematic),
      nPM1300 (33, vs Nordic PS QFN32 table), PE4259 (6, vs pSemi DS Table
      7); every symbol pin exists as a footprint pad; all 4 symbols export
      via `kicad-cli sym export svg`; ERC still 0.
- [ ] **M2b — Radio block drawn** (`sheets/radio.kicad_sch`): nRF5340 +
      nRF7002 + PE4259 + antenna pi pads (shunt-L/series-C, keep-out note for
      M3) + both crystals w/ load caps + coex PTA pins — dimension-for-
      dimension from the Nordic nRF7002 DK reference schematic (fetch it
      first).
      *Validate:* ERC 0; netlist export; **`kicad/scripts/netlist_audit.py`
      (new, written this step) in per-block mode** — radio nets vs pin map,
      zero diffs; SVG export of the sheet for eyeball review.
- [ ] **M2c — Power block drawn** (`sheets/power.kicad_sch`): nPM1300 power
      tree (2× 2.2 µH BUCK inductors, PS v1.3 Table 3), battery HSZ 362123 +
      NTC, all rails incl. SD gated rail, LED + 1 kΩ on P1.09. Record the
      datasheet verdict on nPM1300 integrated VBUS input protection (add
      VBUS TVS only if absent) — checklist item from the pogo removal.
      *Validate:* ERC 0; netlist_audit.py per-block (rail nets, gating
      GPIOs, charger sense) — zero diffs.
- [ ] **M2d — Memory + USB blocks drawn** (`sheets/memory.kicad_sch`,
      `sheets/usb.kicad_sch`): PY25Q64HA (footprint fits Winbond alt),
      microSD DM3AT on gated rail, USB-C USB4105 + 2× 5.1 kΩ CC Rd +
      USBLC6-2SC6 ESD; **no pogo pads anywhere**.
      *Validate:* ERC 0; netlist_audit.py per-block — zero diffs; explicit
      check that no pull-up on a gated rail sources from an ungated rail.
- [ ] **M2e — Audio + Misc blocks drawn** (`sheets/audio.kicad_sch`,
      `sheets/misc.kicad_sch`): PDM mics L/R (T5837 primary, footprint fits
      Knowles SPH0641 sub), ERM haptic on PMIC GPIO drive, SWD + test points
      on every rail and bus, user button KMR231NG.
      *Validate:* ERC 0; netlist_audit.py per-block — zero diffs.
- [ ] **M2f — Full acceptance & docs.** netlist_audit.py in full mode:
      netlist vs `hardware_reference.md` pin map, **zero diffs**; ERC clean
      on the whole project; fold any pin-map corrections learned while
      drawing back into `hardware_reference.md`; MILESTONES/HANDOFF status
      updates. (May share a session with M2e when smooth.)

- **Acceptance (umbrella):** `kicad-cli sch erc` clean; scripted netlist
  audit passes (netlist vs `hardware_reference.md` pin map, zero diffs).

## M3 — PCB layout ☐
- [ ] Floorplan (antenna → RF → MCU → crystals → power → edge)
- [ ] Antenna keep-out on all layers; 50 Ω CPWG; USB 90 Ω pair length-matched
- [ ] Switched rails can't back-feed powered-down devices (SD power-gating)
- [ ] No back-feeding pull-ups from MAIN 3V3 onto gated rails
- **Acceptance:** `kicad-cli pcb drc --schematic-parity on` clean; 3D viewer
  check; gerbers exported and fab DFM check passed.

## M4 — Fabrication & assembly ☐
- [ ] 4-layer fab order (ENIG), stencil, components ordered
- [ ] Assembly notes (reflow/hand-solder order: PMIC first, QFNs, then passives)
- **Acceptance:** order placed; board files + BOM + PnP archived in repo.

## M5 — Firmware bring-up ☐ (blocked by M4)
- [ ] Port bench test images (`tests/clip`, `tests/re`, `tests/battery_cycle`
      — stub their private `oled.c` modules same as M0)
- [ ] Bring-up order: PMIC rails → SWD → netcore/BLE → crystal tune (`lfxo`/
      `hfxo` shell) → PDM mics → flash → SD → WiFi
- **Acceptance:** hardware test suite `tests/clip` passes on the clone;
  tuned crystal caps recorded in DTS.

## M6 — Power validation ☐ (blocked by M5)
- **Acceptance:** PPK2/Joulescope trace: idle ≤ ~350 µA @ 3.7 V (production
  snippet), SD power-gating engages after 45 s, recording < 80 mA.

## Deferred / decisions log
- No OLED → no visual UI (haptic + button only). ~~Optional LED on spare GPIO
  (P1.02/P1.03/P1.08/P1.09 free) — decide by M2.~~ **DECIDED (M1): add a
  status LED + 0402 series resistor on spare GPIO P1.09 (formerly OLED
  reset).** No firmware consequence today (P1.09 is unused in the no-OLED
  tree); an LED app module is future work, not M1 scope.
- Keep coex PTA pins (P0.25/28/30/31) for now; revisit if antenna switch is
  simplified.
