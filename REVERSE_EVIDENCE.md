# RLC Reverse Engineering — Evidence Dossier

**Repository:** https://github.com/MussonOld/RLC  
**Source dump:** `nRLC_2_0_01.txt` — Ghidra decompile, 409 functions  
**Working notes:** `1.txt`, `2.txt`, `3.txt`, `4.txt`  
**Status document:** `REVERSE_STATUS.md`  
**Date:** 2026-09-04

## 0. Purpose

This document records evidence used to reconstruct the original firmware architecture. It deliberately separates direct observations from strong inferences and unresolved questions.

Confidence levels:

- **CONFIRMED** — directly supported by code, register addresses, vector/xref evidence, or equivalent hard evidence.
- **PROBABLE** — strong architectural inference, but not yet directly proven.
- **UNKNOWN** — insufficient evidence; no assignment should be made in the reconstructed firmware.

The rule for reconstruction is: **do not turn a probable interpretation into a permanent hardware/software assignment until the corresponding evidence is recovered.**

---

## 1. MCU and memory-map evidence

### 1.1 MCU family

**CORRECTED 2026-09-04:** the firmware is for an STM32F303 (STM32F3-class)
device, not STM32F0 as originally concluded. The addresses below are
near-identical between F0 and F3 (shared AHB2/APB bus layout) and by
themselves do not distinguish the families — that was the error. Family
was re-established via: vector table entries with no STM32F0 equivalent
(ADC1_2, USB_HP_CAN_TX, TIM8, ADC3, ADC4, per-channel DMA1_CH1..CH7 vectors);
a direct firmware reference to `0x50000000` (ADC1_2 common — F3-specific
bus placement; F0's ADC is at `0x40012400` on a different bus entirely);
and initial SP `0x20009968` (~39.4KB into SRAM), consistent only with
STM32F303xB/C's 40KB SRAM.

Observed peripheral address ranges in the decompile, re-labeled per the
official STM32F303.svd:

| Address | Interpretation | Confidence |
|---|---|---|
| `0x48000000` | GPIOA | confirmed (SVD) |
| `0x48000400` | GPIOB | confirmed (SVD) |
| `0x48000800` | GPIOC | confirmed (SVD) |
| `0x48000C00` | GPIOD | confirmed (SVD) |
| `0x48001000` | GPIOE | confirmed (SVD) |
| `0x40010000` | SYSCFG | confirmed |
| `0x40010008` | SYSCFG EXTICR-related access | high |
| `0x40005C00` | USB peripheral | very high |
| `0x40012C00` | TIM1 | confirmed |
| `0x40014000` | TIM15 | register layout confirmed (SVD); no direct firmware reference found — downgrade attribution to PROBABLE |
| `0x40014400` | TIM16 | confirmed in use (direct reference) |
| `0x40014800` | TIM17 | register layout confirmed (SVD); no direct firmware reference found — downgrade attribution to PROBABLE |
| `0x50000000` | ADC1_2 common (F3-specific) | confirmed (direct reference; decisive family evidence) |

Five GPIO bases are GPIOA..GPIOE on an STM32F303 device (confirmed per SVD).

**Part number:** exact variant still not pinned down, but both known
firmware images (`nRLC_2_0_01.hex` ~158.7KB, `nRLC_2_0_12_FREEWARE.hex`
~185KB) exceed STM32F303CB's 128KB Flash — actual silicon is CC/RC
(256KB) or larger, despite CB appearing on the board schematic silkscreen.

---

## 2. Startup and main() evidence

### 2.1 Reset/startup trampoline

At `0x08000190` there is:

`thunk_FUN_08015fd4`

It transfers control through `DAT_08000194` to `FUN_08015fd4 @ 0x08015FD4`.

**PROBABLE:** `0x08000190` is a startup/reset trampoline and `FUN_08015fd4()` is the application entry/main function.

The important point is not merely its address. `FUN_08015fd4()` has the behavior expected from a firmware main routine: substantial hardware initialization, configuration loading, peripheral setup, diagnostic/startup work, followed by an endless application loop.

### 2.2 Main-loop structure

The loop contains `WaitForInterrupt()` and repeated application-level calls including:

- `FUN_08000608()`
- `FUN_0801831c(0)`
- `FUN_08009610()`
- repeated `FUN_08000608()` execution

**HIGH CONFIDENCE:** `FUN_08015fd4()` is the main application candidate.

**PROBABLE:** `FUN_08000608()` is an application state-machine/event-processing function rather than an ISR.

### 2.3 Main initialization phases

The observed execution order supports the following conceptual decomposition:

```text
FUN_08015fd4()
  |
  +-- hardware/GPIO initialization
  +-- configuration loading
  +-- peripheral/driver initialization
  +-- initial diagnostics/startup
  +-- application startup
  +-- while(1)
        +-- WaitForInterrupt()
        +-- event/state processing
        +-- application functions
```

This decomposition is an architectural reconstruction, not a claim about original source-file boundaries.

---

## 3. ISR evidence

### 3.1 `FUN_0800019c @ 0x0800019C`

`FUN_0800019c()` is a strong interrupt/periodic-handler candidate.

Observed properties:

- located immediately after the startup/trampoline area;
- no obvious normal application-entry semantics;
- no obvious normal application callers in the exported analysis;
- updates timing counters;
- modifies event/flag state;
- maintains timing-related fields associated with `DAT_080004ec`;
- performs periodic hardware actions;
- contains a 64-bit counter and multiple dividers/counters, including factors such as 10, 3 and 5;
- calls `FUN_0800fdd8()`.

**CONFIRMED:** the function behaves like an ISR/periodic handler.

**UNKNOWN:** exact vector number, exact IRQ line, and exact peripheral/timer source.

**Important restriction:** the timer must not be identified solely from the function's address or its position near startup code.

---

## 4. NVIC / interrupt evidence

### 4.1 NVIC helper functions

`FUN_0800602e(IRQ)` is a high-confidence IRQ-enable routine.

`FUN_0800604c(...)` is a high-confidence IRQ-priority configuration routine.

### 4.2 Observed enabled IRQs

| IRQ | Hex | Evidence / current interpretation |
|---:|---:|---|
| 11 | `0x0B` | explicitly enabled; `FUN_0800019c()` is an associated candidate, but vector mapping is not proven |
| 20 | `0x14` | associated with peripheral `0x40005C00`, strongly consistent with USB |
| 37 | `0x25` | enabled; peripheral/handler unresolved |
| 40 | `0x28` | enabled; peripheral/handler unresolved |
| 54 | `0x36` | enabled by a specific peripheral object/setup path; handler unresolved |
| 55 | `0x37` | enabled; peripheral/handler unresolved |

`FUN_08007770()` configures SysTick.

**UNKNOWN:** SysTick handler.

### 4.3 Current IRQ reconstruction rule

The enabled IRQ number alone is not enough to assign a handler. The final mapping must be obtained from the actual vector table/startup representation and cross-referenced with handler addresses.

---

## 5. USB evidence

Peripheral base `0x40005C00` is the USB peripheral (address shared between STM32F0 and STM32F303; not family-distinguishing on its own — see section 1 correction for the actual family evidence).

A separate IRQ `0x14` (decimal 20) is associated with this peripheral setup.

Therefore:

```text
IRQ 20 (0x14)
    |
    +-- peripheral @ 0x40005C00
          |
          +-- USB (very high confidence)
```

**UNKNOWN:** exact USB ISR function.

---

## 6. GPIO / EXTI evidence

`FUN_08005cac()` is a low-level GPIO configuration routine.

Its behavior includes configuration of:

- GPIO mode;
- input/output state;
- pull configuration;
- alternate function;
- EXTI-related configuration;
- multiple GPIO peripheral bases;
- SYSCFG access.

Observed GPIO bases:

```text
0x48000000
0x48000400
0x48000800
0x48000C00
0x48001000
```

Observed SYSCFG-related address:

```text
0x40010008
```

This is strong evidence for GPIO + SYSCFG/EXTI configuration on STM32F303 (address range shared with F0; see section 1 for the family-distinguishing evidence).

### Reconstruction target

The function can eventually be decomposed conceptually into operations such as:

```c
GPIO_Config(...);
GPIO_SetMode(...);
GPIO_SetPull(...);
GPIO_SetAlternateFunction(...);
GPIO_SetEXTI(...);
```

These are **reconstruction names**, not recovered original symbol names.

**UNKNOWN:** exact MCU pinout and application signal names.

---

## 7. Timer evidence

The following peripheral bases are identified:

```text
TIM1  = 0x40012C00
TIM15 = 0x40014000
TIM16 = 0x40014400
TIM17 = 0x40014800
```

`FUN_080101b4()` and `FUN_08008384()` contain code operating on the `0x40014000 / 0x40014400 / 0x40014800` group, providing direct support for the TIM15/16/17 interpretation.

**CONFIRMED:** TIM1 address.

**VERY HIGH CONFIDENCE:** TIM15/TIM16/TIM17 addresses and their presence in the firmware.

**UNKNOWN:**

- which timer generates `FUN_0800019c()`;
- exact timer-to-IRQ mapping;
- timer clock source;
- PSC values;
- ARR values;
- resulting interrupt periods;
- exact application role of each timer.

These values must be extracted from the original register writes before creating the final CubeIDE timer configuration.

---

## 8. Peripheral initialization evidence

### 8.1 `FUN_08007924()`

`FUN_08007924()` acts as a probable common peripheral clock/setup dispatcher.

It distinguishes different peripheral blocks, including timer and SPI/I2C-like peripherals, and contains an IRQ-enable path for one peripheral.

**CONFIRMED at architectural level:** the firmware has a common low-level peripheral initialization layer.

**UNKNOWN:** exact original driver/module names.

### 8.2 `FUN_08003418()`

`FUN_08003418()` performs a coherent peripheral initialization sequence:

1. enables a peripheral clock;
2. calculates a frequency-dependent parameter;
3. calls `FUN_080078c0()`;
4. configures the peripheral;
5. enables IRQ `0x36` (54);
6. starts the peripheral by setting a bit at offset `+0x0C`.

Therefore IRQ 54 is tied to a specific peripheral object handled by this setup path.

**CONFIRMED:** IRQ 54 is not merely a random global flag; it is enabled as part of a concrete peripheral initialization path.

**UNKNOWN:** exact peripheral identity and ISR.

### 8.3 Common initializer sequence

The following functions appear in a repeated peripheral/driver initialization sequence:

```text
FUN_080078c0()
FUN_08007aee()
FUN_08008320()
FUN_0800782c()
FUN_08007fd8()
FUN_0800779c()
FUN_08007c78()
FUN_08008384()
```

They should be treated as a related low-level API/driver layer until individual roles are proven.

### 8.4 `DAT_08016894`

`DAT_08016894` is an important initialization object. Values observed during setup include:

```text
0x40000000
0
0
0xFFFF
```

followed by multiple initializer calls.

**UNKNOWN:** exact structure type and peripheral identity.

Do not assign a C structure name until field usage and offsets are reconstructed.

---

## 9. Configuration system evidence

`FUN_080045c4()` is a high-confidence configuration parameter access function.

Observed behavior: it searches for a 16-bit parameter identifier and returns/uses the associated value.

Known identifiers:

```text
0x556
0x557
0x558
0x559
0x560
0x561
0x562
0x563
0x567
0x568
0x569
0x571
0x572
0x575
0x576
0x577
0x578
0x579
0x580
0x581
0x582
```

Observed value domains/usages from the current notes:

| ID | Observed values / role | Status |
|---|---|---|
| `0x571` | mode/type | probable |
| `0x556` | parameter used with `asStack_2c` | unknown semantic name |
| `0x581` | parameter via `DAT_080163f8` | unknown |
| `0x557` | value | unknown |
| `0x558` | `0..7` | unknown |
| `0x561` | `0`, `0x78`, `300`, `600` | unknown |
| `0x559` + `0x560` | composite 32-bit value | probable |
| `0x562` | `1,3,4,6,9,10` | unknown |
| `0x563` | boolean | probable |
| `0x567` | `0..2` | unknown |
| `0x568` | `0..3` | unknown |
| `0x569` | boolean | probable |
| `0x572` | boolean | probable |
| `0x575` | `1..4` | unknown |
| `0x576` | `0..2` | unknown |
| `0x577` | `50` or `100` | unknown |
| `0x578` | boolean | probable |
| `0x579` | boolean | probable |
| `0x580` | boolean | probable |
| `0x582` | `0,1,2` | unknown |

**Reconstruction rule:** preserve these numeric IDs in `config.h/config.c` until their semantic meanings are directly established.

---

## 10. Command-interface evidence

The firmware contains the following command strings:

```text
get_buff
get_dpf
get_sin
get_dac
get_window
setCount
setRUI
setDACperiod
setDACfreq
setDACTest
setLCD
POWER_OFF
isSerial
DAC_ZERO
autofreq
```

`setRUI` passes three parameters to `FUN_08000ec0()`.

DAC-related commands manipulate DAC parameters.

This justifies a future reconstructed module boundary such as:

```text
commands.c
commands.h
```

but the complete parser/protocol is **not yet reconstructed**.

---

## 11. Main-loop event architecture

The main-loop code accesses multiple event/flag bytes represented by Ghidra as offsets such as:

```text
pcVar2[3]
pcVar2[7]
pcVar2[0xB]
pcVar2[0xC]
pcVar2[0xD]
pcVar2[0xE]
pcVar2[0xF]
pcVar2[0x11]
pcVar2[0x12]
```

There are also numerous global event/data objects in the `DAT_080171xx` region.

**PROBABLE:** the application uses an event-driven/state-machine architecture with interrupt-generated timing/events feeding the main loop.

**UNKNOWN:** exact event names, structure layout, and producer/consumer relationships.

This is one reason the interrupt map must be reconstructed before rewriting the application loop.

---

## 12. Important function index

| Address | Ghidra function | Current interpretation | Confidence |
|---|---|---|---|
| `0x08000190` | `thunk_FUN_08015fd4` | startup/reset trampoline | high |
| `0x0800019C` | `FUN_0800019c` | periodic ISR candidate | high for ISR role; peripheral unknown |
| `0x08000608` | `FUN_08000608` | application state machine | probable |
| `0x08003418` | `FUN_08003418` | peripheral setup + IRQ enable/start | high |
| `0x080045C4` | `FUN_080045c4` | configuration parameter access | high |
| `0x08005CAC` | `FUN_08005cac` | GPIO/EXTI low-level configuration | high |
| `0x0800602E` | `FUN_0800602e` | NVIC IRQ enable | high |
| `0x0800604C` | `FUN_0800604c` | NVIC priority setup | high |
| `0x08007770` | `FUN_08007770` | SysTick configuration | high |
| `0x08007924` | `FUN_08007924` | peripheral clock/setup dispatcher | high |
| `0x08008384` | `FUN_08008384` | timer/peripheral initialization | high |
| `0x080101B4` | `FUN_080101b4` | TIM15/16/17-related code | high |
| `0x08015FD4` | `FUN_08015fd4` | main candidate | high |

---

## 13. What is established vs. not established

### Established with high confidence

- STM32F303 (STM32F3-class) target — corrected 2026-09-04 from an earlier
  "STM32F0-class" conclusion; see section 1.
- GPIO peripheral region and five observed GPIO bases (GPIOA..E, confirmed per SVD).
- SYSCFG/EXTI involvement.
- TIM1 at `0x40012C00`.
- TIM16 at `0x40014400` (confirmed by direct reference). TIM15/TIM17
  register layout at `0x40014000`/`0x40014800` confirmed per SVD, but no
  direct firmware reference found — downgraded to PROBABLE.
- USB peripheral at `0x40005C00`.
- Direct reference to `0x50000000` (ADC1_2 common, F3-specific) — the
  decisive evidence for the family correction above.
- `FUN_08015fd4()` as the main/application-entry candidate.
- `FUN_0800602e()` as NVIC IRQ enable helper.
- `FUN_0800604c()` as IRQ-priority helper.
- `FUN_08007770()` as SysTick configuration.
- `FUN_08005cac()` as low-level GPIO/EXTI configuration.
- `FUN_080045c4()` as configuration parameter access.
- `FUN_08003418()` as a peripheral setup/start path with IRQ 54 enable.
- `FUN_0800019c()` as a strong ISR/periodic-handler candidate.

### Not yet established

- exact STM32F303 part number (image size on both known firmware builds
  exceeds CB's 128KB, so actual silicon is CC/RC or larger, not CB);
- complete vector table;
- exact vector -> IRQ -> handler mapping;
- exact timer -> IRQ mapping;
- SysTick handler;
- exact ADC/DAC identity and configuration;
- DMA channels and functions;
- USART/SPI/I2C mapping;
- complete GPIO pin functions;
- global structure layouts;
- measurement timing;
- DAC waveform generation;
- frequency/autofreq algorithm;
- R/L/C calculation;
- complete serial protocol;
- persistent-storage implementation;
- final CubeIDE `.ioc`.

---

## 14. Current reconstruction strategy

The reconstruction should proceed in this order:

```text
Ghidra dump
   |
   v
hardware/peripheral map
   |
   v
vector table
   |
   v
IRQ -> handler
   |
   v
handler -> peripheral
   |
   v
peripheral -> GPIO/pins
   |
   v
global structures
   |
   v
measurement/RLC algorithm
   |
   v
CubeIDE .ioc
   |
   v
startup/main/ISR implementation
   |
   v
peripheral/application modules
   |
   v
build + validation
```

Do not skip directly from register addresses to a guessed `.ioc`.

---

## 15. Immediate next actions

1. Recover the actual vector table/startup representation.
2. Enumerate every vector entry and resolve its target address.
3. Match vector targets against the 409 Ghidra functions.
4. Prove or disprove the mapping of IRQ 11 to `FUN_0800019c()`.
5. Resolve IRQ 20 / USB ISR.
6. Resolve IRQ 54 and identify the associated peripheral.
7. Resolve IRQs 37, 40 and 55.
8. Resolve the SysTick handler.
9. Extract timer clock, PSC and ARR register values.
10. Derive actual timer periods.
11. Only then begin final `.ioc` reconstruction.

---

## 16. Evidence sources

Primary reverse-engineering material in repository:

- `nRLC_2_0_01.txt` — raw Ghidra decompile.
- `1.txt` — initial reverse-engineering observations.
- `2.txt` — reconstruction plan and vector/IRQ roadmap.
- `3.txt` — main/configuration/ISR observations.
- `4.txt` — interrupt/peripheral/timer/USB follow-up observations.
- `REVERSE_STATUS.md` — current project status and handoff state.

Repository: https://github.com/MussonOld/RLC

The notes above are consolidated evidence, not a replacement for checking the raw decompile when a hardware or function assignment becomes important.
