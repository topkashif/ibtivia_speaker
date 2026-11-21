# reSpeaker Clone — Hardware Reference (extracted from firmware)

Source: `boards/seeed/clip/clip_nrf5340_cpuapp.dts`, `clip-pinctrl.dtsi`,
`nrf70_common.dtsi`, `docs/power.md`, `docs/requirements.md` in the
reSpeaker_Clip firmware repo.

## 1. Core components (BOM level)

| Function | Part (as used on Clip) | Key specs / notes |
|---|---|---|
| MCU | Nordic **nRF5340 QKAA** (dual Cortex-M33) | DCDC mode for main+radio regulators; 1MB flash / 512KB RAM; package **aQFN-94, 7×7 mm** (orderable NRF5340-QKAA-**R7**, 7″ reel code, same silicon) |
| WiFi/BLE coexist | **nRF7002** module (QSPI) | iovdd-ctrl P0.26, BUCKEN P0.11, HOST_IRQ P0.12, QSPI 24 MHz quad |
| PMIC / Charger | **Nordic nPM1300** @ I2C1 addr 0x6B | Li charger 220 mA, term 4.25 V, VBUS limit 500 mA, NTC 10 kΩ β=3380. Datasheet-checked (PS v1.3): all four values are supported — but PMIC reset default is VTERM 3.60 V / VBUS limit 100 mA, so the host **must** configure them at boot (this firmware already does). 220 mA confirmed in range (32–800 mA); β=3380 is an explicit supported NTC profile |
| Microphones | Dual **PDM** mics, up to 16 kHz | L+R on shared CLK/DIN; rail 1.8 V. **Primary: TDK T5837 MMICT5837-00-012** (−37 dBFS, bottom port, 3.5×2.65 LGA, L/R SEL GND=R/VDD=L — footprint- and convention-identical to T5838; ~+4 dB hotter → gain trim at bring-up). Alternates: T5838 (reference, 0 India shelf) / Knowles SPH0641LU4H-1 (no fw change) |
| External flash | **Puya PY25Q64H** 8 MB SPI-NOR (quad) | JEDEC ID 85 20 17; max 24 MHz used; own rail flash_vdd. Orderable **PY25Q64HA-SUH-IR** (LCSC only — Puya not franchised at DK/Mouser); ⚠ NOT P25Q64H (JEDEC 85 60 17, fails DTS check). Winbond alternates (BOM U4A: W25Q64JVSSIQ SOIC-8 drop-in / SSIM / ZPIQ WSON6×5 / XGIM XSON4×4, all JEDEC **EF 40 17**): swap = DTS `jedec-id` edit + **delete the `sfdp-bfp` override** (Puya-captured) + pristine build; prefer −Q suffixes (QE fixed) over −M (DTR/QPI variant) |
| Storage | microSD (FAT) over SPI4 @ 24 MHz | Own rail VDD_SD (LDO2, power-gated) |
| Battery | Li-Po **HSZ 362123, 240 mAh**, 4.20 V cell | On-cell protection IC; NTC to PMIC TS pin. Alternate on file (BOM BT1A): WLY 601235 — same capacity + PCM but **6.0 mm thick (vs 2.3 mm design) and 2-wire, no NTC**: adopting it requires NTC-pin strap + `DISABLENTC=1` (JEITA supervision lost + driver fix), charge current cut to ≤120 mA (0.5 C), and `battery_model.inc` OCV re-profile |
| Haptic | LRA/ERM vibration motor on BUCK1 (3.3 V) | Switched via nPM1300 GPIO1 (host drives P1.06 → PMIC GPIO1) |
| Button | User button, active-low, pull-up | P1.15 |
| Charging connector | **USB-C receptacle only** (rev-B: magnetic pogo REMOVED) | 16-pin (GCT USB4105-GF-A class), VBUS+D+/D− to nRF5340 USBD; **Rd 5.1 kΩ on each of CC1/CC2 (required — no VBUS without them)** + USBLC6-2SC6 ESD on D+/D−. VBUS → nPM1300 input (500 mA limit); no PD needed (220 mA charge) |
| Crystals | 32 MHz HFXO + 32.768 kHz LFXO | **No external load caps** — internal caps tuned (HFXO 9 pF, LFXO 7 pF) |
| DCDC inductors | **2× 10 µH** (L1, L2) for nRF5340 vregmain/vregradio | Mandatory for the ~500–600 µA DCDC saving |
| nPM1300 BUCK inductors | **2× 2.2 µH** (BUCK1, BUCK2) | Per nPM1300 PS v1.3 Table 3: nominal 2.2 µH, ≤20 %, DCR ≤400 mΩ, Isat >350 mA, ≥4 µF effective out cap. Distinct from the nRF5340 10 µH parts — do not reuse |
| RF antenna switch | SPDT 2.4 GHz on rfsw_vdd (P0.29 rail) | GPIO-controlled (active-high select), 1.8–3.3 V; candidate **pSemi PE42359SCAA-Z** (PE4259-63 cross, same footprint/control) |
| Status LED (rev-B add) | 0402 green LED + 0402 1 kΩ series R on **P1.09** | ~1–1.2 mA when on, 0 when off; P1.09 freed by OLED removal |

## 2. Power tree

```
LiPo 240 mAh ── nPM1300 ─┬─ BUCK1 3V3 ── haptic motor
 (NTC→TS pin)            ├─ BUCK2 3V3 ── MAIN rail (always on): nRF5340,
                         │               nRF7002, OLED-via-oleg_vdd, sensors
                         ├─ LDO1 1V8 ── VDDMIC_1V8 (mics)      [also gated by P1.14 mic_vdd]
                         └─ LDO2 3V3 ── VDD_SD (microSD)       [power-gated, PMIC GPIO3]

GPIO-switched rails: P1.14 mic_vdd · P0.29 rfsw_vdd · P0.27 flash_vdd   [oled_vdd (P1.08) REMOVED — no OLED]
USB-C VBUS → nPM1300 VBUS input (500 mA limit) — sole charge path (rev-B: pogo removed, nothing in firmware referenced it; charging/VBUS/shutdown gating all read the PMIC)
```

## 3. Full pin map (keep identical so firmware builds unchanged)

| Signal | Pin | Notes |
|---|---|---|
| UART TX / RX | P1.05 / P1.04 | Console 921600 baud |
| I2C1 (PMIC) SDA/SCL | P0.04 / P0.05 | PMIC @0x6B |
| I2C2 (OLED) SDA/SCL | P1.02 / P1.03 | CH1115 @0x3C |
| PDM CLK / DIN | P1.10 / P1.11 | Dual mics, L/R select on mic RST/SEL pin |
| SPI3 flash SCK/MOSI/MISO | P0.22 / P0.24 / P0.23 | PY25Q64H |
| Flash CS / WP / HOLD | P0.20 / P0.19 / P0.21 | |
| SPI4 SD SCK/MOSI/MISO | P0.06 / P0.08 / P0.07 | microSD |
| SD CS | P0.09 | |
| QSPI SCK/CSN | P0.17 / P0.18 | nRF7002 |
| QSPI IO0–IO3 | P0.13 / P0.14 / P0.15 / P0.16 | nRF7002 |
| nRF7002 iovdd-ctrl / BUCKEN / HOST_IRQ | P0.26 / P0.11 / P0.12 | |
| Coex REQ/STATUS0/GRANT/SWCTRL1 | P0.28 / P0.25 / P0.31 / P0.30 | PTA, only if you keep coex |
| RF switch rail enable | P0.29 | rfsw_vdd |
| Flash rail enable | P0.27 | flash_vdd |
| Mic rail enable | P1.14 | mic_vdd |
| OLED rail enable | P1.08 | oled_vdd |
| PMIC interrupt | P0.10 | nPM1300 GPIO1 → GPOIRQ |
| Haptic control (→ PMIC GPIO1) | P1.06 | |
| OLED reset | P1.09 | |
| User button | P1.15 | pull-up, active-low |
| USB | D+/D− → nRF5340 USBD | CDC ACM + MSC; VBUS detect required |

## 4. Firmware-relevant layout facts

- Idle target: **~350 µA @ 3.7 V** (production build); every leak counts.
- Crystals have **no external caps**; tuning is done in DTS (`lfxo`/`hfxo` test
  commands in `tests/clip`). Layout quality directly affects the tuned value.
- SD rail is power-gated — don't add pull-ups from MAIN 3V3 to SD lines
  (they back-feed a powered-down card).
- VBUS-aware USB — wire VBUS to a voltage divider/GPIO (or PMIC VBUS status).
- `boot_mode0` recovery + nRF5340 SWD (SWDIO/SWCLK, both cores via DCC) and
  **test points on every rail and SPI bus** make bring-up possible.

## 5. Rev-B delta: OLED removed

Freed hardware:
- **I2C2 bus (P1.02/P1.03) disappears entirely** — the OLED was its only device.
- **oled_vdd rail gone** (was gpio1.08); OLED reset line gpio1.09 freed.
- P1.08 / P1.09 / P1.02 / P1.03 become spare GPIOs (good UART/I2C breakout points).

Firmware changes (APPLIED in this tree — see git diff / file list below):
1. `clip_nrf5340_cpuapp.dts`: removed `zephyr,display` from `chosen`, the
   `ch1115` node, the `oled_reg` regulator, and the `&i2c2` block.
   `i2c2_default/i2c2_sleep` pinctrl groups left in place (unreferenced = inert).
2. `applications/clip/Kconfig`: added `CONFIG_CLIP_DISPLAY` (default y).
   `display.h` now compiles to no-op inline stubs when disabled — all 9
   callers build unchanged. `CMakeLists.txt` compiles `display.c`/`icons.c`
   only under the guard.
3. `applications/clip/prj.conf`: `CONFIG_CLIP_DISPLAY=n`, `CONFIG_DISPLAY=n`
   (this tree is the no-OLED clone; flip both back to re-add a display).
4. `boards/seeed/clip/sysbuild/mcuboot.conf`: `CONFIG_MCUBOOT_DISPLAY=n`;
   `mcuboot.overlay`: removed `&oled_reg` enable.
5. `applications/clip/boards/clip_nrf5340_cpuapp.overlay`: removed the
   `&ch1115`/`&i2c2` enable blocks.
6. NOT ported (bench tools, defer to bring-up): `tests/clip`, `tests/re`,
   `tests/battery_cycle`, `tests/dtm`, `tests/wifi_radio`, `tests/wifi_shell`
   overlays still reference `&oled_reg`/`&i2c2` and will not build until their
   `oled.c` modules are stubbed the same way.
7. Compile check pending: this machine has no NCS/west toolchain — verify with
   `west build --pristine --board clip/nrf5340/cpuapp applications/clip` or push
   to a fork so the `firmware.yml` CI build runs.

Layout impact: no display cutout / FPC at the board edge, one fewer switched
rail to route, small idle-power saving (~OLED sleep draw). Everything else in
the phase plan is unchanged.
