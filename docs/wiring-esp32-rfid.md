# CheckCheck - Esquema de Montagem (ESP32-S3 N16R8 + 2x PN532 V3 + LEDs + buzzer + keypad 4x3)

Este guia mostra como montar o hardware na protoboard com base no firmware atual do projeto.

## 1) Visão geral da topologia

- ESP32 faz a leitura RFID e envia para o servidor no PC local.
- Dois leitores PN532 V3:
  - Leitor 1: entrada (`ENTRY`)
  - Leitor 2: saída (`EXIT`)
- LEDs:
  - amarelo = pronto
  - verde = sucesso
  - vermelho = erro
- Keypad numérico 4x3:
   - matrícula: apenas dígitos
   - confirmação: `#` ou `*`

## 2) Mapeamento de pinos (firmware atual)

Referência do firmware: [firmware/esp32-rfid/esp32s3_n16r8_checkcheck.ino](firmware/esp32-rfid/esp32s3_n16r8_checkcheck.ino)

### 2.1 Sinalização

| Função | GPIO ESP32 | Ligação recomendada |
|---|---:|---|
| LED amarelo (pronto) | 4 | GPIO4 -> resistor 220Ω -> anodo LED amarelo; catodo LED -> GND |
| LED verde (sucesso) | 5 | GPIO5 -> resistor 220Ω -> anodo LED verde; catodo LED -> GND |
| LED vermelho (erro) | 6 | GPIO6 -> resistor 220Ω -> anodo LED vermelho; catodo LED -> GND |
| Buzzer | 7 | GPIO7 -> pino S do módulo buzzer; VCC do módulo -> 3.3V/5V (conforme módulo), GND -> GND |

### 2.4 Keypad 4x3 (numérico)

| Pino keypad | ESP32 |
|---|---:|
| R1 | 8 |
| R2 | 9 |
| R3 | 14 |
| R4 | 15 |
| C1 | 17 |
| C2 | 18 |
| C3 | 21 |

### 2.2 RFID 1 (ENTRY - PN532 V3 em SPI)

| Pino PN532 #1 | ESP32 |
|---|---:|
| SS / NSS / SDA | 10 |
| SCK | 12 |
| MOSI | 11 |
| MISO | 13 |
| RSTO / RSTPDN | não usado |
| 3.3V | 3V3 |
| GND | GND |

### 2.3 RFID 2 (EXIT - PN532 V3 em SPI)

| Pino PN532 #2 | ESP32 |
|---|---:|
| SS / NSS / SDA | 16 |
| SCK | 12 (compartilhado) |
| MOSI | 11 (compartilhado) |
| MISO | 13 (compartilhado) |
| RSTO / RSTPDN | não usado |
| 3.3V | 3V3 |
| GND | GND |

## 3) Sequência física de montagem na protoboard

1. Posicione a ESP32 no centro da protoboard, ocupando os dois lados.
2. Leve GND da ESP32 para o trilho negativo da protoboard.
3. Leve 3V3 da ESP32 para um trilho positivo dedicado de 3.3V.
4. Configure os dois PN532 V3 para modo `SPI` (chaves/jumpers da placa).
5. Ligue os dois PN532 com 3.3V e GND primeiro.
6. Ligue os sinais SPI compartilhados dos dois PN532:
   - SCK -> GPIO12
   - MOSI -> GPIO11
   - MISO -> GPIO13
7. Ligue os pinos exclusivos de seleção do leitor:
   - ENTRY: SS/NSS/SDA -> GPIO10
   - EXIT: SS/NSS/SDA -> GPIO16
8. Monte os LEDs sempre nesta ordem elétrica:
   - GPIO -> resistor 220Ω -> anodo do LED
   - catodo do LED -> GND
9. Ligue o buzzer no GPIO7 conforme o tipo do seu módulo.
10. Ligue o keypad 4x3 nos pinos R1..R4 e C1..C3 (não usa VCC/GND).
11. Revise todos os GNDs em comum (ESP32 + 2 leitores + buzzer + LEDs).
12. Só então energize a ESP32 via USB/fonte 5V.

## 4) Diagrama lógico rápido

```text
              +-------------------+
              |   ESP32-S3 N16R8  |
              |                   |
 WIFI <------>|                   |
              | 12 SCK -----------+------ PN532_1 SCK
              | 11 MOSI ----------+------ PN532_1 MOSI
              | 13 MISO ----------+------ PN532_1 MISO
              | 10 SS (ENTRY) ----------- PN532_1 SS/NSS
              |
              | 12 SCK -----------+------ PN532_2 SCK
              | 11 MOSI ----------+------ PN532_2 MOSI
              | 13 MISO ----------+------ PN532_2 MISO
              | 16 SS (EXIT) ------------ PN532_2 SS/NSS
              |
              | 4  -> R220 -> LED amarelo -> GND
              | 5  -> R220 -> LED verde   -> GND
              | 6  -> R220 -> LED vermelho-> GND
              | 7  ----------------------- Buzzer
              | 8  ----------------------- Keypad R1
              | 9  ----------------------- Keypad R2
              | 14 ----------------------- Keypad R3
              | 15 ----------------------- Keypad R4
              | 17 ----------------------- Keypad C1
              | 18 ----------------------- Keypad C2
              | 21 ----------------------- Keypad C3
              +-------------------+

Todos os módulos compartilham GND comum.
PN532 em modo SPI e alimentação 3.3V.
```

## 5) Regras elétricas importantes

- PN532 V3 deve estar configurado em `SPI` antes da energização.
- Preferir alimentação 3.3V para manter nível lógico compatível com ESP32-S3.
- Use GND comum para todos os componentes.
- Se o buzzer for do tipo "somente 5V" e consumir corrente alta, use transistor NPN (2N2222) com resistor de base de 1kΩ.
- Em protoboard, mantenha fios curtos para reduzir ruído no RFID.

## 6) Checklist de teste após montagem

1. Energizar ESP32.
2. Confirmar LED amarelo aceso (pronto).
3. Aproximar cartão no leitor ENTRY.
4. Validar: LED amarelo apaga, verde pisca, dois beeps, amarelo volta.
5. Repetir no leitor EXIT.
6. Confirmar novo registro no dashboard em tempo real.

## 7) Cadastro de matrícula no primeiro uso

- Quando um cartão ainda não existe no servidor, a ESP32 consulta `/api/cards/check` e recebe `needsMatricula = true`.
- No firmware atual, a matrícula (7 a 10 dígitos) é digitada no **keypad 4x3**.
- Fluxo atual:
   1. Encostar cartão novo.
   2. Digitar matrícula no keypad (ex.: `1234567`).
   3. Confirmar digitando `#` ou `*`.
   3. ESP32 envia para `/api/scan` com `rfidUid`, `entrada` e `matricula`.
   4. O servidor cria o vínculo cartão/matrícula automaticamente.

Observação importante: `#` e `*` servem apenas como confirmação e **não** são enviados ao servidor.
