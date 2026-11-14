ENTRY(nrlc_SysTick_Handler_body)
SECTIONS
{
  . = 0x08100000;
  .text : { *(.text*) *(.rodata*) *(.glue_7*) *(.vfp11_veneer) *(.v4_bx) }
  . = ALIGN(4);
  .data : { *(.data*) }
  .bss  : { *(.bss*) *(COMMON) }
  /DISCARD/ : { *(.ARM.attributes) *(.comment) *(.ARM.exidx*) *(.ARM.extab*) }
}
