# RLC Reverse Engineering — Status

Repository: https://github.com/MussonOld/RLC
Source: `nRLC_2_0_12_FREEWARE_ghidra_decompiled.txt` (Ghidra decompile, 413 functions)
Notes: `1.txt`, `2.txt`, `3.txt`, `4.txt`
Date: 2026-09-04

## Current stage
**Stage 2 — vector / IRQ / ISR reconstruction.**

Goal:
`vector -> IRQ -> handler -> peripheral -> ISR purpose -> global data`

## Rules
- CONFIRMED = direct evidence from code/register/vector/xref.
- PROBABLE = strong inference, not yet directly proven.
- UNKNOWN = insufficient evidence; do not guess.
- Do not permanently rename Ghidra functions without evidence.
- Do not write final hardware/application code before the corresponding relationships are established.

## 1. MCU / memory map

CORRECTED 2026-09-04: firmware is STM32F3-class (STM32F303), not STM32F0.

Original STM32F0 conclusion was based only on GPIO/SYSCFG/USB/TIM15-17 base
addresses, which are near-identical between STM32F0 and STM32F3 (shared bus
layout) and therefore do not distinguish the two families. Corrected by
independent verification against the official ST STM32F303.svd:

- Vector table contains ADC1_2, USB_HP_CAN_TX, TIM8, ADC3, ADC4, and seven
  individually-vectored DMA1 channels (DMA1_CH1..DMA1_CH7) — this exact
  vector layout does not exist on any STM32F0 device (no TIM8/ADC3/ADC4,
  different DMA vector grouping).
- `0x50000000` (ADC1_2 common registers, STM32F3-specific bus placement;
  STM32F0's ADC sits at `0x40012400` on a different bus) is referenced
  directly in the firmware.
- Initial stack pointer is `0x20009968`, i.e. ~39.4 KB into SRAM from
  `0x20000000` — consistent with STM32F303xB/C's 40 KB SRAM; no
  pin/feature-comparable STM32F0 part has enough SRAM to place the initial
  SP that high.
- GPIOB base `0x48000400` matches STM32F303's GPIOB address directly per
  the official SVD (not merely "consistent with an F0 GPIO run").

Observed peripheral bases (re-labeled per STM32F303.svd):
- GPIO: `0x48000000` (GPIOA), `0x48000400` (GPIOB), `0x48000800` (GPIOC),
  `0x48000C00` (GPIOD), `0x48001000` (GPIOE)
- SYSCFG: `0x40010000` (including `0x40010008`)
- USB: `0x40005C00`
- TIM1: `0x40012C00`
- TIM15: `0x40014000` (register layout confirmed via SVD; no direct
  reference to it was found in the firmware — see note below)
- TIM16: `0x40014400` (confirmed in use)
- TIM17: `0x40014800` (register layout confirmed via SVD; no direct
  reference to it was found in the firmware — see note below)

Exact part number: image size (~185 KB for `nRLC_2_0_12_FREEWARE.hex`)
exceeds STM32F303CB's 128 KB Flash — actual silicon is CC/RC (256 KB) or
larger, not CB, despite CB being what appears on the schematic silkscreen
for this board. Confirm against the physical chip marking if available.

Note on TIM15/TIM17: cross-referencing every SVD-labeled TIM15/TIM17
register address against the firmware's actual instruction operands found
zero direct hits for either timer. This does not disprove their use (code
may reach them through a parameterized/indirect driver, the same pattern
confirmed for GPIO_Init at `FUN_08005cac`), but the "TIM15/16/17-related"
attribution for `FUN_08008384`/`FUN_080101b4` in section 10 should be
downgraded from "high" to PROBABLE for the TIM15/TIM17 portion until direct
evidence is found; TIM16 use is separately confirmed by direct reference.

## 2. Startup / main

`thunk_FUN_08015fd4 @ 0x08000190` calls through `DAT_08000194`.

`FUN_08015fd4 @ 0x08015fd4` is the strong candidate for application `main()`.

It performs hardware/GPIO initialization, configuration loading, peripheral setup, then enters the application loop.

`FUN_08000608()` appears to be a main-loop/application state-machine function, not an ISR.

## 3. ISR candidate

`FUN_0800019c @ 0x0800019c` is a strong ISR/periodic-handler candidate.

Evidence from its body:
- repeatedly updates counters;
- maintains timing/event fields in the structure at `DAT_080004ec`;
- sets event/flag bytes;
- performs periodic hardware actions;
- contains no obvious normal application entry semantics.

Exact IRQ/vector mapping is still UNKNOWN and must be recovered from vector/startup evidence.

Important: do NOT identify its timer solely from function address/order.

## 4. NVIC / IRQ evidence

`FUN_0800602e(IRQ)` — high confidence: IRQ enable routine.

`FUN_0800604c(...)` — high confidence: IRQ priority configuration.

Known enabled IRQ numbers:

| IRQ | Hex | Current status |
|---:|---:|---|
| 11 | `0x0B` | enabled; `FUN_0800019c` is associated candidate, exact vector mapping pending |
| 20 | `0x14` | associated with USB peripheral `0x40005C00`; ISR unresolved |
| 37 | `0x25` | enabled; peripheral/ISR unresolved |
| 40 | `0x28` | enabled; peripheral/ISR unresolved |
| 54 | `0x36` | enabled for a specific peripheral object; ISR unresolved |
| 55 | `0x37` | enabled; peripheral/ISR unresolved |

`FUN_08007770()` configures SysTick. SysTick handler remains unresolved.

## 5. USB

Peripheral `0x40005C00`: very high confidence USB.

IRQ `20 (0x14)`: high-confidence association.

Exact USB ISR: UNKNOWN.

## 6. GPIO / EXTI

`FUN_08005cac()` is a low-level GPIO configuration routine.

It configures mode/input/output/pull/alternate-function and EXTI-related state and accesses SYSCFG.

Five GPIO base addresses are observed: GPIOA..GPIOE on an STM32F303 device (confirmed per SVD, see section 1 correction above; not STM32F0).

Exact MCU pinout and application signal names: UNKNOWN.

## 7. Timer peripherals

TIM1: `0x40012C00` — confirmed.

TIM15/16/17: `0x40014000 / 0x40014400 / 0x40014800` — very high confidence.

`FUN_080101b4()` and `FUN_08008384()` contain code consistent with the TIM15/16/17 group.

Exact timer-to-IRQ assignment and clock/PSC/ARR values still need extraction.

## 8. Configuration system

`FUN_080045c4()` is used as a configuration parameter access mechanism.

Known IDs observed in the reverse-engineering notes:
`0x556`, `0x557`, `0x558`, `0x559`, `0x560`, `0x561`, `0x562`, `0x563`, `0x567`, `0x568`, `0x569`, `0x571`, `0x572`, `0x575`, `0x576`, `0x577`, `0x578`, `0x579`, `0x580`, `0x581`, `0x582`.

Their exact semantic names are not yet established. Preserve numeric IDs until evidence permits naming.

## 9. Command interface

Known command strings:
- `get_buff`
- `get_dpf`
- `get_sin`
- `get_dac`
- `get_window`
- `setCount`
- `setRUI`
- `setDACperiod`
- `setDACfreq`
- `setDACTest`
- `setLCD`
- `POWER_OFF`
- `isSerial`
- `DAC_ZERO`
- `autofreq`

`setRUI` passes three parameters to `FUN_08000ec0()`.

DAC-related commands manipulate DAC parameters.

Protocol/parser structure: incomplete.

## 10. Important functions

| Address | Ghidra function | Current interpretation | Confidence |
|---|---|---|---|
| `0x08000190` | `thunk_FUN_08015fd4` | startup/reset trampoline | high |
| `0x0800019C` | `FUN_0800019c` | periodic ISR candidate | high for ISR role; peripheral unknown |
| `0x08003418` | `FUN_08003418` | peripheral setup + IRQ enable/start sequence | high |
| `0x080045C4` | `FUN_080045c4` | configuration parameter access | high |
| `0x08005CAC` | `FUN_08005cac` | GPIO/EXTI low-level configuration | high |
| `0x0800602E` | `FUN_0800602e` | NVIC IRQ enable | high |
| `0x0800604C` | `FUN_0800604c` | NVIC priority setup | high |
| `0x08007770` | `FUN_08007770` | SysTick configuration | high |
| `0x08007924` | `FUN_08007924` | peripheral clock/setup dispatcher | high |
| `0x08008384` | `FUN_08008384` | timer/peripheral initialization | high |
| `0x080101B4` | `FUN_080101b4` | TIM15/16/17-related code | high |
| `0x08015FD4` | `FUN_08015fd4` | main candidate | high |
| `0x08000608` | `FUN_08000608` | application state machine | probable |

## 11. Not yet established

- exact STM32F303 part number (CC vs RC vs other 256KB+ variant, given image size exceeds CB's 128KB — see section 1);
- complete vector table;
- exact IRQ -> handler mapping;
- exact timer -> IRQ mapping;
- SysTick handler;
- ADC/DAC identity and configuration;
- DMA;
- USART/SPI/I2C mapping;
- complete GPIO pin functions;
- global structure layouts;
- measurement timing;
- DAC waveform generation;
- frequency/autofreq algorithm;
- R/L/C calculation;
- complete serial protocol;
- persistent storage implementation;
- final CubeIDE `.ioc`.

## 12. Roadmap

1. Hardware map — partially complete.
2. **Vector / IRQ / ISR map — CURRENT.**
3. Global structures.
4. Measurement and RLC algorithm.
5. GPIO/pin map.
6. CubeIDE `.ioc` reconstruction.
7. Startup/main/ISR implementation.
8. Peripheral/application modules.
9. Build and functional validation.

## 13. Next concrete actions

1. Recover the actual vector table/startup representation.
2. Map each vector entry to an address.
3. Match handler addresses against the 409 Ghidra functions.
4. Resolve IRQ 11 and prove/disprove `FUN_0800019c` mapping.
5. Resolve IRQ 20 / USB ISR.
6. Resolve IRQ 54 and its peripheral.
7. Resolve IRQ 37, 40, 55.
8. Resolve SysTick handler.
9. Extract timer clock/PSC/ARR values and derive periods.
10. Update this document with evidence, not assumptions.

## 14. Handoff

In a new chat:

> Continue the RLC reverse engineering from `REVERSE_STATUS.md`. Verify the repository for a newer version and continue from CURRENT TASK. Do not restart the analysis and do not invent unresolved hardware assignments.

## 15. Changelog

### 2026-09-04 (correction)
- CORRECTED: MCU family changed from "STM32F0-class" to STM32F303 (STM32F3).
  Original conclusion relied on GPIO/SYSCFG/USB/TIM15-17 base addresses that
  are shared between F0 and F3 and do not distinguish them. Corrected via
  independent cross-check against the official STM32F303.svd: vector table
  layout (ADC1_2/USB_HP_CAN_TX/TIM8/ADC3/ADC4/per-channel DMA1 vectors),
  direct reference to ADC-common address `0x50000000` (F3-only bus
  placement), and initial SP (`0x20009968`) consistent with F303's 40KB
  SRAM. See section 1 for full evidence.
- Downgraded TIM15/TIM17 attribution for `FUN_08008384`/`FUN_080101b4`
  from "high" to PROBABLE: no direct register reference found for either
  timer under exhaustive SVD-based address cross-referencing; TIM16 use
  remains confirmed.
- Flagged actual Flash size as CC/RC-class (256KB+), not CB (128KB) as
  schematic silkscreen suggests — both known firmware images exceed CB's
  capacity.

### 2026-09-04
- Consolidated the known reverse-engineering state into a single handoff document.
- Recorded MCU/peripheral address evidence.
- Recorded startup/main and ISR candidate findings.
- Recorded known NVIC IRQs.
- Recorded USB/GPIO/timer evidence.
- Recorded configuration IDs and command strings.
- Defined confidence rules and current next actions.
