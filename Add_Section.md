
Файл временный. Аосле обработки удалить.
Дизассемблирую ядро коррелятора напрямую из .hex (флеш-образ по методу §6.7: flash = 0x0802D7DC + (ram - 0x10000000))

cd /home/claude/RLC && python3 << 'EOF'
mem = {}
ext = 0
with open("nRLC_2_0_12_FREEWARE.hex") as f:
    for line in f:
        line=line.strip()
        if not line.startswith(':'): continue
        n = int(line[1:3],16)
        addr = int(line[3:7],16)
        rtype = int(line[7:9],16)
        data = line[9:9+n*2]
        if rtype==0:
            full = ext + addr
            for i in range(n):
                mem[full+i] = int(data[i*2:i*2+2],16)
        elif rtype==4:
            ext = int(data,16) << 16

RAM_START = 0x100001b8
RAM_END   = 0x10000b28  # exclusive, per doc (incl. 4-byte literal pool)
FLASH_BASE = 0x0802D7DC

blob = bytearray()
for ram in range(RAM_START, RAM_END):
    flash = FLASH_BASE + (ram - 0x10000000)
    blob.append(mem.get(flash, 0))

with open("correlator.bin","wb") as f:
    f.write(blob)
print("len", len(blob), hex(len(blob)))
print("first 16 bytes:", blob[:16].hex())
EOF

Output
len 2416 0x970
first 16 bytes: 2de9f74ffe4b98b0d3f808c01a9a6244


bash
cd /home/claude/RLC && python3 << 'EOF'
from capstone import *

with open("correlator.bin","rb") as f:
    blob = f.read()

md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
md.detail = False
base = 0x100001b8


Analyzing register push instructions in assembly code.

Tracing stack offsets to locate saved input registers.

Mapping struct fields to their source registers and pointers.

Tracing buffer pointer offsets and accumulator initialization steps.

Locating the mode flag branch and loop entry point.

bash

cd /home/claude/RLC && grep -n "smlad\|smlsd\|smuad" correlator_disasm.txt | head -30; echo "total smlad-family:"; grep -ci "smlad\|smlsd\|smuad" correlator_disasm.txt

Output

45:0x10000234:	smlad	r6, sl, r8, r6
46:0x10000238:	smlad	r7, sl, sb, r7
51:0x1000024a:	smlad	r6, sl, r8, r6
52:0x1000024e:	smlad	r7, sl, sb, r7
70:0x10000288:	smlad	r6, fp, r8, r6
71:0x1000028c:	smlad	r7, fp, sb, r7
92:0x100002d0:	smlad	r6, fp, r8, r6
93:0x100002d4:	smlad	r7, fp, sb, r7
109:0x10000310:	smlad	fp, sl, r8, fp
112:0x1000031c:	smlad	fp, sl, sb, fp
116:0x1000032c:	smlad	r2, sl, r8, fp
118:0x10000334:	smlad	r8, sl, sb, fp
134:0x10000370:	smlad	r3, sl, r7, r3
135:0x10000374:	smlad	ip, sl, r8, ip
150:0x100003ac:	smlad	r3, sl, r7, r3
151:0x100003b0:	smlad	ip, sl, r8, ip
166:0x100003e4:	smlad	r3, sl, r7, r3
167:0x100003e8:	smlad	ip, sl, r8, ip
182:0x10000422:	smlad	r1, fp, r7, lr
183:0x10000426:	smlad	lr, fp, r8, lr
187:0x10000436:	smlad	r7, fp, r7, r1
189:0x1000043e:	smlad	r1, fp, r8, lr
284:0x1000058c:	smlad	r6, sl, fp, r6
286:0x10000594:	smlad	r7, sl, fp, r7
316:0x100005ec:	smlad	r6, sl, fp, r6
318:0x100005f4:	smlad	r7, sl, fp, r7
339:0x1000063c:	smlad	r6, sl, fp, r6
341:0x10000644:	smlad	r7, sl, fp, r7
358:0x10000682:	smlad	sl, fp, sl, r2
360:0x1000068a:	smlad	lr, fp, lr, r2
total smlad-family:
42


Verifying instruction counts against the documented pattern.

bash
cd /home/claude/RLC && sed -n '1,60p' correlator_disasm.txt

Output
0x100001b8:	push.w	{r0, r1, r2, r4, r5, r6, r7, r8, sb, sl, fp, lr}
0x100001bc:	ldr	r3, [pc, #0x3f8]
0x100001be:	sub	sp, #0x60
0x100001c0:	ldr.w	ip, [r3, #8]
0x100001c4:	ldr	r2, [sp, #0x68]

Disassembling machine code instruction by instruction.

Tracing the multiply-accumulate loop against fixed reference values.

Reconsidering whether reference pairs represent a fixed phase.

Searching for where accumulated results get stored to memory.

bash

cd /home/claude/RLC && python3 << 'EOF'
import re, struct

with open("correlator.bin","rb") as f:
    blob = f.read()
base = 0x100001b8

def read_u32(addr):
    off = addr - base
    if 0 <= off <= len(blob)-4:
        return struct.unpack_from("<I", blob, off)[0]
    return None

with open("correlator_disasm.txt") as f:
    lines = f.readlines()

out = []
lit_map = {}
pat = re.compile(r"0x([0-9a-f]+):\s+(ldr(?:\.w)?)\s+(\w+),\s+\[pc,\s+#(0x[0-9a-f]+|-0x[0-9a-f]+)\]")
for line in lines:
    m = pat.search(line)
    if m:
        addr = int(m.group(1),16)
        reg = m.group(3)
        imm = int(m.group(4),16)
        # Thumb PC = instr_addr + 4, word aligned
        pc = (addr + 4) & ~3
        lit_addr = pc + imm
        val = read_u32(lit_addr)
        line = line.rstrip("\n") + f"\t; [0x{lit_addr:08x}] = 0x{val:08x}\n" if val is not None else line
    out.append(line)

with open("correlator_disasm_annot.txt","w") as f:
    f.writelines(out)
print("done")
EOF
grep -n "; \[0x" correlator_disasm_annot.txt | head -20

Output

done
2:0x100001bc:	ldr	r3, [pc, #0x3f8]	; [0x100005b8] = 0x200048a8
14:0x100001d8:	ldr	r2, [pc, #0x3e0]	; [0x100005bc] = 0x20000000
23:0x100001f2:	ldr.w	r8, [pc, #0x3cc]	; [0x100005c0] = 0x200049e8
126:0x10000354:	ldr.w	r8, [pc, #0x260]	; [0x100005b8] = 0x200048a8
128:0x1000035a:	ldr	r7, [pc, #0x260]	; [0x100005bc] = 0x20000000
197:0x1000045c:	ldr	r1, [pc, #0x158]	; [0x100005b8] = 0x200048a8
201:0x10000468:	ldr	r1, [pc, #0x14c]	; [0x100005b8] = 0x200048a8
208:0x1000047e:	ldr	r1, [pc, #0x138]	; [0x100005b8] = 0x200048a8
255:0x1000052a:	ldr	r1, [pc, #0x8c]	; [0x100005b8] = 0x200048a8
273:0x1000056a:	ldr.w	sb, [pc, #0x58]	; [0x100005c4] = 0x200048a0
296:0x100005b8:	ldr	r0, [pc, #0x2a0]	; [0x1000085c] = 0xf0216801
300:0x100005c0:	ldr	r1, [pc, #0x3a0]	; [0x10000964] = 0x3012f820
302:0x100005c4:	ldr	r0, [pc, #0x280]	; [0x10000848] = 0xf0216801
373:0x100006ba:	ldr.w	r8, [pc, #0x404]	; [0x10000ac0] = 0x200048a8
376:0x100006c4:	ldr	r7, [pc, #0x3f4]	; [0x10000abc] = 0x20000000
451:0x100007da:	ldr	r1, [pc, #0x2e4]	; [0x10000ac0] = 0x200048a8
460:0x100007f0:	ldr	r6, [pc, #0x2cc]	; [0x10000ac0] = 0x200048a8
465:0x100007fa:	ldr	r0, [pc, #0x2c8]	; [0x10000ac4] = 0x20007c70
486:0x10000838:	ldr	r0, [pc, #0x28c]	; [0x10000ac8] = 0x2000465f
495:0x10000850:	ldr	r0, [pc, #0x278]	; [0x10000acc] = 0x40000400

Tracking down a pointer offset discrepancy in the struct.

Tracing a base address into a possible lookup table.

Mapping table entry layout from the double-word load pattern.

Verifying the literal address against raw blob bytes.

bash

cd /home/claude/RLC && python3 -c "
import struct
with open('correlator.bin','rb') as f:
    blob=f.read()
base=0x100001b8
off = 0x100005bc - base
print('bytes:', blob[off:off+4].hex())
print('u32:', hex(struct.unpack_from('<I',blob,off)[0]))
"

Output

bytes: 00000020
u32: 0x20000000


Investigating a memory address's role in the system.

bash
cd /home/claude/RLC && grep -n "sp, #0x6\|sp, #0x5c\|sp, #0x58" correlator_disasm.txt | head -10

Output
3:0x100001be:	sub	sp, #0x60
5:0x100001c4:	ldr	r2, [sp, #0x68]
10:0x100001d0:	ldr	r2, [sp, #0x68]
195:0x10000456:	ldr	r1, [sp, #0x68]
453:0x100007e0:	ldr.w	sb, [sp, #0x68]
516:0x1000088a:	addhs	sp, #0x6c
543:0x100008d4:	add	sp, #0x6c
699:0x10000ab8:	add	sp, #0x6c


Untangling register push order on the stack.

bash
cd /home/claude/RLC && grep -n "sp, #0x60\]" correlator_disasm.txt

Output
exit code 1


Tracing register usage in the disassembled code.

bash
cd /home/claude/RLC && grep -n "\br0\b" correlator_disasm.txt

Output
1:0x100001b8:	push.w	{r0, r1, r2, r4, r5, r6, r7, r8, sb, sl, fp, lr}
259:0x10000534:	strd	sb, sl, [r0, #8]
261:0x1000053c:	strd	sb, fp, [r0, #0x10]
263:0x10000544:	strd	sb, sl, [r0, #0x20]
265:0x1000054c:	strd	sb, sl, [r0, #0x28]
272:0x10000566:	str.w	sb, [r0, #0x30]
274:0x1000056e:	movs	r0, #1
276:0x10000572:	strh.w	r0, [sb]
277:0x10000576:	ldrb	r0, [r1, #1]
278:0x10000578:	cmp	r0, #0
296:0x100005b8:	ldr	r0, [pc, #0x2a0]
297:0x100005ba:	movs	r0, #0
298:0x100005bc:	movs	r0, r0
299:0x100005be:	movs	r0, #0
301:0x100005c2:	movs	r0, #0
302:0x100005c4:	ldr	r0, [pc, #0x280]
303:0x100005c6:	movs	r0, #0
456:0x100007e8:	ldrb	r0, [r1]
457:0x100007ea:	cmp	r0, #0x64
461:0x100007f2:	ldr	r0, [sp, #0x4c]
463:0x100007f6:	cmp	r0, r1
465:0x100007fa:	ldr	r0, [pc, #0x2c8]
468:0x10000802:	str.w	lr, [r0, #0x14]
469:0x10000806:	str.w	sb, [r0, #8]
470:0x1000080a:	strd	r1, r2, [r0, #0xc]
471:0x1000080e:	strd	r8, r3, [r0, #0x20]
472:0x10000812:	strd	ip, r7, [r0, #0x28]
479:0x1000082a:	str	r1, [r0, #0x30]
480:0x1000082c:	movs	r0, #0
481:0x1000082e:	str	r0, [r6, #0xc]
482:0x10000830:	str	r0, [r6, #0x24]
483:0x10000832:	str	r0, [r6, #8]
484:0x10000834:	movs	r0, #1
485:0x10000836:	strb	r0, [r6, #2]
486:0x10000838:	ldr	r0, [pc, #0x28c]
487:0x1000083a:	ldrb	r0, [r0]
488:0x1000083c:	cbz	r0, #0x10000884
489:0x1000083e:	movs	r0, #0xb
491:0x10000844:	mov.w	r0, #0x40000000
492:0x10000848:	ldr	r1, [r0]
494:0x1000084e:	str	r1, [r0]
495:0x10000850:	ldr	r0, [pc, #0x278]
496:0x10000852:	ldr	r1, [r0]
498:0x10000858:	str	r1, [r0]
499:0x1000085a:	ldr	r0, [pc, #0x274]
500:0x1000085c:	ldr	r1, [r0]
502:0x10000862:	str	r1, [r0]
503:0x10000864:	ldr	r0, [pc, #0x26c]
505:0x1000086a:	str	r1, [r0]
506:0x1000086c:	mov.w	r0, #0x50000000
507:0x10000870:	ldr	r1, [r0, #8]
509:0x10000876:	str	r1, [r0, #8]
510:0x10000878:	ldr.w	r1, [r0, #0x108]
512:0x10000880:	str.w	r1, [r0, #0x108]
518:0x10000890:	ldr	r0, [pc, #0x244]
519:0x10000892:	ldr	r3, [r0]
520:0x10000894:	ldr	r0, [pc, #0x244]
522:0x10000898:	add.w	r1, r0, #0x190
530:0x100008ac:	strh.w	ip, [r0, r3, lsl #1]
536:0x100008c0:	strh.w	ip, [r0, r3, lsl #1]
548:0x100008e2:	strh.w	r3, [r0, r2, lsl #1]
554:0x100008f2:	strh.w	r3, [r0, r2, lsl #1]
560:0x10000902:	strh.w	r3, [r0, r2, lsl #1]
566:0x10000912:	strh.w	r3, [r0, r2, lsl #1]
572:0x10000922:	strh.w	r3, [r0, r2, lsl #1]
578:0x10000932:	strh.w	r3, [r0, r2, lsl #1]
584:0x10000942:	strh.w	r3, [r0, r2, lsl #1]
590:0x10000952:	strh.w	r3, [r0, r2, lsl #1]
596:0x10000964:	strh.w	r3, [r0, r2, lsl #1]
602:0x10000978:	strh.w	r3, [r0, r2, lsl #1]
608:0x1000098c:	strh.w	r3, [r0, r2, lsl #1]
614:0x100009a0:	strh.w	r3, [r0, r2, lsl #1]
620:0x100009b4:	strh.w	r3, [r0, r2, lsl #1]
626:0x100009c8:	strh.w	r3, [r0, r2, lsl #1]
634:0x100009e0:	strh.w	r3, [r0, r2, lsl #1]
640:0x100009f4:	strh.w	r3, [r0, r2, lsl #1]
646:0x10000a08:	strh.w	r3, [r0, r2, lsl #1]
652:0x10000a1c:	strh.w	r3, [r0, r2, lsl #1]
658:0x10000a30:	strh.w	r3, [r0, r2, lsl #1]
664:0x10000a44:	strh.w	r3, [r0, r2, lsl #1]
670:0x10000a58:	strh.w	r3, [r0, r2, lsl #1]
676:0x10000a6c:	strh.w	r3, [r0, r2, lsl #1]
682:0x10000a80:	strh.w	r3, [r0, r2, lsl #1]
688:0x10000a94:	strh.w	r3, [r0, r2, lsl #1]
694:0x10000aa8:	strh.w	r3, [r0, r2, lsl #1]
695:0x10000aac:	ldrh.w	r0, [r4, #0xc0]
696:0x10000ab0:	strh.w	r0, [r1, r2, lsl #1]
697:0x10000ab4:	adds	r0, r2, #1
698:0x10000ab6:	strb	r0, [r6]
701:0x10000abc:	movs	r0, r0
702:0x10000abe:	movs	r0, #0
703:0x10000ac0:	ldr	r0, [pc, #0x2a0]
704:0x10000ac2:	movs	r0, #0
705:0x10000ac4:	ldrb	r0, [r6, #0x11]
706:0x10000ac6:	movs	r0, #0
708:0x10000aca:	movs	r0, #0
709:0x10000acc:	lsls	r0, r0, #0x10
710:0x10000ace:	ands	r0, r0
711:0x10000ad0:	strb	r0, [r0, #0x10]
712:0x10000ad2:	ands	r0, r0
713:0x10000ad4:	strb	r0, [r1, #0x10]
714:0x10000ad6:	ands	r0, r0
716:0x10000ada:	movs	r0, #0
717:0x10000adc:	ldrh	r0, [r7, r1]
718:0x10000ade:	movs	r0, #0
725:0x10000aee:	strh.w	r3, [r0, r2, lsl #1]
726:0x10000af2:	ldrh	r0, [r4]
727:0x10000af4:	strh.w	r0, [r1, r2, lsl #1]
728:0x10000af8:	adds	r0, r2, #1
729:0x10000afa:	strb	r0, [r6]
736:0x10000b08:	adds	r0, r3, #1
737:0x10000b0a:	strh	r0, [r6, #4]
751:0x10000b26:	movs	r0, #0

Tracing assembly instructions to locate correlation storage.

Confirming output pointer offsets for accumulated results.

bash

cd /home/claude/RLC && sed -n '225,280p' correlator_disasm.txt

Output

0x100004c0:	strd	sb, sl, [sp, #8]
0x100004c4:	ldrd	sb, sl, [r1, #0x40]
0x100004c8:	adds.w	sb, sb, ip
0x100004cc:	adc.w	sl, sl, r7
0x100004d0:	strd	sb, sl, [r1, #0x40]
0x100004d4:	strd	sb, sl, [sp]
0x100004d8:	ldrd	sb, sl, [r1, #0x48]
0x100004dc:	adds.w	r2, sb, r2
0x100004e0:	adc.w	r6, sl, r6
0x100004e4:	strd	r2, r6, [r1, #0x48]
0x100004e8:	str	r6, [sp, #0x2c]
0x100004ea:	str	r2, [sp, #0x38]
0x100004ec:	ldrd	sb, sl, [r1, #0x50]
0x100004f0:	ldr	r2, [sp, #0x40]
0x100004f2:	adds.w	r2, sb, r2
0x100004f6:	adc.w	r6, sl, lr
0x100004fa:	strd	r2, r6, [r1, #0x50]
0x100004fe:	mov	lr, r6
0x10000500:	ldrd	r6, sb, [r1, #0x58]
0x10000504:	adds.w	r8, r6, r8
0x10000508:	adc.w	r3, sb, r3
0x1000050c:	strd	r8, r3, [r1, #0x58]
0x10000510:	ldrd	r6, sb, [r1, #0x60]
0x10000514:	adds.w	ip, r6, ip
0x10000518:	adc.w	r7, sb, r7
0x1000051c:	strd	ip, r7, [r1, #0x60]
0x10000520:	ldr	r6, [sp, #0x50]
0x10000522:	ldr	r1, [r1, #0x1c]
0x10000524:	cmp	r6, r1
0x10000526:	blo.w	#0x100007f0
0x1000052a:	ldr	r1, [pc, #0x8c]
0x1000052c:	movs	r6, #0
0x1000052e:	str	r6, [r1, #0x24]
0x10000530:	ldrd	sb, sl, [sp, #0x18]
0x10000534:	strd	sb, sl, [r0, #8]
0x10000538:	ldr.w	sb, [sp, #0x10]
0x1000053c:	strd	sb, fp, [r0, #0x10]
0x10000540:	ldrd	sb, sl, [sp, #8]
0x10000544:	strd	sb, sl, [r0, #0x20]
0x10000548:	ldrd	sb, sl, [sp]
0x1000054c:	strd	sb, sl, [r0, #0x28]
0x10000550:	strd	r6, r6, [r1, #0x28]
0x10000554:	strd	r6, r6, [r1, #0x30]
0x10000558:	strd	r6, r6, [r1, #0x38]
0x1000055c:	mov	sb, r6
0x1000055e:	strd	sb, sb, [r1, #0x40]
0x10000562:	ldr.w	sb, [sp, #0x50]
0x10000566:	str.w	sb, [r0, #0x30]
0x1000056a:	ldr.w	sb, [pc, #0x58]
0x1000056e:	movs	r0, #1
0x10000570:	str	r6, [r1, #8]
0x10000572:	strh.w	r0, [sb]
0x10000576:	ldrb	r0, [r1, #1]
0x10000578:	cmp	r0, #0
0x1000057a:	bne.w	#0x100007f0
0x1000057e:	b.w	#0x100007e8


Decoding pointer structures in low-level code analysis.

Mapping persistent accumulator fields across multiple function calls.

Tracing the finalization step that writes summed results.

Uncovering a status flag set at measurement completion.

Связывая накопленные значения с известными координатами Re/Im.

bash

cd /home/claude/RLC && sed -n '60,225p' correlator_disasm.txt

Output

0x10000268:	str.w	sl, [sp, #0x38]
0x1000026c:	adds	r6, r6, r7
0x1000026e:	ldr.w	sl, [sp, #0x28]
0x10000272:	str	r6, [sp, #0x40]
0x10000274:	adc.w	r7, sl, r7, asr #31
0x10000278:	mov.w	r6, #0
0x1000027c:	str	r7, [sp, #0x28]
0x1000027e:	mov	r7, r6
0x10000280:	mov.w	sl, r6
0x10000284:	ldr	fp, [r2], #4
0x10000288:	smlad	r6, fp, r8, r6
0x1000028c:	smlad	r7, fp, sb, r7
0x10000290:	add.w	sl, sl, #1
0x10000294:	cmp.w	sl, #0xf
0x10000298:	ble	#0x10000284
0x1000029a:	mov	sl, lr
0x1000029c:	asr.w	lr, r6, #0x1f
0x100002a0:	ldr.w	fp, [sp, #0x38]
0x100002a4:	adds.w	r6, sl, r6
0x100002a8:	adc.w	sl, fp, lr
0x100002ac:	mov	lr, r6
0x100002ae:	ldr	r6, [sp, #0x40]
0x100002b0:	str.w	sl, [sp, #0x38]
0x100002b4:	adds	r6, r6, r7
0x100002b6:	ldr.w	sl, [sp, #0x28]
0x100002ba:	str	r6, [sp, #0x40]
0x100002bc:	adc.w	r7, sl, r7, asr #31
0x100002c0:	mov.w	r6, #0
0x100002c4:	str	r7, [sp, #0x28]
0x100002c6:	mov	r7, r6
0x100002c8:	mov.w	sl, r6
0x100002cc:	ldr	fp, [r2], #4
0x100002d0:	smlad	r6, fp, r8, r6
0x100002d4:	smlad	r7, fp, sb, r7
0x100002d8:	add.w	sl, sl, #1
0x100002dc:	cmp.w	sl, #0xf
0x100002e0:	ble	#0x100002cc
0x100002e2:	mov	sl, lr
0x100002e4:	ldr.w	fp, [sp, #0x38]
0x100002e8:	adds.w	sl, sl, r6
0x100002ec:	adc.w	r6, fp, r6, asr #31
0x100002f0:	str.w	sl, [sp, #0x48]
0x100002f4:	ldr.w	fp, [sp, #0x40]
0x100002f8:	asr.w	lr, r7, #0x1f
0x100002fc:	ldr.w	sl, [sp, #0x28]
0x10000300:	adds.w	r7, fp, r7
0x10000304:	adc.w	lr, sl, lr
0x10000308:	ldr.w	sl, [r2]
0x1000030c:	mov.w	fp, #0
0x10000310:	smlad	fp, sl, r8, fp
0x10000314:	str.w	fp, [sp, #0x18]
0x10000318:	mov.w	fp, #0
0x1000031c:	smlad	fp, sl, sb, fp
0x10000320:	str.w	fp, [sp, #0x14]
0x10000324:	ldr.w	sl, [r2, #4]
0x10000328:	ldr.w	fp, [sp, #0x18]
0x1000032c:	smlad	r2, sl, r8, fp
0x10000330:	ldr.w	fp, [sp, #0x14]
0x10000334:	smlad	r8, sl, sb, fp
0x10000338:	ldr.w	sl, [sp, #0x48]
0x1000033c:	asr.w	sb, r2, #0x1f
0x10000340:	adds.w	r2, sl, r2
0x10000344:	adc.w	r6, r6, sb
0x10000348:	adds.w	r7, r7, r8
0x1000034c:	adc.w	r8, lr, r8, asr #31
0x10000350:	str.w	r8, [sp, #0x28]
0x10000354:	ldr.w	r8, [pc, #0x260]
0x10000358:	str	r7, [sp, #0x40]
0x1000035a:	ldr	r7, [pc, #0x260]
0x1000035c:	ldr.w	r8, [r8, #0x24]
0x10000360:	mov.w	sb, #0
0x10000364:	add.w	r8, r7, r8, lsl #2
0x10000368:	ldrd	r7, r8, [r8]
0x1000036c:	ldr	sl, [r1], #4
0x10000370:	smlad	r3, sl, r7, r3
0x10000374:	smlad	ip, sl, r8, ip
0x10000378:	add.w	sb, sb, #1
0x1000037c:	cmp.w	sb, #0xf
0x10000380:	ble	#0x1000036c
0x10000382:	ldrd	sb, sl, [sp, #0x30]
0x10000386:	adds.w	fp, sb, r3
0x1000038a:	adc.w	lr, sl, r3, asr #31
0x1000038e:	ldrd	r3, sb, [sp, #0x20]
0x10000392:	adds.w	r3, r3, ip
0x10000396:	adc.w	ip, sb, ip, asr #31
0x1000039a:	strd	r3, ip, [sp, #0x20]
0x1000039e:	mov.w	r3, #0
0x100003a2:	mov	ip, r3
0x100003a4:	mov.w	sb, r3
0x100003a8:	ldr	sl, [r1], #4
0x100003ac:	smlad	r3, sl, r7, r3
0x100003b0:	smlad	ip, sl, r8, ip
0x100003b4:	add.w	sb, sb, #1
0x100003b8:	cmp.w	sb, #0xf
0x100003bc:	ble	#0x100003a8
0x100003be:	mov	sb, lr
0x100003c0:	adds.w	lr, fp, r3
0x100003c4:	adc.w	fp, sb, r3, asr #31
0x100003c8:	ldrd	r3, sb, [sp, #0x20]
0x100003cc:	adds.w	r3, r3, ip
0x100003d0:	adc.w	ip, sb, ip, asr #31
0x100003d4:	strd	r3, ip, [sp, #0x20]
0x100003d8:	mov.w	r3, #0
0x100003dc:	mov	ip, r3
0x100003de:	mov	sb, r3
0x100003e0:	ldr	sl, [r1], #4
0x100003e4:	smlad	r3, sl, r7, r3
0x100003e8:	smlad	ip, sl, r8, ip
0x100003ec:	add.w	sb, sb, #1
0x100003f0:	cmp.w	sb, #0xf
0x100003f4:	ble	#0x100003e0
0x100003f6:	asr.w	sb, r3, #0x1f
0x100003fa:	adds.w	r3, lr, r3
0x100003fe:	adc.w	sl, fp, sb
0x10000402:	ldrd	fp, sb, [sp, #0x20]
0x10000406:	asr.w	lr, ip, #0x1f
0x1000040a:	adds.w	ip, fp, ip
0x1000040e:	adc.w	sb, sb, lr
0x10000412:	add.w	lr, r1, #4
0x10000416:	ldr.w	fp, [r1]
0x1000041a:	str.w	lr, [sp, #0x1c]
0x1000041e:	mov.w	lr, #0
0x10000422:	smlad	r1, fp, r7, lr
0x10000426:	smlad	lr, fp, r8, lr
0x1000042a:	str.w	lr, [sp, #0x10]
0x1000042e:	ldr.w	lr, [sp, #0x1c]
0x10000432:	ldr.w	fp, [lr]
0x10000436:	smlad	r7, fp, r7, r1
0x1000043a:	ldr.w	lr, [sp, #0x10]
0x1000043e:	smlad	r1, fp, r8, lr
0x10000442:	adds.w	r8, r3, r7
0x10000446:	adc.w	r3, sl, r7, asr #31
0x1000044a:	adds.w	ip, ip, r1
0x1000044e:	adc.w	r7, sb, r1, asr #31
0x10000452:	ldr.w	sb, [sp, #0x54]
0x10000456:	ldr	r1, [sp, #0x68]
0x10000458:	udiv	sb, r1, sb
0x1000045c:	ldr	r1, [pc, #0x158]
0x1000045e:	ldr.w	sl, [r1, #0x24]
0x10000462:	add	sb, sl
0x10000464:	str.w	sb, [r1, #0x24]
0x10000468:	ldr	r1, [pc, #0x14c]
0x1000046a:	ldr.w	sb, [r1, #0x24]
0x1000046e:	movw	sl, #0xbb7
0x10000472:	cmp	sb, sl
0x10000474:	itt	hi
0x10000476:	movhi.w	sb, #0
0x1000047a:	strhi.w	sb, [r1, #0x24]
0x1000047e:	ldr	r1, [pc, #0x138]
0x10000480:	ldrd	sb, sl, [r1, #0x28]
0x10000484:	adds.w	sb, sb, r2
0x10000488:	adc.w	sl, sl, r6
0x1000048c:	strd	sb, sl, [r1, #0x28]
0x10000490:	strd	sb, sl, [sp, #0x18]
0x10000494:	ldrd	sl, fp, [r1, #0x30]
0x10000498:	ldr.w	sb, [sp, #0x40]
0x1000049c:	ldr.w	lr, [sp, #0x28]
0x100004a0:	adds.w	sb, sl, sb
0x100004a4:	adc.w	fp, fp, lr
0x100004a8:	strd	sb, fp, [r1, #0x30]
0x100004ac:	str.w	sb, [sp, #0x10]
0x100004b0:	ldrd	sb, sl, [r1, #0x38]
0x100004b4:	adds.w	sb, sb, r8
0x100004b8:	adc.w	sl, sl, r3
0x100004bc:	strd	sb, sl, [r1, #0x38]
0x100004c0:	strd	sb, sl, [sp, #8]


Reverse engineering a program's control flow structure.

Mapping accumulator fields within the state structure.

Counting and tracing multiple 64-bit accumulator fields.

Tracing buffer pointers feeding a second correlation loop.

Mapping struct offsets to their matching output fields.

Confirming the full accumulator-to-output mapping chain.

bash

cd /home/claude/RLC && sed -n '1936,2044p' REVERSE_STATUS.md

Output

  флеш-источника.

**Открыто:** разобрать сам ISR `DMA1_CH1` (не тайл-функцию, а
непосредственно обработчик прерывания) на предмет фактического значения
`r1` при вызове; установить `.data`-источник `0x200048bc` и проверить,
равен ли он `0x20005758` (DMA2-буфер, канал B).

### 6.16 Место записи `Re`/`Im` (`0x20005668`/`0x20005670`) найдено внутри
`FUN_08000f52` — CONFIRMED адреса и механизм, PROBABLE точная формула,
2026-09-08 (сведено из независимой сессии + перекрёстно подтверждено
разделом 6.12)

Продолжение пункта 25 раздела 13 и раздела 6.11. Работа велась
параллельно с независимой сессией, которая в это же время нашла раздел
6.12 (`FUN_0800dbf8`) — координаты обеих находок сошлись на **одном и
том же буфере `0x20007840`** с точным совпадением смещений, что
взаимно подтверждает оба независимых захода.

**Структура `0x20005610` (`puVar21`, диспетчер стадий, раздел 6.13) —
CONFIRMED, прямая запись найдена.** Внутри `FUN_08000f52`:

```c
pfVar4 = DAT_08001180;   // = 0x20007840 — ТОТ ЖЕ буфер, что в разделе 6.12/6.13
                          // (DAT_08001620 там же резолвится в 0x20007840)
```

Далее, пока счётчик отсчётов `*(puVar21+0x22) < 0xf9` (249), каждый
вызов функции читает из этого буфера **те же самые смещения**, что
раздел 6.12 определил как "канал 1"/"канал 2":

| Прочитано (`pfVar4[N]`, float) | Смещение в `0x20007840` | Соответствует (раздел 6.12) |
|---|---|---|
| `pfVar4[2]`,`[3]` | `+0x08`,`+0x0c` | канал 1, Re |
| `pfVar4[4]`,`[5]` | `+0x10`,`+0x14` | канал 1, Im |
| `pfVar4[8]`,`[9]` | `+0x20`,`+0x24` | канал 2, Re |
| `pfVar4[10]`,`[11]` | `+0x28`,`+0x2c` | канал 2, Im |

Совпадение смещений с разделом 6.12 — CONFIRMED прямым сравнением
адресов (`0x20007840+0x08` и т.д.), не совпадение по смыслу "на глаз".

Из каждой пары вычисляется отношение (`FUN_0800285a` — вероятно, то же
семейство операций, что `FUN_080029b8` в разделе 6.12, PROBABLE:
hypot/magnitude или ratio), делится на `param_1` (параметр функции,
PROBABLE — нормировка по времени/частоте цикла), и результат **пишется
в два параллельных кольцевых буфера-истории**:

```c
DAT_08001610[idx] = <результат для канала 1>;   // = 0x200060f8
DAT_08001614[idx] = <результат для канала 2>;   // = 0x200064e0
idx = *(puVar21 + 0x22)++;                       // счётчик отсчётов, растёт с каждым вызовом
```

**Контigуйность буферов `0x200060f8`/`0x200064e0` — CONFIRMED
арифметикой:** `0x200060f8 + 0xfa·4 = 0x200064e0` (проверено вычислением,
не на глаз) — то есть `DAT_08001610 + 0xfa` (при типе `undefined4*`,
арифметика в 4-байтных элементах) указывает ровно на начало
`DAT_08001614`. Оба — 250-элементные (`0xfa`) массивы `float`/`int32`,
физически смежные.

**Когда счётчик достигает `0xf9` (249) — CONFIRMED, найдена сама запись
Re/Im:**

```c
*(undefined8 *)(puVar21 + 0x58) = uVar53;   // = 0x20005668 — Re, запись НАЙДЕНА
*(undefined8 *)(puVar21 + 0x60) = uVar53;   // = 0x20005670 — Im, запись НАЙДЕНА
// затем цикл на 249 итераций, попарно перемножающий/накапливающий
// значения из DAT_08001610[i] и DAT_08001614[i] (через FUN_0800268c/
// FUN_08002698/FUN_0800254a — double-арифметика, раздел 6.9), с
// финальным накоплением обратно в (puVar21+0x58) и (puVar21+0x60).
```

Это **CONFIRMED снимает вопрос раздела 6.11/пункта 25** "где пишется
Re/Im" — адреса и сама запись найдены и прочитаны напрямую в
декомпиляции. PROBABLE (не до конца разобрано на уровне формулы): точная
математическая операция цикла — похоже на перекрёстную корреляцию двух
временных рядов (канал 1 × канал 2 по отсчётам), а не на умножение на
опорную синус/косинус-таблицу, как предполагалось при первом заходе на
эту находку в этой же сессии — это уточнение первоначальной гипотезы,
исправлено после того, как нашлось, что `DAT_08001610` сам является
буфером записи (`DAT_08001610[idx] = ...`), а не константной таблицей.

**Полная подтверждённая цепочка на сегодня для одного цикла измерения
(стадия 6 диспетчера, раздел 6.13):**
```
DMA1_CH1 ISR → thunk_EXT_FUN_100001b8 (CCM RAM, разд. 6.7)
    накапливает сырые Re/Im для 2 каналов в 0x20007840 (+0x08/0x0c/0x10/0x14/0x20/0x24/0x28/0x2c)
        │
        ├─ FUN_08000f52, вызывается 249 раз подряд (стадия 6):
        │     читает 0x20007840, считает отношение канал1/канал2,
        │     копит 249-точечную историю в 0x200060f8 / 0x200064e0
        │     → на 249-м вызове считает Re/Im и пишет в 0x20005610+0x58/0x60
        │       (= 0x20005668/0x20005670, ОТОБРАЖАЕМЫЕ Re/Im, разд. 6.11)
        │
        └─ FUN_08002ec0(0x20007840) → FUN_0800dbf8(0x20007840) (разд. 6.12)
              считает магнитуду/отношение каналов НАПРЯМУЮ из сырого
              буфера (без 249-точечной истории) → 0x20004920
              → копируется в 0x20005610+0x50/0x54 (разд. 6.11's puVar21+0x50)
```

Иными словами, у прошивки, похоже, ДВА параллельных пути обработки
одного и того же сырого буфера `0x20007840`: быстрый (`FUN_0800dbf8`,
скаляр за один вызов, PROBABLE = похоже на грубую/промежуточную оценку
величины) и накопительный (`FUN_08000f52`, 249-точечная история,
итоговые Re/Im). Это PROBABLE интерпретация архитектуры, не
подтверждена документально — оба пути видны в коде, их конкретное
назначение (промежуточный/финальный, per-range/per-channel) не
установлено.

**Открыто:** точная формула цикла на 249 итераций (что именно

Reverse-engineering memory offsets documented in existing notes.

Linking correlator output fields to buffer offsets confirmed.

bash

cd /home/claude/RLC && grep -n "0x20000000\b" REVERSE_STATUS.md | head -10

Output

105:  SRAM (`0x20000000`) — согласуется с 40 КБ SRAM у STM32F303xB/C.
414:src=0x0802D01C dst=0x20000000 len=0x68C8 func=0x08002D6C   ; .data -> SRAM
1892:0x100001d8  r2(др.) = 0x20000000        ; литерал — БАЗА SRAM, вычислено
1895:0x100001f6  r5 = r2 + r1*2              ; = 0x20000000 + (параметр r1)*2
1901:**Ключевая находка:** источник канала A — это `0x20000000` (адрес самого
1911:`DMA1_CH1` равен `0x58e8`, итоговый адрес получается **`0x20000000 +
1914:(`0x20000000+0x58e8=0x200058e8`), не на глаз.
1918:  ×2`) и то, что `0x20000000+0x58e8` действительно даёт адрес буфера
2106:арифметики `0x20000000+0x58e8=0x200058e8`, отмеченное в 6.15, по
3775:  источников данных для корреляции. Канал A: адрес = `0x20000000`


Разбираясь в архитектуре и адресации каналов устройства.

Сопоставляя указатели буферов с адресом таблицы значений.

bash

cd /home/claude/RLC && sed -n '1862,1936p' REVERSE_STATUS.md

Output

`08003420`/`08003424` из `FUN_08003140`, минуя decompiled-текст, где эти
значения не показаны как числа), и по официальному датащиту
STM32F303xB/xC (pin definitions: PA0→ADC1_IN1, PA6→ADC2_IN3). Все
адреса регистров, битовые маски CCR1 (HTIE|TCIE|EN), ADC1_CFGR/ADC2_CFGR
(DMAEN|DMACFG), NVIC IRQ11 и GPIO-маски (`0x1`/`0x40`) подтвердились
без расхождений.

### 6.15 Связь коррелятора (раздел 6.7) с сырыми ADC-буферами (раздел 6.14) —
найден источник данных канала A — CONFIRMED арифметика, PROBABLE
интерпретация параметра, 2026-09-08

Продолжение пункта 27 раздела 13 (разбор `FUN_08000f52`) — по пути
дизассемблировал самое НАЧАЛО `thunk_EXT_FUN_100001b8` (`0x100001b8`),
которое раньше не смотрели детально (раздел 6.7 начинал разбор дальше,
с `0x10000870`).

**Настройка указателей на входные данные — CONFIRMED прямым чтением:**
```
0x100001bc  r3 = &0x200048a8            ; литерал, вычислен через .hex
0x100001c0  ip = *(r3+8)                ; = *0x200048b0
0x100001c4  r2 = [sp+0x68]              ; параметр функции (со стека)
0x100001c6  r2 = r2 + ip
0x100001c8  *(r3+8) = r2                ; накопление — тот же паттерн,
                                        ; что и для 0x200049e8 (раздел 6.8)
...
0x100001e4  r2 = *(r3+0x10)             ; = *0x200048b8
0x100001e6  r3 = *(r3+0x14)             ; = *0x200048bc — r3 ПЕРЕОПРЕДЕЛЁН,
                                        ; теперь это ДИНАМИЧЕСКИЙ указатель
                                        ; из RAM, не литерал функции
...
0x100001d8  r2(др.) = 0x20000000        ; литерал — БАЗА SRAM, вычислено
                                        ; через .hex, не на глаз
...
0x100001f6  r5 = r2 + r1*2              ; = 0x20000000 + (параметр r1)*2
                                        ; — ИСТОЧНИК ДАННЫХ КАНАЛА A
0x100001fe  r1(др.) = r3(dynamic) + r1*2 ; — источник данных канала B,
                                        ; база берётся из RAM (0x200048bc)
```

**Ключевая находка:** источник канала A — это `0x20000000` (адрес самого
начала SRAM, не случайное совпадение — резолвится через `.hex`, не
предположение) плюс параметр функции `r1`, умноженный на 2 (индекс
16-битных отсчётов).

> ⚠ Гипотеза `r1=0x58e8` ниже — ОТКЛОНЕНА в разделе 6.17 (реальный
> `r1`/`r2` оказался runtime-значением из `0x200048a2`, не литералом).
> Оставлено как есть для истории рассуждения.

Если этот параметр `r1` при вызове из ISR
`DMA1_CH1` равен `0x58e8`, итоговый адрес получается **`0x20000000 +
0x58e8 = 0x200058e8`** — это ТОЧНО совпадает с уже подтверждённым в
разделе 6.14 адресом `DMA1_CH1 CMAR1`. Проверено арифметикой
(`0x20000000+0x58e8=0x200058e8`), не на глаз.

**Что это доказывает и что нет:**
- CONFIRMED: механизм вычисления адреса источника (`SRAM_база + параметр
  ×2`) и то, что `0x20000000+0x58e8` действительно даёт адрес буфера
  DMA1.
- PROBABLE, не CONFIRMED: что параметр `r1` при РЕАЛЬНОМ вызове из ISR
  `DMA1_CH1` действительно равен `0x58e8` — это не прочитано в этой
  сессии (не разобран сам ISR `DMA1_CH1`, только косвенно выведено из
  совпадения арифметики). Раздел 6.7 ранее предполагал, что `r1` — это
  "0 для HT, halfword-значение для TC"; если так, `0x58e8` был бы
  значением именно для случая TC (transfer complete, вторая половина
  кольцевого буфera).
- Источник канала B (`0x200048bc`, динамический указатель) — где именно
  он ЗАПИСЫВАЕТСЯ, НЕ найдено. Исчерпывающий поиск по литералу
  `0x200048bc` во всём образе — 0 совпадений. Единственная НЕ-CCM-RAM
  ссылка на базовый адрес структуры `0x200048a8` (`0x08002f04`) пишет
  float-поле по смещению `+0x20`, не указатель по `+0x14`. Вероятно,
  `0x200048bc` — часть инициализированной `.data` (статическое начальное
  значение, скопированное при старте, а не записанное инструкцией `str`)
  — это НЕ проверено, требует установления границ `.data`-копирования в
  `Reset_Handler` (раздел 2) и прямого чтения соответствующего
  флеш-источника.

Verifying a register calculation against documentation.

Разбираясь в возможной ошибке трактовки регистра в документации.

Перепроверяя дизассемблированный код построчно для истины.

Прослеживая переприсвоение регистров построчно в дизассемблере.

Сверяя отклонённую гипотезу с более ранним разделом документации.

bash

cd /home/claude/RLC && python3 << 'EOF'
from capstone import *
with open("correlator.bin","rb") as f:
    blob = f.read()
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
md.detail = True
base = 0x100001b8
count = 0
for insn in md.disasm(blob, base):
    if 0x100001b8 <= insn.address <= 0x10000210:
        ops = ", ".join(f"{op.type}:{insn.op_str}" for op in [])
        print(f"0x{insn.address:08x}: {insn.mnemonic} {insn.op_str}   bytes={insn.bytes.hex()}")
EOF

Output

0x100001b8: push.w {r0, r1, r2, r4, r5, r6, r7, r8, sb, sl, fp, lr}   bytes=2de9f74f
0x100001bc: ldr r3, [pc, #0x3f8]   bytes=fe4b
0x100001be: sub sp, #0x60   bytes=98b0
0x100001c0: ldr.w ip, [r3, #8]   bytes=d3f808c0
0x100001c4: ldr r2, [sp, #0x68]   bytes=1a9a
0x100001c6: add r2, ip   bytes=6244
0x100001c8: str r2, [r3, #8]   bytes=9a60
0x100001ca: str r2, [sp, #0x50]   bytes=1492
0x100001cc: ldr.w ip, [r3, #0xc]   bytes=d3f80cc0
0x100001d0: ldr r2, [sp, #0x68]   bytes=1a9a
0x100001d2: add r2, ip   bytes=6244
0x100001d4: str r2, [r3, #0xc]   bytes=da60
0x100001d6: str r2, [sp, #0x4c]   bytes=1392
0x100001d8: ldr r2, [pc, #0x3e0]   bytes=f84a
0x100001da: ldr.w ip, [r3, #0x24]   bytes=d3f824c0
0x100001de: movs r6, #0   bytes=0026
0x100001e0: add.w sb, r2, ip, lsl #2   bytes=02eb8c09
0x100001e4: ldr r2, [r3, #0x10]   bytes=1a69
0x100001e6: ldr r3, [r3, #0x14]   bytes=5b69
0x100001e8: strd r6, r6, [sp, #0x30]   bytes=cde90c66
0x100001ec: str r6, [sp, #0x38]   bytes=0e96
0x100001ee: strd r6, r6, [sp, #0x20]   bytes=cde90866
0x100001f2: ldr.w r8, [pc, #0x3cc]   bytes=dff8cc83
0x100001f6: add.w r5, r2, r1, lsl #1   bytes=02eb4105
0x100001fa: str r6, [sp, #0x40]   bytes=1096
0x100001fc: str r6, [sp, #0x28]   bytes=0a96
0x100001fe: add.w r1, r3, r1, lsl #1   bytes=03eb4101
0x10000202: ldr.w r8, [r8]   bytes=d8f80080
0x10000206: mov r2, r5   bytes=2a46
0x10000208: mov r4, r1   bytes=0c46
0x1000020a: mov r7, r6   bytes=3746
0x1000020c: mov r3, r6   bytes=3346
0x1000020e: mov ip, r6   bytes=b446
0x10000210: mov lr, r6   bytes=b646

Disassembling raw bytes to verify an instruction.

Подтвердила ошибку в документации и подготовила разбор для пользователя.

Сопоставляя оба канала АЦП с единым опорным сигналом.

Пересчитывая количество отсчётов в каждом цикле накопления.

Референс — не сырые отсчёты, а фиксированная пара на весь вызов:

sb = 0x20000000 + 4·(*struct+0x24)      ; индекс в таблице от базы SRAM
ldrd r8, sb, [sb]                       ; ОДНИМ вызовом читает пару 32-бит слов

r8/sb не меняются во всём цикле обработки буфера — то есть это одна фиксированная опорная пара (похоже на sin/cos DDS-отсчёт при текущей фазе), которая умножается через smlad на КАЖДЫЙ новый отсчёт буфера. Всего 42 smlad в двух почти симметричных блоках: сначала буфер A (r2-пойнтер) против r8/sb, затем буфер B (r1-пойнтер) против той же самой пары r8/sb (индекс struct+0x24 между блоками не меняется) — то есть оба ADC-канала коррелируются с одним и тем же референсом за один вызов. Итог по каждому каналу — пара 64-битных сумм (произведение на первую и на вторую половину референс-слова), это и есть Re/Im-накопление.

Поправка к §6.15 (найдена ошибка в предыдущей сессии). §6.15 утверждает: "источник канала A — это 0x20000000 (адрес начала SRAM) + параметр·2". Я перепроверил побайтово:

0x100001d8: ldr r2, [pc, #0x3e0]   ; r2 = 0x20000000   (bytes: f84a)
...
0x100001e4: ldr r2, [r3, #0x10]    ; r2 ПЕРЕОПРЕДЕЛЁН = *(0x200048a8+0x10)   (bytes: 1a69)
0x100001f6: add.w r5, r2, r1, lsl#1  ; использует уже НОВЫЙ r2, не литерал

Между литералом 0x20000000 и вычислением r5 регистр r2 переприсваивается — литерал 0x20000000 используется только для вычисления sb (референс-таблица), не для буфера A. Буфер A, симметрично буферу B, — это рантайм-указатель из RAM (*0x200048b8), не флеш-константа. Старая находка про "0x20000000+0x58e8=CMAR1" — совпадение, возникшее из-за того, что литерал 0x20000000 не был отслежен до переприсваивания; сам вывод про переопределение r1 (не литерал 0x58e8) в §6.17 уже был сделан верно, но соседняя часть той же находки (про r2/буфер A) осталась неисправленной.

2. Цепочка до 0x20007840 — CONFIRMED, разрыва нет

Нашёл блок финализации (когда персистентный счётчик struct+8 достигает порога struct+0x1c):

strd sb, sl, [r0, #8]     ; struct+0x28 → 0x20007840+0x08/0x0c
strd sb, fp, [r0, #0x10]  ; struct+0x30 → 0x20007840+0x10/0x14
strd sb, sl, [r0, #0x20]  ; struct+0x38 → 0x20007840+0x20/0x24
strd sb, sl, [r0, #0x28]  ; struct+0x40 → 0x20007840+0x28/0x2c
str.w sb, [r0, #0x30]     ; счётчик отсчётов
strh.w #1, [0x200048a0]   ; флаг готовности (halfword=1, смещение +0, не +2)

Это ровно те же смещения +0x08/+0x10/+0x20/+0x28, что §6.16 уже подтвердил с потребительской стороны (FUN_08000f52 читает их как канал1 Re/Im, канал2 Re/Im). То есть producer (коррелятор) и consumer (FUN_08000f52/FUN_0800dbf8) теперь сходятся на одних и тех же адресах с обеих сторон — цепочка DMA→коррелятор→0x20007840→FUN_08000f52/FUN_0800dbf8→0x20005610→FUN_0800d578→0x20004a48 без дыр на этом участке.

Остаётся открытым: ещё 4 персистентных 64-битных поля в struct (+0x48/+0x50/+0x58/+0x60) тоже накапливаются похожим образом, но в блок финализации НЕ попадают (по крайней мере не в этом фрагменте) — их назначение не установлено (UNKNOWN). Также не пересчитано скриптом точное число отсчётов на канал за вызов (несколько развёрнутых циклов по 15-16 итераций) — оценочно, не CONFIRMED с точностью до отсчёта.
