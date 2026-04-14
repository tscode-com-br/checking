# Esquemático de Montagem - ESP32-S3 + 2x RFID-RC522 v133

## 1. Premissas da placa
Base de hardware considerada:
- ESP32-S3 identificada na COM5.
- Classe equivalente a ESP32-S3 N16R8.
- Alimentação lógica em 3.3V.
- Flash 16 MB e PSRAM 8 MB.

Referência de identificação da placa:
- ver `docs/context/esp32-com5-specs.md` para os detalhes coletados via serial

## 2. Premissas de alimentação
- Alimentar a placa ESP32 dev board em 5V pela USB-C ou VIN da placa.
- Alimentar os módulos RC522 em 3.3V.
- Manter GND comum entre ESP32 e os 2 leitores.
- Não aplicar 5V nos pinos lógicos do RC522.

## 3. Topologia recomendada
Os 2 RC522 compartilham o mesmo barramento SPI e usam pinos independentes de `SDA/SS`.

Barramento SPI compartilhado:
- ESP32 GPIO 12 -> SCK de ambos os RC522
- ESP32 GPIO 11 -> MOSI de ambos os RC522
- ESP32 GPIO 13 -> MISO de ambos os RC522
- ESP32 GPIO 9 -> RST de ambos os RC522
- ESP32 3.3V -> VCC de ambos os RC522
- ESP32 GND -> GND de ambos os RC522

Seleção individual dos leitores:
- ESP32 GPIO 10 -> SDA/SS do RC522 #1, dedicado a check-in
- ESP32 GPIO 15 -> SDA/SS do RC522 #2, dedicado a check-out

Pinos não utilizados do RC522:
- IRQ pode ficar desconectado nos dois módulos

## 4. Mapa funcional dos leitores
- RC522 #1: quando lê um cartão, o firmware envia `action=checkin`
- RC522 #2: quando lê um cartão, o firmware envia `action=checkout`
- A API executa a ação recebida, sem inferência automática baseada no estado atual do usuário

## 5. Tabela de conexão
| Sinal | RC522 #1 | RC522 #2 | ESP32-S3 |
| --- | --- | --- | --- |
| VCC | VCC | VCC | 3.3V |
| GND | GND | GND | GND |
| RST | RST | RST | GPIO 9 |
| SCK | SCK | SCK | GPIO 12 |
| MOSI | MOSI | MOSI | GPIO 11 |
| MISO | MISO | MISO | GPIO 13 |
| SDA/SS | SDA | - | GPIO 10 |
| SDA/SS | - | SDA | GPIO 15 |

## 6. Componentes adicionais recomendados
- 1 capacitor eletrolítico de 100 uF entre 5V e GND na alimentação principal
- 1 capacitor de 100 nF próximo a cada RC522 entre 3.3V e GND
- Cabos curtos no barramento SPI para reduzir ruído e queda de sinal

## 7. Checklist de montagem
1. Confirmar que a ESP32 está desligada.
2. Conectar GND comum primeiro.
3. Ligar os 2 RC522 em 3.3V.
4. Montar o barramento SPI compartilhado.
5. Conectar `SS` dedicado de cada leitor nos GPIOs corretos.
6. Conferir se não existe nenhum fio do RC522 em 5V lógico.
7. Energizar a placa e validar boot serial.

## 8. Checklist de teste elétrico
1. Medir 3.3V no VCC dos dois RC522.
2. Validar que nenhum módulo aquece de forma anormal.
3. Confirmar no serial que os 2 leitores foram inicializados.
4. Aproximar um cartão do leitor 1 e confirmar envio de `checkin`.
5. Aproximar um cartão do leitor 2 e confirmar envio de `checkout`.

## 9. Observações de integração
- O RC522 trabalha com 13.56 MHz, assim como o PN532, mas a biblioteca e o protocolo de comunicação mudam completamente.
- Como os dois leitores compartilham SPI, somente o leitor com `SS` ativo deve responder em cada transação.
- Se houver leituras instáveis, reduza o comprimento dos fios e revise o aterramento.

## 10. Alertas de segurança
- Nunca alimentar o RC522 com 5V logico.
- Nunca trocar conexões do barramento com o sistema energizado.
- Em caso de variação de pinagem da dev board, validar a serigrafia física da placa antes de energizar.
