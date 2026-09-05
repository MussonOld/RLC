# RLC Reverse Engineering — Status

Repository: https://github.com/MussonOld/RLC
Source: `nRLC_2_0_12_FREEWARE_ghidra_decompiled.txt` (Ghidra decompile, 413 functions)
Date: 2026-09-04

## Current stage
**Stage 2 — vector / IRQ / ISR reconstruction.**

Goal:
`vector -> IRQ -> handler -> peripheral -> ISR purpose -> global data`

### Agreed analysis order (2026-09-04)
Anchor-first, not function-by-function guessing: establish who writes
which peripheral registers and from what context before assigning
meaning to any individual function.

1. `Reset_Handler` at `0x080023B8` — anchor. Expect: `.data` init,
   `.bss` clear, where control passes to `main`, which peripheral-init
   functions get called from here. **DONE 2026-09-04 — see section 2.**
   Result: 4-instruction trampoline calling `FUN_0800ff68` then tail-
   chaining through `0x08000188` -> `FUN_08002d48` -> `FUN_08016274`
   (confirmed main()). No explicit inline `.data`/`.bss` loop was found
   in `Reset_Handler` itself — it must happen inside one of the three
   called functions, not yet individually opened.
2. `SysTick_Handler` at `0x0800FDCC` — what register/flag it touches,
   whether there's a software tick/scheduler, actual period. **DONE
   2026-09-04 — see section 4.2.** Result: resolves the `FUN_0800019c`
   question from step-3-in-waiting — it's the SysTick body, reached by
   tail-call, not a plain `bl`. Reload value / actual period still
   open.
3. Confirmed-vector ISRs, in this order (all addresses direct from the
   vector table, see section 4.1):
   `DMA1_CH1 0x08000644`, `DMA1_CH3 0x08004010`, `DMA1_CH4 0x0800401C`,
   `DMA1_CH5 0x08004028`, `USB 0x080126E4`, `USART1 0x08010B5C`,
   `TIM6 0x0800237C`, `TIM7 0x0800FF78`, `DMA2_CH1 0x08004034`,
   `DMA2_CH3 0x08004040`. TIM6/TIM7 + DMA are the priority pair — likely
   source of the real timing architecture.

### Explicitly not doing yet
- reconstructing `main.c` from Ghidra names;
- assigning `FUN_0800019c` any purpose;
- concluding a DMA channel's purpose from its channel number alone;
- searching the binary blindly for PSC/ARR values.

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

## 2. Startup / main — CONFIRMED 2026-09-04 (full traced chain, not pattern-matched)

Traced directly from `Reset_Handler` forward — every hop below is a
verified `blx`/`bl`/tail-jump target read from the actual instruction
operands and literal pool, not inferred from address proximity:

```
Reset_Handler (0x080023B8, 4 instructions total)
  |-- blx FUN_0800ff68        (0 callees, touches no labeled peripheral —
  |                             likely low-level setup: clock/FPU/watchdog)
  `-- tail-jump (bx) -> trampoline @ 0x08000188
        |-- reloads SP (ldr.w sp, [pc, #0xc])
        |-- bl FUN_08002d48   (2 callees, no labeled peripheral — likely
        |                       C runtime init: .data copy / .bss zero)
        `-- tail-jump (bx, via literal) -> FUN_08016274
              (84 callees; touches ADC4, CRC, DBGMCU, GPIOA, GPIOB,
               GPIOC, IWDG, RCC, SPI1, TIM1, TIM16, TIM2, TIM3 —
               this is CONFIRMED as the application main() equivalent:
               broad hardware/peripheral init, matches the profile
               previously found by pattern alone for 2.0.01's
               FUN_08015fd4, but here established by direct call-chain
               trace from Reset_Handler rather than inference)
```

`FUN_08016274` performs hardware/GPIO initialization, configuration
loading, and peripheral setup, then (not yet traced further) presumably
enters the application loop.

`FUN_0800019c` is NOT reachable through this chain — none of the four
functions above call or jump to it. This doesn't resolve how
`FUN_0800019c` is reached (see section 3), it only rules out "part of
normal startup" as an explanation.

`FUN_08000608()` appears to be a main-loop/application state-machine
function, not an ISR (address/role carried over from prior analysis;
not yet re-verified against 2.0.12 by direct trace).

## 3. ISR candidate — status revised 2026-09-04, RESOLVED 2026-09-04 (see section 4.2)

**Resolved: `FUN_0800019c` is the SysTick handler body, reached via a
tail-call `b.w` branch from `SysTick_Handler` — see section 4.2 for the
full evidence.** The reasoning trail below is kept for the record (it
correctly identified that the "zero callers" finding was insufficient
evidence of dead code, which is exactly what turned out to be true).

`FUN_0800019c @ 0x0800019c` — was rated a strong ISR/periodic-handler
candidate based on zero direct `bl` callers plus its body evidence
(counters, timing/event fields, periodic hardware actions).

**Vector-table check (this session): direct disproof of ISR-via-vector.**
Read the full vector table of `nRLC_2_0_12_FREEWARE.hex` (first 100
entries, IRQ -16..84) and searched for `0x0800019c` — not present at any
vector slot. Also searched the entire firmware image for the literal
32-bit value `0x0800019c`/`0x0800019d` (Thumb-bit set) as raw data — zero
occurrences anywhere, meaning it is not stored in any plain
function-pointer table either.

**New lead:** the firmware contains 14 Thumb-2 `TBB`/`TBH` instructions
(compact PC-relative jump tables, typically compiled from `switch`
statements) at addresses including `0x08002258`, `0x0800c7c2`,
`0x0800c862`, `0x0800c9a4`, `0x0800caa6`, `0x0800cd50`, `0x0800df0a`,
`0x0800fd34`, `0x08010714`, `0x08010736` (+4 more, see decompile). This
is the most likely way `FUN_0800019c` — and possibly the command
dispatcher behind the confirmed command strings in section 9 — is
reached, since `bl`/raw-pointer search excludes the two more common
mechanisms. None of the 14 tables have been decoded yet to confirm or
rule out a jump target at `0x0800019c`.

**Status: no static caller found by the four mechanisms checked so far
(direct `bl` call, vector table, raw pointer data, TBB/TBH jump table).
This is NOT evidence that the function is dead/unreferenced — several
untested reach mechanisms remain (see list below). Correct current
formulation: "`FUN_0800019c` is not proven as an ISR and has no
statically-discovered caller yet" — NOT "`FUN_0800019c` is dead code."**
The body evidence (counters/timing fields/periodic actions) still
stands and doesn't rule out an ISR; the original "strong candidate"
rating rested on an assumption (no callers implies ISR) that a third
dispatch mechanism (TBB/TBH) invalidates, so the confidence level is
revised down to UNKNOWN pending further evidence, not down to "unused."

**TBB/TBH decode result (this session): negative.** Decoded all 14
TBB/TBH tables (bounds detected from the preceding `cmp`/bounds-check
instruction, plus a generous 60-entry re-scan at both possible table
alignments as a safety margin) — none of the 14 tables contain an entry
resolving to `0x0800019c`. Combined with the vector-table and raw-
pointer-data searches above, **none of the four reach mechanisms
checked so far (direct call, vector table, raw pointer, TBB/TBH jump
table) explain how this function is invoked.**

Remaining hypotheses, none yet investigated:
- called via a computed address held in a register (`BX`/`BLX Rn`)
  where the register is loaded from something other than a static
  literal or the tables checked so far;
- address formed arithmetically at runtime (base + computed offset)
  rather than read from any fixed table;
- `FUN_0800019c` is an entry point reached by a mechanism other than an
  ordinary call — e.g. a secondary/chained vector table, a bootloader
  handoff, or similar — not yet checked;
- the function boundary Ghidra assigned is imprecise — the real,
  referenced entry point could be a different address within or
  adjacent to this code, with `0x0800019c` merely a convenient (but
  wrong) split point;
- dead/unreferenced code (e.g. from a statically-linked library
  routine never actually called by this build) — listed for
  completeness only; not privileged over the other hypotheses above
  and not to be treated as a working conclusion.

**Follow-up (same session): vector-table search completed exhaustively,
still negative; retraction of a misreading.** The original vector-table
search (idx 0..99) missed the table's final entry (idx 100 = IRQ84 =
SPI4); re-checked through idx 105 — still zero matches for
`0x0800019c`/`0x0800019d`. The real vector table runs `idx 0..100`
(addresses `0x08000000`-`0x08000190`), ending at IRQ84, immediately
followed by a small literal pool (values `0x08016275` and `0x20009968`
at idx 101/102 are data, not vector entries — they are constants read
by a `ldr r0,[pc,#0]; bx r0` computed-jump sequence at
`0x08000190`-`0x08000192`, targeting `0x08016275`). An earlier note in
this section describing this region as a "mini Reset_Handler /
possible embedded secondary image" was a misreading — it's ordinary
vector-table tail + literal pool + one computed jump unrelated to
`FUN_0800019c`, not a distinct embedded structure. `FUN_0800019c`
begins immediately after this literal pool at `0x0800019c`, which
appears to be coincidental placement, not evidence of anything.

Net effect: the vector-table hypothesis is now confirmed exhaustively
dead (not just "likely" dead). The three remaining hypotheses above are
unchanged; the computed-address-dataflow route is probably the most
promising next step, given a `bx r0`-style computed jump was just found
one function earlier in the image — worth checking whether similar
patterns elsewhere in the firmware target `0x0800019c` specifically.

Important: do NOT identify its timer solely from function address/order.

## 4. NVIC / IRQ evidence

`FUN_0800602e(IRQ)` — high confidence: IRQ enable routine.

`FUN_0800604c(...)` — high confidence: IRQ priority configuration.

### 4.1 Vector table — CONFIRMED (direct read of nRLC_2_0_12_FREEWARE.hex vector table, cross-checked against the official STM32F303.svd interrupt map)

| IRQ | STM32F303 designation | Handler address | Status |
|---:|---|---|---|
| 11 | DMA1_CH1 | `0x08000644` | implemented |
| 13 | DMA1_CH3 | `0x08004010` | implemented |
| 14 | DMA1_CH4 | `0x0800401C` | implemented |
| 15 | DMA1_CH5 | `0x08004028` | implemented |
| 20 | USB_LP_CAN_RX0 | `0x080126E4` | implemented |
| 37 | USART1_EXTI25 | `0x08010B5C` | implemented |
| 40 | EXTI15_10 | `0x10000B28` | implemented; body relocated to CCM RAM (0x1000xxxx) |
| 54 | TIM6_DACUNDER | `0x0800237C` | implemented |
| 55 | TIM7 | `0x0800FF78` | implemented |
| 56 | DMA2_CH1 | `0x08004034` | implemented |
| 57 | DMA2_CH2 | `0x080023D2` | implemented |
| 58 | DMA2_CH3 | `0x08004040` | implemented |
| 59 | DMA2_CH4 | `0x080023D2` | **not implemented** — same address as default/unhandled-IRQ handler |
| 60 | DMA2_CH5 | `0x080023D2` | **not implemented** — same address as default/unhandled-IRQ handler |
| 61 | ADC4 | `0x080023D2` | **not implemented** — same address as default/unhandled-IRQ handler |

Correction note: an earlier pass had IRQ54-59 mapped as
DMA2_Channel1..DMA2_Channel4/ADC4 directly following IRQ40, which
incorrectly skipped the TIM6_DACUNDER (54) and TIM7 (55) vector slots
present in the real STM32F303 vector table. The table above replaces
that mapping; it is a direct read of the vector table cross-checked
against the SVD interrupt list, not a reconstruction from memory.

### 4.2 SysTick — RESOLVED 2026-09-04

`SysTick_Handler @ 0x0800FDCC` (confirmed by vector table idx=15,
Cortex-M exception 15 = SysTick, value `0x0800FDCD` matches exactly):

```
push {r4, lr}
bl   FUN_08005f88      ; ordinary call, not yet opened
pop  {r4, lr}
b.w  0x0800019c          ; TAIL CALL (branch, not bl) into FUN_0800019c
```

This resolves the `FUN_0800019c` mystery from section 3: it is reached
via an unconditional tail-call branch (`b.w`), not a `bl` instruction —
which is exactly why every `bl`-based caller search in section 3 found
zero results. It was never dead code; the reach mechanism just wasn't
one of the four checked. **`FUN_0800019c` is CONFIRMED as the body of
the SysTick handler**, executed on every SysTick tick after
`SysTick_Handler` first calls `FUN_08005f88`. Section 3's original body
evidence (counters, timing/event fields, periodic hardware actions) is
now explained, not just consistent.

`FUN_08005f88` — not yet opened; likely candidate for a millisecond
tick counter or similar SysTick-adjacent bookkeeping, unconfirmed.

Still open: SysTick reload value (`SYST_RVR`) / actual tick period not
yet extracted — needed to convert `FUN_0800019c`'s counters into real
time units.

`FUN_08007770()` was previously listed as "configures SysTick" — this
was a 2.0.01 address never re-verified for 2.0.12 (see the stale-table
warning in section 10); do not rely on it until re-checked.

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

**⚠ STALE TABLE — flagged 2026-09-04, not yet fixed.** All rows below
were established against `nRLC_2_0_01.hex`. When this session switched
the analysis target to `nRLC_2_0_12_FREEWARE.hex`, these addresses were
never re-verified. Direct check just now: of the 11 addresses below,
**only `FUN_0800019c` still resolves to a function at the same address
in 2.0.12** (confirmed coincidentally while tracing Reset_Handler); the
other 10 do NOT exist at these addresses in the 2.0.12 build (function
layout shifted between versions). Do not treat any "high confidence"
rating below as applying to 2.0.12 until each row is individually
re-resolved against the current binary — treat this whole table as
UNKNOWN/unverified-for-2.0.12 except the two rows marked CONFIRMED.

| Address | Ghidra function | Current interpretation | Confidence |
|---|---|---|---|
| `0x080023B8` | `Reset_Handler` | reset entry — CONFIRMED 2026-09-04 for 2.0.12, see section 2 | high (2.0.12) |
| `0x0800FF68`, `0x08002D48`, `0x08016274` | startup chain (see section 2) | clock/FPU/wdg init, C runtime init, main() | high (2.0.12) |
| `0x0800019C` | `FUN_0800019c` | **RESOLVED**: body of SysTick handler, reached via tail-call `b.w` from `SysTick_Handler` — see section 4.2 | confirmed |
| `0x08003418` | `FUN_08003418` (2.0.01 address) | peripheral setup + IRQ enable/start sequence | **unverified for 2.0.12 — address does not resolve** |
| `0x080045C4` | `FUN_080045c4` (2.0.01 address) | configuration parameter access | **unverified for 2.0.12 — address does not resolve** |
| `0x08005CAC` | `FUN_08005cac` (2.0.01 address) | GPIO/EXTI low-level configuration | **unverified for 2.0.12 — address does not resolve** |
| `0x0800602E` | `FUN_0800602e` (2.0.01 address) | NVIC IRQ enable | **unverified for 2.0.12 — address does not resolve** |
| `0x0800604C` | `FUN_0800604c` (2.0.01 address) | NVIC priority setup | **unverified for 2.0.12 — address does not resolve** |
| `0x08007770` | `FUN_08007770` (2.0.01 address) | SysTick configuration | **unverified for 2.0.12 — address does not resolve; see section 4.2, real SysTick anchor for 2.0.12 is `0x0800FDCC`** |
| `0x08007924` | `FUN_08007924` (2.0.01 address) | peripheral clock/setup dispatcher | **unverified for 2.0.12 — address does not resolve** |
| `0x08008384` | `FUN_08008384` (2.0.01 address) | timer/peripheral initialization | **unverified for 2.0.12 — address does not resolve** |
| `0x080101B4` | `FUN_080101b4` (2.0.01 address) | TIM15/16/17-related code | **unverified for 2.0.12 — address does not resolve** |
| `0x08000608` | `FUN_08000608` (2.0.01 address) | application state machine | **unverified for 2.0.12 — address does not resolve** |

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

1. Recover the actual vector table/startup representation. — DONE 2026-09-04
2. Map each vector entry to an address. — DONE for IRQ 11/13/14/15/20/37/40/54-61 (see 4.1)
3. Match handler addresses against the Ghidra functions. — partially done
4. Resolve IRQ 11 and prove/disprove `FUN_0800019c` mapping. — DISPROVED as a vector-table match; TBB/TBH hypothesis also checked and DISPROVED (all 14 tables decoded, no match). New task: trace via computed-address dataflow, or verify `0x0800019c` is a real function entry point at all (see section 3)
5. Resolve IRQ 20 / USB ISR.
6. ~~Resolve IRQ 54 and its peripheral.~~ RESOLVED 2026-09-04: IRQ54 = TIM6_DACUNDER (see 4.1)
7. ~~Resolve IRQ 37, 40, 55.~~ RESOLVED 2026-09-04 (IRQ37=USART1, IRQ40=EXTI15_10, IRQ55=TIM7 — see 4.1)
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
