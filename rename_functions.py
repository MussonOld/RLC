# -*- coding: utf-8 -*-
# Ghidra-скрипт: переименовывает функции и ставит комментарии.
# Сгенерировано из REVERSE_STATUS.md (см. FUNCTIONS.md в том же коммите).
# Только CONFIRMED и PROBABLE записи — SKIP-адреса сюда не попадают
# намеренно (либо не существуют в этом дампе, либо не подтверждены
# для версии 2.0.12 — переименовывать их значило бы внести в Ghidra
# непроверенную информацию).
# Запуск: Ghidra -> Script Manager -> добавить эту папку -> запустить.

from ghidra.program.model.symbol import SourceType

currentProgram_ = currentProgram
fm = currentProgram_.getFunctionManager()

# (addr_hex, new_name, comment, confidence)
ENTRIES = [
    ("0800019c", "SysTick_Handler_body", """[CONFIRMED, раздел 4.2, 6.32] Тело обработчика SysTick (хвостовой b.w из SysTick_Handler). Каждые 3 тика безусловно запускает цикл измерения: ADC1_CR|=5, ADC2_CR|=5, TIM2_CR1|=1, TIM3_CR1|=1, DAC1_CR|=4, NVIC_EnableIRQ(DMA1_CH1). Параметров нет, не возвращает значение.""", "CONFIRMED"),
    ("08000270", "CommandDispatcher_Parser", """[CONFIRMED, раздел 6.25/6.26] Парсер входящих команд протокола (case 0x8b..0x8e — setDACfreq/setDACperiod/autofreq и др.).""", "CONFIRMED"),
    ("08000618", "MeasurementStageDispatcher", """[CONFIRMED, раздел 6.13] Диспетчер стадий измерения над структурой 0x20005610 (switch по байту состояния). case 6 -> FUN_08000f52 (MeasurementOrchestrator).""", "CONFIRMED"),
    ("080006a8", "GetCurrentFrequency", """[CONFIRMED, раздел 6.25/6.26] Возвращает текущую частоту DDS: (float)(*(0x200049a8+0x3c))/(*(0x200049a8+0x14)).""", "CONFIRMED"),
    ("080009f0", "TIM3_CH4_OC_Config", """[CONFIRMED, раздел 6.25] Настройка TIM3 CH4 (Output Compare, генерация формы сигнала DAC) — самодостаточная инициализация struct.""", "CONFIRMED"),
    ("08000d5a", "GetPGA_GainCh1", """[CONFIRMED, раздел 6.12 доп. 2026-09-13] Читает байт-индекс усиления PGA113 канала 1 из 0x20005610+0x10; если <8, берёт значение из таблицы DAT_08001104[idx], домножает на 1.5. void->float.""", "CONFIRMED"),
    ("08000d7c", "GetPGA_GainCh2", """[CONFIRMED, раздел 6.12 доп. 2026-09-13] То же самое, что GetPGA_GainCh1, но для канала 2: индекс из 0x20005610+0x11.""", "CONFIRMED"),
    ("08000d9e", "GetRangeCalibConst", """[CONFIRMED, раздел 6.12] Калибровочная/дефолтная константа диапазона: ветвится по 0x20005610+0xf, иначе берёт из +0x20 через VectorUnsignedToFloat.""", "CONFIRMED"),
    ("08000dbe", "ReadREF_ComputeStageValue", """[CONFIRMED, раздел 6.8 доп. 2026-09-13] Делит REF (0x200049e4) на элемент таблицы (0x200049b2), пишет результат в структуру 0x20005610 (+0x24/+0x2a/+0x34) и ещё одно поле по DAT_08001140/44.""", "CONFIRMED"),
    ("08000f52", "MeasurementOrchestrator", """[CONFIRMED, раздел 6.12/6.13] Оркестратор одного цикла измерения (float param_1, передан через s0). Вызывает FUN_0800dbf8 дважды (буфер 0x20007840 — живой аккумулятор, и 0x20007c70 — его снимок), считает дельту previous/current (0x20005610+0x48/+0x50), делает автопереключение диапазона и оценку стабильности, в конце — при взведённом флаге 0x20004a48[0] — вызывает FUN_08009618 (отрисовка экрана). Тело разобрано не целиком (~1100 строк декомпиляции).""", "CONFIRMED"),
    ("080023dc", "UnsignedDivHelper_lib", """[CONFIRMED, раздел 6.19] Библиотечный примитив, похож на __aeabi_uldivmod (беззнаковое деление).""", "CONFIRMED"),
    ("0800243e", "CountAccumulatedSamples", """[CONFIRMED, раздел 6.19] Подсчитывает накопленные отсчёты; разобрана целиком.""", "CONFIRMED"),
    ("0800254a", "FloatAdd_lib", """[CONFIRMED, раздел 6.9/6.16] Часть библиотеки soft-float общего назначения (double-арифметика, сложение) — используется, например, со весами FUN_08002886/FUN_080028a8.""", "CONFIRMED"),
    ("08002698", "FloatOp_lib2", """[CONFIRMED, раздел 6.9/6.12] Soft-float примитив общего назначения (см. группу §6.9); участвует в вычислении дельты previous/current в 0x20005610+0x68.""", "CONFIRMED"),
    ("0800277c", "FloatSubOrDivide_lib", """[CONFIRMED, раздел 6.9/6.12/6.16] Soft-float примитив; используется и в формуле Q=|(+0x58)/(+0x50)| (0x20004a4d-структура), и в объединении дельты с накопителем в 0x20005610+0x68.""", "CONFIRMED"),
    ("0800285a", "Int64ToFloat_lib", """[CONFIRMED, раздел 6.12 доп. 2026-09-13] Конвертер знакового 64-битного целого во float (LZCOUNT-нормализация двух 32-битных половин, паттерн вида __aeabi_l2d, но с float-результатом). Используется для перевода 64-битных пар корреляционных аккумуляторов (напр. param+0x08/+0x0c) во float одним вызовом.""", "CONFIRMED"),
    ("08002932", "FloatOp_lib4", """[CONFIRMED, раздел 6.9/6.12] Soft-float примитив общего назначения (см. группу §6.9); используется многократно, в т.ч. в вычислении дельты previous/current 0x20005610+0x68.""", "CONFIRMED"),
    ("08002958", "CompareAgainstThresholds", """[CONFIRMED, раздел 6.19] Сравнивает значение с порогами DAT_08001b80/88/90 с эскалацией 2->4->6->8.""", "CONFIRMED"),
    ("08002d48", "ScatterLoad_Init", """[CONFIRMED, раздел 2 доп. 2026-09-13] ARM scatter-load загрузчик, вызывается из трамплина Reset_Handler. Читает таблицу из 3 записей {src,dest,length,fn} по адресу 0x0802cfec..0x0802d01c и для каждой вызывает fn(src,dest,length): запись0=.data (СЖАТА, распаковщик fn=0x08002d6c), запись1=CCM RAM (плоское копирование), запись2=.bss (зануление).""", "CONFIRMED"),
    ("08002ec0", "ComputeCorrOutput_Buf2", """[CONFIRMED, раздел 6.13 доп. 2026-09-15] Третий вариант той же цепочки, что FUN_0800dbf8/начало FUN_0800d578 — читает Re/Im пары по идентичным словным смещениям структуры-аккумулятора коррелятора. Вызывается как FUN_08002ec0(0x20007c38) — подтверждает, что 0x20007840/0x20007c38/0x20007c70 это три экземпляра ОДНОЙ структуры (доп. 2026-09-15), не три разных формата.""", "CONFIRMED"),
    ("08003140", "ADC_MSP_Init", """[CONFIRMED, раздел 6.14] Инициализация ADC1/ADC2 (вместе с MSP FUN_08005404) — каналы, ранги, DMA/GPIO обвязка.""", "CONFIRMED"),
    ("08003428", "TIM6_FullInit", """[CONFIRMED, раздел 6.4] Полная самодостаточная инициализация TIM6: RCC enable, PSC=99, ARR, DIER, NVIC IRQ54 приоритет 0.""", "CONFIRMED"),
    ("08003940", "FindREFTableIndex_A", """[CONFIRMED, раздел 6.8 доп. 2026-09-13] Инлайн-копия алгоритма поиска: делит REF (0x200049e4) на элементы таблицы, ищет совпадающий индекс (сравнение с table[7]).""", "CONFIRMED"),
    ("080039b0", "FlashPageSearch", """[CONFIRMED, раздел 6.8 доп. 2026-09-13] Использует REF (0x200049e4) для поиска нужного блока флеша при записи настроек — паттерн флеш-хранилища конфигурации.""", "CONFIRMED"),
    ("08004c1c", "ADC_AnalogWatchdogConfig", """[CONFIRMED, раздел 6.х (пересмотрено 2026-09-07)] НЕ конфигуратор канала (первый проход ошибочно принял за него) — реально настраивает аналоговый watchdog (AWD2CR/AWD3CR), пишет по iVar1+0x24/+0x28 с паттерном 1<<channel.""", "CONFIRMED"),
    ("08004d94", "ADC_ConfigChannel", """[CONFIRMED, раздел 6.х (пересмотрено 2026-09-07)] Настоящий конфигуратор канала ADC — пишет *param_2<<(rank*6) в регистр SQR1 (Instance+0x30), точная формула STM32F3.""", "CONFIRMED"),
    ("08005148", "ADC_GetValue", """[CONFIRMED, раздел 10] Геттер значения ADC — аналог HAL_ADC_GetValue, читает ADC_DR (смещение 0x40 от хэндла).""", "CONFIRMED"),
    ("08005150", "ADC_SetTriggerConfig", """[CONFIRMED, раздел 6.29] Настройка ExternalTrigConv/ExternalTrigConvEdge регистра ADCx_CFGR (вызывается из FUN_08003140).""", "CONFIRMED"),
    ("08005404", "ADC_MSP_GPIO_Init", """[CONFIRMED, раздел 6.14] MSP-инициализация GPIO для ADC1/ADC2 (аналоговые входы PA0/PA6 и др.).""", "CONFIRMED"),
    ("08005798", "DAC_ConfigChannel", """[CONFIRMED, раздел 6.25 доп. 2026-09-12] Конфигуратор канала DAC (аналог HAL_DAC_ConfigChannel) — вызывается как (handle,&cfg,DAC_CHANNEL_1), cfg={DAC_Trigger=0x24=T2_TRGO, DAC_OutputBuffer=0}.""", "CONFIRMED"),
    ("080059ba", "DMA_GenericISR_Dispatcher", """[CONFIRMED, раздел 4.4] Общий обработчик для DMA1_CH3/CH4/CH5 и DMA2_CH1/CH3 (используется как общий диспетчер в таблице векторов).""", "CONFIRMED"),
    ("08005a88", "DMA_Init_HALlike", """[CONFIRMED, раздел 6.23/6.27] Инициализация DMA — раскладка полей побитово совпадает с HAL DMA_InitTypeDef.""", "CONFIRMED"),
    ("08005ccc", "GPIO_Init_HALlike", """[CONFIRMED, раздел 6.1/6.30] Настройка GPIO — аналог HAL_GPIO_Init, принимает (port_base, &init_struct).""", "CONFIRMED"),
    ("08005efc", "GPIO_ReadBit_or_TimSR", """[CONFIRMED, раздел 10] Геттер бита по смещению 0x10 от базы — контекстно это либо GPIO IDR, либо TIM SR.""", "CONFIRMED"),
    ("08005f06", "GPIO_WriteBit", """[CONFIRMED, раздел 10] Запись бита GPIO: val!=0 -> BSRR (+0x18), val==0 -> BRR (+0x28). (port,mask,val)->void.""", "CONFIRMED"),
    ("0800604e", "NVIC_EnableIRQ", """[CONFIRMED, раздел 10] NVIC_EnableIRQ(irq).""", "CONFIRMED"),
    ("0800606c", "NVIC_SetPriority", """[CONFIRMED, раздел 10] NVIC_SetPriority(irq, prio).""", "CONFIRMED"),
    ("08006328", "USB_IRQHandler_main", """[CONFIRMED, раздел 5.2] Основной обработчик событий USB — аналог HAL_PCD_IRQHandler, диспетчеризует по битам USB_ISTR (RESET/CTR/WKUP/SUSP/SOF).""", "CONFIRMED"),
    ("080065c2", "USB_WKUP_Handler", """[CONFIRMED, раздел 5.2] Обработчик события WKUP (маска 0x1000 в USB_ISTR).""", "CONFIRMED"),
    ("080065ca", "USB_SOF_Handler", """[CONFIRMED, раздел 5.2] Обработчик события SOF (маска 0x200 в USB_ISTR).""", "CONFIRMED"),
    ("0800663c", "USB_SUSP_Handler", """[CONFIRMED, раздел 5.2] Обработчик события SUSP (маска 0x800 в USB_ISTR).""", "CONFIRMED"),
    ("08007298", "SPI1_MSP_Init_DMA_RCC", """[CONFIRMED, раздел 6.30] MSP-инициализация SPI1 — только DMA/RCC-обвязка (условие *param_1==&SPI1_CR1).""", "CONFIRMED"),
    ("0800784c", "TIM_Base_SetConfig_like", """[CONFIRMED, раздел 6.4] Настройка базовых параметров таймера — похоже на TIM_Base_SetConfig (аргументы вида 0x40/0x80).""", "CONFIRMED"),
    ("080078e0", "TIM_MspInit_variant1", """[CONFIRMED, раздел 6.4] MSP-инициализация таймера (используется, например, для TIM6, вызывается сразу после ручного enable).""", "CONFIRMED"),
    ("08007944", "RCC_NVIC_Dispatcher", """[CONFIRMED, раздел 6.4/10] Общий диспетчер RCC-enable + NVIC для TIM1/2/3/4/7/16 (handle)->void.""", "CONFIRMED"),
    ("08007d14", "TIM_OC_Config_HALlike", """[CONFIRMED, раздел 6.25/6.27] Настройка Output Compare — раскладка полей побитово совпадает с HAL TIM_OC_InitTypeDef.""", "CONFIRMED"),
    ("080087f8", "SPI1_Display_MSP_GPIO_Init", """[CONFIRMED, раздел 6.31] MSP-колбэк — boot-time настройка GPIO Output для дисплея/SPI1.""", "CONFIRMED"),
    ("08009618", "DisplayRefresh_DrawResult", """[CONFIRMED, раздел 6.11/6.13/6.22 доп. 2026-09-14] Отрисовка экрана — читает структуру результата 0x20004a48 (Rs/Rp/L/C/Z на +0x68=0x20004ab0) и другие поля, вызывается из MeasurementOrchestrator при взведённом флаге готовности. Содержит несколько lerp-блоков сглаживания (20-шаговый разгон) между RAW-полями (напр. +0x48) и выводимыми (+0x68); доп. 2026-09-14.""", "CONFIRMED"),
    ("0800ade8", "PrintCharToScreenBuffer", """[CONFIRMED, раздел 6.19] НЕ расчётная функция — посимвольный вывод строки на экран (спецобработка '.' как десятичной точки); вызывается при достижении стабильности показаний.""", "CONFIRMED"),
    ("0800ae7c", "RangeRelayControl", """[CONFIRMED, раздел 6.19] Управление реле переключения диапазона: (channel_or_flag 0/1, value)->void.""", "CONFIRMED"),
    ("0800d578", "FormulaRsRpLC", """[CONFIRMED, раздел 6.13/6.23/6.27, доп. 2026-09-14/15] Формула Rs/Rp/L/C(+X) — двухпараметровая (buf, alt_flag). В начале тела повторяет вычисление FUN_0800dbf8 (Z=U/I той же цепочкой) и пишет double-результат в 0x20004914+0x14/+0x18 (=0x20004928, доп. 2026-09-15 — 'соседний слот' с 0x20004920 из FUN_0800dbf8); дальше пишет в структуру результата 0x20004a48: Rs(+0x30), Rp(+0x40), L(+0x90), C(+0x98), X?(+0x38, копия +0x28) и RAW Z(+0x48, несглаженный источник экранного Z после сглаживания в FUN_08009618). Единственный вызов — из MeasurementOrchestrator с буфером 0x20007c70 или новым 0x20007c38 (не с живым 0x20007840).""", "CONFIRMED"),
    ("0800dbf8", "ConvertCorrToPhysical", """[CONFIRMED, раздел 6.12] Конвертер выхода коррелятора (Re/Im пары по offsets +0x08/+0x0c и +0x20/+0x24 от 0x20007840) в калиброванную комплексную величину Z=U/I; пишет double-результат в 0x20004920. int(param_1=буфер)->void, побочный эффект через глобали.""", "CONFIRMED"),
    ("0800e754", "USB_CTR_EndpointTransfer", """[CONFIRMED, раздел 5.2] Обработка успешной передачи (CTR, маска 0x8000 в USB_ISTR), endpoint transfer.""", "CONFIRMED"),
    ("0800ef20", "FindREFTableIndex_B", """[CONFIRMED, раздел 6.8 доп. 2026-09-13] Второй экземпляр (отдельная функция, не инлайн) того же алгоритма поиска индекса по REF, что и FindREFTableIndex_A.""", "CONFIRMED"),
    ("0800fcf4", "SetAutoOffThreshold", """[CONFIRMED, раздел 6.5/10] Сеттер порога автовыключения: (ms:short, save:int)->void, использует тот же указатель pcVar1, что и TIM7 ISR.""", "CONFIRMED"),
    ("0800ff78", "TIM7_ISR", """[CONFIRMED, раздел 6.3/10] Обработчик TIM7, IRQ55 — таймаут автовыключения + долгое удержание кнопок + блок C.""", "CONFIRMED"),
    ("080126d0", "StructField_Getter_0x40", """[CONFIRMED, раздел 5.2] Геттер поля по смещению 0x40 от *param_1 (используется, среди прочего, в FUN_08006328).""", "CONFIRMED"),
    ("080126f0", "StructField_Getter_0x44", """[CONFIRMED, раздел 5.2] Геттер 16-битного поля по смещению 0x44 от *param_1.""", "CONFIRMED"),
    ("080129e2", "ComplexDivide", """[CONFIRMED, раздел 6.12/6.27] Комплексное деление — используется как Z = канал1 ⊘ канал2 (U/I). Совпадает с независимой оценкой Grok.""", "CONFIRMED"),
    ("08012a04", "ComplexMultiply", """[CONFIRMED, раздел 6.12/6.27] Комплексное умножение — используется в переводе магнитуды в физические единицы. Совпадает с независимой оценкой Grok.""", "CONFIRMED"),
    ("08013690", "ScatterLoad_PlainCopy", """[CONFIRMED, раздел 2 доп. 2026-09-13 / 4.3] Простое словное копирование (ldm/stm) — функция-копировщик записи 1 в scatter-load таблице (CCM RAM).""", "CONFIRMED"),
    ("08013ffc", "SinTableLookup", """[CONFIRMED, раздел 6.26] Табличный sin() — аргумент это фаза в радианах вида 2*pi*i/N.""", "CONFIRMED"),
    ("080154c8", "SoftwareDelay_ms", """[CONFIRMED, раздел 10] Программная задержка на миллисекундах (busy-wait, калибровка по частоте шины): (ms)->void.""", "CONFIRMED"),
    ("08015de0", "CorrelatorScaleGetter", """[CONFIRMED, раздел 6.12/6.26] Масштаб/нормировка коррелятора — вероятно возвращает число накопленных отсчётов N: (param_1)->float.""", "CONFIRMED"),
    ("08015ff0", "WriteStringToScreenBuffer", """[CONFIRMED, раздел 6.19] Запись строки в текстовый буфер экрана: (буфер, длина)->void.""", "CONFIRMED"),
    ("08016274", "MainApplicationInit", """[CONFIRMED, раздел 2] Эквивалент application main() — широкая инициализация железа/периферии (ADC4/CRC/DBGMCU/GPIOx/IWDG/RCC/SPI1/TIM1/16/2/3), 84 вызываемые функции.""", "CONFIRMED"),
    ("08017dc8", "BatteryCalibConstants", """[CONFIRMED, раздел 6.6] Калибровочные константы защиты по батарее — формула делителя напряжения (коэфф. 1.47), калибровка вокруг 4.20В (Li-Ion), порог отключения 3.45В.""", "CONFIRMED"),
    ("08017f70", "AutoFreqSearchAndReportBuilder", """[CONFIRMED, раздел 6.26] Поиск частоты для команды autofreq (критерий round(REF/candidate)<3) — и одновременно построитель отчёта, не только поиск частоты.""", "CONFIRMED"),
    ("08018158", "SetDACFrequency", """[CONFIRMED, раздел 6.25/6.26] Устанавливает частоту DAC/DDS — вызывается и из setDACfreq напрямую, и из autofreq с вычисленным на лету аргументом.""", "CONFIRMED"),
    ("100001b8", "CorrelatorCore_CCM", """[CONFIRMED, раздел 6.7] Ядро ДСП-коррелятора в CCM RAM (тайл-функция thunk_EXT_FUN_100001b8, флеш-веньир 0x08002dcc). Границы и calling convention CONFIRMED, внутренняя семантика частично PROBABLE.""", "CONFIRMED"),
    ("10000b5c", "GPIOB_Toggle_Inert", """[CONFIRMED, раздел 4.3/6.19/6.20] Переключение PB6/PB7 push-pull/open-drain в CCM RAM. Байткод CONFIRMED (20+ вызовов из MeasurementOrchestrator через вениир 0x08002de0), но физически инертна — PB6/PB7 не разведены (NC) на плате. Атрибуция "I2C-битбэнг" — PROBABLE.""", "CONFIRMED"),
    ("10000bc0", "BuzzerDriver", """[CONFIRMED, раздел 4.3] Неблокирующий драйвер пищалки PA8/ZP в CCM RAM: (ms)->void.""", "CONFIRMED"),
    ("080005e0", "ApplyDACFreqToHW_probable", """[PROBABLE, раздел 6.25] Похоже, применяет вычисленную частоту DAC к железу; что именно передаёт — не установлено.""", "PROBABLE"),
    ("08000608", "MainLoop_or_FSM_probable", """[PROBABLE, раздел 2] Предположительно главный цикл/конечный автомат приложения — роль перенесена из прежнего анализа, не перепроверена на 2.0.12 прямым прослеживанием.""", "PROBABLE"),
    ("0800268c", "FloatOp_lib_unclassified", """[PROBABLE, раздел 6.16] Часть той же группы soft-float примитивов; используется вместе с DAT_08001610/08001614. Точная операция не установлена.""", "PROBABLE"),
    ("08002886", "WeightFunctionA_probable", """[PROBABLE, раздел 6.16] Похоже на весовую функцию вида (0x14-N) в скользящем сложении по 249-точечной истории.""", "PROBABLE"),
    ("080028a8", "WeightFunctionB_probable", """[PROBABLE, раздел 6.16] Похоже на весовую функцию от счётчика шага N (pbVar2[0xc]).""", "PROBABLE"),
    ("08002900", "FloatOp_lib3_unclassified", """[PROBABLE, раздел 6.12] Часть группы soft-float примитивов §6.9; конкретная операция не установлена.""", "PROBABLE"),
    ("080029b8", "MagnitudeFromReIm_probable", """[PROBABLE, раздел 6.12] Похоже на свёртку пары Re/Im в магнитуду (hypot-подобная функция).""", "PROBABLE"),
    ("08005b2c", "FlashMemoryHelper_A_probable", """[PROBABLE, раздел 6.26] Работа с памятью, участвует в поиске/записи блока флеша вместе с thunk_FUN_08005bfc.""", "PROBABLE"),
    ("08005bfc", "FlashMemoryHelper_B_probable", """[PROBABLE, раздел 6.26] См. FlashMemoryHelper_A — тот же контекст работы с флеш-памятью (thunk).""", "PROBABLE"),
    ("08005f88", "SysTickSubCounter_probable", """[PROBABLE, раздел 4.2] Вызывается из тела SysTick_Handler; вероятный кандидат на отдельный счётчик. Не разобрана целиком.""", "PROBABLE"),
    ("0800659c", "USB_Reset_Sub_probable", """[PROBABLE, раздел 5.2] Вызывается веткой RESET обработчика USB и при первом входе (флаг +0xaa).""", "PROBABLE"),
    ("08007190", "GenericInitWithFailLock_probable", """[PROBABLE, раздел 6.30] Init-вызов общего вида: при ошибке — блокировка (типовой паттерн проекта). Конкретная периферия не установлена.""", "PROBABLE"),
    ("080078e8", "TIM_MspInit_variant2_probable", """[PROBABLE, раздел 6.4] Второй вариант MSP-инициализации таймера — не имеет ни одного прямого вызова (bl) по всему образу (возможно, только табличный указатель).""", "PROBABLE"),
    ("08007a00", "TIM6_Start_probable", """[PROBABLE, раздел 6.4] Вызывается в последовательности инициализации TIM6, вероятно TIM_Base_Start-подобная.""", "PROBABLE"),
    ("08007a70", "TIM6_Start2_probable", """[PROBABLE, раздел 6.4] Вызывается в последовательности инициализации TIM6 сразу после FUN_08007a00.""", "PROBABLE"),
    ("08008384", "TIM15_16_17_Related_A_probable", """[PROBABLE, раздел 7/10] Код, согласующийся с группой TIM15/16/17 — атрибуция понижена с высокой до PROBABLE, прямых доказательств не найдено.""", "PROBABLE"),
    ("08009574", "ThresholdEscalation_probable", """[PROBABLE, раздел 6.19] Вызывается при достижении порога эскалации (0x13,8) в цепочке debounce.""", "PROBABLE"),
    ("0800afac", "PowerButtonCheck_probable", """[PROBABLE, раздел 6.3] Проверяется в ветке TIM7 ISR (порог 600 тиков); при ненулевом результате вызывает FUN_080178dc. Связь с FUN_0800ee00 (PowerOff) НЕ установлена — отдельная ветка.""", "PROBABLE"),
    ("0800ee00", "PowerOffHandler_probable", """[PROBABLE, раздел 6.2] Вероятный обработчик команды POWER_OFF.""", "PROBABLE"),
    ("0800fa48", "ScreenCursorSet_A_probable", """[PROBABLE, раздел 6.19] Вероятно, установка позиции курсора экрана: (N)->void.""", "PROBABLE"),
    ("0800fa82", "ScreenCursorSet_B_probable", """[PROBABLE, раздел 6.19] Вероятно, установка строки/столбца курсора экрана: (M)->void.""", "PROBABLE"),
    ("0800fb24", "CountdownLoop_probable", """[PROBABLE, раздел 6.2] Цикл с обратным отсчётом, используется в последовательности выключения питания.""", "PROBABLE"),
    ("0800ff68", "LowLevelStartup_probable", """[PROBABLE, раздел 2] Низкоуровневая настройка при старте сразу после Reset_Handler — не вызывает ни одной подписанной периферии (вероятно тактирование/FPU/watchdog).""", "PROBABLE"),
    ("080101b4", "TIM15_16_17_Related_B_probable", """[PROBABLE, раздел 7/10] См. TIM15_16_17_Related_A — та же пониженная атрибуция PROBABLE.""", "PROBABLE"),
    ("08010b68", "USART1_BaudSetup_probable", """[PROBABLE, раздел 6.31] Связана с установкой Baud=115200 для USART1.""", "PROBABLE"),
    ("08012728", "USB_FirstEnumInit_probable", """[PROBABLE, раздел 5.2] Вызывается при первом входе в ветку RESET обработчика USB (флаг по смещению 0xaa).""", "PROBABLE"),
    ("08012f18", "HypotOrCombine_probable", """[PROBABLE, раздел 6.12/6.16] Вероятно hypot-подобная функция (sqrt(a^2+b^2)) или объединение двух дельт; участвует в формуле по смещению 0x20005610+0x68.""", "PROBABLE"),
    ("080133d0", "FloatOp_lib5_unclassified", """[PROBABLE, раздел 6.9] Нерасшифрованный fixed-point/float примитив из общей группы §6.9.""", "PROBABLE"),
    ("08015eb0", "CheckConditionThenAction_probable", """[PROBABLE, раздел 6.19] Проверка условия (0x3c,...); если истина — выполняется дальнейшее действие в вызывающем коде.""", "PROBABLE"),
]

renamed, skipped_missing, failed = 0, 0, 0
for addr_hex, new_name, comment, conf in ENTRIES:
    addr = currentProgram_.getAddressFactory().getAddress("0x" + addr_hex)
    func = fm.getFunctionAt(addr)
    if func is None:
        print("SKIP (no function at address): 0x%s" % addr_hex)
        skipped_missing += 1
        continue
    try:
        func.setName(new_name, SourceType.USER_DEFINED)
        func.setComment(comment)
        renamed += 1
    except Exception as e:
        print("FAILED 0x%s -> %s: %s" % (addr_hex, new_name, e))
        failed += 1

print("Renamed: %d, missing-at-address: %d, failed: %d" % (renamed, skipped_missing, failed))
