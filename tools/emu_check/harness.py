# -*- coding: utf-8 -*-
"""
Проверка переноса на C без железа: функция из образа (флеш) и её перенос из
src/nrlc_funcs.c запускаются в эмуляторе Cortex-M4 (Unicorn) на одинаковом начальном
состоянии RAM; сравниваются возвращаемое значение и итоговое состояние RAM.
"""
import os, struct, subprocess, random
from unicorn import *
from unicorn.arm_const import *

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CC   = "arm-none-eabi-gcc"
CODE_BASE = 0x08100000
SENTINEL  = 0x08FF0000
RAM_BASE, RAM_SIZE = 0x20000000, 0x20000
STACK_TOP = RAM_BASE + RAM_SIZE - 0x100

def load_image():
    mem = {}; ext = 0
    for line in open(os.path.join(REPO, "nRLC_2_0_12_FREEWARE.hex")):
        line = line.strip()
        if not line.startswith(":"): continue
        n = int(line[1:3], 16); a = int(line[3:7], 16); t = int(line[7:9], 16); d = line[9:9 + n * 2]
        if t == 4: ext = int(d, 16) << 16
        elif t == 0:
            for i in range(n): mem[ext + a + i] = int(d[i * 2:i * 2 + 2], 16)
    lo = min(mem); hi = max(mem)
    buf = bytearray(hi - lo + 1)
    for a, b in mem.items(): buf[a - lo] = b
    return lo, bytes(buf)

def build_port(opt="-O1"):
    """Собирает src/nrlc_funcs.c для Cortex-M4 и возвращает (образ, {символ: адрес})."""
    out = "/tmp/emu_port"
    flags = ["-mcpu=cortex-m4", "-mthumb", "-mfpu=fpv4-sp-d16", "-mfloat-abi=hard",
             "-DSTM32F303xC", "-I/tmp/cm/Device", "-I/tmp/cm/Include", "-I" + os.path.join(REPO, "src"),
             "-ffp-contract=off", "-fno-builtin", "-falign-functions=16", "-fno-inline", "-fno-ipa-pure-const", "-fno-ipa-ra", "-fno-ipa-icf", "-fno-ipa-cp", "-fno-ipa-sra", "-fno-ipa-modref", "-fno-ipa-reference", opt]
    subprocess.check_call([CC] + flags + ["-c", os.path.join(REPO, "src/nrlc_funcs.c"), "-o", out + ".o"])
    defs = []
    for l in subprocess.check_output(["arm-none-eabi-nm", "-u", out + ".o"]).decode().splitlines():
        name = l.split()[-1]
        if name.startswith("FUN_"): defs.append("-Wl,--defsym=%s=0x%X" % (name, int(name[4:], 16) | 1))
        elif name == "thunk_EXT_FUN_10000000": defs.append("-Wl,--defsym=%s=0x10000001" % name)
    subprocess.check_call([CC, "-nostdlib", "-mcpu=cortex-m4", "-mthumb", "-mfpu=fpv4-sp-d16", "-mfloat-abi=hard",
                           "-T", os.path.join(HERE, "link.ld"), "-Wl,--unresolved-symbols=ignore-all"] + defs +
                          [out + ".o", "-Wl,--start-group", "-lm", "-lc", "-lgcc", "-lnosys", "-Wl,--end-group", "-o", out + ".elf"])
    subprocess.check_call(["arm-none-eabi-objcopy", "-O", "binary", out + ".elf", out + ".bin"])
    syms = {}
    for l in subprocess.check_output(["arm-none-eabi-nm", out + ".elf"]).decode().splitlines():
        p = l.split()
        if len(p) == 3: syms[p[2]] = int(p[0], 16)
    return open(out + ".bin", "rb").read(), syms

_IMG = None
def image():
    global _IMG
    if _IMG is None: _IMG = load_image()
    return _IMG

PATCH = {   # имя заглушки в переносе -> адрес оригинала в образе
    "nrlc_TIM7_ISR": 0x0800FF78, "nrlc_TimBase_Init": 0x080078E0, "nrlc_TIMEx_MasterConfigSync": 0x0800784C,
    "nrlc_GPIO_Init": 0x08005CCC, "nrlc_DMA_Init": 0x08005A88, "nrlc_USB_CTR_EndpointTransfer": 0x0800E754,
}

class Machine:
    def __init__(self, port_bin=None):
        lo, img = image()
        uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        uc.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M4)
        uc.mem_map(0x08000000, 0x00200000)           # флеш + место под перенос
        uc.mem_write(lo, img)
        if port_bin:
            uc.mem_write(CODE_BASE, port_bin)
            for nm, tgt in PATCH.items():
                a = PORT[1][nm]
                assert a % 16 == 0, nm
                uc.mem_write(a, b"\xdf\xf8\x00\xf0" + struct.pack("<I", tgt | 1))   # ldr.w pc,[pc,#0]
        uc.mem_map(0x08FF0000, 0x1000); uc.mem_write(SENTINEL, b"\xfe\xe7")
        uc.mem_map(0x10000000, 0x4000)               # CCM RAM, копия по таблице scatter-load
        uc.mem_write(0x10000000, img[0x0802D7DC - lo: 0x0802D7DC - lo + 0xC18])
        uc.mem_map(RAM_BASE, RAM_SIZE)
        for base, size in ((0x40000000, 0x24000), (0x48000000, 0x2000), (0x50000000, 0x1000), (0xE000E000, 0x1000)):
            uc.mem_map(base, size)                   # периферия и SCS как обычная память
        uc.reg_write(UC_ARM_REG_C1_C0_2, 0xF00000)   # доступ к FPU
        self.uc = uc
        self.trace = []
        def on_write(u, access, addr, size, value, ud):
            if addr >= 0x40000000 or 0x08000000 <= addr < 0x08100000:   # периферия, SCS и записи во флеш образа
                self.trace.append((addr, size, value & ((1 << (8 * size)) - 1)))
        uc.hook_add(UC_HOOK_MEM_WRITE, on_write)

    def write(self, addr, data): self.uc.mem_write(addr, bytes(data))
    def w32(self, a, v): self.uc.mem_write(a, struct.pack("<I", v & 0xFFFFFFFF))
    def w16(self, a, v): self.uc.mem_write(a, struct.pack("<H", v & 0xFFFF))
    def w8 (self, a, v): self.uc.mem_write(a, bytes([v & 0xFF]))
    def wf (self, a, v): self.uc.mem_write(a, struct.pack("<f", v))
    def r32(self, a): return struct.unpack("<I", self.uc.mem_read(a, 4))[0]
    def ram(self): return bytes(self.uc.mem_read(RAM_BASE, RAM_SIZE))

    def call(self, addr, args=(), fargs=(), max_insn=60000000):
        uc = self.uc
        for i, v in enumerate(args): uc.reg_write(UC_ARM_REG_R0 + i, v & 0xFFFFFFFF)
        for i, f in enumerate(fargs): uc.reg_write(UC_ARM_REG_S0 + i, struct.unpack("<I", struct.pack("<f", f))[0])
        uc.reg_write(UC_ARM_REG_SP, STACK_TOP)
        uc.reg_write(UC_ARM_REG_LR, SENTINEL | 1)
        uc.emu_start(addr | 1, SENTINEL, count=max_insn)
        r = [uc.reg_read(UC_ARM_REG_R0 + i) for i in range(2)]
        f = [uc.reg_read(UC_ARM_REG_S0 + i) & 0xFFFFFFFF for i in range(2)]
        return r[0], f[0], r[1], f[1]

def diff_ram(a, b, limit=8):
    out = []
    cut = RAM_SIZE - 0x2000                      # область стека не сравниваем
    a = a[:cut]; b = b[:cut]
    for i in range(0, len(a), 4):
        if a[i:i + 4] != b[i:i + 4]:
            out.append((RAM_BASE + i, a[i:i + 4].hex(), b[i:i + 4].hex()))
            if len(out) >= limit: break
    return out

def compare(orig_addr, port_name, setup, args=(), fargs=(), compare_r0=True, compare_s0=False, pair=False):
    """setup(m) заполняет начальное состояние; запускает оригинал и перенос на одинаковом состоянии."""
    port_bin, syms = PORT
    mo = Machine(port_bin); setup(mo)
    mp = Machine(port_bin); setup(mp)
    ro = mo.call(orig_addr, args, fargs)
    rp = mp.call(syms[port_name], args, fargs)
    ok = True; notes = []
    if compare_r0 and ro[0] != rp[0]: ok = False; notes.append("r0 %08x != %08x" % (ro[0], rp[0]))
    if compare_s0 and ro[1] != rp[1]: ok = False; notes.append("s0 %08x != %08x" % (ro[1], rp[1]))
    if pair:   # результат из двух float: у оригинала и переноса конвенции могут различаться
        po = (ro[0], ro[2]) if (ro[0], ro[2]) != (0, 0) and ro[1] == 0 else (ro[1], ro[3])
        pp = (rp[1], rp[3])
        if po != pp: ok = False; notes.append("pair %08x,%08x != %08x,%08x" % (po + pp))
    d = diff_ram(mo.ram(), mp.ram())
    if d: ok = False; notes.append("RAM: " + str(d[:4]))
    if mo.trace != mp.trace:
        ok = False
        n = next((i for i, (x, y) in enumerate(zip(mo.trace, mp.trace)) if x != y), min(len(mo.trace), len(mp.trace)))
        notes.append("periph-trace differs at #%d (orig %d writes, port %d): %s | %s" % (
            n, len(mo.trace), len(mp.trace), mo.trace[n:n + 1], mp.trace[n:n + 1]))
    return ok, notes

PORT = None
def init():
    global PORT
    PORT = build_port()
    return PORT


def call_regs(m, addr, regs, max_insn=60000000):
    """Низкоуровневый вызов с произвольным набором регистров (для арифметики с double/uint64)."""
    uc = m.uc
    for r, v in regs.items(): uc.reg_write(r, v)
    uc.reg_write(UC_ARM_REG_SP, STACK_TOP); uc.reg_write(UC_ARM_REG_LR, SENTINEL | 1)
    uc.emu_start(addr | 1, SENTINEL, count=max_insn)
    return {"r0": uc.reg_read(UC_ARM_REG_R0), "r1": uc.reg_read(UC_ARM_REG_R1),
            "s0": uc.reg_read(UC_ARM_REG_S0) & 0xFFFFFFFF, "d0": uc.reg_read(UC_ARM_REG_D0),
            "d0lo": uc.reg_read(UC_ARM_REG_D0) & 0xFFFFFFFF, "d0hi": (uc.reg_read(UC_ARM_REG_D0) >> 32) & 0xFFFFFFFF}
