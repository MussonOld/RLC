/*
 * nrlc_funcs.h -- подтверждённые функции прошивки nRLC 2.0.12, перенесённые на C.
 *
 * Это "свалка": все функции со статусом CONFIRMED из FUNCTIONS.md в одной паре
 * .c/.h. При написании нового кода их берут отсюда и раскладывают по модулям.
 * Источник истины - INVESTIGATION_STATUS.md и листинг функций
 * nRLC_2_0_12_FREEWARE_functions.txt; здесь только перенос в C.
 *
 * Статус каждой функции указан в .c перед её определением:
 *   [PORTED]    тело перенесено с листинга, логика сохранена (с оговорками в комментарии)
 *   [LIB]       служебная арифметика компилятора (soft-float / 64-бит деление):
 *               в C это обычные операторы, функция оставлена ради соответствия адресу
 *   [HAL-EQUIV] функция совпадает по смыслу с вызовом HAL; тело не копируется,
 *               в новом проекте вызывать HAL (указано какой)
 *   [STUB]      слишком большая/неполно разобранная; оставлены прототип, описание
 *               и пометка, что тело ещё нужно переносить
 *
 * Адреса в RAM даны макросами NRLC_ADDR_*, как в оригинале. Когда функции будут
 * разложены по модулям, эти макросы заменяются настоящими переменными/структурами.
 *
 * Не перенесённые вызываемые функции (FUN_xxxxxxxx) объявлены в конце файла как extern.
 */
#ifndef NRLC_FUNCS_H
#define NRLC_FUNCS_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ------------------------------------------------------------------ */
/* Типы                                                               */
/* ------------------------------------------------------------------ */

/* Пара float (re, im). В листинге такие значения возвращаются как "undefined8". */
typedef struct {
    float re;
    float im;
} nrlc_cplxf;

/* ------------------------------------------------------------------ */
/* Доступ к абсолютным адресам RAM/флеша (как в оригинале)            */
/* ------------------------------------------------------------------ */
#define NRLC_R8(a)   (*(volatile uint8_t  *)(uintptr_t)(a))
#define NRLC_R16(a)  (*(volatile uint16_t *)(uintptr_t)(a))
#define NRLC_R32(a)  (*(volatile uint32_t *)(uintptr_t)(a))
#define NRLC_RF(a)   (*(volatile float    *)(uintptr_t)(a))

/* Карта RAM, которую используют перенесённые функции */
#define NRLC_ADDR_SYSTICK_STATE  0x20004650u /* счётчики/флаги SysTick (см. nrlc_SysTick_Handler_body) */
#define NRLC_ADDR_DDS            0x200049A8u /* состояние генератора: +0x3c частота выборки, +0x14 ... */
#define NRLC_ADDR_REF            0x200049E4u /* REF: делимое при поиске индекса по таблице */
#define NRLC_ADDR_REF_TABLE      0x20007878u /* таблица из 8 слов; [7] (+0x1c) - искомое значение */
#define NRLC_ADDR_CAL_K          0x20004998u /* float-коэффициент калибровки */
#define NRLC_ADDR_SYSCLK_VAR     0x20004788u /* переменная с частотой шины (SystemCoreClock) */
#define NRLC_ADDR_STAB           0x20005610u /* структура диапазонов/стабильности (+0x0f, +0x10, +0x11, +0x20 ...) */
#define NRLC_ADDR_PGA_TABLE      0x20005650u /* 8 байт: коэффициенты усиления PGA113 (RAM, не флеш) */
#define NRLC_ADDR_SETTINGS       0x200056A0u /* настройки: +0x2a порог автовыключения, +0x2c */
#define NRLC_ADDR_BATTERY        0x200056D0u /* состояние контроля батареи */
#define NRLC_ADDR_ADC4_HANDLE    0x20006968u /* хэндл ADC, из которого читается напряжение батареи */
#define NRLC_ADDR_ZRES           0x20004914u /* результат Z: +0x0c (0x20004920), +0x14 (0x20004928) */
#define NRLC_ADDR_FLAG_4A4D      0x20004A4Du /* флаг "результат обновлён" */
#define NRLC_ADDR_DDS_TABLE      0x20002EE0u /* буфер таблицы синуса для DAC (int16) */
#define NRLC_ADDR_TIM6_HANDLE    0x20007CA8u /* htim6 */
#define NRLC_ADDR_RELAY_STATE    0x20004AF4u /* текущие коды реле диапазона [0]=канал A, [1]=канал B */
#define NRLC_ADDR_RELAY_CMD_A    0x2000569Au
#define NRLC_ADDR_RELAY_CMD_B    0x2000569Bu
#define NRLC_ADDR_SCREEN_STATE   0x2000570Cu /* состояние вывода текста: +8 = позиция по X (mod 0x400) */
#define NRLC_FLASH_SETTINGS_BASE 0x0803C000u /* 7 страниц по 0x800 для настроек */
#define NRLC_FLASH_SETTINGS_PAGE 0x800u
#define NRLC_SETTINGS_BLOB_SIZE  0x244u

/* Таблица синуса из образа: sin(2*pi*i/512), i = 0..512 (513 значений) */
extern const float nrlc_sin_table[513];

/* ------------------------------------------------------------------ */
/* Арифметика компилятора (LIB)                                       */
/* ------------------------------------------------------------------ */
double   nrlc_DoubleMultiply(double a, double b);         /* FUN_08002698 */
double   nrlc_DoubleDivide(double a, double b);           /* FUN_0800277c */
double   nrlc_DoubleAdd(double a, double b);              /* FUN_0800254a */
double   nrlc_FloatToDouble(float x);                     /* FUN_08002932 */
float    nrlc_Int64ToFloat(int64_t x);                    /* FUN_0800285a */
uint64_t nrlc_UnsignedDiv64(uint64_t n, uint64_t d);      /* FUN_080023dc */
int64_t  nrlc_SignedDiv64(int64_t n, int64_t d);          /* FUN_0800243e */
int      nrlc_DoubleCompareGE(double a, double b);        /* FUN_08002958 */
void     nrlc_ScatterLoad_PlainCopy(const uint32_t *src, uint32_t *dst, uint32_t len); /* FUN_08013690 */
nrlc_cplxf nrlc_ComplexMultiply(float ar, float ai, float br, float bi); /* FUN_08012a04 */
nrlc_cplxf nrlc_ComplexDivide(float ar, float ai, float br, float bi);   /* FUN_080129e2 */
float    nrlc_SinTableLookup(float phase_rad);            /* FUN_08013ffc */
void     nrlc_SoftwareDelay_ms(uint32_t ms);              /* FUN_080154c8 */

/* ------------------------------------------------------------------ */
/* Низкий уровень: GPIO, NVIC, ADC, USB                               */
/* ------------------------------------------------------------------ */
uint32_t nrlc_ADC_GetValue(void *hadc);                                    /* FUN_08005148 */
uint32_t nrlc_GPIO_ReadBit(void *gpio_base, uint32_t mask);                /* FUN_08005efc */
void     nrlc_GPIO_WriteBit(void *gpio_base, uint32_t mask, int value);    /* FUN_08005f06 */
void     nrlc_NVIC_EnableIRQ(int32_t irq);                                 /* FUN_0800604e */
void     nrlc_NVIC_SetPriority(int32_t irq, uint32_t preempt, uint32_t sub); /* FUN_0800606c */
uint32_t nrlc_USB_EnableGlobalInt(void *usb_base);                         /* FUN_080126d0 */
uint16_t nrlc_USB_ReadInterrupts(void *usb_base);                          /* FUN_080126f0 */
uint32_t nrlc_USB_ResumeCallback(void *hpcd);                              /* FUN_080065c2 */
uint32_t nrlc_USB_SOF_Callback(void *hpcd);                                /* FUN_080065ca */
void     nrlc_USB_SuspendCallback(void *hpcd);                             /* FUN_0800663c */
void     nrlc_USB_IRQHandler_main(void *hpcd);                             /* FUN_08006328 */
void     nrlc_USB_CTR_EndpointTransfer(void *hpcd);                        /* FUN_0800e754 [STUB] */
void     nrlc_TimerClockEnable(void *htim);                                /* FUN_08007944 */
void     nrlc_TIM6_FullInit(void);                                         /* FUN_08003428 */
void     nrlc_SPI1_MspInit(void *hspi);                                    /* FUN_08007298 */
void     nrlc_USART1_MspInit(void *huart);                                 /* FUN_080087f8 */
uint32_t nrlc_DAC_ConfigChannel(void *hdac, const uint32_t *cfg, uint32_t channel_shift); /* FUN_08005798 */

/* HAL-эквиваленты (тело не копируется) */
uint32_t nrlc_GPIO_Init(void *gpio_base, void *init);                      /* FUN_08005ccc = HAL_GPIO_Init */
uint32_t nrlc_DMA_Init(void *hdma);                                        /* FUN_08005a88 = HAL_DMA_Init */
void     nrlc_DMA_GenericISR(void *hdma);                                  /* FUN_080059ba = HAL_DMA_IRQHandler */
uint32_t nrlc_TimBase_Init(void *htim);                                    /* FUN_080078e0 = HAL_TIM_Base_Init */
uint32_t nrlc_TIMEx_MasterConfigSync(void *htim, const uint32_t *cfg);     /* FUN_0800784c = HAL_TIMEx_MasterConfigSynchronization */
uint32_t nrlc_TIM_OC_Config(void *htim, void *oc, uint32_t channel);       /* FUN_08007d14 [HAL-EQUIV, сигнатура не проверена] */
uint32_t nrlc_ADC_SetTriggerConfig(void *hadc, void *cfg);                 /* FUN_08005150 [HAL-EQUIV, сигнатура не проверена] */
uint32_t nrlc_ADC_ConfigChannel(void *hadc, void *cfg);                    /* FUN_08004d94 = HAL_ADC_ConfigChannel */
uint32_t nrlc_ADC_AnalogWatchdogConfig(void *hadc, void *cfg);             /* FUN_08004c1c = HAL_ADC_AnalogWDGConfig */
void     nrlc_ADC_MspInit(void *hadc);                                     /* FUN_08003140 [STUB] */
void     nrlc_ADC_MspGpioInit(void *hadc);                                 /* FUN_08005404 [STUB] */
void     nrlc_TIM3_CH4_OC_Config(void);                                    /* FUN_080009f0 [STUB] */

/* ------------------------------------------------------------------ */
/* Измерительный тракт                                                */
/* ------------------------------------------------------------------ */
void     nrlc_SysTick_Handler_body(void);                  /* FUN_0800019c */
float    nrlc_GetPGA_GainCh1(void);                        /* FUN_08000d5a */
float    nrlc_GetPGA_GainCh2(void);                        /* FUN_08000d7c */
float    nrlc_GetRangeCalibConst(void);                    /* FUN_08000d9e */
float    nrlc_GetCurrentFrequency(void);                   /* FUN_080006a8 */
float    nrlc_CorrelatorScaleGetter(const uint32_t *corr); /* FUN_08015de0 */
void     nrlc_ConvertCorrToPhysical(const uint32_t *corr); /* FUN_0800dbf8 */
void     nrlc_ComputeCorrOutput_Buf2(uint32_t *buf);       /* FUN_08002ec0 (читает и пишет ту же структуру) */
void     nrlc_ReadREF_ComputeStageValue(void);             /* FUN_08000dbe */
uint32_t nrlc_FindREFTableIndex(void);                     /* FUN_0800ef20 */
uint32_t nrlc_FlashPageErase_ByREF(void);                  /* FUN_08003940 */
uint32_t nrlc_FlashPageSave_ByREF(void);                   /* FUN_080039b0 */
void     nrlc_SetAutoOffThreshold(uint16_t ms, int save);  /* FUN_0800fcf4 */
void     nrlc_BatteryCalibConstants(void);                 /* FUN_08017dc8 */
void     nrlc_SetDACFrequency(uint32_t freq_hz);           /* FUN_08018158 */
void     nrlc_RangeRelayControl(int u_channel, uint32_t code); /* FUN_0800ae7c */
uint32_t nrlc_PrintCharToScreenBuffer(int mode, const char *s); /* FUN_0800ade8 */
uint32_t nrlc_I2C_WriteBytes_BitBang(const uint8_t *data, int len); /* FUN_08015ff0 */

/* STUB: крупные функции, тело не перенесено (см. .c) */
void     nrlc_MeasurementStageDispatcher(void);            /* FUN_08000618 [STUB] */
void     nrlc_CommandDispatcher_Parser(void);              /* FUN_08000270 [STUB] */
void     nrlc_MeasurementOrchestrator(float arg);          /* FUN_08000f52 [STUB] */
void     nrlc_DisplayRefresh_DrawResult(void);             /* FUN_08009618 [STUB] */
void     nrlc_MainApplicationInit(void);                   /* FUN_08016274 [STUB] */
void     nrlc_TIM7_ISR(void);                              /* FUN_0800ff78 [STUB] */
void     nrlc_FormulaRsRpLC(const uint32_t *corr, int alt_flag); /* FUN_0800d578 [STUB, частично] */
void     nrlc_AutoFreqSearchAndReportBuilder(void);        /* FUN_08017f70 [STUB] */
void     nrlc_ScatterLoad_Init(void);                      /* FUN_08002d48 [STUB: делает стартовый код проекта] */
void     nrlc_CorrelatorCore_CCM(void);                    /* 0x100001B8 [STUB: ARM-ассемблер в CCM RAM] */
void     nrlc_GPIOB_Toggle_Inert(void);                    /* 0x10000B5C [STUB: ассемблер в CCM RAM] */
void     nrlc_BuzzerDriver(uint32_t ms);                   /* 0x10000BC0 [STUB: ассемблер в CCM RAM] */

/* ------------------------------------------------------------------ */
/* Вызываемые функции, которые ещё не подтверждены/не перенесены       */
/* ------------------------------------------------------------------ */
extern void     FUN_08005c9c(void);                 /* HAL_FLASH_Unlock (по использованию) */
extern void     FUN_08005bfc(void);                 /* HAL_FLASH_Lock (по использованию) */
extern uint32_t FUN_08005c10(uint32_t type, uint32_t addr, uint32_t lo, uint32_t hi); /* HAL_FLASH_Program */
extern uint32_t FUN_08005b2c(void *erase_init, uint32_t *page_error);                 /* HAL_FLASHEx_Erase */
extern void     FUN_08004720(uint16_t offset, uint16_t value); /* запись параметра настроек во флеш (не разобрана) */
extern void     FUN_080048a4(void);                 /* обработчик ошибки (Error_Handler) */
extern uint32_t FUN_08009428(int mode, uint8_t ch); /* вывод одного символа (не разобрана) */
extern void     FUN_08012764(uint32_t word);        /* отправка слова в PGA113/ключи (не разобрана) */
extern void     FUN_08011578(void *pdev);           /* USBD_LL_Suspend (по использованию) */
extern void     FUN_0800659c(void *hpcd);           /* ResetCallback USB */
extern void     FUN_08012728(void *usb_base);       /* USB_SetDevAddress(0) (по использованию) */
extern void     FUN_0800ee00(int reason);           /* выключение питания (по использованию) */
extern int32_t  FUN_080132d0(double x);             /* double -> целое (способ округления не проверен) */
extern void     FUN_08007a00(void *htim);           /* вызывается при запуске TIM6 (назначение не подтверждено) */
extern void     FUN_08007a70(void *htim);           /* вызывается при запуске TIM6 (назначение не подтверждено) */
extern void     thunk_EXT_FUN_10000000(void);       /* функция в CCM RAM, вызывается после построения таблицы */

#ifdef __cplusplus
}
#endif

#endif /* NRLC_FUNCS_H */
