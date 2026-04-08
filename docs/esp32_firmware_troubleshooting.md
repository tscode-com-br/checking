# Troubleshooting do Firmware ESP32

## 1. Objetivo
Este documento centraliza diagnostico rapido para problemas operacionais do firmware da ESP32-S3 usado no sistema Checking.

Ele cobre principalmente:
- conectividade com Wi-Fi e API
- interpretacao dos estados do LED interno
- leituras RFID repetidas ou ausentes
- comportamento dos dois leitores RC522
- validacao basica via serial e upload

## 2. Referencias relacionadas
- Estados oficiais do LED interno: `docs/descritivo_sistema.md`, secao `6.1.2 Tabela oficial de estados do LED interno`
- Esquematico de montagem: `docs/esquematico_esp32_rc522_duplo.md`
- Identificacao da placa conectada na COM5: `docs/esp32-com5-specs.md`
- Firmware principal: `firmware/esp32_checking/esp32_checking.ino`

## 3. Leitura rapida por sintoma

### 3.1 LED azul piscando durante a inicializacao por muito tempo
Significa:
- a placa esta inicializando
- ou tentando conectar no Wi-Fi
- ou tentando validar a API
- o estado visual esperado agora e azul com 3 piscadas dentro de 1500 ms

Causas provaveis:
- SSID ou senha incorretos no firmware
- Wi-Fi indisponivel
- API inacessivel nas portas `8000` ou `8001`
- instabilidade de energia na placa

Como verificar:
1. Abrir monitor serial em `115200`.
2. Procurar mensagens como:
   - `[NET] Connecting Wi-Fi SSID=...`
   - `[NET] Wi-Fi connect failed. status=...`
   - `[NET] API not reachable on 8000/8001`
3. Confirmar que a API responde em `GET /api/health`.

### 3.2 LED vermelho piscando lentamente no offline
Significa:
- a placa entrou no estado offline
- a leitura de cartoes esta bloqueada

Observacao:
- o estado visual esperado agora e uma piscada vermelha de 40 ms a cada 2 segundos

Causas provaveis:
- perda de Wi-Fi apos entrar online
- falha no heartbeat
- API fora do ar

Como verificar:
1. Monitorar a serial e procurar:
   - `[NET] Wi-Fi lost while online.`
   - `[NET] Heartbeat failed.`
2. Validar rede local e disponibilidade do host configurado em `API_HOST`.
3. Aguardar ate 30 segundos e confirmar se a placa reinicia sozinha.

### 3.3 LED laranja em cartao nao cadastrado
Significa na especificacao atual:
- o firmware executa o estado `LED-07`, com 3 piscadas de 40 ms dentro de 1500 ms

Causas provaveis quando parecer diferente do esperado:
- o mesmo UID esta sendo relido repetidamente
- o cartao esta muito tempo apoiado sobre a antena
- o observador percebe as piscadas como luz quase continua por persistencia visual

Como verificar:
1. Aproximar o cartao nao cadastrado e remover rapidamente.
2. Observar na serial se aparece:
   - `[SCAN] UID=...`
   - `[SCAN] parsed_outcome=pending_registration`
3. Confirmar no painel administrativo que a pendencia foi criada ou atualizada.

### 3.4 Cartao nao gera resposta visivel
Possiveis causas:
- leitor RC522 nao inicializado
- falha no barramento SPI
- cartao nao esta sendo detectado
- nuvem offline bloqueando processamento

Como verificar:
1. Procurar na serial:
   - `[RC522] sensor-1 sem resposta no barramento SPI`
   - `[RC522] sensor-2 sem resposta no barramento SPI`
   - `[RC522] initialized=partial-or-failed`
2. Confirmar alimentacao, GND comum e ligacoes de `SCK`, `MISO`, `MOSI`, `RST` e `SS`.
3. Confirmar que o LED nao esta em offline vermelho antes do teste.

### 3.5 Apenas um dos leitores funciona
Possiveis causas:
- falha no pino `SS` de um dos leitores
- solda ruim
- leitor sem resposta na inicializacao
- interferencia fisica ou energia insuficiente

Como verificar:
1. Conferir logs por sensor:
   - `sensor-1`
   - `sensor-2`
2. Validar pinagem configurada no firmware:
   - `sensor-1 SS = GPIO 10`
   - `sensor-2 SS = GPIO 15`
   - `RST = GPIO 9`
3. Testar cada leitor isoladamente se necessario.

### 3.6 LED azul fica ativo e demora a sair
Significa:
- a placa esta processando a leitura e aguardando a resposta da API

Causas provaveis:
- latencia de rede
- backend lento
- timeout alto no lado HTTP da ESP32

Como verificar:
1. Observar intervalo entre `showProcessingLed()` e o log de resposta `[SCAN] response=...`.

### 3.7 ESP32 reinicia apos falha de leitura
Significa:
- a leitura do cartao terminou em falha de regra de negocio, erro operacional do backend ou resposta nao reconhecida
- o firmware foi configurado para manter o `RST` compartilhado dos RC522 em nivel baixo por 2 segundos e depois reiniciar a placa apos concluir o padrao vermelho correspondente

Como verificar:
1. Observar na serial se aparece uma das respostas de falha no scan:
   - `parsed_led=red_2s`
   - `parsed_led=red_blink_5x_1s`
   - resposta nao reconhecida seguida de fallback vermelho
2. Confirmar o log imediatamente antes do reboot:
   - `[SYS] Restarting after scan failure: ...`
3. Se o reboot ocorrer com frequencia, revisar a causa da falha na API ou no fluxo de negocio, porque o reinicio e consequencia e nao causa raiz.
2. Validar se a API esta respondendo com rapidez.
3. Revisar disponibilidade do servidor e do banco.

### 3.7 LED vermelho de fallback aparece sem motivo claro
Significa:
- a resposta da API nao foi reconhecida pelo firmware como um dos estados esperados

Causas provaveis:
- backend respondeu payload diferente do contrato atual
- corpo da resposta nao contem `led` ou `outcome` esperados
- erro HTTP ou corpo truncado

Como verificar:
1. Procurar na serial:
   - `[SCAN] response=...`
   - `[SCAN] parsed_led=...`
   - `[SCAN] parsed_outcome=...`
   - `[SCAN] Unrecognized API response; fallback red_1s activated.`
2. Comparar a resposta real com o contrato documentado em `sistema/app/schemas.py`.

## 4. Estados de LED e o que observar

| ID | Interpretacao pratica | O que verificar |
|---|---|---|
| LED-01 | Boot ou handshake | Wi-Fi, SSID, reachability da API; 3 piscadas azuis em 1500 ms |
| LED-02 | Sistema pronto | Estado normal de prontidao; 1 piscada verde de 20 ms a cada 2 s |
| LED-04 | Leitura em processamento | Latencia da API ou fila de rede |
| LED-07 | RFID nao cadastrado | Pendencia criada com 3 piscadas laranja de 40 ms |
| LED-08 | Checkout invalido | Usuario sem check-in ativo; 3 piscadas vermelhas de 40 ms |
| LED-09 | Falha operacional | Contrato da API, timeout de automacao ou erro backend; vermelho fixo por 1500 ms |
| LED-10 | Offline | Wi-Fi, heartbeat, host, portas `8000/8001`; 1 piscada vermelha de 40 ms a cada 2 s |
| LED-11 | Resposta inesperada | Divergencia entre backend e firmware |

## 5. Logs seriais importantes

Procure por estas mensagens durante o diagnostico:
- `[NET] Connecting Wi-Fi SSID=...`
- `[NET] Wi-Fi connected. IP: ...`
- `[NET] Wi-Fi connect failed. status=...`
- `[NET] API not reachable on 8000/8001`
- `[NET] Cloud heartbeat acknowledged.`
- `[NET] Cloud heartbeat failed.`
- `[NET] Wi-Fi lost while online.`
- `[RC522] sensor-1 ...`
- `[RC522] sensor-2 ...`
- `[DIAG] wifi_status=...`
- `[SCAN] UID=...`
- `[SCAN] parsed_led=...`
- `[SCAN] parsed_outcome=...`
- `[SCAN] Suppressed repeated UID=...`

## 6. Procedimento minimo de diagnostico

1. Confirmar alimentacao da placa e dos dois RC522.
2. Observar o LED logo apos o boot.
3. Abrir o monitor serial em `115200`.
4. Confirmar Wi-Fi conectado e heartbeat aceito.
5. Aproximar um cartao conhecido e um cartao nao cadastrado.
6. Verificar se o `outcome` recebido na serial combina com o LED exibido.
7. Se houver divergencia, comparar o corpo da resposta de `/api/scan` com os estados documentados.

## 7. Upload e monitoramento

Comandos usuais no workspace:
- Upload: task `Upload ESP32 Firmware`
- Monitor serial: task `Monitor ESP32 Serial`

Observacoes:
- O upload atual usa `COM5`.
- O monitor serial atual usa `115200 baud`.
- A placa identificada neste ambiente e uma `ESP32-S3`.

## 8. Quando revisar o backend junto com o firmware
Revise backend e firmware ao mesmo tempo quando houver:
- resposta da API diferente do contrato esperado
- novos valores de `led` ou `outcome`
- mudanca no fluxo de check-in ou checkout
- alteracao de timeout, fila ou comportamento do Forms
