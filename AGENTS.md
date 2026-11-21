# Agent instructions for this workspace

Read this first. It is the entry point for any AI agent (Claude Code, Codex,
Hermes, or a fresh session) picking up work here.

## What this project is

A pin-compatible clone of the Seeed Studio **reSpeaker Clip** wearable voice
recorder (nRF5340 + nRF7002 + nPM1300), **built without the OLED display**.
The firmware source is the authoritative hardware spec.

## Directory map

| Path | Contents |
|---|---|
| `reSpeaker_Clip-main/reSpeaker_Clip-main/` | Firmware repo (Zephyr/NCS). Its own `CLAUDE.md` documents the firmware in depth — read it before touching firmware. **All clone firmware edits happen in this tree; keep them minimal and documented in `HANDOFF.md`.** |
| `hardware_reference.md` | **The hardware contract** — pin map, power tree, BOM-level parts, OLED-removal delta. Every schematic symbol and every DTS decision must agree with this file. Update it when the design changes. |
| `MILESTONES.md` | Milestone list with acceptance criteria and current status. Update status as work completes. |
| `HANDOFF.md` | Current state snapshot for session handoff. **Update this at the end of every working session** — done items, next actions, open questions. |
| `nrf_env.sh` | Build environment for NCS v3.3.0 (source it in git-bash before any `west` command). |
| `kicad/` *(from M2)* | PCB project. |

## Environment facts

- Windows 11, git-bash (MSYS) shell. Python 3.14 (system), KiCad 10.0.8 with
  `kicad-cli` and bundled Python 3.11 at `C:\Program Files\KiCad\10.0\bin\`.
- **NCS v3.3.0 is the only working SDK for this firmware tree.** v3.4.2 fails
  (board partitioning API drift: `s0_partition` vs `slot0_partition`).
  - SDK sources: `C:\ncs\v3.3.0` · toolchain: `C:\ncs\toolchains\936afb6332`
  - The repo's 5 MCUboot patches are ALREADY applied to
    `C:\ncs\v3.3.0\bootloader\mcuboot` (applied 2026-11-20).
  - ccache.exe was copied into the v3.3.0 toolchain `opt/bin` (cross-toolchain
    PATH leak fix).
- No debug probe / hardware yet.

## Core commands

```bash
source /c/Users/Home/Documents/ai/neo_n1_clone/try1/nrf_env.sh
cd reSpeaker_Clip-main/reSpeaker_Clip-main

# firmware build (acceptance: exit 0 + signed artifacts in build-clip/)
west build --build-dir build-clip --pristine --board clip/nrf5340/cpuapp applications/clip

# KiCad checks (from M2 on)
"/c/Program Files/KiCad/10.0/bin/kicad-cli.exe" sch erc kicad/<project>.kicad_sch
"/c/Program Files/KiCad/10.0/bin/kicad-cli.exe" pcb drc --schematic-parity on kicad/<project>.kicad_pcb
```

## Working rules

1. **Verify before claiming done.** Firmware changes → pristine build must
   pass. Schematic → ERC clean + netlist audit vs `hardware_reference.md`.
   Layout → DRC clean. Never report unverified work as done.
2. **Pin-compatibility is the default.** Any pin/rail change must be reflected
   in `hardware_reference.md` AND must name its firmware consequence.
3. **Firmware edits stay minimal** — the upstream repo is the reference; our
   deltas are the OLED removal (M0) plus future documented needs.
4. Commit at every verified milestone and after significant doc updates.
   No `Co-Authored-By` lines; no compiler warnings.
5. Subagent delegation: children see nothing of this conversation — pass the
   file paths in this map plus the specific task context.
