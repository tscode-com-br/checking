# Esquematico de Montagem - ESP32-S3 + 1x PN532 + LEDs

## 1. Premissas de alimentacao
Voce possui uma fonte unica ajustavel 3V-12V, 12W.

Regra de uso:
- Operar a fonte em 5V para a placa ESP32 de desenvolvimento (USB-C/VIN).
- Nao alternar seletor 3V/5V com o sistema energizado.
- Confirmar tensao com multimetro antes de ligar os componentes.

## 2. Topologia eletrica recomendada
- Fonte 5V -> entrada da ESP32 dev board.
- GND comum entre ESP32, PN532 e LEDs.
- PN532 alimentado em 3.3V logico.
- LEDs ligados aos GPIOs com resistor de 200 ohms em serie.

## 3. Ligacao dos LEDs (com os 4 resistores de 200 ohms)
- LED branco: GPIO 1 -> resistor 200 ohms -> anodo LED; catodo -> GND.
- LED amarelo: GPIO 2 -> resistor 200 ohms -> anodo LED; catodo -> GND.
- LED verde: GPIO 3 -> resistor 200 ohms -> anodo LED; catodo -> GND.
- LED vermelho: GPIO 4 -> resistor 200 ohms -> anodo LED; catodo -> GND.

## 4. Ligacao do PN532
Recomendacao adotada no firmware atual: tentativa em I2C primeiro, com fallback automatico para SPI.

Teste I2C (preferencial para o proximo diagnostico):
- ESP32 GPIO 8 -> SDA do PN532
- ESP32 GPIO 9 -> SCL do PN532
- 3.3V e GND para o PN532
- Ajustar seletor/jumpers do PN532 V3 para modo I2C

Fallback SPI (caso I2C nao responda):
- ESP32 GPIO 12 -> SCK do PN532
- ESP32 GPIO 13 -> MISO do PN532
- ESP32 GPIO 11 -> MOSI do PN532
- ESP32 GPIO 9 -> SS/CS do PN532
- 3.3V e GND para o PN532

Observacao critica:
- No teste I2C, desconectar os fios de SPI para evitar conflito eletrico no modulo.
- No teste SPI, recolocar seletor/jumpers em modo SPI.

## 5. Componentes adicionais minimos recomendados
- 1x capacitor eletrolitico 100uF entre 5V e GND na alimentacao principal.
- 1x capacitor 100nF proximo ao PN532 para desacoplamento.

## 6. Mapa funcional do leitor
- PN532 unico: envia RFID para API.
- A API decide automaticamente check-in/check-out pelo campo users.checkin.

## 7. Checklist de montagem
1. Ajustar fonte para 5V (equipamento desligado).
2. Medir 5V na saida da fonte.
3. Montar GND comum.
4. Conectar LEDs com resistor em serie.
5. Conectar PN532 em 3.3V e barramento SPI.
6. Revisar polaridade de todos os componentes.
7. Energizar e validar boot da ESP32.

## 8. Checklist de teste eletrico
1. Medir 3.3V nos pinos VCC dos PN532.
2. Confirmar sem aquecimento anormal da placa.
3. Validar heartbeat da ESP32 no backend.
4. Validar mudanca de LED por resposta de status.

## 9. Alertas de seguranca
- Nunca trocar seletor de tensao com circuito ligado.
- Nunca alimentar PN532 diretamente em 5V logico sem validar o modulo.
- Em duvida de pinagem exata da sua placa, validar com o datasheet do fabricante da sua dev board.
