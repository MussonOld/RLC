# GPIO Port Map & Non-Obvious Hardware Behavior

Source: schematic (as improved/annotated by MussonOld) + `nRLC_STM32F303CBT6.NET`
(Protel netlist export, component reference `U15` in this netlist revision).
Pin-to-port mapping cross-checked against the official ST datasheet (DS9118,
Table 13, LQFP48 column).

**MCU on this schematic revision: `STM32F303CCT6` (256KB Flash), not CBT6.**
Confirmed directly from the netlist parts list — matches the earlier
reverse-engineering finding that both known firmware images exceed CBT6's
128KB capacity. Peripheral/pinout map is identical between CBT6 and CCT6
(same silicon family, only Flash size differs), so this does not affect any
ISR/peripheral-address work already done.

## Full pin table (LQFP48)

| Pin | Port | Net | Role |
|---:|---|---|---|
| 5 | PF0-OSC_IN | OSC_IN | HSE crystal |
| 6 | PF1-OSC_OUT | OSC_OUT | HSE crystal |
| 7 | NRST | N\R\S\T\ | reset |
| 8 | VSSA/VREF- | AGND | analog ground |
| 9 | VDDA/VREF+ | An_3V3 | analog supply |
| 10 | PA0 | — | **I_DAC** — current-channel DAC output |
| 11 | PA1 | — | **JOY_OK** button read (center joystick) |
| 12 | PA2 | JOY_C | joystick button C |
| 13 | PA3 | — | **not connected** |
| 14 | PA4 | NetR18-1 | analog front-end (PGA feedback network) |
| 15 | PA5 | NetR11-1 | analog front-end |
| 16 | PA6 | NetC35-2 | analog front-end |
| 17 | PA7 | — | **not connected** |
| 18 | PB0 | ACLK | SPI clock to both PGA113 (U10/U11) |
| 19 | PB1 | AMOSI | SPI MOSI to both PGA113 |
| 20 | PB2 | I_CS | PGA113 chip-select, current channel |
| 21 | PB10 | U_CS | PGA113 chip-select, voltage channel |
| 22 | PB11 | NetBLE1-1 | to Bluetooth module (HM17/HM19) |
| 23 | VSS | GND | digital ground |
| 24 | VDD | Dig_3V3 | digital supply |
| 25 | PB12 | — | **JOY_B button read** (see joystick/power section) |
| 26 | PB13 | AX_CS | BMI160 (accelerometer) chip-select, SPI |
| 27 | PB14 | — | **JOY_A / JOY_D analog read** (ADC) — see joystick section |
| 28 | PB15 | Display_CS | LCD chip-select |
| 29 | PA8 | ZP | piezo/speaker |
| 30 | PA9 | TX | USART1 TX |
| 31 | PA10 | RX | USART1 RX |
| 32 | PA11 | — | **not connected** — MCU's built-in USB (D-) is unused |
| 33 | PA12 | — | **not connected** — MCU's built-in USB (D+) is unused |
| 34 | PA13 | NetR48-2 | SWDIO |
| 35 | VSS | GND | digital ground |
| 36 | VDD | Dig_3V3 | digital supply |
| 37 | PA14 | NetR49-2 | SWCLK |
| 38 | PA15 | Vbus1 | USB VBUS detect (input only — board has a physical USB-C connector for charging, but the MCU does not implement a USB device stack; see pin 32/33) |
| 39 | PB3 | NetR50-4 | SPI3 (confirmed by MussonOld) |
| 40 | PB4 | NetR50-3 | SPI3 |
| 41 | PB5 | NetR50-2 | SPI3 |
| 42 | PB6 | — | **not connected** — I2C1_SCL unused, free for repurposing |
| 43 | PB7 | — | **not connected** — I2C1_SDA unused, free for repurposing |
| 44 | BOOT0 | NetR51-1 | boot mode select — see JOY_B section |
| 45 | PB8 | BL | display backlight |
| 46 | PB9 | VD_ON | power self-latch (see power-on section) |
| 47 | VSS | GND | digital ground |
| 48 | VDD | Dig_3V3 | digital supply |

Pins 13/17/32/33/42/43 (`PA3`, `PA7`, `PA11`, `PA12`, `PB6`, `PB7`) have **no
net connection anywhere in the netlist** — confirmed absent by direct search,
not just "no interesting label". I2C1 was independently confirmed unused by
Ghidra peripheral cross-reference (zero register accesses anywhere in the
firmware) before this schematic check — two independent sources now agree.

## Power-on mechanism

Two independent hardware paths can power on the device from fully off:

1. **JOY_OK long press** — mechanically pulls both `PA1` (so firmware can
   read the button) and `PWR_ON` low at the same time. `PWR_ON` going low
   turns on `Q2` (P-channel MOSFET), which applies VCC to the rest of the
   board. This works even with the MCU completely unpowered — it's a pure
   hardware latch trigger, not something firmware initiates.
2. **Accelerometer INT1** — ORed with `VD_ON` through diode `D3` onto the
   gate of `Q1` (N-channel), which pulls `PWR_ON` low the same way. Lets the
   BMI160 wake the device (e.g. on motion) without the firmware or JOY_OK
   involved.

**Self-latch:** once running, firmware must itself drive `VD_ON` (= `PB9`)
to keep `Q1` (and therefore `Q2`/VCC) held on. If firmware never asserts
`VD_ON`, or stops asserting it, the board powers back off. This is the
likely reason a low-level periodic housekeeping task exists (candidate:
part of what `FUN_0800019c` / the SysTick body does — not yet confirmed by
direct code reading, flagged here as a lead for that analysis).

## Joystick (5-way, `SW1_Disp`)

| Button | Read via | Mechanism |
|---|---|---|
| **JOY_OK** (center) | `PA1` | short press = ordinary button; **long press** additionally triggers the power-on hardware path above |
| **JOY_B** (up) | `PB12` | opens `Q2_Disp`, which applies `VBAT` to *both* `BOOT0` and `PB12` simultaneously. `PB12` lets firmware read it as a normal button; `BOOT0` being pulled high (if held across a reset) puts the STM32 into hardware DFU bootloader mode. Same physical button therefore serves double duty depending on when it's pressed. |
| **JOY_C** | `PA2` | ordinary digital button |
| **JOY_A** / **JOY_D** | `PB14` (ADC, shared with battery monitoring) | both buttons sag the same analog line (`BAT`) that's also used for battery-voltage monitoring, but to different levels — confirmed by MussonOld: **JOY_A pulls the line fully to 0**, **JOY_D only partially sags it** (resistor divider, not a direct short). Expect at least 3 threshold bands when this ADC channel's handling code is read: ~0 = JOY_A, some partial-sag band = JOY_D, normal/higher range = battery-voltage reading (possibly with further sub-bands for charge level). This is a concrete prediction to check against once the PB14 ADC-handling code is opened — not yet done. |

## Open items this file doesn't resolve

- Exact ADC threshold constants used to distinguish JOY_A / JOY_D / battery
  level on the PB14 channel — not yet located in the firmware.
- Whether `VD_ON` assertion is actually inside `FUN_0800019c` (SysTick body)
  or elsewhere — plausible given the self-latch requirement, not confirmed
  by code reading yet.
- `NetR51-1` is shared between `PB12` (pin 25) and `BOOT0` (pin 44) in the
  netlist parse — worth a sanity check against the schematic image directly
  if this becomes relevant, since it reads as slightly unusual (a resistor
  network node touching both a GPIO and BOOT0 rather than each having its
  own independent pull network).
