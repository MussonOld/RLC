/*
 * nrlc_funcs.c -- подтверждённые функции прошивки nRLC 2.0.12 на C.
 * Описание статусов [PORTED]/[LIB]/[HAL-EQUIV]/[STUB] - в nrlc_funcs.h.
 *
 * Правило этого файла: код следует листингу. Если анализатор потерял аргумент
 * (аргументы в регистрах), это отмечено словом "ЛИСТИНГ:" и выбрано самое
 * правдоподобное прочтение; такие места надо перепроверять на железе.
 */
#include "nrlc_funcs.h"
#include "stm32f3xx.h"

/* Короткая задержка между фронтами при программном I2C (в оригинале цикл из одной итерации). */
#define NRLC_TINY_DELAY()  do { volatile uint8_t d_ = 0; do { d_++; } while (d_ == 0); } while (0)

/* ================================================================== */
/* Таблица синуса (из образа, флеш 0x08026A64, 513 значений)           */
/* ================================================================== */
const float nrlc_sin_table[513] = {
    0.0f, 0.0122715402f, 0.0245412309f, 0.0368072204f, 0.0490676686f, 0.0613207407f,
    0.0735645592f, 0.0857973099f, 0.0980171412f, 0.110222213f, 0.122410677f, 0.134580716f,
    0.146730468f, 0.158858135f, 0.170961887f, 0.183039889f, 0.195090324f, 0.207111374f,
    0.219101235f, 0.231058106f, 0.242980182f, 0.254865646f, 0.266712755f, 0.27851969f,
    0.290284693f, 0.302005947f, 0.313681751f, 0.32531029f, 0.336889863f, 0.348418683f,
    0.359895051f, 0.371317178f, 0.382683426f, 0.393992037f, 0.405241311f, 0.416429549f,
    0.427555084f, 0.438616246f, 0.449611336f, 0.460538715f, 0.471396744f, 0.482183784f,
    0.492898196f, 0.50353837f, 0.514102757f, 0.524589658f, 0.534997642f, 0.545324981f,
    0.555570245f, 0.565731823f, 0.575808167f, 0.585797846f, 0.59569931f, 0.605511069f,
    0.615231574f, 0.624859512f, 0.634393275f, 0.643831551f, 0.653172851f, 0.662415802f,
    0.671558976f, 0.680601001f, 0.689540565f, 0.698376238f, 0.707106769f, 0.715730846f,
    0.724247098f, 0.732654274f, 0.740951121f, 0.749136388f, 0.757208824f, 0.765167296f,
    0.773010433f, 0.780737221f, 0.78834641f, 0.795836926f, 0.803207517f, 0.81045723f,
    0.817584813f, 0.824589312f, 0.831469595f, 0.838224709f, 0.84485358f, 0.851355195f,
    0.857728601f, 0.863972843f, 0.870086968f, 0.876070082f, 0.881921232f, 0.887639642f,
    0.893224299f, 0.898674488f, 0.903989315f, 0.909168005f, 0.914209783f, 0.919113874f,
    0.923879504f, 0.928506076f, 0.932992816f, 0.937339008f, 0.941544056f, 0.945607305f,
    0.949528158f, 0.953306019f, 0.956940353f, 0.960430503f, 0.963776052f, 0.966976464f,
    0.970031261f, 0.972939968f, 0.975702107f, 0.97831738f, 0.980785251f, 0.983105481f,
    0.985277653f, 0.987301409f, 0.989176512f, 0.990902662f, 0.992479503f, 0.993906975f,
    0.99518472f, 0.996312618f, 0.997290432f, 0.998118103f, 0.99879545f, 0.999322355f,
    0.999698818f, 0.999924719f, 1.0f, 0.999924719f, 0.999698818f, 0.999322355f,
    0.99879545f, 0.998118103f, 0.997290432f, 0.996312618f, 0.99518472f, 0.993906975f,
    0.992479503f, 0.990902662f, 0.989176512f, 0.987301409f, 0.985277653f, 0.983105481f,
    0.980785251f, 0.97831738f, 0.975702107f, 0.972939968f, 0.970031261f, 0.966976464f,
    0.963776052f, 0.960430503f, 0.956940353f, 0.953306019f, 0.949528158f, 0.945607305f,
    0.941544056f, 0.937339008f, 0.932992816f, 0.928506076f, 0.923879504f, 0.919113874f,
    0.914209783f, 0.909168005f, 0.903989315f, 0.898674488f, 0.893224299f, 0.887639642f,
    0.881921232f, 0.876070082f, 0.870086968f, 0.863972843f, 0.857728601f, 0.851355195f,
    0.84485358f, 0.838224709f, 0.831469595f, 0.824589312f, 0.817584813f, 0.81045723f,
    0.803207517f, 0.795836926f, 0.78834641f, 0.780737221f, 0.773010433f, 0.765167296f,
    0.757208824f, 0.749136388f, 0.740951121f, 0.732654274f, 0.724247098f, 0.715730846f,
    0.707106769f, 0.698376238f, 0.689540565f, 0.680601001f, 0.671558976f, 0.662415802f,
    0.653172851f, 0.643831551f, 0.634393275f, 0.624859512f, 0.615231574f, 0.605511069f,
    0.59569931f, 0.585797846f, 0.575808167f, 0.565731823f, 0.555570245f, 0.545324981f,
    0.534997642f, 0.524589658f, 0.514102757f, 0.50353837f, 0.492898196f, 0.482183784f,
    0.471396744f, 0.460538715f, 0.449611336f, 0.438616246f, 0.427555084f, 0.416429549f,
    0.405241311f, 0.393992037f, 0.382683426f, 0.371317178f, 0.359895051f, 0.348418683f,
    0.336889863f, 0.32531029f, 0.313681751f, 0.302005947f, 0.290284693f, 0.27851969f,
    0.266712755f, 0.254865646f, 0.242980182f, 0.231058106f, 0.219101235f, 0.207111374f,
    0.195090324f, 0.183039889f, 0.170961887f, 0.158858135f, 0.146730468f, 0.134580716f,
    0.122410677f, 0.110222213f, 0.0980171412f, 0.0857973099f, 0.0735645592f, 0.0613207407f,
    0.0490676686f, 0.0368072204f, 0.0245412309f, 0.0122715402f, 0.0f, -0.0122715402f,
    -0.0245412309f, -0.0368072204f, -0.0490676686f, -0.0613207407f, -0.0735645592f, -0.0857973099f,
    -0.0980171412f, -0.110222213f, -0.122410677f, -0.134580716f, -0.146730468f, -0.158858135f,
    -0.170961887f, -0.183039889f, -0.195090324f, -0.207111374f, -0.219101235f, -0.231058106f,
    -0.242980182f, -0.254865646f, -0.266712755f, -0.27851969f, -0.290284693f, -0.302005947f,
    -0.313681751f, -0.32531029f, -0.336889863f, -0.348418683f, -0.359895051f, -0.371317178f,
    -0.382683426f, -0.393992037f, -0.405241311f, -0.416429549f, -0.427555084f, -0.438616246f,
    -0.449611336f, -0.460538715f, -0.471396744f, -0.482183784f, -0.492898196f, -0.50353837f,
    -0.514102757f, -0.524589658f, -0.534997642f, -0.545324981f, -0.555570245f, -0.565731823f,
    -0.575808167f, -0.585797846f, -0.59569931f, -0.605511069f, -0.615231574f, -0.624859512f,
    -0.634393275f, -0.643831551f, -0.653172851f, -0.662415802f, -0.671558976f, -0.680601001f,
    -0.689540565f, -0.698376238f, -0.707106769f, -0.715730846f, -0.724247098f, -0.732654274f,
    -0.740951121f, -0.749136388f, -0.757208824f, -0.765167296f, -0.773010433f, -0.780737221f,
    -0.78834641f, -0.795836926f, -0.803207517f, -0.81045723f, -0.817584813f, -0.824589312f,
    -0.831469595f, -0.838224709f, -0.84485358f, -0.851355195f, -0.857728601f, -0.863972843f,
    -0.870086968f, -0.876070082f, -0.881921232f, -0.887639642f, -0.893224299f, -0.898674488f,
    -0.903989315f, -0.909168005f, -0.914209783f, -0.919113874f, -0.923879504f, -0.928506076f,
    -0.932992816f, -0.937339008f, -0.941544056f, -0.945607305f, -0.949528158f, -0.953306019f,
    -0.956940353f, -0.960430503f, -0.963776052f, -0.966976464f, -0.970031261f, -0.972939968f,
    -0.975702107f, -0.97831738f, -0.980785251f, -0.983105481f, -0.985277653f, -0.987301409f,
    -0.989176512f, -0.990902662f, -0.992479503f, -0.993906975f, -0.99518472f, -0.996312618f,
    -0.997290432f, -0.998118103f, -0.99879545f, -0.999322355f, -0.999698818f, -0.999924719f,
    -1.0f, -0.999924719f, -0.999698818f, -0.999322355f, -0.99879545f, -0.998118103f,
    -0.997290432f, -0.996312618f, -0.99518472f, -0.993906975f, -0.992479503f, -0.990902662f,
    -0.989176512f, -0.987301409f, -0.985277653f, -0.983105481f, -0.980785251f, -0.97831738f,
    -0.975702107f, -0.972939968f, -0.970031261f, -0.966976464f, -0.963776052f, -0.960430503f,
    -0.956940353f, -0.953306019f, -0.949528158f, -0.945607305f, -0.941544056f, -0.937339008f,
    -0.932992816f, -0.928506076f, -0.923879504f, -0.919113874f, -0.914209783f, -0.909168005f,
    -0.903989315f, -0.898674488f, -0.893224299f, -0.887639642f, -0.881921232f, -0.876070082f,
    -0.870086968f, -0.863972843f, -0.857728601f, -0.851355195f, -0.84485358f, -0.838224709f,
    -0.831469595f, -0.824589312f, -0.817584813f, -0.81045723f, -0.803207517f, -0.795836926f,
    -0.78834641f, -0.780737221f, -0.773010433f, -0.765167296f, -0.757208824f, -0.749136388f,
    -0.740951121f, -0.732654274f, -0.724247098f, -0.715730846f, -0.707106769f, -0.698376238f,
    -0.689540565f, -0.680601001f, -0.671558976f, -0.662415802f, -0.653172851f, -0.643831551f,
    -0.634393275f, -0.624859512f, -0.615231574f, -0.605511069f, -0.59569931f, -0.585797846f,
    -0.575808167f, -0.565731823f, -0.555570245f, -0.545324981f, -0.534997642f, -0.524589658f,
    -0.514102757f, -0.50353837f, -0.492898196f, -0.482183784f, -0.471396744f, -0.460538715f,
    -0.449611336f, -0.438616246f, -0.427555084f, -0.416429549f, -0.405241311f, -0.393992037f,
    -0.382683426f, -0.371317178f, -0.359895051f, -0.348418683f, -0.336889863f, -0.32531029f,
    -0.313681751f, -0.302005947f, -0.290284693f, -0.27851969f, -0.266712755f, -0.254865646f,
    -0.242980182f, -0.231058106f, -0.219101235f, -0.207111374f, -0.195090324f, -0.183039889f,
    -0.170961887f, -0.158858135f, -0.146730468f, -0.134580716f, -0.122410677f, -0.110222213f,
    -0.0980171412f, -0.0857973099f, -0.0735645592f, -0.0613207407f, -0.0490676686f, -0.0368072204f,
    -0.0245412309f, -0.0122715402f, -0.0f
};

/* ================================================================== */
/* Арифметика компилятора [LIB]                                        */
/* В оригинале это soft-float/64-бит рутины рантайма; в C - операторы.  */
/* ================================================================== */

/* [LIB] FUN_08002698: умножение double */
double nrlc_DoubleMultiply(double a, double b) { return a * b; }

/* [LIB] FUN_0800277c: деление double (числитель - первая пара регистров) */
double nrlc_DoubleDivide(double a, double b) { return a / b; }

/* [LIB] FUN_0800254a: сложение double (вычитание - через смену знака) */
double nrlc_DoubleAdd(double a, double b) { return a + b; }

/* [LIB] FUN_08002932: float -> double */
double nrlc_FloatToDouble(float x) { return (double)x; }

/* [LIB] FUN_0800285a: знаковое 64-бит целое (lo, hi) -> float */
float nrlc_Int64ToFloat(int64_t x) { return (float)x; }

/* [LIB] FUN_080023dc: беззнаковое 64-бит деление, возвращает частное.
 * Сдвиг-вычитание из листинга при делителе 0 даёт все единицы. */
uint64_t nrlc_UnsignedDiv64(uint64_t n, uint64_t d)
{
    if (d == 0u) {
        return ~(uint64_t)0;
    }
    return n / d;
}

/* [LIB] FUN_0800243e: знаковое 64-бит деление поверх беззнакового (как в листинге). */
int64_t nrlc_SignedDiv64(int64_t n, int64_t d)
{
    int neg_n = (n < 0);
    int neg_d = (d < 0);
    uint64_t un = neg_n ? (uint64_t)0 - (uint64_t)n : (uint64_t)n;
    uint64_t ud = neg_d ? (uint64_t)0 - (uint64_t)d : (uint64_t)d;
    uint64_t q  = nrlc_UnsignedDiv64(un, ud);
    if (neg_n != neg_d) {
        q = (uint64_t)0 - q;
    }
    return (int64_t)q;
}

/* [LIB] FUN_08002958: сравнение double. В листинге видна только подготовка знака
 * (результат передаётся через флаги процессора, как у __aeabi_cdcmple), поэтому
 * здесь это просто сравнение "a >= b". ЛИСТИНГ: направление сравнения выведено
 * из мест вызова, не из тела. */
int nrlc_DoubleCompareGE(double a, double b) { return a >= b; }

/* [PORTED] FUN_08013690: копирование слов (запись 1 таблицы scatter-load).
 * Разобрано по машинному коду: цикл "пока len != 0: *dst++ = *src++; len -= 4".
 * len должен быть кратен 4, иначе цикл не завершится (как и в оригинале). */
void nrlc_ScatterLoad_PlainCopy(const uint32_t *src, uint32_t *dst, uint32_t len)
{
    while (len != 0u) {
        *dst++ = *src++;
        len -= 4u;
    }
}

/* [PORTED] FUN_08012a04: комплексное умножение (a*b), пара float (re, im). */
nrlc_cplxf nrlc_ComplexMultiply(float ar, float ai, float br, float bi)
{
    nrlc_cplxf r;
    r.re = ar * br - ai * bi;
    r.im = ar * bi + ai * br;
    return r;
}

/* [PORTED] FUN_080129e2: комплексное деление (a/b). */
nrlc_cplxf nrlc_ComplexDivide(float ar, float ai, float br, float bi)
{
    nrlc_cplxf r;
    float den = br * br + bi * bi;
    r.re = (ar * br + ai * bi) / den;
    r.im = (ai * br - ar * bi) / den;
    return r;
}

/* [PORTED] FUN_08013ffc: sin() по таблице с линейной интерполяцией.
 * Аргумент в радианах: умножается на 1/(2*pi), берётся дробная часть,
 * 512 ячеек таблицы + интерполяция между соседними. */
float nrlc_SinTableLookup(float phase_rad)
{
    float p = phase_rad * 0.15915493667125702f;     /* 0x3E22F983 = 1/(2*pi) */
    int32_t i = (int32_t)p;
    if (p < 0.0f) {
        i -= 1;
    }
    float f = (p - (float)i) * 512.0f;              /* 0x44000000 = 512.0 */
    uint32_t idx = ((uint32_t)f) & 0xFFFFu;
    if (idx > 0x1FFu) {
        idx = 0u;
        f = f - 512.0f;
    }
    float frac = f - (float)idx;
    return (1.0f - frac) * nrlc_sin_table[idx] + frac * nrlc_sin_table[idx + 1u];
}

/* [PORTED] FUN_080154c8: программная задержка в мс. Длина внутреннего цикла
 * зависит от частоты шины (72 МГц: 9000, 48 МГц: 7200, 24 МГц: 4500, ниже: 0). */
void nrlc_SoftwareDelay_ms(uint32_t ms)
{
    uint32_t n;
    uint32_t clk = NRLC_R32(NRLC_ADDR_SYSCLK_VAR);
    uint32_t cnt;

    if (clk >= 72000000u) {
        cnt = 9000u;
    } else if (clk >= 48000000u) {
        cnt = 7200u;
    } else if (clk >= 24000000u) {
        cnt = 4500u;
    } else {
        cnt = 0u;
    }
    for (n = 0u; n < ms; n++) {
        volatile uint32_t k;
        for (k = 0u; k < cnt; k++) {
        }
    }
}

/* ================================================================== */
/* GPIO, NVIC, ADC                                                     */
/* ================================================================== */

/* [PORTED] FUN_08005148: значение регистра данных ADC (смещение 0x40). */
uint32_t nrlc_ADC_GetValue(void *hadc)
{
    uint32_t inst = *(uint32_t *)hadc;
    return NRLC_R32(inst + 0x40u);
}

/* [PORTED] FUN_08005efc: чтение бита GPIO (IDR, смещение 0x10): 1 или 0. */
uint32_t nrlc_GPIO_ReadBit(void *gpio_base, uint32_t mask)
{
    return (NRLC_R32((uintptr_t)gpio_base + 0x10u) & mask) ? 1u : 0u;
}

/* [PORTED] FUN_08005f06: запись бита GPIO: value != 0 -> BSRR (0x18), иначе BRR (0x28). */
void nrlc_GPIO_WriteBit(void *gpio_base, uint32_t mask, int value)
{
    if (value != 0) {
        NRLC_R32((uintptr_t)gpio_base + 0x18u) = mask;
    } else {
        NRLC_R32((uintptr_t)gpio_base + 0x28u) = mask;
    }
}

/* [PORTED] FUN_0800604e: NVIC_EnableIRQ (ISER, 0xE000E100). */
void nrlc_NVIC_EnableIRQ(int32_t irq)
{
    if (irq < 0) {
        return;
    }
    NRLC_R32(0xE000E100u + ((uint32_t)irq >> 5) * 4u) = 1u << ((uint32_t)irq & 0x1Fu);
}

/* [PORTED] FUN_0800606c: приоритет прерывания (preempt, sub) с учётом PRIGROUP.
 * Разобрана арифметика листинга: совпадает с CMSIS NVIC_EncodePriority + NVIC_SetPriority. */
void nrlc_NVIC_SetPriority(int32_t irq, uint32_t preempt, uint32_t sub)
{
    NVIC_SetPriority((IRQn_Type)irq,
                     NVIC_EncodePriority(NVIC_GetPriorityGrouping(), preempt, sub));
}

/* ================================================================== */
/* USB (устройство). Хэндл hpcd - как PCD_HandleTypeDef из HAL:        */
/* +0x00 база USB, +0x18 low_power_enable, +0x24 адрес, +0x2a8 Lock,   */
/* +0x2e8 указатель на USBD-хэндл (state +0x29c, old_state +0x29d,     */
/* pClass +0x2b4).                                                     */
/* ================================================================== */

/* [PORTED] FUN_080126d0 (в FUNCTIONS.md было записано как геттер - это установщик):
 * ISTR (+0x44) = 0, CNTR (+0x40) = 0xBF00 (маски прерываний). */
uint32_t nrlc_USB_EnableGlobalInt(void *usb_base)
{
    uintptr_t b = (uintptr_t)usb_base;
    NRLC_R16(b + 0x44u) = 0u;
    NRLC_R16(b + 0x40u) = 0xBF00u;
    return 0u;
}

/* [PORTED] FUN_080126f0: чтение ISTR (+0x44). */
uint16_t nrlc_USB_ReadInterrupts(void *usb_base)
{
    return NRLC_R16((uintptr_t)usb_base + 0x44u);
}

/* [PORTED] FUN_080065c2: выход из SUSPENDED (state 4) в предыдущее состояние. */
uint32_t nrlc_USB_ResumeCallback(void *hpcd)
{
    uintptr_t pdev = NRLC_R32((uintptr_t)hpcd + 0x2E8u);
    if (NRLC_R8(pdev + 0x29Cu) == 4u) {
        NRLC_R8(pdev + 0x29Cu) = NRLC_R8(pdev + 0x29Du);
    }
    return 0u;
}

/* [PORTED] FUN_080065ca: SOF - если устройство в CONFIGURED (3) и у класса есть
 * обработчик SOF (pClass+0x1c), вызвать его. ЛИСТИНГ: аргумент вызова не виден;
 * по соглашению USBD передаётся pdev. */
uint32_t nrlc_USB_SOF_Callback(void *hpcd)
{
    uintptr_t pdev = NRLC_R32((uintptr_t)hpcd + 0x2E8u);
    if (NRLC_R8(pdev + 0x29Cu) == 3u) {
        uintptr_t pclass = NRLC_R32(pdev + 0x2B4u);
        uintptr_t fn = NRLC_R32(pclass + 0x1Cu);
        if (fn != 0u) {
            ((void (*)(void *))fn)((void *)pdev);
        }
    }
    return 0u;
}

/* [PORTED] FUN_0800663c: Suspend - USBD_LL_Suspend, затем при low_power_enable
 * включить SLEEPDEEP|SLEEPONEXIT в SCB->SCR. */
void nrlc_USB_SuspendCallback(void *hpcd)
{
    FUN_08011578((void *)(uintptr_t)NRLC_R32((uintptr_t)hpcd + 0x2E8u));
    if (NRLC_R32((uintptr_t)hpcd + 0x18u) != 0u) {
        SCB->SCR |= 6u;
    }
}

/* [PORTED] FUN_08006328: обработчик прерывания USB (эквивалент HAL_PCD_IRQHandler).
 * Порядок проверки флагов ISTR как в оригинале: CTR, RESET, PMAOVR, ERR, WKUP, SUSP, SOF, ESOF. */
void nrlc_USB_IRQHandler_main(void *hpcd)
{
    uintptr_t h   = (uintptr_t)hpcd;
    uintptr_t usb = NRLC_R32(h);

    if (nrlc_USB_ReadInterrupts((void *)usb) & 0x8000u) {            /* CTR */
        nrlc_USB_CTR_EndpointTransfer(hpcd);
    }
    if (nrlc_USB_ReadInterrupts((void *)usb) & 0x0400u) {            /* RESET */
        NRLC_R16(usb + 0x44u) &= 0xFBFFu;
        FUN_0800659c(hpcd);
        if (NRLC_R8(h + 0x2A8u) != 1u) {
            NRLC_R8(h + 0x2A8u) = 1u;
            NRLC_R8(h + 0x24u) = 0u;
            FUN_08012728((void *)usb);
            NRLC_R8(h + 0x2A8u) = 0u;
        }
    }
    if (nrlc_USB_ReadInterrupts((void *)usb) & 0x4000u) {            /* PMAOVR */
        NRLC_R16(usb + 0x44u) &= 0xBFFFu;
    }
    if (nrlc_USB_ReadInterrupts((void *)usb) & 0x2000u) {            /* ERR */
        NRLC_R16(usb + 0x44u) &= 0xDFFFu;
    }
    if (nrlc_USB_ReadInterrupts((void *)usb) & 0x1000u) {            /* WKUP */
        NRLC_R16(usb + 0x40u) &= 0xFFFBu;
        NRLC_R16(usb + 0x40u) &= 0xFFF7u;
        nrlc_USB_ResumeCallback(hpcd);
        NRLC_R16(usb + 0x44u) &= 0xEFFFu;
    }
    if (nrlc_USB_ReadInterrupts((void *)usb) & 0x0800u) {            /* SUSP */
        NRLC_R16(usb + 0x40u) |= 8u;
        NRLC_R16(usb + 0x44u) &= 0xF7FFu;
        NRLC_R16(usb + 0x40u) |= 4u;
        nrlc_USB_SuspendCallback(hpcd);
    }
    if (nrlc_USB_ReadInterrupts((void *)usb) & 0x0200u) {            /* SOF */
        NRLC_R16(usb + 0x44u) &= 0xFDFFu;
        nrlc_USB_SOF_Callback(hpcd);
    }
    if (nrlc_USB_ReadInterrupts((void *)usb) & 0x0100u) {            /* ESOF */
        NRLC_R16(usb + 0x44u) &= 0xFEFFu;
    }
}

/* [STUB] FUN_0800e754: обработка завершения передачи (CTR) по конечным точкам, 403 строки листинга. */
void nrlc_USB_CTR_EndpointTransfer(void *hpcd)
{
    (void)hpcd; /* TODO: перенести тело (эквивалент PCD_EP_ISR_Handler из HAL). */
}

/* ================================================================== */
/* Таймеры, SPI/USART MSP, DAC                                         */
/* ================================================================== */

/* [PORTED] FUN_08007944: включить тактирование таймера по базе из хэндла
 * (+ для TIM7: приоритет и разрешение IRQ 55). */
void nrlc_TimerClockEnable(void *htim)
{
    uint32_t inst = *(uint32_t *)htim;

    if (inst == (uint32_t)TIM1) {
        RCC->APB2ENR |= 0x800u;
    } else if (inst == (uint32_t)TIM2) {
        RCC->APB1ENR |= 0x1u;
    } else if (inst == (uint32_t)TIM3) {
        RCC->APB1ENR |= 0x2u;
    } else if (inst == (uint32_t)TIM4) {
        RCC->APB1ENR |= 0x4u;
    } else if (inst == (uint32_t)TIM7) {
        RCC->APB1ENR |= 0x20u;
        nrlc_NVIC_SetPriority(0x37, 0xFu, 0u);   /* ЛИСТИНГ: третий аргумент не виден, взят 0 */
        nrlc_NVIC_EnableIRQ(0x37);
    } else if (inst == (uint32_t)TIM16) {
        RCC->APB2ENR |= 0x20000u;
    }
}

/* [PORTED] FUN_08003428: полная инициализация TIM6 (htim6 в RAM 0x20007CA8).
 * PSC=99, период считается из частоты шины, прерывание IRQ 54, DIER.UIE=1. */
void nrlc_TIM6_FullInit(void)
{
    uint32_t *h = (uint32_t *)NRLC_ADDR_TIM6_HANDLE;
    uint32_t mcfg[3];
    uint64_t prod;

    RCC->APB1ENR |= 0x10u;
    (void)(RCC->APB1ENR & 0x10u);

    h[0] = (uint32_t)TIM6;          /* Instance */
    h[1] = 99u;                     /* Prescaler */
    h[2] = 0u;                      /* CounterMode */
    h[4] = 0u;                      /* ClockDivision */
    h[6] = 0u;                      /* AutoReloadPreload */
    h[5] = 0u;                      /* RepetitionCounter */
    prod = (uint64_t)0x51EB851Fu * ((uint64_t)NRLC_R32(NRLC_ADDR_SYSCLK_VAR) / 100u);
    h[3] = ((((uint32_t)(prod >> 32)) << 10) >> 16) - 1u;      /* Period */

    nrlc_TimBase_Init(h);
    mcfg[0] = 0u; mcfg[1] = 0u; mcfg[2] = 0u;
    nrlc_TIMEx_MasterConfigSync(h, mcfg);
    FUN_08007a00(h);
    FUN_08007a70(h);
    nrlc_NVIC_SetPriority(0x36, 0u, 0u);   /* ЛИСТИНГ: sub-приоритет не виден */
    nrlc_NVIC_EnableIRQ(0x36);
    TIM6->DIER |= 1u;
}

/* [PORTED] FUN_08007298: MSP-инициализация SPI1 (GPIOB: PB3,PB4,PB5 AF5; DMA1 канал 3, TX). */
void nrlc_SPI1_MspInit(void *hspi)
{
    uint32_t *h = (uint32_t *)hspi;
    uint32_t gi[5];
    uint32_t *d;

    if (h[0] != (uint32_t)SPI1) {
        return;
    }
    RCC->APB2ENR |= 0x1000u;       /* SPI1EN */
    RCC->AHBENR  |= 0x40000u;      /* IOPBEN */
    (void)(RCC->AHBENR & 0x40000u);

    gi[0] = 0x38u;  /* Pin: PB3|PB4|PB5 */
    gi[1] = 2u;     /* Mode: AF push-pull */
    gi[2] = 0u;     /* Pull */
    gi[3] = 3u;     /* Speed: high */
    gi[4] = 5u;     /* Alternate: AF5 */
    nrlc_GPIO_Init((void *)GPIOB, gi);

    d = (uint32_t *)0x20006D04u;   /* hdma_spi1_tx */
    d[0] = 0x40020030u;            /* DMA1_Channel3 */
    d[1] = 0x10u;                  /* Direction: память -> периферия */
    d[2] = 0u;                     /* PeriphInc */
    d[3] = 0x80u;                  /* MemInc */
    d[4] = 0x100u;                 /* PeriphDataAlignment: полуслово */
    d[5] = 0x400u;                 /* MemDataAlignment: полуслово */
    d[6] = 0u;                     /* Mode */
    d[7] = 0u;                     /* Priority */
    if (nrlc_DMA_Init(d) != 0u) {
        FUN_080048a4();
    }
    h[0x15] = (uint32_t)d;         /* hspi->hdmatx */
    d[9] = (uint32_t)h;            /* hdma->Parent */
}

/* [PORTED] FUN_080087f8 (в FUNCTIONS.md было названо MSP для SPI1/дисплея - по листингу это USART1):
 * GPIOA PA9,PA10 AF7, DMA1 канал 4 (TX) и канал 5 (RX), IRQ 37. */
void nrlc_USART1_MspInit(void *huart)
{
    uint32_t *h = (uint32_t *)huart;
    uint32_t gi[5];
    uint32_t *d;

    if (h[0] != (uint32_t)USART1) {
        return;
    }
    RCC->APB2ENR |= 0x4000u;       /* USART1EN */
    RCC->AHBENR  |= 0x20000u;      /* IOPAEN */
    (void)(RCC->AHBENR & 0x20000u);

    gi[0] = 0x600u; /* PA9|PA10 */
    gi[1] = 2u;
    gi[2] = 0u;
    gi[3] = 3u;
    gi[4] = 7u;     /* AF7 */
    nrlc_GPIO_Init((void *)GPIOA, gi);

    d = (uint32_t *)0x20006D48u;   /* hdma_usart1_tx */
    d[0] = 0x40020044u;            /* DMA1_Channel4 */
    d[1] = 0x10u; d[2] = 0u; d[3] = 0x80u; d[4] = 0u; d[5] = 0u; d[6] = 0u; d[7] = 0u;
    if (nrlc_DMA_Init(d) != 0u) {
        FUN_080048a4();
    }
    h[0x1B] = (uint32_t)d;         /* huart->hdmatx */
    d[9] = (uint32_t)h;

    d = (uint32_t *)0x20006D8Cu;   /* hdma_usart1_rx */
    d[0] = 0x40020058u;            /* DMA1_Channel5 */
    d[1] = 0u;  d[2] = 0u; d[3] = 0x80u; d[4] = 0u; d[5] = 0u; d[6] = 0u; d[7] = 0u;
    if (nrlc_DMA_Init(d) != 0u) {
        FUN_080048a4();
    }
    h[0x1C] = (uint32_t)d;         /* huart->hdmarx */
    d[9] = (uint32_t)h;

    nrlc_NVIC_SetPriority(0x25, 2u, 0u);   /* ЛИСТИНГ: sub-приоритет не виден */
    nrlc_NVIC_EnableIRQ(0x25);
}

/* [PORTED] FUN_08005798: настройка канала DAC (аналог HAL_DAC_ConfigChannel).
 * cfg[0] = триггер, cfg[1] = выходной буфер; channel_shift = 0 (канал 1) или 16 (канал 2).
 * Возврат: 0 ок, 2 - хэндл занят. */
uint32_t nrlc_DAC_ConfigChannel(void *hdac, const uint32_t *cfg, uint32_t channel_shift)
{
    uint8_t  *hb = (uint8_t *)hdac;
    uint32_t *h  = (uint32_t *)hdac;
    volatile uint32_t *cr;
    uint32_t sh = channel_shift & 0xFFu;

    if (hb[5] == 1u) {
        return 2u;
    }
    hb[5] = 1u;
    hb[4] = 2u;
    cr = (volatile uint32_t *)(uintptr_t)h[0];
    *cr = ((cfg[1] | cfg[0]) << sh) | (*cr & ~(0xFFEu << sh));
    *cr = *cr & ~(0xC0u << sh);
    hb[4] = 1u;
    hb[5] = 0u;
    return 0u;
}

/* ================================================================== */
/* HAL-эквиваленты [HAL-EQUIV]: тело не копируется, вызывать HAL.      */
/* Заглушки возвращают 1 (HAL_ERROR), чтобы случайный вызов был заметен.*/
/* ================================================================== */

/* [HAL-EQUIV] FUN_08005ccc = HAL_GPIO_Init(port, &GPIO_InitTypeDef{Pin,Mode,Pull,Speed,Alternate}). */
uint32_t nrlc_GPIO_Init(void *gpio_base, void *init)  { (void)gpio_base; (void)init; return 1u; }

/* [HAL-EQUIV] FUN_08005a88 = HAL_DMA_Init(&hdma). Возвращает 0 при успехе, 1 если хэндл NULL. */
uint32_t nrlc_DMA_Init(void *hdma)                    { (void)hdma; return 1u; }

/* [HAL-EQUIV] FUN_080059ba = HAL_DMA_IRQHandler(&hdma). */
void nrlc_DMA_GenericISR(void *hdma)                  { (void)hdma; }

/* [HAL-EQUIV] FUN_080078e0 = HAL_TIM_Base_Init(&htim). */
uint32_t nrlc_TimBase_Init(void *htim)                { (void)htim; return 1u; }

/* [HAL-EQUIV] FUN_0800784c = HAL_TIMEx_MasterConfigSynchronization(&htim, &cfg)
 * (в FUNCTIONS.md было названо TIM_Base_SetConfig - по листингу меняет CR2.MMS и SMCR.MSM). */
uint32_t nrlc_TIMEx_MasterConfigSync(void *htim, const uint32_t *cfg) { (void)htim; (void)cfg; return 1u; }

/* [HAL-EQUIV] FUN_08007d14: настройка Output Compare (раскладка совпадает с TIM_OC_InitTypeDef);
 * точная сигнатура не проверялась. */
uint32_t nrlc_TIM_OC_Config(void *htim, void *oc, uint32_t channel) { (void)htim; (void)oc; (void)channel; return 1u; }

/* [HAL-EQUIV] FUN_08005150: ExternalTrigConv/Edge для ADC (133 строки листинга, сигнатура не проверялась). */
uint32_t nrlc_ADC_SetTriggerConfig(void *hadc, void *cfg) { (void)hadc; (void)cfg; return 1u; }

/* [HAL-EQUIV] FUN_08004d94 = HAL_ADC_ConfigChannel(&hadc, &ADC_ChannelConfTypeDef). */
uint32_t nrlc_ADC_ConfigChannel(void *hadc, void *cfg)    { (void)hadc; (void)cfg; return 1u; }

/* [HAL-EQUIV] FUN_08004c1c = HAL_ADC_AnalogWDGConfig (аналоговый watchdog, не конфигуратор канала). */
uint32_t nrlc_ADC_AnalogWatchdogConfig(void *hadc, void *cfg) { (void)hadc; (void)cfg; return 1u; }

/* [STUB] FUN_08003140: инициализация ADC1/ADC2 (каналы, ранги, DMA, триггер), 163 строки листинга. */
void nrlc_ADC_MspInit(void *hadc)      { (void)hadc; /* TODO */ }

/* [STUB] FUN_08005404: MSP-инициализация GPIO для ADC (аналоговые входы). */
void nrlc_ADC_MspGpioInit(void *hadc)  { (void)hadc; /* TODO */ }

/* [STUB] FUN_080009f0: настройка TIM3 CH4 (Output Compare, запуск выборки ADC), 178 строк листинга. */
void nrlc_TIM3_CH4_OC_Config(void)     { /* TODO */ }

/* ================================================================== */
/* Измерительный тракт                                                 */
/* ================================================================== */

/* [PORTED] FUN_0800019c: тело SysTick. Каждые 3 тика безусловно запускает цикл измерения:
 * ADC1/ADC2 (ADEN|ADSTART), TIM2/TIM3 (CEN), DAC1 (TEN1), разрешение DMA1_Channel1.
 * Параллельно ведёт набор счётчиков в структуре 0x20004650 (смещения указаны ниже),
 * в конце вызывает обработчик TIM7 (FUN_0800ff78) как обычную функцию. */
void nrlc_SysTick_Handler_body(void)
{
    const uintptr_t p = NRLC_ADDR_SYSTICK_STATE;
    uint16_t v;
    uint8_t b;
    uint32_t lo;

    if (NRLC_R16(p + 0x24u) != 0u) {
        NRLC_R16(p + 0x24u) = (uint16_t)(NRLC_R16(p + 0x24u) - 1u);
    }

    v = NRLC_R16(p + 0x30u);                 /* 0..300, по переполнению взводит флаг [0] */
    if (v < 300u) {
        NRLC_R16(p + 0x30u) = (uint16_t)(v + 1u);
    } else {
        NRLC_R16(p + 0x30u) = 0u;
        NRLC_R8(p) = 1u;
    }

    v = NRLC_R16(p + 0x1Eu);                 /* 0..10, по переполнению ++ счётчиков +0x22, +0x26 */
    if (v < 10u) {
        NRLC_R16(p + 0x1Eu) = (uint16_t)(v + 1u);
    } else {
        NRLC_R16(p + 0x1Eu) = 0u;
        NRLC_R16(p + 0x22u) = (uint16_t)(NRLC_R16(p + 0x22u) + 1u);
        NRLC_R16(p + 0x26u) = (uint16_t)(NRLC_R16(p + 0x26u) + 1u);
    }

    v = NRLC_R16(p + 0x20u);                 /* 0..10, по переполнению взводит флаг [3] */
    if (v < 10u) {
        NRLC_R16(p + 0x20u) = (uint16_t)(v + 1u);
    } else {
        NRLC_R16(p + 0x20u) = 0u;
        NRLC_R8(p + 3u) = 1u;
    }

    NRLC_R16(p + 0x28u) = 1u;
    NRLC_R8(p + 4u) = 1u;

    lo = NRLC_R32(p + 0x78u);                /* 64-битный счётчик тиков: +0x78 (младшее), +0x7c */
    NRLC_R32(p + 0x78u) = lo + 1u;
    NRLC_R32(p + 0x7Cu) = NRLC_R32(p + 0x7Cu) + ((lo == 0xFFFFFFFFu) ? 1u : 0u);

    NRLC_R8(p + 8u) = 1u;

    v = NRLC_R16(p + 0x2Eu);                 /* 0..3: на переполнении стартует цикл измерения */
    if (v < 3u) {
        NRLC_R16(p + 0x2Eu) = (uint16_t)(v + 1u);
    } else {
        NRLC_R16(p + 0x2Eu) = 0u;
        ADC1->CR |= 5u;
        ADC2->CR |= 5u;
        TIM2->CR1 |= 1u;
        TIM3->CR1 |= 1u;
        DAC1->CR |= 4u;
        nrlc_NVIC_EnableIRQ(11);             /* DMA1_Channel1 */
    }

    b = NRLC_R8(p + 9u);                     /* 0..5; на переполнении переключает/сбрасывает байт +10 */
    if (b < 5u) {
        NRLC_R8(p + 9u) = (uint8_t)(b + 1u);
    } else {
        NRLC_R8(p + 9u) = 0u;
        if (NRLC_R8(p + 0xFu) == 0u) {
            NRLC_R8(p + 10u) = 0u;
        } else {
            NRLC_R8(p + 10u) = (NRLC_R8(p + 10u) == 0u) ? 1u : 0u;
        }
    }

    nrlc_TIM7_ISR();
}

/* [PORTED] общая часть FUN_08000d5a / FUN_08000d7c: коэффициент усиления канала.
 * Индекс усиления (байт) < 8 берёт значение из таблицы PGA в RAM, иначе 1.0; результат x1.5. */
static float nrlc_pga_gain(uint32_t index_offset)
{
    uint8_t idx = NRLC_R8(NRLC_ADDR_STAB + index_offset);
    float g = 1.0f;
    if (idx < 8u) {
        g = (float)NRLC_R8(NRLC_ADDR_PGA_TABLE + idx);
    }
    return g * 1.5f;
}

/* [PORTED] FUN_08000d5a: усиление канала 1 (индекс в 0x20005610+0x10). */
float nrlc_GetPGA_GainCh1(void) { return nrlc_pga_gain(0x10u); }

/* [PORTED] FUN_08000d7c: усиление канала 2 (индекс в 0x20005610+0x11). */
float nrlc_GetPGA_GainCh2(void) { return nrlc_pga_gain(0x11u); }

/* [PORTED] FUN_08000d9e: константа диапазона. Байт +0x0f: 0 -> значение из слова +0x20,
 * 1 -> 10000.0 (0x461C4000), другое ненулевое -> 100.0 (0x42C80000). */
float nrlc_GetRangeCalibConst(void)
{
    uint8_t mode = NRLC_R8(NRLC_ADDR_STAB + 0x0Fu);
    if (mode != 0u) {
        return (mode == 1u) ? 10000.0f : 100.0f;
    }
    return (float)NRLC_R16(NRLC_ADDR_STAB + 0x20u);
}

/* [PORTED] FUN_080006a8: текущая частота. Считает отношение частоты выборки (+0x3c) к
 * делителю (+0x14), кладёт целую часть в +0x48 и возвращает её как float; 1.0 если делитель 0. */
float nrlc_GetCurrentFrequency(void)
{
    const uintptr_t d = NRLC_ADDR_DDS;
    if (NRLC_R32(d + 0x14u) != 0u) {
        float a = (float)NRLC_R32(d + 0x3Cu);
        float b = (float)NRLC_R32(d + 0x14u);
        uint32_t q = (uint32_t)(a / b);
        NRLC_R32(d + 0x48u) = q;
        return (float)q;
    }
    return 1.0f;
}

/* [PORTED] FUN_08015de0: масштаб коррелятора = (float)(corr[+0x30] * 32767 * 0.5).
 * В листинге промежуточные значения double, итог приводится к float. */
float nrlc_CorrelatorScaleGetter(const uint32_t *corr)
{
    double d = (double)corr[0x30u / 4u];
    d = d * 32767.0;
    d = d * 0.5;
    return (float)d;
}

/* [PORTED] FUN_0800dbf8: перевод выхода коррелятора в калиброванный комплексный Z = U/I.
 * Вход - структура коррелятора (напр. 0x20007840): 64-битные аккумуляторы
 *   канал A: Re = [+0x08,+0x0c], Im = [+0x10,+0x14];  канал B: Re = [+0x20,+0x24], Im = [+0x28,+0x2c];
 *   масштаб от слова +0x30. Результат - пара float в 0x20004914+0x0c/+0x10 (т.е. 0x20004920/0x20004924),
 *   флаги 0x20004914 и 0x20004A4D взводятся в 1. */
void nrlc_ConvertCorrToPhysical(const uint32_t *corr)
{
    float g1    = nrlc_GetPGA_GainCh1();
    float g2    = nrlc_GetPGA_GainCh2();
    float calib = nrlc_GetRangeCalibConst();
    float k     = NRLC_RF(NRLC_ADDR_CAL_K) * 0.000244140625f;   /* 0x39800000 = 2^-12 */
    float n     = nrlc_CorrelatorScaleGetter(corr);
    float a_re  = nrlc_Int64ToFloat((int64_t)(((uint64_t)corr[3]  << 32) | corr[2]))  / n;
    float a_im  = nrlc_Int64ToFloat((int64_t)(((uint64_t)corr[5]  << 32) | corr[4]))  / n;
    float b_re  = nrlc_Int64ToFloat((int64_t)(((uint64_t)corr[9]  << 32) | corr[8]))  / n;
    float b_im  = nrlc_Int64ToFloat((int64_t)(((uint64_t)corr[11] << 32) | corr[10])) / n;
    nrlc_cplxf ca = nrlc_ComplexMultiply(a_re, a_im, k / g1, 0.0f);
    nrlc_cplxf cb = nrlc_ComplexMultiply(b_re, b_im, k / g2, 0.0f);
    nrlc_cplxf z  = nrlc_ComplexDivide(ca.re, ca.im, cb.re, cb.im);
    z = nrlc_ComplexMultiply(z.re, z.im, calib, 0.0f);

    NRLC_R8(NRLC_ADDR_ZRES) = 1u;
    NRLC_R8(NRLC_ADDR_FLAG_4A4D) = 1u;
    NRLC_RF(NRLC_ADDR_ZRES + 0x0Cu) = z.re;
    NRLC_RF(NRLC_ADDR_ZRES + 0x10u) = z.im;
}

/* [PORTED, частично выведено] FUN_08002ec0: третий вариант той же цепочки для буфера 0x20007C38.
 * Читает те же смещения структуры коррелятора, пишет два float прямо в неё: [0] и [6]
 * (амплитуда каналов A и B = 2*sqrt(re^2+im^2) после умножения на коэффициент 0x200048A8+0x20).
 * ЛИСТИНГ: часть аргументов комплексных умножений потеряна анализатором; мнимая часть множителя
 * принята 0.0, как в FUN_0800dbf8. FUN_080134b0 считается корнем (по использованию). */
void nrlc_ComputeCorrOutput_Buf2(uint32_t *buf)
{
    float n = nrlc_CorrelatorScaleGetter(buf);
    float a_re, a_im, b_re, b_im, kf;
    nrlc_cplxf ca, cb;
    float mag2;

    kf = NRLC_RF(NRLC_ADDR_CAL_K) * 1000.0f * 0.000244140625f;
    NRLC_RF(0x200048A8u + 0x20u) = kf;

    a_re = nrlc_Int64ToFloat((int64_t)(((uint64_t)buf[3]  << 32) | buf[2]))  / n;
    a_im = nrlc_Int64ToFloat((int64_t)(((uint64_t)buf[5]  << 32) | buf[4]))  / n;
    b_re = nrlc_Int64ToFloat((int64_t)(((uint64_t)buf[9]  << 32) | buf[8]))  / n;
    b_im = nrlc_Int64ToFloat((int64_t)(((uint64_t)buf[11] << 32) | buf[10])) / n;

    ca = nrlc_ComplexMultiply(a_re, a_im, kf, 0.0f);
    mag2 = ca.re * ca.re + ca.im * ca.im;
    ((float *)buf)[0] = (float)(FUN_080134b0(mag2) * 2.0);

    cb = nrlc_ComplexMultiply(b_re, b_im, kf, 0.0f);
    mag2 = cb.re * cb.re + cb.im * cb.im;
    ((float *)buf)[6] = (float)(FUN_080134b0(mag2) * 2.0);
}

/* [PORTED] FUN_08000dbe: читает REF (0x200049E4), считает значение стадии и пишет в структуру
 * 0x20005610 (+0x24, +0x2a, +0x34) и в 0x200048C0 (ограничение снизу значением из 0x200048C4). */
void nrlc_ReadREF_ComputeStageValue(void)
{
    const uintptr_t s = NRLC_ADDR_STAB;
    uint16_t u3 = NRLC_R16(0x200049B2u);
    uint16_t u8 = NRLC_R16(s + 0x28u);
    uint16_t u4 = (uint16_t)(NRLC_R32(NRLC_ADDR_REF) / ((uint32_t)u3 * (uint32_t)u8));
    uint16_t u10;
    uint8_t  b1;
    uint16_t u7;
    uint8_t  c2;
    int      z;
    uint8_t  b;
    uint16_t u8b;
    uint32_t u9, u11;

    NRLC_R16(s + 0x34u) = u4;
    u10 = (uint16_t)NRLC_R32(0x200049BCu);
    NRLC_R16(s + 0x24u) = 0xB54u;
    NRLC_R16(s + 0x2Au) = 0xC80u;

    b1 = NRLC_R8(s + 7u);
    u7 = b1;
    if (b1 != 0u) {
        u10 = (uint16_t)((uint32_t)u4 * u8);
        NRLC_R16(s + 0x34u) = u10;
    }

    c2 = NRLC_R8(s + 0xEu);
    z = (c2 == 0u);
    if (z) {
        c2 = NRLC_R8(s + 3u);
    }
    if (z && c2 == 0xFFu) {
        z = (NRLC_R8(s + 4u) == 0xFFu);
        if (z && b1 == 0u) {
            u7 = 1u;
            NRLC_R16(s + 0x34u) = u7;
        }
    }

    b = NRLC_R8(0x2000465Fu);
    u8b = b;
    if (b != 0u) {
        u8b = 2u;
        NRLC_R16(s + 0x34u) = u8b;
    }

    u9  = NRLC_R32(0x200048C4u);
    u11 = u9 * (((uint32_t)NRLC_R16(s + 0x34u) * (uint32_t)u3) / u9);
    NRLC_R32(0x200048C0u) = u11;
    if (u9 <= u11) {
        return;
    }
    NRLC_R32(0x200048C0u) = u9;
}

/* [PORTED] FUN_0800ef20: индекс i (0..6), для которого REF / table[i] == table[7]; 0xFF если нет.
 * table = 0x20007878 (8 слов). */
uint32_t nrlc_FindREFTableIndex(void)
{
    uint32_t i = 0u;
    do {
        if (NRLC_R32(NRLC_ADDR_REF) / NRLC_R32(NRLC_ADDR_REF_TABLE + i * 4u)
            == NRLC_R32(NRLC_ADDR_REF_TABLE + 0x1Cu)) {
            return i;
        }
        i = (i + 1u) & 0xFFu;
    } while (i < 7u);
    return 0xFFu;
}

/* [PORTED] FUN_08003940 (в FUNCTIONS.md описано только как поиск индекса - на деле стирает страницу):
 * найденный индекс i выбирает страницу флеша 0x0803C000 + i*0x800 (7 страниц настроек) и стирает её
 * (HAL_FLASHEx_Erase, 1 страница). Возврат 1 при успехе, иначе 0. */
uint32_t nrlc_FlashPageErase_ByREF(void)
{
    uint32_t i = 0u;
    do {
        if (NRLC_R32(NRLC_ADDR_REF) / NRLC_R32(NRLC_ADDR_REF_TABLE + i * 4u)
            == NRLC_R32(NRLC_ADDR_REF_TABLE + 0x1Cu)) {
            uint32_t erase[3];
            uint32_t page_error = 0u;
            uint32_t ok = 0u;
            if (i == 0xFFu) {
                return 0u;
            }
            FUN_08005c9c();                                         /* HAL_FLASH_Unlock */
            erase[0] = 0u;                                          /* TypeErase: страницы */
            erase[1] = NRLC_FLASH_SETTINGS_BASE + i * NRLC_FLASH_SETTINGS_PAGE;
            erase[2] = 1u;                                          /* NbPages */
            FUN_08005b2c(erase, &page_error);
            if (page_error == 0u) {
                ok = 1u;
            }
            FUN_08005bfc();                                         /* HAL_FLASH_Lock */
            return ok;
        }
        i = (i + 1u) & 0xFFu;
    } while (i < 7u);
    return 0u;
}

/* [PORTED] FUN_080039b0: то же определение страницы по REF, затем запись блока настроек
 * (0x244 байта из 0x20007878+0x1c) во флеш по словам (HAL_FLASH_Program, WORD). Возврат 1 при записи. */
uint32_t nrlc_FlashPageSave_ByREF(void)
{
    uint32_t i = 0u;
    do {
        if (NRLC_R32(NRLC_ADDR_REF) / NRLC_R32(NRLC_ADDR_REF_TABLE + i * 4u)
            == NRLC_R32(NRLC_ADDR_REF_TABLE + 0x1Cu)) {
            uint32_t off;
            if (i == 0xFFu) {
                return 0u;
            }
            FUN_08005c9c();                                         /* HAL_FLASH_Unlock */
            for (off = 0u; off < NRLC_SETTINGS_BLOB_SIZE; off += 4u) {
                FUN_08005c10(2u,
                             NRLC_FLASH_SETTINGS_BASE + i * NRLC_FLASH_SETTINGS_PAGE + off,
                             NRLC_R32(NRLC_ADDR_REF_TABLE + 0x1Cu + off),
                             0u);
            }
            FUN_08005bfc();                                         /* HAL_FLASH_Lock */
            return 1u;
        }
        i = (i + 1u) & 0xFFu;
    } while (i < 7u);
    return 0u;
}

/* [PORTED] FUN_0800fcf4: порог автовыключения (мс) в настройках 0x200056A0+0x2a;
 * при save != 0 дополнительно записывает значение через FUN_08004720 (запись параметра во флеш). */
void nrlc_SetAutoOffThreshold(uint16_t ms, int save)
{
    const uintptr_t s = NRLC_ADDR_SETTINGS;
    NRLC_R16(s + 0x2Cu) = 0u;
    NRLC_R16(s + 0x2Au) = ms;
    if (save == 0) {
        return;
    }
    FUN_08005c9c();
    FUN_08004720(NRLC_R16(0x08018C3Eu + 0x0Cu), NRLC_R16(s + 0x2Au));
    FUN_08005bfc();
}

/* [PORTED] FUN_08017dc8: контроль батареи. Читает ADC (хэндл 0x20006968), держит последнее
 * значение выше 2300, фильтрует (вес растёт 1..9 из 10), переводит в вольты формулой
 * f * 2^-12 * K * 147/100 * 4.07 / 3.95 / 4.22 * 4.2 (K = float по 0x20004998) и кладёт в +0x0c.
 * Если напряжение ниже 3.45 В более 100 вызовов подряд - FUN_0800ee00(1) (выключение). */
void nrlc_BatteryCalibConstants(void)
{
    const uintptr_t b = NRLC_ADDR_BATTERY;
    float raw = (float)nrlc_ADC_GetValue((void *)NRLC_ADDR_ADC4_HANDLE);
    float held;
    float volts;
    double acc;

    NRLC_RF(b + 0x10u) = raw;
    if (raw > 2300.0f) {                      /* 0x450FC000 */
        NRLC_RF(b + 0x08u) = raw;
        held = raw;
    } else {
        held = NRLC_RF(b + 0x08u);
        NRLC_RF(b + 0x10u) = held;
    }

    if (held > 0.0f) {
        double w_new, w_old;
        uint8_t n = NRLC_R8(b + 1u);
        if (n < 9u) {
            n = (uint8_t)(n + 1u);
            NRLC_R8(b + 1u) = n;
        }
        w_new = (double)(int32_t)(10 - (int32_t)n) * 0.1 * (double)held;
        w_old = (double)n * 0.1 * (double)NRLC_RF(b + 4u);
        NRLC_RF(b + 4u) = (float)(w_old + w_new);
    }

    acc = (double)NRLC_RF(b + 4u) * 0.000244140625;
    acc = acc * (double)NRLC_RF(NRLC_ADDR_CAL_K);
    acc = acc * 147.0;
    acc = acc / 100.0;
    acc = acc * 4.07;
    acc = acc / 3.95;
    acc = acc / 4.22;
    acc = acc * 4.2;
    volts = (float)acc;
    NRLC_RF(b + 0x0Cu) = volts;

    if (volts < 3.45f) {                      /* 0x405CCCCD */
        uint8_t cnt = (uint8_t)(NRLC_R8(b) + 1u);
        NRLC_R8(b) = cnt;
        if (cnt > 100u) {
            FUN_0800ee00(1);
        }
    } else {
        NRLC_R8(b) = 0u;
    }
}

/* [PORTED] FUN_08018158: установка частоты DAC (минимум 1000). Считает период в отсчётах
 * N = (частота выборки)/(частота), подбирает длину таблицы кратно N и строит таблицу синуса
 * амплитудой amp и смещением off в 0x20002EE0, затем вызывает функцию в CCM RAM.
 * Поля структуры 0x200049A8: int16[0]=смещение, [1]=амплитуда, [5]=длина таблицы, [6]=макс. длина;
 * +0x3c частота выборки, +0x4c = N, +0x50 = частота выборки / N.
 * ЛИСТИНГ: аргумент одного из преобразований (2*pi / ?) не виден, по смыслу это N;
 * FUN_080132d0 принята как преобразование double->int (способ округления не проверен). */
void nrlc_SetDACFrequency(uint32_t freq_hz)
{
    const uintptr_t s = NRLC_ADDR_DDS;
    volatile int16_t *ps = (volatile int16_t *)s;
    uint32_t rate, n, maxlen, q, k, i;
    double step;
    int16_t *table = (int16_t *)NRLC_ADDR_DDS_TABLE;

    if (freq_hz < 1000u) {
        freq_hz = 1000u;
    }
    rate = NRLC_R32(s + 0x3Cu);
    n = (uint32_t)((float)rate / (float)freq_hz);
    NRLC_R32(s + 0x4Cu) = n;

    maxlen = (uint16_t)ps[6];
    q = (n != 0u) ? (maxlen / n) : 0u;
    if (n < maxlen) {
        ps[5] = (int16_t)((int16_t)n * (int16_t)q);
    } else {
        uint32_t u8v;
        int carry, nz;
        k = (uint8_t)q;
        ps[5] = (int16_t)(n * k);
        if (n < ((n * k) & 0xFFFFu)) {
            do {
                uint32_t u1;
                u8v = (n * k) & 0xFFFFu;
                ps[5] = (int16_t)(n * k);
                k = (k - 1u) & 0xFFu;
                u1 = (uint32_t)(((uint64_t)0x51EB851Fu * u8v) >> 37) * (uint32_t)(-100);
                carry = ((uint64_t)u8v + u1) > 0xFFFFFFFFull;
                nz = (uint32_t)(u8v + u1) != 0u;
                if (nz) {
                    carry = (n <= u8v);
                }
            } while (carry && nz && (u8v != n));
        }
    }
    if (ps[5] == 0) {
        ps[5] = (int16_t)n;
    }
    NRLC_R32(s + 0x50u) = (n != 0u) ? (rate / n) : 0u;

    step = 6.283185307179586 / (double)n;     /* ЛИСТИНГ: делитель выведен как N */
    for (i = 0u; (int32_t)i < (int32_t)((uint16_t)ps[5]) - 1; i++) {
        uint32_t idx = (n != 0u) ? (i - n * (i / n)) : 0u;
        float x = (float)((double)idx * step);
        double amp_sin = (double)(uint32_t)(int32_t)ps[1] * (double)nrlc_SinTableLookup(x);
        int16_t v = (int16_t)FUN_080132d0(amp_sin);
        table[i & 0xFFFFu] = (int16_t)(v + ps[0]);
    }
    thunk_EXT_FUN_10000000();
}

/* [PORTED] FUN_0800ae7c: выбор диапазона - выдаёт команду в PGA113 (0x2A01 | код<<4) по
 * 3-проводному протоколу с выбором линии CS. u_channel != 0: CS = PB10 (U_CS), иначе PB2 (I_CS).
 * Повторно не отправляет, если код не изменился. ЛИСТИНГ: в первой ветке третий аргумент
 * снятия CS не виден, принят 1 (как во второй ветке). */
void nrlc_RangeRelayControl(int u_channel, uint32_t code)
{
    uint8_t *st = (uint8_t *)NRLC_ADDR_RELAY_STATE;
    uint32_t sh = (code & 0xFu) << 4;
    uint8_t  b  = (uint8_t)code;

    if (u_channel != 0) {
        NRLC_R8(NRLC_ADDR_RELAY_CMD_A) = b;
        if ((uint32_t)st[0] != code) {
            nrlc_GPIO_WriteBit((void *)GPIOB, 0x400u, 0);
            FUN_08012764(sh | 0x2A01u);
            nrlc_GPIO_WriteBit((void *)GPIOB, 0x400u, 1);
        }
        st[0] = b;
        return;
    }
    NRLC_R8(NRLC_ADDR_RELAY_CMD_B) = b;
    if ((uint32_t)st[1] != code) {
        nrlc_GPIO_WriteBit((void *)GPIOB, 4u, 0);
        FUN_08012764(sh | 0x2A01u);
        nrlc_GPIO_WriteBit((void *)GPIOB, 4u, 1);
    }
    st[1] = b;
}

/* [PORTED] FUN_0800ade8: посимвольный вывод строки на экран через FUN_08009428.
 * В режиме 2 символ '.' сдвигает позицию X (+8 в 0x2000570C) на -2 до символа и ещё на -5 после
 * (по модулю 0x400). Возврат: 1, если вывод прервала FUN_08009428, иначе 0. */
uint32_t nrlc_PrintCharToScreenBuffer(int mode, const char *s)
{
    const uintptr_t scr = NRLC_ADDR_SCREEN_STATE;
    uint32_t i = 0u;
    for (;;) {
        char c = s[i];
        uint32_t r;
        if (c == '\0') {
            return 0u;
        }
        if (mode == 2 && c == '.' && i != 0u) {
            NRLC_R32(scr + 8u) = (uint32_t)(((int32_t)NRLC_R32(scr + 8u) - 2) % 0x400);
        }
        r = FUN_08009428(mode, (uint8_t)s[i]);
        if (mode == 2 && c == '.') {
            NRLC_R32(scr + 8u) = (uint32_t)(((int32_t)NRLC_R32(scr + 8u) - 5) % 0x400);
        }
        if (r == 1u) {
            break;
        }
        i = (i + 1u) & 0xFFu;
    }
    return 1u;
}

/* [PORTED] FUN_08015ff0 (в FUNCTIONS.md называлась WriteStringToScreenBuffer; по листингу это
 * программный I2C-мастер на GPIOB: PB6 = SCL (0x40), PB7 = SDA (0x80)). Каждый байт - 8 бит
 * старшим вперёд, затем ACK; при NACK выдаётся STOP и возвращается 0. Всё прошло - 1.
 * ВНИМАНИЕ: раньше PB6/PB7 считались не подключёнными - расхождение надо разобрать. */
uint32_t nrlc_I2C_WriteBytes_BitBang(const uint8_t *data, int len)
{
    void *gpio = (void *)GPIOB;

    while (len != 0) {
        uint32_t byte = *data;
        int bit;
        for (bit = 0; bit < 8; bit++) {
            nrlc_GPIO_WriteBit(gpio, 0x40u, 0);
            NRLC_TINY_DELAY();
            nrlc_GPIO_WriteBit(gpio, 0x80u, (byte & 0x80u) != 0u);
            byte = (byte & 0x7Fu) << 1;
            NRLC_TINY_DELAY();
            nrlc_GPIO_WriteBit(gpio, 0x40u, 1);
            NRLC_TINY_DELAY();
        }
        nrlc_GPIO_WriteBit(gpio, 0x40u, 0);
        nrlc_GPIO_WriteBit(gpio, 0x40u, 0);
        NRLC_TINY_DELAY();
        nrlc_GPIO_WriteBit(gpio, 0x80u, 1);          /* отпустить SDA для ACK */
        NRLC_TINY_DELAY();
        nrlc_GPIO_WriteBit(gpio, 0x40u, 1);
        NRLC_TINY_DELAY();
        if (nrlc_GPIO_ReadBit(gpio, 0x80u) != 0u) {  /* NACK -> STOP */
            nrlc_GPIO_WriteBit(gpio, 0x40u, 0);
            nrlc_GPIO_WriteBit(gpio, 0x40u, 0);
            NRLC_TINY_DELAY();
            nrlc_GPIO_WriteBit(gpio, 0x80u, 0);
            NRLC_TINY_DELAY();
            nrlc_GPIO_WriteBit(gpio, 0x40u, 1);
            NRLC_TINY_DELAY();
            nrlc_GPIO_WriteBit(gpio, 0x80u, 1);
            NRLC_TINY_DELAY();
            return 0u;
        }
        nrlc_GPIO_WriteBit(gpio, 0x40u, 0);
        len--;
        data++;
    }
    return 1u;
}

/* ================================================================== */
/* Крупные функции [STUB]: тело ещё нужно переносить                   */
/* ================================================================== */

/* [STUB] FUN_08000618: диспетчер стадий измерения (switch по байту состояния над 0x20005610);
 * case 6 вызывает FUN_08000f52. 143 строки листинга. Раздел 6.13. */
void nrlc_MeasurementStageDispatcher(void) { /* TODO */ }

/* [STUB] FUN_08000270: разбор входящих команд (case 0x8b..0x8e: setDACfreq/setDACperiod/autofreq и др.).
 * 159 строк листинга. Разделы 6.25, 6.26. */
void nrlc_CommandDispatcher_Parser(void) { /* TODO */ }

/* [STUB] FUN_08000f52: оркестратор одного цикла измерения (~1100 строк листинга): два вызова
 * nrlc_ConvertCorrToPhysical (буферы 0x20007840 и 0x20007c70), дельта previous/current
 * (0x20005610+0x48/+0x50), автодиапазон, оценка стабильности, вызов отрисовки. Разделы 6.12, 6.13. */
void nrlc_MeasurementOrchestrator(float arg) { (void)arg; /* TODO */ }

/* [STUB] FUN_08009618: отрисовка результата (~830 строк листинга): читает структуру 0x20004A48
 * (Rs/Rp/L/C/Z), содержит блоки сглаживания. Разделы 6.11, 6.22. */
void nrlc_DisplayRefresh_DrawResult(void) { /* TODO */ }

/* [STUB] FUN_08016274: эквивалент main(): инициализация всей периферии (~1600 строк листинга). Раздел 2.
 * В новом проекте это делает код CubeMX. */
void nrlc_MainApplicationInit(void) { /* TODO */ }

/* [STUB] FUN_0800ff78: обработчик TIM7 (IRQ 55): таймаут автовыключения, долгое удержание кнопок,
 * антидребезг (~360 строк листинга). Разделы 6.3, 6.5. Вызывается из nrlc_SysTick_Handler_body. */
void nrlc_TIM7_ISR(void) { /* TODO */ }

/* [STUB, частично] FUN_0800d578: формула Rs/Rp/L/C. Начало повторяет nrlc_ConvertCorrToPhysical,
 * но пишет результат в 0x20004914+0x14/+0x18 (0x20004928); дальше R/L/C-формулы и запись в структуру
 * 0x20004A48. Листинг сильно искажён (потеряны аргументы в регистрах, условия через флаги
 * сравнения FUN_08002958/FUN_08002988), поэтому тело не переносилось. Разделы 6.23, 6.27. */
void nrlc_FormulaRsRpLC(const uint32_t *corr, int alt_flag) { (void)corr; (void)alt_flag; /* TODO */ }

/* [STUB] FUN_08017f70: поиск частоты для autofreq (критерий round(REF/candidate) < 3)
 * и построение отчёта. 107 строк листинга. Раздел 6.26. */
void nrlc_AutoFreqSearchAndReportBuilder(void) { /* TODO */ }

/* [STUB] FUN_08002d48: ARM scatter-load: обход таблицы из 3 записей {src,dest,len,fn}
 * (.data сжата, CCM RAM копируется, .bss обнуляется). Раздел 2. В новом проекте это
 * делает стартовый код и скрипт линковки. */
void nrlc_ScatterLoad_Init(void) { /* TODO: не нужно в новом проекте */ }

/* [STUB] 0x100001B8 (флеш-зеркало 0x0802D994): ядро корреляции на ассемблере в CCM RAM
 * (~2400 байт, несколько встроенных литерал-пулов). Раздел 6.7. Листинга нет. */
void nrlc_CorrelatorCore_CCM(void) { /* TODO */ }

/* [STUB] 0x10000B5C: переключение PB6/PB7 между push-pull и open-drain (ассемблер в CCM RAM).
 * Раздел 4.3. Листинга нет. */
void nrlc_GPIOB_Toggle_Inert(void) { /* TODO */ }

/* [STUB] 0x10000BC0: неблокирующий драйвер пищалки PA8/ZP (ассемблер в CCM RAM). Раздел 4.3. Листинга нет. */
void nrlc_BuzzerDriver(uint32_t ms) { (void)ms; /* TODO */ }
