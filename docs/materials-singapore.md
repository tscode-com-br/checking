# CheckCheck - Lista de Materiais Completa (Singapura)

Este documento traz uma BOM completa para montar o sistema em produção local (escritório), com modelos específicos e quantidade sugerida.

## 1) Computação e rede

### 1.1 Raspberry (servidor)

- 1x **Raspberry Pi 4 Model B (4GB RAM)**
  - Modelo recomendado: `RPI4-MODBP-4GB`
  - Observação: 8GB também funciona, mas 4GB já atende este projeto.

- 1x **Fonte oficial Raspberry Pi 4 USB-C 5.1V 3A**
  - Modelo: `Raspberry Pi Official PSU 5.1V/3A`

- 1x **MicroSD 32GB A1/UHS-I (ou superior)**
  - Modelos recomendados:
    - `SanDisk Ultra microSDHC 32GB A1`
    - `Samsung EVO Plus 32GB`

- 1x **Case para Raspberry Pi 4 com dissipação**
  - Modelo recomendado:
    - `Argon NEO for Raspberry Pi 4` (passivo)
    - ou case com ventoinha 5V

- 1x **Cabo de rede Cat6 (opcional, recomendado)**
  - Para estabilidade maior que Wi-Fi entre Raspberry e roteador.

### 1.2 Rede local

- 1x **Roteador Wi-Fi dual-band estável** (se já não houver)
  - Modelos comuns em SG:
    - `ASUS RT-AX53U`
    - `TP-Link Archer AX23`

## 2) Leitura RFID e microcontrolador

### 2.1 Controlador

- 1x **ESP32 DevKit V1 (WROOM-32, 4MB Flash)**
  - Modelo recomendado: `DOIT ESP32 DEVKIT V1`

### 2.2 Leitores RFID

- 2x **MFRC522 13.56MHz SPI RFID Reader Module**
  - Um para `ENTRY` e outro para `EXIT`
  - Também pode iniciar com 1 unidade e usar alternância no backend.

- Cartões RFID (compatíveis 13.56MHz):
  - 20x **MIFARE Classic 1K Cards** (ou conforme equipe)

## 3) Sinalização e áudio

- 1x LED amarelo 5mm + resistor 220Ω
- 1x LED verde 5mm + resistor 220Ω
- 1x LED vermelho 5mm + resistor 220Ω
- 1x **Buzzer ativo 3.3V/5V**
  - Modelo comum: `KY-012 Active Buzzer Module`

## 4) Montagem e alimentação

- 1x Protoboard (830 pontos) para protótipo
- Kit jumpers macho-macho e macho-fêmea
- 1x Fonte 5V para ESP32 (ou USB da própria Raspberry em testes)
- 1x Cabo USB para ESP32 (normalmente USB-C ou micro-USB, depende da placa)
- 1x Caixa de projeto (project box ABS)
  - Tamanho sugerido: ~`20cm x 15cm x 8cm`

## 5) Opcional para produção robusta

- 1x HAT RTC para Raspberry (se quiser independência de NTP)
- 1x UPS mini para Raspberry
- Etiquetas para identificar leitor `ENTRY` e `EXIT`
- TV/monitor pequeno no local para dashboard sempre visível

## 6) Onde comprar em Singapura

Locais/plataformas comuns com boa disponibilidade:

- Sim Lim Tower / Sim Lim Square (lojas de eletrônica)
- element14 Singapore
- RS Components Singapore
- Lazada Singapore
- Shopee Singapore

## 7) Quantidades mínimas recomendadas (MVP)

- Raspberry Pi 4 (4GB): 1
- ESP32 DevKit V1: 1
- MFRC522: 2
- Cartões RFID MIFARE 1K: 20
- LEDs (amarelo/verde/vermelho): 1 de cada
- Resistores 220Ω: 3
- Buzzer ativo: 1
- Protoboard + jumpers: 1 kit
- Fonte Raspberry oficial: 1
- MicroSD 32GB: 1

## 8) Compatibilidade elétrica (importante)

- ESP32 e MFRC522 trabalham em **3.3V**.
- Não alimente MFRC522 com 5V direto.
- Use GND comum em todos os módulos.
