# Сессия RE: железо + генератор + .ioc — 2026-09-09

Отчёт для проверки (не патч в `REVERSE_STATUS.md`). Источники: `.hex`, Ghidra decomp, netlist/`GPIO_MAP.md`, HSE=12 МГц (подтверждение владельца).

---

## 1. RCC / тактирование — CONFIRMED

**Вход:** HSE = 12 МГц (кварц на плате).

**Из прошивки** (`FUN_0800fddc` ≈ SystemClock_Config, `FUN_0800fee0` ≈ SystemCoreClockUpdate, литералы в `.hex`):

| Параметр | Значение |
|----------|----------|
| HSE | 12 000 000 |
| PLL source | HSE |
| PREDIV | 1 |
| PLLMUL | ×6 |
| **SYSCLK / HCLK** | **72 МГц** |
| APB1 | /2 → **36 МГц** |
| APB2 | /1 → **72 МГц** |
| TIM2 / TIM3 clock | **72 МГц** (×2 при APB1 ≠ 1) |
| `SystemCoreClock` | `0x20004788` |

Литералы: `0x00B71B00` (12 M), `0x007A1200` (8 M HSI), `0x003D0900` (4 M), `0x044AA200` (72 M).

---

## 2. Генератор возбуждения (DAC) — CONFIRMED

### Функции

| Функция | Роль |
|---------|------|
| `FUN_080009f0(param_1, param_2)` | Ядро: TIM2 + DMA1_CH5 + DAC, старт |
| `FUN_080005e0` | Обёртка → `009f0` (Ghidra: `void(void)` — **ошибка**; callers передают 2 args) |
| `FUN_08018158(freq)` | Rebuild sine-таблицы по Гц (`freq ≥ 1000`) |
| `FUN_08000c96` | Смена делителя `+4`, пересчёт таблицы без полного restart |
| `FUN_080006ea` | Заполнение sine |
| `FUN_08000ed0` | **Не DAC** — стадии + PGA (`0x20005610`) |
| `FUN_0800ae7c` | PGA113 bitbang (PB10/PB2) |

### Периферия

| Элемент | Значение |
|---------|----------|
| TIM2 Instance | `0x40000000` (F303; **не** `0x40000400`) |
| TIM2_ARR | **23** (`0x17`) — CONFIRMED |
| TIM2_PSC | `*(0x200049A8 + 0x40) - 1` — CONFIRMED |
| TIM3 | `0x40000400`, ARR=23, PSC=0; роль (ADC sync) — **PROBABLE** |
| DMA1_CH5 | CCR base `0x40020058` |
| DAC | `DHR12RD = 0x40007420` (dual) |
| Sine buffer CMAR | `0x20002EE0` |
| State struct | `0x200049A8` |

### Частота

\[
f_{\mathrm{out}} \approx \frac{72\cdot 10^{6}}{N \cdot 24 \cdot M}
\]

- \(N = *(0x200049A8 + 0x40)\)
- \(M \in \{1000, 2000, 3000\}\) (режим `*0x20004657`) или из `FUN_08018158`
- Пример: \(N=1\), \(M=1000\) → **≈ 3 кГц**

CLI: `setDACfreq` / `setDACTest` → `FUN_08018158`; `setDACperiod` / `autofreq` → halfword-поля структуры.

---

## 3. USART1 — CONFIRMED

- PA9 = TX, PA10 = RX (AF7)
- **Baud = 115200** — `FUN_08010b68(0x1c200, 0)` в `main`
- Handle `0x20006B80`, IRQ 37, DMA RX/TX в MSP

---

## 4. SPI1 (дисплей) — пины CONFIRMED

- PB3 SCK / PB4 MISO / PB5 MOSI — **AF5** (`FUN_08007298`)
- PB15 = Display_CS, PC13 = Display_DC
- Mode Master (по использованию)
- CPOL / CPHA / prescaler — **не разобраны** (в `.ioc` — заглушка)
- SPI2/SPI3 в образе **не используются**

---

## 5. ADC (сводка, без регрессии)

| Канал | Пин | DMA destination |
|-------|-----|-----------------|
| ADC1_IN1 | PA0 I_Measure | DMA1_CH1 → `0x200058E8` |
| ADC2_IN3 | PA6 U_Measure | DMA2_CH1 → `0x20005758` |
| ADC4_IN4 | PB14 BAT / JOY | блок C |

Hardware external trigger (поле `0x3c0` / edge `0x400`); точный EXTSEL ↔ TIM3 — **PROBABLE**.

---

## 6. Черновик `nRLC.ioc`

**Файл:** `nRLC.ioc` (~8485 байт; md5 `3baffe4aed877c626aa87e77d5665fb2` на момент сессии).

Содержимое:

- MCU: STM32F303CCTx, LQFP48
- HSE: **PF0-OSC_IN / PF1-OSC_OUT**, Crystal, 12 МГц
- PLL ×6 → SYSCLK 72 МГц; APB1 /2; `SYSCLKSourceVirtual=PLL`
- Пины: ADC1/2/4, USART1, SPI1, GPIO (PGA, display, joy, BL, VD_ON, ZP)
- TIM2/TIM3 Period=23; USART1 115200; SPI1 Master
- NVIC: USART1, TIM7, DMA1_CH1/CH5, DMA2_CH1

**Ограничения:**

1. Без PF0/PF1 CubeMX открывал файл «пустым» — исправлено во 2-й версии.
2. DMA request mapping (ADC→CH, DAC→CH5) лучше добить в GUI.
3. SPI baud/CPOL — не из прошивки.
4. TIM2 PSC runtime (`N-1`), в `.ioc` только ARR.
5. PA4 DAC Mode CubeMX может предложить поправить.

Пути в среде сессии: `artifacts/RLC/nRLC.ioc`, `attachments/nRLC.ioc` (не путать с заготовкой 3807 B).

---

## 7. Не делалось (очередь RLC / хвост железа)

- Формула **`FUN_0800d578`** (запись Rs/Rp/L/C, поля `+0x18/+0x20/+0x28`, байт `+3`)
- Назначение `0x200048a0+2` в ISR коррелятора
- SPI1 CR1 (CPOL/CPHA/BR)
- Жёсткая привязка ADC EXTSEL → TIM3_TRGO

---

## 8. Предлагаемые пункты для `REVERSE_STATUS.md` (после ревью)

1. Раздел **RCC**: HSE 12 МГц → PLL×6 → 72 МГц — CONFIRMED.
2. Раздел **генератор возбуждения**: TIM2+DMA1_CH5+DAC, `0x200049A8`, формула \(f_{\mathrm{out}}\).
3. **USART1** 115200; **SPI1** pins AF5.
4. Заметка: черновик `nRLC.ioc` — каркас, не 1:1 с прошивкой.

---

## 9. Итог одной строкой

Тактирование и тракт возбуждения (TIM2 → DMA → dual DAC) закрыты по железу; USART/SPI pins закрыты; есть черновик `.ioc` для CubeMX; математика RLC (`FUN_0800d578`) и тонкий SPI/EXTSEL — следующий этап.
