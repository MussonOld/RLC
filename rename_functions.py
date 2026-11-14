# -*- coding: utf-8 -*-
# скрипт: переименовывает функции и ставит комментарии.
# Сгенерировано из INVESTIGATION_STATUS.md (см. FUNCTIONS.md в том же коммите).
# Только CONFIRMED и PROBABLE записи — SKIP-адреса сюда не попадают
# намеренно (либо не существуют в этом дампе, либо не подтверждены
# для версии 2.0.12 — переименовывать их значило бы внести в анализаторе
# непроверенную информацию).
# Запуск: Script Manager -> добавить эту папку -> запустить.

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
    ("08000f52", "MeasurementOrchestrator", """[CONFIRMED, раздел 6.12/6.13] Оркестратор одного цикла измерения (float param_1, передан через s0). Вызывает FUN_0800dbf8 дважды (буфер 0x20007840 — живой аккумулятор, и 0x20007c70 — его снимок), считает дельту previous/current (0x20005610+0x48/+0x50), делает автопереключение диапазона и оценку стабильности, в конце — при взведённом флаге 0x20004a48[0] — вызывает FUN_08009618 (отрисовка экрана). Тело разобрано не целиком (~1100 строк листинга).""", "CONFIRMED"),
    ("080023dc", "UnsignedDivHelper_lib", """[CONFIRMED, раздел 6.19] Библиотечный примитив, похож на __aeabi_uldivmod (беззнаковое деление).""", "CONFIRMED"),
    ("0800243e", "SignedDiv64_lib", """[CONFIRMED, раздел уточнено при переносе на C] Знаковое 64-битное деление поверх беззнакового FUN_080023dc (знак результата по знакам операндов). Возвращает частное. В C — оператор деления.""", "CONFIRMED"),
    ("0800254a", "DoubleAdd_lib", """[CONFIRMED, раздел 6.9/6.16, уточнено при переносе на C] Сложение double (вычитание — через смену знака). В C — оператор +.""", "CONFIRMED"),
    ("08002698", "DoubleMultiply_lib", """[CONFIRMED, раздел 6.9/6.12, уточнено при переносе на C] Умножение double (soft-float рутина рантайма). В C — оператор *.""", "CONFIRMED"),
    ("0800277c", "DoubleDivide_lib", """[CONFIRMED, раздел 6.9/6.12/6.16, уточнено при переносе на C] Деление double (сдвиг-вычитание, числитель — первая пара регистров). Используется в формуле Q=|(+0x58)/(+0x50)| и в объединении дельты в 0x20005610+0x68. В C — оператор /.""", "CONFIRMED"),
    ("0800285a", "Int64ToFloat_lib", """[CONFIRMED, раздел 6.12 доп. 2026-09-13] Конвертер знакового 64-битного целого во float (LZCOUNT-нормализация двух 32-битных половин, паттерн вида __aeabi_l2d, но с float-результатом). Используется для перевода 64-битных пар корреляционных аккумуляторов (напр. param+0x08/+0x0c) во float одним вызовом.""", "CONFIRMED"),
    ("08002932", "FloatToDouble_lib", """[CONFIRMED, раздел 6.9/6.12, уточнено при переносе на C] Преобразование float -> double (soft-float рутина). В C — приведение типа. Используется многократно, в т.ч. в вычислении дельты previous/current в 0x20005610+0x68.""", "CONFIRMED"),
    ("08002958", "DoubleCompare_lib", """[CONFIRMED, раздел 6.19, уточнено при переносе на C] Сравнение double (результат через флаги процессора, как у семейства __aeabi_cdcmple). В теле видна только подготовка знака; направление сравнения выведено из мест вызова. В C — обычное сравнение.""", "CONFIRMED"),
    ("08002d48", "ScatterLoad_Init", """[CONFIRMED, раздел 2 доп. 2026-09-13] ARM scatter-load загрузчик, вызывается из трамплина Reset_Handler. Читает таблицу из 3 записей {src,dest,length,fn} по адресу 0x0802cfec..0x0802d01c и для каждой вызывает fn(src,dest,length): запись0=.data (СЖАТА, распаковщик fn=0x08002d6c), запись1=CCM RAM (плоское копирование), запись2=.bss (зануление).""", "CONFIRMED"),
    ("08002ec0", "ComputeCorrOutput_Buf2", """[CONFIRMED, раздел 6.13 доп. 2026-09-15] Третий вариант цепочки FUN_0800dbf8/FUN_0800d578: читает Re/Im пары по тем же смещениям структуры коррелятора и пишет два float прямо в неё ([0] и [6], амплитуды каналов). Вызывается как FUN_08002ec0(0x20007c38) — три буфера 0x20007840/0x20007c38/0x20007c70 имеют одну структуру. Аргументы восстановлены по машинному коду, перенос на C совпал с образом на 40 случайных наборах.""", "CONFIRMED"),
    ("08003140", "ADC_MSP_Init", """[CONFIRMED, раздел 6.14] Инициализация ADC1/ADC2 (вместе с MSP FUN_08005404) — каналы, ранги, DMA/GPIO обвязка.""", "CONFIRMED"),
    ("08003428", "TIM6_FullInit", """[CONFIRMED, раздел 6.4] Полная самодостаточная инициализация TIM6: RCC enable, PSC=99, ARR, DIER, NVIC IRQ54 приоритет 0.""", "CONFIRMED"),
    ("08003940", "FlashPageErase_ByREF", """[CONFIRMED, раздел 6.8 доп. 2026-09-13, уточнено при переносе на C] Ищет индекс i (0..6), для которого REF(0x200049e4)/table[i]==table[7], и стирает страницу флеша 0x0803C000+i*0x800 (HAL_FLASHEx_Erase, 1 страница). Возврат 1 при успехе. Страницы 0x0803C000.. — хранилище настроек.""", "CONFIRMED"),
    ("080039b0", "FlashPageSave_ByREF", """[CONFIRMED, раздел 6.8 доп. 2026-09-13, уточнено при переносе на C] Тот же поиск страницы по REF, затем запись блока настроек 0x244 байта (из 0x20007878+0x1c) во флеш по словам (HAL_FLASH_Program).""", "CONFIRMED"),
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
    ("08007298", "SPI1_MspInit_GPIO_DMA", """[CONFIRMED, раздел 6.30, уточнено при переносе на C] MSP-инициализация SPI1: GPIOB PB3/PB4/PB5 AF5 и DMA1 канал 3 (TX, полуслова).""", "CONFIRMED"),
    ("0800784c", "TIMEx_MasterConfigSync_HALlike", """[CONFIRMED, раздел 6.4, уточнено при переносе на C] Аналог HAL_TIMEx_MasterConfigSynchronization: пишет CR2.MMS и SMCR.MSM из структуры {MasterOutputTrigger, ..., MasterSlaveMode}. (Ранее была названа TIM_Base_SetConfig.)""", "CONFIRMED"),
    ("080078e0", "TimBase_Init_HALlike", """[CONFIRMED, раздел 6.4, уточнено при переносе на C] Аналог HAL_TIM_Base_Init: при первом вызове — FUN_08007944 (тактирование/NVIC), состояния каналов, настройка базы таймера.""", "CONFIRMED"),
    ("08007944", "RCC_NVIC_Dispatcher", """[CONFIRMED, раздел 6.4/10] Общий диспетчер RCC-enable + NVIC для TIM1/2/3/4/7/16 (handle)->void; для TIM7 приоритет IRQ 55 равен (15,15).""", "CONFIRMED"),
    ("08007d14", "TIM_OC_Config_HALlike", """[CONFIRMED, раздел 6.25/6.27] Настройка Output Compare — раскладка полей побитово совпадает с HAL TIM_OC_InitTypeDef.""", "CONFIRMED"),
    ("080087f8", "USART1_MspInit_DMA", """[CONFIRMED, раздел 6.31, уточнено при переносе на C] MSP-инициализация USART1: GPIOA PA9/PA10 AF7, DMA1 канал 4 (TX) и 5 (RX), IRQ 37 с приоритетом (2,2). (Ранее была записана как MSP SPI1/дисплея.)""", "CONFIRMED"),
    ("08009618", "DisplayRefresh_DrawResult", """[CONFIRMED, раздел 6.11/6.13/6.22 доп. 2026-09-14] Отрисовка экрана — читает структуру результата 0x20004a48 (Rs/Rp/L/C/Z на +0x68=0x20004ab0) и другие поля, вызывается из MeasurementOrchestrator при взведённом флаге готовности. Содержит несколько lerp-блоков сглаживания (20-шаговый разгон) между RAW-полями (напр. +0x48) и выводимыми (+0x68); доп. 2026-09-14.""", "CONFIRMED"),
    ("0800ade8", "PrintCharToScreenBuffer", """[CONFIRMED, раздел 6.19] НЕ расчётная функция — посимвольный вывод строки на экран (спецобработка '.' как десятичной точки); вызывается при достижении стабильности показаний.""", "CONFIRMED"),
    ("0800ae7c", "PGA113_RangeCommand", """[CONFIRMED, раздел 6.19, уточнено при переносе на C] Выбор диапазона: отправляет в PGA113 слово 0x2A01|код<<4 (FUN_08012764) с выбором линии CS (PB10=U_CS для ненулевого первого аргумента, иначе PB2=I_CS); не отправляет повторно, если код не изменился. (Ранее была записана как управление реле.)""", "CONFIRMED"),
    ("0800d578", "FormulaRsRpLC", """[CONFIRMED, раздел 6.13/6.23/6.27, доп. 2026-09-14/15] Формула Rs/Rp/L/C(+X) — двухпараметровая (buf, alt_flag). В начале тела повторяет вычисление FUN_0800dbf8 (Z=U/I той же цепочкой) и пишет результат как пару float в 0x20004914+0x14/+0x18 (=0x20004928, доп. 2026-09-15 — 'соседний слот' с 0x20004920 из FUN_0800dbf8); дальше пишет в структуру результата 0x20004a48: Rs(+0x30), Rp(+0x40), L(+0x90), C(+0x98), X?(+0x38, копия +0x28) и RAW Z(+0x48, несглаженный источник экранного Z после сглаживания в FUN_08009618). Единственный вызов — из MeasurementOrchestrator с буфером 0x20007c70 или новым 0x20007c38 (не с живым 0x20007840).""", "CONFIRMED"),
    ("0800dbf8", "ConvertCorrToPhysical", """[CONFIRMED, раздел 6.12] Конвертер выхода коррелятора (Re/Im пары по offsets +0x08/+0x0c и +0x20/+0x24 от 0x20007840) в калиброванную комплексную величину Z=U/I; пишет результат как пару float (re, im) в 0x20004920/0x20004924. int(param_1=буфер)->void, побочный эффект через глобали.""", "CONFIRMED"),
    ("0800e754", "USB_CTR_EndpointTransfer", """[CONFIRMED, раздел 5.2] Обработка успешной передачи (CTR, маска 0x8000 в USB_ISTR), endpoint transfer.""", "CONFIRMED"),
    ("0800ef20", "FindREFTableIndex_B", """[CONFIRMED, раздел 6.8 доп. 2026-09-13] Второй экземпляр (отдельная функция, не инлайн) того же алгоритма поиска индекса по REF, что и FindREFTableIndex_A.""", "CONFIRMED"),
    ("0800fcf4", "SetAutoOffThreshold", """[CONFIRMED, раздел 6.5/10] Сеттер порога автовыключения: (ms:short, save:int)->void, использует тот же указатель pcVar1, что и TIM7 ISR.""", "CONFIRMED"),
    ("0800ff78", "TIM7_ISR", """[CONFIRMED, раздел 6.3/10] Обработчик TIM7, IRQ55 — таймаут автовыключения + долгое удержание кнопок + блок C.""", "CONFIRMED"),
    ("080126d0", "USB_EnableGlobalInt", """[CONFIRMED, раздел 5.2, уточнено при переносе на C] Установщик (не геттер): ISTR(+0x44)=0, CNTR(+0x40)=0xBF00 — маски прерываний USB. Аналог HAL USB_EnableGlobalInt.""", "CONFIRMED"),
    ("080126f0", "USB_ReadInterrupts", """[CONFIRMED, раздел 5.2, уточнено при переносе на C] Чтение 16-битного регистра ISTR (+0x44) USB. Аналог HAL USB_ReadInterrupts.""", "CONFIRMED"),
    ("080129e2", "ComplexDivide", """[CONFIRMED, раздел 6.12/6.27] Комплексное деление — используется как Z = канал1 ⊘ канал2 (U/I). Совпадает с независимой оценкой Grok.""", "CONFIRMED"),
    ("08012a04", "ComplexMultiply", """[CONFIRMED, раздел 6.12/6.27] Комплексное умножение — используется в переводе магнитуды в физические единицы. Совпадает с независимой оценкой Grok.""", "CONFIRMED"),
    ("08013690", "ScatterLoad_PlainCopy", """[CONFIRMED, раздел 2 доп. 2026-09-13 / 4.3] Простое словное копирование (ldm/stm) — функция-копировщик записи 1 в scatter-load таблице (CCM RAM).""", "CONFIRMED"),
    ("08013ffc", "SinTableLookup", """[CONFIRMED, раздел 6.26] Табличный sin() — аргумент это фаза в радианах вида 2*pi*i/N.""", "CONFIRMED"),
    ("080154c8", "SoftwareDelay_ms", """[CONFIRMED, раздел 10] Программная задержка на миллисекундах (busy-wait, калибровка по частоте шины): (ms)->void.""", "CONFIRMED"),
    ("08015de0", "CorrelatorScaleGetter", """[CONFIRMED, раздел 6.12/6.26] Масштаб/нормировка коррелятора — вероятно возвращает число накопленных отсчётов N: (param_1)->float.""", "CONFIRMED"),
    ("08015ff0", "I2C_WriteBytes_BitBang", """[CONFIRMED, раздел уточнено при переносе на C] Программный I2C-мастер на GPIOB: PB6=SCL, PB7=SDA; байты по 8 бит старшим вперёд с проверкой ACK, при NACK — STOP и возврат 0. (Ранее была записана как запись строки в буфер экрана. Расхождение: PB6/PB7 раньше считались не подключёнными — разобрать.)""", "CONFIRMED"),
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
    ("080134b0", "DoubleSqrt_lib", """[PROBABLE, раздел 6.13 доп. 2026-09-15, проверка в эмуляторе] Корень из double (аргумент и результат в d0). Совпадение с sqrt() подтверждено сравнением в эмуляторе: результат ComputeCorrOutput_Buf2 с sqrt совпал с образом бит в бит на 40 случайных наборах (после приведения к float).""", "PROBABLE"),
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
