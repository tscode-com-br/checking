# Especificacao da ESP32 conectada na COM5

Data da coleta: 2026-03-24
Porta serial: COM5

## Resumo

Foi identificada uma placa baseada em `ESP32-S3`, acessivel pela porta `COM5`.
As informacoes abaixo foram obtidas diretamente via comunicacao serial com `esptool` e `espefuse`, exceto onde indicado como inferencia.

## Interface USB-Serial

- Porta: `COM5`
- Interface detectada no Windows: `USB-Enhanced-SERIAL CH343`
- USB VID:PID: `1A86:55D3`
- Observacao: isso identifica o conversor USB-serial da placa, nao necessariamente o nome comercial da placa.

## SoC

- Chip: `ESP32-S3`
- Encapsulamento: `QFN56`
- Revisao: `v0.2`
- CPU: `Dual Core + LP Core`
- Frequencia maxima: `240 MHz`
- Cristal: `40 MHz`
- Recursos de radio: `Wi-Fi` e `Bluetooth 5 LE`
- Endereco MAC: `ac:a7:04:15:00:74`

## Memoria

- Flash detectada: `16 MB`
- Modo da flash: `quad` (4 linhas de dados)
- Tensao da flash: `3.3 V`
- ID do fabricante da flash: `0x68`
- ID do dispositivo da flash: `0x4018`
- PSRAM embutida: `8 MB`
- Vendor da PSRAM: `AP_3v3`
- Faixa termica da PSRAM reportada: `85C`

## Seguranca e eFuses

- Secure Boot: `Disabled`
- Flash Encryption: `Disabled`
- SPI Boot Crypt Count: `0x0`
- JTAG desabilitado permanentemente: `nao`
- USB Serial/JTAG interno desabilitado: `nao`
- Download mode desabilitado: `nao`
- VDD_SPI definido por eFuse: `3.3 V`

## Identidade e calibracao

- Wafer version major: `0`
- Wafer version minor: `2`
- Block version minor: `3`
- Optional Unique ID:
  - `10 89 06 01 15 f8 84 97 47 48 73 3e 19 d0 81 dc`

Foram tambem lidos dados internos de calibracao de ADC, LDO, temperatura e tensoes, o que confirma que a leitura dos eFuses foi concluida com sucesso.

## Inferencia sobre o modulo

Com base na combinacao de:

- `ESP32-S3`
- `16 MB` de flash
- `8 MB` de PSRAM

esta placa provavelmente pertence a uma classe equivalente a `ESP32-S3 N16R8`.

Importante: isso e uma inferencia. O nome exato do modulo ou da placa comercial nao pode ser garantido apenas pela serial. Para confirmar o modelo fisico exato, e preciso inspecionar a serigrafia do modulo/placa.

## Ferramentas usadas na identificacao

- `esptool v5.2.0`
- `espefuse v5.2.0`
- Windows PnP / Serial Port enumeration

## Observacoes

- O chip respondeu corretamente ao auto-reset via RTS.
- A leitura serial confirmou o SoC, a revisao, a flash, a PSRAM e o estado de seguranca.
- Algumas consultas precisaram ser executadas em sequencia porque a porta serial e de acesso exclusivo.
