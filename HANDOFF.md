# Handoff — read me first

Last updated: 2026-11-20. Project map and rules: `AGENTS.md`.
Milestones: `MILESTONES.md`. Hardware contract: `hardware_reference.md`.

## Current state (30-second version)

Building a pin-compatible clone of the Seeed reSpeaker Clip wearable recorder
**without the OLED**. Firmware tree is modified and verified: it builds
completely under NCS v3.3.0 with the display compiled out. No KiCad project
exists yet. No hardware exists yet.

## Done and verified

- OLED removal applied across 7 firmware files (board DTS, app Kconfig /
  CMakeLists / display.h stubs / prj.conf, MCUboot conf + overlay, app board
  overlay). Verified: build exit 0, signed artifacts generated,
  `CONFIG_CLIP_DISPLAY`/`CONFIG_MCUBOOT_DISPLAY` not set, no display objects
  linked. See `MILESTONES.md` M0 and `hardware_reference.md` §5 for the
  file-by-file delta.
- NCS v3.3.0 installed at `C:\ncs\v3.3.0` (toolchain `936afb6332`); the 5
  MCUboot patches applied to `C:\ncs\v3.3.0\bootloader\mcuboot`; ccache copied
  into that toolchain's `opt/bin`. **v3.4.2 does not build this tree** — do
  not "upgrade".
- A successful build lives in
  `reSpeaker_Clip-main/reSpeaker_Clip-main/build-clip/` (gitignored).

## Next actions (in order)

1. **M1 — BOM:** turn `hardware_reference.md` §1 into `bom/bom.csv` with MPNs,
   stock, price, second sources. Cross-check firmware-encoded specs against
   datasheets; flag non-substitutable parts (nPM1300, battery w/ NTC, flash
   JEDEC ID).
2. Decide: LED indicator on a spare GPIO (yes/no) before schematic capture.
3. **M2 — KiCad:** create `kicad/` project; copy nRF7002 DK reference
   schematics for the nRF5340+nRF7002+antenna block; then write the netlist
   audit script (KiCad Python) comparing nets to `hardware_reference.md`.

## Open questions / decisions pending

- LED indicator: add or stay haptic-only? (blocks M2 start)
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
