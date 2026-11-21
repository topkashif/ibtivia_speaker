# Stackup & layer assignment — Neo N1 (M2 decision)

4-layer build, assigned per the RF-wearable rule (SIG / GND / PWR / SIG):

| Layer    | KiCad name (in file) | Assignment                                                      |
|----------|----------------------|-----------------------------------------------------------------|
| F.Cu     | `F.Cu`               | **SIG** — components + RF feed (50 Ω CPWG to antenna, ref In1)  |
| In1.Cu   | `GND`                | **GND** — unbroken ground plane; RF reference                   |
| In2.Cu   | `PWR`                | **PWR** — power rails poured/tracked                            |
| B.Cu     | `B.Cu`               | **SIG** — secondary routing, test points                        |

## Impedance targets (to be honored in M3 routing)

| Interface            | Target            | Reference plane |
|----------------------|-------------------|-----------------|
| 2.4 GHz antenna feed | 50 Ω single-ended | In1 GND         |
| USB D+/D−            | 90 Ω differential | In1 GND         |

## Physical stackup — NOMINAL, finalize in M3

The fab house is still undecided (HANDOFF open question), so exact dielectric
thicknesses are not committed yet. Design constraint that drives the choice:
**thin prepreg (~0.1–0.2 mm) between F.Cu and the In1 GND plane** so the 50 Ω
antenna feed is achievable on F.Cu with a reasonable trace width. Standard
1.6 mm finished thickness, 1 oz outer copper assumed as the nominal. When the
fab house is picked, encode the vendor's exact stackup numbers into
`neo_n1.kicad_pcb`'s `(stackup ...)` section and the Board Setup impedance
presets.

The board file created in M2 step 1 carries the layer count and inner-layer
names only (no physical stackup section) — regenerate it with
`kicad/scripts/make_board_skeleton.py` if ever lost.
