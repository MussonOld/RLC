# -*- coding: utf-8 -*-
"""Сравнение оригинала из образа с переносом на C (src/nrlc_funcs.c) в эмуляторе. Запуск: python3 run_checks.py [N]"""
import sys, struct, random
import harness as h
from unicorn.arm_const import *

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
rnd = random.Random(12345)
STAB, PGA, DDS, REFA, RTAB, SYS, BAT, SET = 0x20005610, 0x20005650, 0x200049A8, 0x200049E4, 0x20007878, 0x20004788, 0x200056D0, 0x200056A0
results = []

def run(name, orig, port, make, **kw):
    bad = 0; first = None
    for i in range(N):
        setup, args, fargs = make(i)
        try:
            ok, notes = h.compare(orig, port, setup, args=args, fargs=fargs, **kw)
        except Exception as e:
            ok, notes = False, ["EXC " + repr(e)]
        if not ok:
            bad += 1
            if first is None: first = notes
    results.append((name, N - bad, N, first))
    print("%-34s %3d/%-3d %s" % (name, N - bad, N, "" if not bad else "  <- " + str(first)[:230]))

def fl(lo=-1e3, hi=1e3): return rnd.uniform(lo, hi)

def setup_pga(m):
    for i in range(8): m.w8(PGA + i, rnd.randint(1, 200))
    m.w8(STAB + 0x10, rnd.randint(0, 9)); m.w8(STAB + 0x11, rnd.randint(0, 9))
    m.w8(STAB + 0xF, rnd.choice([0, 1, 2, 7])); m.w16(STAB + 0x20, rnd.randint(0, 65535))
    m.wf(0x20004998, fl(0.1, 10))

def corr(m, base=0x20007840):
    for off in (0x08, 0x10, 0x20, 0x28):
        v = rnd.randint(-2**40, 2**40) & 0xFFFFFFFFFFFFFFFF
        m.w32(base + off, v & 0xFFFFFFFF); m.w32(base + off + 4, v >> 32)
    m.w32(base + 0x30, rnd.randint(1, 100000))

def mk(f):   # обёртка: фиксирует случайное состояние один раз на кейс, чтобы оригинал и перенос видели одно и то же
    def make(i):
        r = random.Random(1000 + i); st = {}
        def setup(m):
            global rnd
            save = rnd; rnd = random.Random(1000 + i)
            try: f(m)
            finally: rnd = save
        return setup, *f.__annotations__.get("ret", ((), ()))
    return make

def case(f, args=(), fargs=()):
    def make(i):
        def setup(m):
            global rnd
            save = rnd; rnd = random.Random(7000 + i)
            try: f(m)
            finally: rnd = save
        a = args(i) if callable(args) else args
        fa = fargs(i) if callable(fargs) else fargs
        return setup, a, fa
    return make

def main():
    h.init()
    run("GetPGA_GainCh1", 0x08000D5A, "nrlc_GetPGA_GainCh1", case(setup_pga), compare_r0=False, compare_s0=True)
    run("GetPGA_GainCh2", 0x08000D7C, "nrlc_GetPGA_GainCh2", case(setup_pga), compare_r0=False, compare_s0=True)
    run("GetRangeCalibConst", 0x08000D9E, "nrlc_GetRangeCalibConst", case(setup_pga), compare_r0=False, compare_s0=True)
    def s_freq(m): m.w32(DDS + 0x14, rnd.choice([0, rnd.randint(1, 5000)])); m.w32(DDS + 0x3C, rnd.randint(1000, 4000000))
    run("GetCurrentFrequency", 0x080006A8, "nrlc_GetCurrentFrequency", case(s_freq), compare_r0=False, compare_s0=True)
    def s_corr(m): corr(m)
    run("CorrelatorScaleGetter", 0x08015DE0, "nrlc_CorrelatorScaleGetter", case(s_corr, args=(0x20007840,)), compare_r0=False, compare_s0=True)
    def s_ref(m):
        t = [rnd.randint(1, 1000) for _ in range(7)]
        r = rnd.randint(1, 100000)
        for i, v in enumerate(t): m.w32(RTAB + 4 * i, v)
        m.w32(REFA, r)
        m.w32(RTAB + 0x1C, (r // t[rnd.randint(0, 6)]) if rnd.random() < 0.8 else rnd.randint(0, 1000))
        for off in range(0x20, 0x260, 4): m.w32(RTAB + off, rnd.getrandbits(32))
    run("FindREFTableIndex", 0x0800EF20, "nrlc_FindREFTableIndex", case(s_ref))
    run("FlashPageErase_ByREF", 0x08003940, "nrlc_FlashPageErase_ByREF", case(s_ref))
    run("FlashPageSave_ByREF", 0x080039B0, "nrlc_FlashPageSave_ByREF", case(s_ref))
    def s_stage(m):
        m.w16(0x200049B2, rnd.randint(1, 2000)); m.w16(STAB + 0x28, rnd.randint(1, 100)); m.w32(REFA, rnd.randint(0, 10**7))
        for off in (7, 0xE, 3, 4): m.w8(STAB + off, rnd.choice([0, 255, rnd.randint(0, 255)]))
        m.w8(0x2000465F, rnd.choice([0, 1])); m.w32(0x200048C4, rnd.randint(1, 5000)); m.w32(0x200049BC, rnd.getrandbits(32))
        m.w16(STAB + 0x34, rnd.getrandbits(16))
    run("ReadREF_ComputeStageValue", 0x08000DBE, "nrlc_ReadREF_ComputeStageValue", case(s_stage), compare_r0=False)
    def s_conv(m): setup_pga(m); corr(m)
    run("ConvertCorrToPhysical", 0x0800DBF8, "nrlc_ConvertCorrToPhysical", case(s_conv, args=(0x20007840,)), compare_r0=False)
    def s_conv2(m): setup_pga(m); corr(m, 0x20007C38)
    run("ComputeCorrOutput_Buf2", 0x08002EC0, "nrlc_ComputeCorrOutput_Buf2", case(s_conv2, args=(0x20007C38,)), compare_r0=False)
    run("ComplexMultiply", 0x08012A04, "nrlc_ComplexMultiply", case(lambda m: None, fargs=lambda i: [fl(), fl(), fl(), fl()]), compare_r0=False, pair=True)
    run("ComplexDivide", 0x080129E2, "nrlc_ComplexDivide", case(lambda m: None, fargs=lambda i: [fl(), fl(), fl(0.5, 100), fl(0.5, 100)]), compare_r0=False, pair=True)
    run("SinTableLookup", 0x08013FFC, "nrlc_SinTableLookup", case(lambda m: None, fargs=lambda i: [fl(-50, 50)]), compare_r0=False, compare_s0=True)

    # ---------- вторая партия: периферия и состояние ----------
    GPIOB, GPIOA = 0x48000400, 0x48000000
    def s_nvic(m):
        m.w32(0xE000ED0C, (0x05FA << 16) | (rnd.randint(0, 7) << 8))
    run("NVIC_SetPriority", 0x0800606C, "nrlc_NVIC_SetPriority", case(s_nvic, args=lambda i: (random.Random(i).randint(0, 80), random.Random(i + 1).randint(0, 15), random.Random(i + 2).randint(0, 3))), compare_r0=False)
    run("NVIC_EnableIRQ", 0x0800604E, "nrlc_NVIC_EnableIRQ", case(lambda m: None, args=lambda i: (random.Random(i).randint(-2, 90),)), compare_r0=False)
    def s_gpio(m): m.w32(GPIOB + 0x10, rnd.getrandbits(16))
    run("GPIO_ReadBit", 0x08005EFC, "nrlc_GPIO_ReadBit", case(s_gpio, args=lambda i: (GPIOB, 1 << random.Random(i).randint(0, 15))))
    run("GPIO_WriteBit", 0x08005F06, "nrlc_GPIO_WriteBit", case(s_gpio, args=lambda i: (GPIOB, 1 << random.Random(i).randint(0, 15), random.Random(i + 5).choice([0, 1, 2]))), compare_r0=False)
    def s_adc(m): m.w32(0x20006968, 0x50000000); m.w32(0x50000040, rnd.getrandbits(32))
    run("ADC_GetValue", 0x08005148, "nrlc_ADC_GetValue", case(s_adc, args=(0x20006968,)))
    def s_usb(m): m.w16(0x40005C44, rnd.getrandbits(16)); m.w16(0x40005C40, rnd.getrandbits(16))
    run("USB_EnableGlobalInt", 0x080126D0, "nrlc_USB_EnableGlobalInt", case(s_usb, args=(0x40005C00,)))
    run("USB_ReadInterrupts", 0x080126F0, "nrlc_USB_ReadInterrupts", case(s_usb, args=(0x40005C00,)), compare_r0=True)
    def s_delay(m): m.w32(SYS, rnd.choice([72000000, 60000000, 48000000, 36000000, 24000000, 8000000]))
    run("SoftwareDelay_ms", 0x080154C8, "nrlc_SoftwareDelay_ms", case(s_delay, args=lambda i: (random.Random(i).randint(0, 3),)), compare_r0=False)
    def s_aoff(m): m.w16(SET + 0x2A, rnd.getrandbits(16)); m.w16(SET + 0x2C, rnd.getrandbits(16))
    run("SetAutoOffThreshold", 0x0800FCF4, "nrlc_SetAutoOffThreshold", case(s_aoff, args=lambda i: (random.Random(i).randint(0, 65535), random.Random(i + 3).choice([0, 1]))), compare_r0=False)
    def s_dac(m):
        m.w32(0x20006000, 0x40007400); m.w8(0x20006004, rnd.randint(0, 3)); m.w8(0x20006005, rnd.choice([0, 1]))
        m.w32(0x40007400, rnd.getrandbits(32)); m.w32(0x20006100, rnd.choice([0, 0x4, 0x24, 0x1C])); m.w32(0x20006104, rnd.choice([0, 2]))
    run("DAC_ConfigChannel", 0x08005798, "nrlc_DAC_ConfigChannel", case(s_dac, args=lambda i: (0x20006000, 0x20006100, random.Random(i).choice([0, 16]))))
    def s_timclk(m):
        m.w32(0x20006000, random.Random(rnd.random()).choice([0x40012C00, 0x40000000, 0x40000400, 0x40000800, 0x40001400, 0x40014400, 0x40001000]))
        m.w32(0x40021018, rnd.getrandbits(32)); m.w32(0x4002101C, rnd.getrandbits(32)); m.w32(0xE000ED0C, 0x05FA0000 | (rnd.randint(0, 7) << 8))
    run("TimerClockEnable", 0x08007944, "nrlc_TimerClockEnable", case(s_timclk, args=(0x20006000,)), compare_r0=False)
    def s_tim6(m): m.w32(SYS, rnd.choice([72000000, 48000000, 24000000, 8000000])); m.w32(0x40021000 + 0x1C, rnd.getrandbits(32)); m.w32(0xE000ED0C, 0x05FA0000)
    run("TIM6_FullInit", 0x08003428, "nrlc_TIM6_FullInit", case(s_tim6), compare_r0=False)
    def s_spi(m): m.w32(0x20006000, 0x40013000); [m.w32(0x20006000 + 4 * i, rnd.getrandbits(32)) for i in range(1, 40)]; m.w32(0x40021018, rnd.getrandbits(32)); m.w32(0x40021014, rnd.getrandbits(32))
    run("SPI1_MspInit", 0x08007298, "nrlc_SPI1_MspInit", case(s_spi, args=(0x20006000,)), compare_r0=False)
    def s_usart(m): m.w32(0x20006000, 0x40013800); [m.w32(0x20006000 + 4 * i, rnd.getrandbits(32)) for i in range(1, 40)]; m.w32(0x40021018, rnd.getrandbits(32)); m.w32(0x40021014, rnd.getrandbits(32)); m.w32(0xE000ED0C, 0x05FA0000 | (rnd.randint(0, 7) << 8))
    run("USART1_MspInit", 0x080087F8, "nrlc_USART1_MspInit", case(s_usart, args=(0x20006000,)), compare_r0=False)
    def s_systick(m):
        for off in (0x24, 0x30, 0x1E, 0x22, 0x26, 0x20, 0x28, 0x2E): m.w16(0x20004650 + off, rnd.choice([0, 1, 2, 3, 9, 10, 299, 300, rnd.getrandbits(16)]))
        for off in (0, 3, 4, 8, 9, 10, 0xF): m.w8(0x20004650 + off, rnd.choice([0, 1, 4, 5, 255]))
        m.w32(0x20004650 + 0x78, rnd.choice([0, 0xFFFFFFFF, rnd.getrandbits(32)])); m.w32(0x20004650 + 0x7C, rnd.getrandbits(32))
        m.w32(0x40021014, rnd.getrandbits(32)); m.w32(0xE000ED0C, 0x05FA0000)
    run("SysTick_Handler_body", 0x0800019C, "nrlc_SysTick_Handler_body", case(s_systick), compare_r0=False)
    def s_dacf(m):
        m.w16(DDS + 0, rnd.randint(0, 2048)); m.w16(DDS + 2, rnd.randint(0, 2000)); m.w16(DDS + 0xC, rnd.randint(200, 3400))
        m.w32(DDS + 0x3C, rnd.choice([3000000, 1000000, 2000000, rnd.randint(100000, 4000000)]))
    run("SetDACFrequency", 0x08018158, "nrlc_SetDACFrequency", case(s_dacf, args=lambda i: (random.Random(i).choice([0, 500, 1000, 1234, 5000, 10000, 12345, 50000, 100000, 250000]),)), compare_r0=False)
    def s_bat(m):
        m.w32(0x20006968, 0x50000300); m.w32(0x50000340, rnd.choice([0, 1800, 2200, 2400, 3000, 3500, 4095]))
        m.w8(BAT + 0, rnd.randint(0, 50)); m.w8(BAT + 1, rnd.randint(0, 12))
        m.wf(BAT + 4, fl(0, 4000)); m.wf(BAT + 8, fl(2300, 4095)); m.wf(BAT + 0xC, fl(0, 5)); m.wf(BAT + 0x10, fl(0, 4095)); m.wf(0x20004998, fl(0.5, 3))
    run("BatteryCalibConstants", 0x08017DC8, "nrlc_BatteryCalibConstants", case(s_bat), compare_r0=False)
    def s_print(m):
        txt = bytes(random.Random(rnd.random()).choice(b"0123456789.AB-") for _ in range(rnd.randint(1, 7))) + b"\0"
        m.write(0x20006400, txt); m.w32(0x2000570C + 8, rnd.randint(0, 1023))
        for off in range(0, 0x40, 4): m.w32(0x2000570C + 0xC + off, rnd.getrandbits(32))
    run("PrintCharToScreenBuffer", 0x0800ADE8, "nrlc_PrintCharToScreenBuffer", case(s_print, args=lambda i: (random.Random(i).choice([0, 1, 2]), 0x20006400)))
    def s_relay(m): m.w8(0x20004AF4, rnd.randint(0, 255)); m.w8(0x20004AF5, rnd.randint(0, 255)); m.w32(GPIOB + 0x14, rnd.getrandbits(16))
    run("RangeRelayControl", 0x0800AE7C, "nrlc_RangeRelayControl", case(s_relay, args=lambda i: (random.Random(i).choice([0, 1]), random.Random(i + 9).randint(0, 20))), compare_r0=False)
    def s_i2c(m):
        m.write(0x20006400, bytes(random.Random(rnd.random()).getrandbits(8) for _ in range(4))); m.w32(GPIOB + 0x10, rnd.choice([0, 0x80]))
    run("I2C_WriteBytes_BitBang", 0x08015FF0, "nrlc_I2C_WriteBytes_BitBang", case(s_i2c, args=lambda i: (0x20006400, random.Random(i).randint(1, 3))))
    def s_scat(m):
        pass
    run("ScatterLoad_PlainCopy", 0x08013690, "nrlc_ScatterLoad_PlainCopy", case(s_scat, args=lambda i: (0x0802D7DC, 0x20003000, 4 * random.Random(i).randint(1, 40))), compare_r0=False)
    # USB
    def s_usbd(m):
        m.w32(0x20006200, 0x40005C00); m.w32(0x20006200 + 0x18, rnd.choice([0, 1])); m.w32(0x20006200 + 0x2E8, 0x20006800)
        m.w8(0x20006800 + 0x29C, rnd.randint(0, 5)); m.w8(0x20006800 + 0x29D, rnd.randint(0, 5)); m.w32(0x20006800 + 0x2B4, 0x20006900)
        m.w32(0x20006900 + 0x1C, rnd.choice([0, 0x0800FCF5])); m.w32(0xE000ED10, rnd.getrandbits(32))
        m.w16(0x40005C44, rnd.getrandbits(16) & 0x7FFF); m.w16(0x40005C40, rnd.getrandbits(16)); m.w8(0x20006200 + 0x2A8, rnd.choice([0, 1]))
    run("USB_ResumeCallback", 0x080065C2, "nrlc_USB_ResumeCallback", case(s_usbd, args=(0x20006200,)))
    PROBE = 0x08FF0100
    def s_sof(m):
        s_usbd(m)
        m.write(PROBE, struct.pack("<HHHH", 0x4A01, 0x6010, 0x4770, 0xBF00) + struct.pack("<I", 0x20006F00))   # записывает r0 в 0x20006F00
        m.w8(0x20006800 + 0x29C, rnd.choice([3, 3, 3, 1])); m.w32(0x20006900 + 0x1C, rnd.choice([0, PROBE | 1]))
    run("USB_SOF_Callback", 0x080065CA, "nrlc_USB_SOF_Callback", case(s_sof, args=(0x20006200,)))
    run("USB_SuspendCallback", 0x0800663C, "nrlc_USB_SuspendCallback", case(s_usbd, args=(0x20006200,)), compare_r0=False)
    run("USB_IRQHandler_main", 0x08006328, "nrlc_USB_IRQHandler_main", case(s_usbd, args=(0x20006200,)), compare_r0=False)
    # арифметика компилятора: оригинал берёт аргументы в r0..r3, перенос (hard-float) - в d0/d1
    import struct as st
    def lib_dbl(name, orig, port, op):
        bad = 0; first = None
        for i in range(N):
            r = random.Random(500 + i)
            a, b = r.uniform(-1e6, 1e6), r.uniform(-1e6, 1e6) or 1.0
            al, ah = st.unpack("<II", st.pack("<d", a)); bl, bh = st.unpack("<II", st.pack("<d", b))
            mo = h.Machine(h.PORT[0]); mp = h.Machine(h.PORT[0])
            ro = h.call_regs(mo, orig, {UC_ARM_REG_R0: al, UC_ARM_REG_R1: ah, UC_ARM_REG_R2: bl, UC_ARM_REG_R3: bh})
            # перенос вызывается через небольшой тест-шим: аргументы double по соглашению компилятора (r0..r3)
            rp = h.call_regs(mp, h.PORT[1][port + "__shim"], {UC_ARM_REG_R0: al, UC_ARM_REG_R1: ah, UC_ARM_REG_R2: bl, UC_ARM_REG_R3: bh}) if (port + "__shim") in h.PORT[1] else None
            if rp is None: first = "нет шима"; bad = N; break
            if (ro["r0"], ro["r1"]) != (rp["r0"], rp["r1"]):
                bad += 1; first = first or "orig %08x%08x port %08x%08x" % (ro["r1"], ro["r0"], rp["r1"], rp["r0"])
        results.append((name, N - bad, N, first)); print("%-34s %3d/%-3d %s" % (name, N - bad, N, "" if not bad else "  <- " + str(first)[:160]))

    import struct as st
    def lib(name, orig, port, regs, cmp_keys, tag=None):
        bad = 0; first = None
        for i in range(N):
            rr = random.Random(900 + i); R = regs(rr)
            mo = h.Machine(h.PORT[0]); mp = h.Machine(h.PORT[0])
            ro = h.call_regs(mo, orig, R[0]); rp = h.call_regs(mp, h.PORT[1][port], R[1])
            for k in cmp_keys:
                if ro[k[0]] != rp[k[1]]:
                    bad += 1; first = first or "orig %s=%08x port %s=%08x" % (k[0], ro[k[0]], k[1], rp[k[1]]); break
        results.append((name, N - bad, N, first)); print("%-34s %3d/%-3d %s" % (name, N - bad, N, "" if not bad else "  <- " + str(first)[:200]))
    def dbl2(rr):
        a, b = rr.uniform(-1e6, 1e6), rr.choice([rr.uniform(-1e6, 1e6), 1.0, 3.0]) or 1.0
        al, ah = st.unpack("<II", st.pack("<d", a)); bl, bh = st.unpack("<II", st.pack("<d", b))
        d = {UC_ARM_REG_R0: al, UC_ARM_REG_R1: ah, UC_ARM_REG_R2: bl, UC_ARM_REG_R3: bh}
        p = {UC_ARM_REG_D0: (ah << 32) | al, UC_ARM_REG_D1: (bh << 32) | bl}   # перенос: double в d0/d1, результат в d0
        return d, p
    lib("DoubleMultiply", 0x08002698, "nrlc_DoubleMultiply", dbl2, [("r0", "d0lo"), ("r1", "d0hi")])
    lib("DoubleDivide", 0x0800277C, "nrlc_DoubleDivide", dbl2, [("r0", "d0lo"), ("r1", "d0hi")])
    lib("DoubleAdd", 0x0800254A, "nrlc_DoubleAdd", dbl2, [("r0", "d0lo"), ("r1", "d0hi")])
    def u64(rr):
        n = rr.getrandbits(rr.choice([8, 32, 63])); d = rr.getrandbits(rr.choice([4, 16, 31, 40])) or 1
        d = {UC_ARM_REG_R0: n & 0xFFFFFFFF, UC_ARM_REG_R1: n >> 32, UC_ARM_REG_R2: d & 0xFFFFFFFF, UC_ARM_REG_R3: d >> 32}
        return d, d
    lib("UnsignedDiv64", 0x080023DC, "nrlc_UnsignedDiv64", u64, [("r0", "r0"), ("r1", "r1")])
    def s64(rr):
        n = rr.randint(-2**62, 2**62); d = rr.choice([-1, 1]) * (rr.getrandbits(rr.choice([4, 16, 31, 40])) or 1)
        n &= 0xFFFFFFFFFFFFFFFF; d &= 0xFFFFFFFFFFFFFFFF
        d = {UC_ARM_REG_R0: n & 0xFFFFFFFF, UC_ARM_REG_R1: n >> 32, UC_ARM_REG_R2: d & 0xFFFFFFFF, UC_ARM_REG_R3: d >> 32}
        return d, d
    lib("SignedDiv64", 0x0800243E, "nrlc_SignedDiv64", s64, [("r0", "r0"), ("r1", "r1")])
    def f2d(rr):
        x = rr.uniform(-1e9, 1e9); b = st.unpack("<I", st.pack("<f", x))[0]
        return {UC_ARM_REG_R0: b}, {UC_ARM_REG_S0: b}
    lib("FloatToDouble", 0x08002932, "nrlc_FloatToDouble", f2d, [("r0", "d0lo"), ("r1", "d0hi")])
    def l2f(rr):
        v = rr.randint(-2**62, 2**62) & 0xFFFFFFFFFFFFFFFF
        d = {UC_ARM_REG_R0: v & 0xFFFFFFFF, UC_ARM_REG_R1: v >> 32}
        return d, d
    lib("Int64ToFloat", 0x0800285A, "nrlc_Int64ToFloat", l2f, [("r0", "s0")])
    print("\nИтого функций с расхождениями:", sum(1 for r in results if r[1] != r[2]), "из", len(results))

if __name__ == "__main__":
    main()
    import datetime
    with open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "RESULTS.md"), "w", encoding="utf-8") as f:
        f.write("# Результаты сравнения переноса на C с оригиналом (эмулятор)\n\n")
        f.write("Случайных наборов на функцию: %d. Эмулятор: Unicorn 2.1.3, Cortex-M4. Версия 2.1.4 исполняет часть кода неверно (IT-блок перед условным переходом), её использовать нельзя.\n\n" % N)
        f.write("| Функция | Совпало | Замечание |\n|---|---|---|\n")
        for n, ok, tot, first in results:
            f.write("| %s | %d/%d | %s |\n" % (n, ok, tot, "" if ok == tot else str(first).replace("|", "/")[:160]))
        f.write("\nНе покрыто проверкой: заглушки и функции-эквиваленты HAL, USB_CTR/TIM7/main/оркестратор/отрисовка, код в CCM RAM, DoubleCompareGE (результат через флаги).\n")
