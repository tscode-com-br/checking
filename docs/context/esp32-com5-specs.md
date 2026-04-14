# Especificação da ESP32 conectada na COM5

Data da coleta: 2026-03-24
Porta serial: COM5

## Resumo

Foi identificada uma placa baseada em `ESP32-S3`, acessível pela porta `COM5`.
As informações abaixo foram obtidas diretamente via comunicação serial com `esptool` e `espefuse`, exceto onde indicado como inferência.

## Interface USB-Serial

- Porta: `COM5`
- Interface detectada no Windows: `USB-Enhanced-SERIAL CH343`
- USB VID:PID: `1A86:55D3`
- Observação: isso identifica o conversor USB-serial da placa, não necessariamente o nome comercial da placa.

## SoC

- Chip: `ESP32-S3`
- Encapsulamento: `QFN56`
- Revisão: `v0.2`
- CPU: `Dual Core + LP Core`
- Frequência máxima: `240 MHz`
- Cristal: `40 MHz`
- Recursos de rádio: `Wi-Fi` e `Bluetooth 5 LE`
- Endereço MAC: `ac:a7:04:15:00:74`

## Memória

- Flash detectada: `16 MB`
- Modo da flash: `quad` (4 linhas de dados)
- Tensão da flash: `3.3 V`
- ID do fabricante da flash: `0x68`
- ID do dispositivo da flash: `0x4018`
- PSRAM embutida: `8 MB`
- Vendor da PSRAM: `AP_3v3`
- Faixa térmica da PSRAM reportada: `85C`

## Segurança e eFuses

- Secure Boot: `Disabled`
- Flash Encryption: `Disabled`
- SPI Boot Crypt Count: `0x0`
- JTAG desabilitado permanentemente: `não`
- USB Serial/JTAG interno desabilitado: `não`
- Download mode desabilitado: `não`
- VDD_SPI definido por eFuse: `3.3 V`

## Identidade e calibração

- Wafer version major: `0`
- Wafer version minor: `2`
- Block version minor: `3`
- Optional Unique ID:
  - `10 89 06 01 15 f8 84 97 47 48 73 3e 19 d0 81 dc`

Foram também lidos dados internos de calibração de ADC, LDO, temperatura e tensões, o que confirma que a leitura dos eFuses foi concluída com sucesso.

## Inferência sobre o módulo

Com base na combinação de:

- `ESP32-S3`
- `16 MB` de flash
- `8 MB` de PSRAM

esta placa provavelmente pertence a uma classe equivalente a `ESP32-S3 N16R8`.

Importante: isso é uma inferência. O nome exato do módulo ou da placa comercial não pode ser garantido apenas pela serial. Para confirmar o modelo físico exato, é preciso inspecionar a serigrafia do módulo/placa.

## Ferramentas usadas na identificação

- `esptool v5.2.0`
- `espefuse v5.2.0`
- Windows PnP / Serial Port enumeration

## Observações

- O chip respondeu corretamente ao auto-reset via RTS.
- A leitura serial confirmou o SoC, a revisão, a flash, a PSRAM e o estado de segurança.
- Algumas consultas precisaram ser executadas em sequência porque a porta serial é de acesso exclusivo.
