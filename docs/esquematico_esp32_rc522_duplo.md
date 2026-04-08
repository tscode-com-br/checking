# Esquematico de Montagem - ESP32-S3 + 2x RFID-RC522 v133

## 1. Premissas da placa
Base de hardware considerada:
- ESP32-S3 identificada na COM5.
- Classe equivalente a ESP32-S3 N16R8.
- Alimentacao logica em 3.3V.
- Flash 16 MB e PSRAM 8 MB.

Referencia de identificacao da placa:
- ver `docs/esp32-com5-specs.md` para os detalhes coletados via serial

## 2. Premissas de alimentacao
- Alimentar a placa ESP32 dev board em 5V pela USB-C ou VIN da placa.
- Alimentar os modulos RC522 em 3.3V.
- Manter GND comum entre ESP32 e os 2 leitores.
- Nao aplicar 5V nos pinos logicos do RC522.

## 3. Topologia recomendada
Os 2 RC522 compartilham o mesmo barramento SPI e usam pinos independentes de `SDA/SS`.

Barramento SPI compartilhado:
- ESP32 GPIO 12 -> SCK de ambos os RC522
- ESP32 GPIO 11 -> MOSI de ambos os RC522
- ESP32 GPIO 13 -> MISO de ambos os RC522
- ESP32 GPIO 9 -> RST de ambos os RC522
- ESP32 3.3V -> VCC de ambos os RC522
- ESP32 GND -> GND de ambos os RC522

Selecao individual dos leitores:
- ESP32 GPIO 10 -> SDA/SS do RC522 #1, dedicado a check-in
- ESP32 GPIO 15 -> SDA/SS do RC522 #2, dedicado a check-out

Pinos nao utilizados do RC522:
- IRQ pode ficar desconectado nos dois modulos

## 4. Mapa funcional dos leitores
- RC522 #1: quando le um cartao, o firmware envia `action=checkin`
- RC522 #2: quando le um cartao, o firmware envia `action=checkout`
- A API executa a acao recebida, sem inferencia automatica baseada no estado atual do usuario

## 5. Tabela de conexao
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
- 1 capacitor eletrolitico de 100 uF entre 5V e GND na alimentacao principal
- 1 capacitor de 100 nF proximo a cada RC522 entre 3.3V e GND
- Cabos curtos no barramento SPI para reduzir ruido e queda de sinal

## 7. Checklist de montagem
1. Confirmar que a ESP32 esta desligada.
2. Conectar GND comum primeiro.
3. Ligar os 2 RC522 em 3.3V.
4. Montar o barramento SPI compartilhado.
5. Conectar `SS` dedicado de cada leitor nos GPIOs corretos.
6. Conferir se nao existe nenhum fio do RC522 em 5V logico.
7. Energizar a placa e validar boot serial.

## 8. Checklist de teste eletrico
1. Medir 3.3V no VCC dos dois RC522.
2. Validar que nenhum modulo aquece de forma anormal.
3. Confirmar no serial que os 2 leitores foram inicializados.
4. Aproximar um cartao do leitor 1 e confirmar envio de `checkin`.
5. Aproximar um cartao do leitor 2 e confirmar envio de `checkout`.

## 9. Observacoes de integracao
- O RC522 trabalha com 13.56 MHz, assim como o PN532, mas a biblioteca e o protocolo de comunicacao mudam completamente.
- Como os dois leitores compartilham SPI, somente o leitor com `SS` ativo deve responder em cada transacao.
- Se houver leituras instaveis, reduzir o comprimento dos fios e revisar o aterramento.

## 10. Alertas de seguranca
- Nunca alimentar o RC522 com 5V logico.
- Nunca trocar conexoes do barramento com o sistema energizado.
- Em caso de variacao de pinagem da dev board, validar a serigrafia fisica da placa antes de energizar.
