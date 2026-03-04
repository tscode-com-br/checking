# CheckCheck - Lista de Materiais Completa (Singapura)

Este documento traz uma BOM completa para montar o sistema com servidor em um computador local do escritório (sempre ligado), sem custo de nuvem.

## 1) Servidor local (obrigatório)

- 1x **Computador local sempre ligado** (Windows ou Linux)
  - Especificação mínima recomendada: `2 vCPU, 4GB RAM, 20GB livres`
  - Requisito: Node.js 20+ instalado

- 1x **Nobreak (UPS) para o PC** (recomendado)
  - Evita indisponibilidade por queda curta de energia

## 2) Rede local do escritório

- 1x **Roteador Wi-Fi dual-band estável** (se já não houver)
  - Modelos comuns em SG:
    - `ASUS RT-AX53U`
    - `TP-Link Archer AX23`

- Requisito operacional:
  - rede local estável entre ESP32 e PC servidor.

## 3) Leitura RFID e microcontrolador

### 3.1 Controlador

- 1x **ESP32-S3 N16R8 Dev Board**
  - Modelo em uso no projeto: `ESP32-S3 N16R8`

### 3.2 Leitores RFID

- 2x **PN532 V3 RFID/NFC Module**
  - Modelo em uso no projeto: `PN532 V3` (2 unidades)
  - Interface adotada: `SPI`
  - Motivo: leitura mais estável e robusta para uso contínuo.

- Cartões RFID:
  - **Não comprar** (cartões já existentes dos usuários).
  - Validar compatibilidade dos cartões existentes com ISO14443A (13.56MHz), padrão suportado pelo PN532.

## 4) Sinalização e áudio

- 1x LED amarelo 5mm + resistor 220Ω
- 1x LED verde 5mm + resistor 220Ω
- 1x LED vermelho 5mm + resistor 220Ω
- 1x **Buzzer ativo 3.3V/5V**
  - Modelo comum: `KY-012 Active Buzzer Module`

## 5) Montagem e alimentação

- 1x Protoboard (830 pontos) para protótipo
- Kit jumpers macho-macho e macho-fêmea
- 1x Fonte 5V dedicada para ESP32 (mínimo 2A; recomendado 3A)
- 1x Cabo USB para ESP32 (normalmente USB-C ou micro-USB, depende da placa)
- 1x Caixa de projeto (project box ABS)
  - Tamanho sugerido: ~`20cm x 15cm x 8cm`

### 5.1 Alimentar via protoboard (importante)

- **ESP32 + RFID + LEDs + buzzer**: pode alimentar pela protoboard em protótipo, com trilhas curtas e boa conexão.
- Para o cenário cloud, não há Raspberry local para alimentar na protoboard.

## 6) Opcional para produção robusta

- Etiquetas para identificar leitor `ENTRY` e `EXIT`
- TV/monitor pequeno no local para dashboard sempre visível
- 1x Nobreak pequeno para roteador + fonte ESP32 (se quiser tolerância a queda curta de energia)
- 1x Display LCD 16x2 com interface I2C (para entrada de matrícula no próprio equipamento)
- 1x Teclado matricial numérico 4x3 (digitação de matrícula de 7 a 10 dígitos, confirmação com `#` ou `*`)

## 7) Opcional - acesso externo e nuvem

- 1x Domínio público (`.com`/`.sg`) para acesso remoto
- 1x DNS gerenciado (Cloudflare, etc.)
- 1x VPS SG (`US$5–8/mês`) apenas se quiser redundância ou acesso externo sem abrir rede local

## 8) Onde comprar em Singapura

Locais/plataformas comuns com boa disponibilidade:

- Sim Lim Tower / Sim Lim Square (lojas de eletrônica)
- element14 Singapore
- RS Components Singapore
- Lazada Singapore
- Shopee Singapore

## 9) Quantidades mínimas recomendadas (MVP)

- Computador local sempre ligado: 1
- ESP32-S3 N16R8: 1
- PN532 V3: 2
- LEDs (amarelo/verde/vermelho): 1 de cada
- Resistores 220Ω: 3
- Buzzer ativo: 1
- Protoboard + jumpers: 1 kit
- Fonte 5V para ESP32/protoboard: 1
- Nobreak para PC (recomendado): 1

## 10) Compatibilidade elétrica (importante)

- ESP32-S3 e PN532 V3 devem trabalhar em **3.3V lógico** no barramento SPI.
- Verifique a posição das chaves/jumpers do PN532 V3 para modo `SPI` antes de ligar.
- Use GND comum em todos os módulos.

## 11) Custos recorrentes estimados

- Servidor local no PC: `US$0/mês` (considerando equipamento já existente)
- Opcional nuvem: VPS SG `US$5–8/mês`
- Domínio opcional: `US$10–20/ano`
