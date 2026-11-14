# Результаты сравнения переноса на C с оригиналом (эмулятор)

Случайных наборов на функцию: 40. Эмулятор: Unicorn 2.1.3, Cortex-M4. Версия 2.1.4 исполняет часть кода неверно (IT-блок перед условным переходом), её использовать нельзя.

| Функция | Совпало | Замечание |
|---|---|---|
| GetPGA_GainCh1 | 40/40 |  |
| GetPGA_GainCh2 | 40/40 |  |
| GetRangeCalibConst | 40/40 |  |
| GetCurrentFrequency | 40/40 |  |
| CorrelatorScaleGetter | 40/40 |  |
| FindREFTableIndex | 40/40 |  |
| FlashPageErase_ByREF | 40/40 |  |
| FlashPageSave_ByREF | 40/40 |  |
| ReadREF_ComputeStageValue | 40/40 |  |
| ConvertCorrToPhysical | 40/40 |  |
| ComputeCorrOutput_Buf2 | 40/40 |  |
| ComplexMultiply | 40/40 |  |
| ComplexDivide | 40/40 |  |
| SinTableLookup | 40/40 |  |
| NVIC_SetPriority | 40/40 |  |
| NVIC_EnableIRQ | 40/40 |  |
| GPIO_ReadBit | 40/40 |  |
| GPIO_WriteBit | 40/40 |  |
| ADC_GetValue | 40/40 |  |
| USB_EnableGlobalInt | 40/40 |  |
| USB_ReadInterrupts | 40/40 |  |
| SoftwareDelay_ms | 40/40 |  |
| SetAutoOffThreshold | 40/40 |  |
| DAC_ConfigChannel | 40/40 |  |
| TimerClockEnable | 40/40 |  |
| TIM6_FullInit | 40/40 |  |
| SPI1_MspInit | 40/40 |  |
| USART1_MspInit | 40/40 |  |
| SysTick_Handler_body | 40/40 |  |
| SetDACFrequency | 40/40 |  |
| BatteryCalibConstants | 40/40 |  |
| PrintCharToScreenBuffer | 40/40 |  |
| RangeRelayControl | 40/40 |  |
| I2C_WriteBytes_BitBang | 40/40 |  |
| ScatterLoad_PlainCopy | 40/40 |  |
| USB_ResumeCallback | 40/40 |  |
| USB_SOF_Callback | 40/40 |  |
| USB_SuspendCallback | 40/40 |  |
| USB_IRQHandler_main | 40/40 |  |
| DoubleMultiply | 40/40 |  |
| DoubleDivide | 40/40 |  |
| DoubleAdd | 40/40 |  |
| UnsignedDiv64 | 40/40 |  |
| SignedDiv64 | 40/40 |  |
| FloatToDouble | 40/40 |  |
| Int64ToFloat | 40/40 |  |

Не покрыто проверкой: заглушки и функции-эквиваленты HAL, USB_CTR/TIM7/main/оркестратор/отрисовка, код в CCM RAM, DoubleCompareGE (результат через флаги).
