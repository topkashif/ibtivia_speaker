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

## M2 — KiCad schematic ☐
- [ ] Project skeleton, 4-layer stackup decided
- [ ] All blocks drawn: nRF5340+nRF7002+antenna switch (copied dimension-for-
      dimension from Nordic nRF7002 DK reference), nPM1300 power tree, PDM
      mics, PY25Q64H, microSD, USB, magnetic charger, SWD + test points
- **Acceptance:** `kicad-cli sch erc` clean; scripted netlist audit passes
  (netlist vs `hardware_reference.md` pin map, zero diffs).

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
