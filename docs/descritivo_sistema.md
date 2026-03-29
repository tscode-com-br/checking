# Descritivo Completo do Sistema - Checking

## 1. Objetivo
Sistema de controle de presenca com ESP32-S3 N16R8 e 2 leitores RFID-RC522 v133, integrado a backend FastAPI e banco de dados, com envio automatizado para Microsoft Forms e tela administrativa.

## 2. Regra Principal dos Dois Leitores
- Existem 2 leitores RFID fisicamente separados.
- O leitor 1 representa a acao de check-in.
- O leitor 2 representa a acao de check-out.
- A ESP32 envia para a API o RFID lido e a acao explicita.
- A API nao infere mais a acao automaticamente a partir de `users.checkin`.

## 3. Escopo Funcional
- Usuarios nao cadastrados vao para pendencia de cadastro.
- Administracao via pagina web com abas Check-In, Check-Out, Cadastro e Eventos.
- Operacao inicial sem usuarios pre-cadastrados e sem CSV.
- O estado `users.checkin` continua sendo atualizado para refletir a ultima operacao bem-sucedida.

## 4. Componentes
- Firmware: ESP32-S3 N16R8 identificada na COM5.
- Leitores: 2x RFID-RC522 v133 operando em SPI compartilhado com CS dedicado por sensor.
- Backend: FastAPI.
- Banco: SQLite para ambiente local e PostgreSQL para producao.
- Automacao: worker Playwright para envio do formulario.

## 5. Modelo de Dados
- users(rfid PK, chave, nome, projeto, checkin, time).
- pending_registrations(id, rfid unico, first_seen_at, last_seen_at, attempts).
- check_events(id, rfid nullable, action, status, message, project, event_time).
- device_heartbeats(id, device_id, is_online, last_seen_at).

## 6. Fluxos de Negocio
### 6.1 Heartbeat
1. ESP32 envia heartbeat a cada 3 minutos.
2. Backend registra sinal de vida e responde status operacional.
3. Cada heartbeat recebido ou rejeitado tambem gera registro detalhado na aba Eventos.

### 6.1.1 Sinalizacao visual de inicializacao e conectividade
1. Ao energizar, a ESP32 acende imediatamente o LED interno amarelo.
2. Enquanto estiver conectando ao Wi-Fi e validando resposta positiva da API na nuvem, o LED permanece amarelo.
3. Quando o heartbeat recebe resposta positiva, o LED amarelo apaga e o LED branco passa a piscar com pulso curto de 30 ms a cada 1 segundo.
4. A cada 3 minutos a ESP32 envia novo heartbeat para manter a verificacao operacional.
5. Se o heartbeat falhar ou a conectividade for perdida, o LED branco para de piscar e o LED vermelho passa a pulsar com 30 ms a cada 1 segundo.
6. Enquanto o LED vermelho estiver ativo por indisponibilidade da nuvem, a leitura de cartoes fica bloqueada.
7. Se a indisponibilidade persistir por 30 segundos, a ESP32 reinicia para refazer a conexao Wi-Fi e o handshake com o sistema.

### 6.1.2 Tabela oficial de estados do LED interno

| ID | Estado | Cor / padrao | Duracao | Gatilho principal |
|---|---|---|---|---|
| LED-01 | Inicializando / conectando nuvem | Amarelo fixo | Indefinida | Boot da placa e inicio do handshake |
| LED-02 | Online em repouso | Branco piscando | 30 ms ligado a cada 1000 ms | Nuvem online e dispositivo pronto |
| LED-03 | Intervalo do repouso online | Apagado | ~970 ms entre pulsos | Parte normal do ciclo de pisca branco |
| LED-04 | Processando leitura | Azul fixo | Ate a resposta da API | Cartao lido e requisicao em andamento |
| LED-05 | Sucesso de operacao | Verde 4 piscadas | 4 x 20 ms dentro de 1000 ms | `submitted` com `green_1s` ou `green_2s` |
| LED-06 | Local atualizado | Verde 4 piscadas | 4 x 20 ms dentro de 1000 ms | `local_updated` com `green_blink_3x_1s` |
| LED-07 | Cadastro pendente | Laranja 2 piscadas | 2 x 40 ms dentro de 1000 ms | `pending_registration` com `orange_4s` |
| LED-08 | Erro de regra de negocio | Vermelho fixo | 2000 ms | `failed` com `red_2s` |
| LED-09 | Erro operacional forte | Vermelho 2 piscadas | 2 x 40 ms dentro de 1000 ms | `red_blink_5x_1s` |
| LED-10 | Offline | Vermelho piscando | 30 ms ligado a cada 1000 ms | Falha de Wi-Fi, API ou heartbeat |
| LED-11 | Fallback de resposta invalida | Vermelho 2 piscadas | 2 x 40 ms dentro de 1000 ms | Resposta da API nao reconhecida |

Observacoes:
- O LED-03 e a fase apagada do LED-02. Como o pulso branco tem 30 ms em um ciclo total de 1000 ms, a fase apagada fica em aproximadamente 970 ms.
- Os estados LED-05, LED-06, LED-07, LED-09 e LED-11 sao animacoes bloqueantes no firmware atual; durante esses efeitos o loop principal aguarda o termino do padrao antes de voltar ao estado de prontidao.
- O LED-10 representa indisponibilidade operacional da nuvem. Enquanto esse estado estiver ativo, a ESP32 nao processa leituras de cartao.

### 6.2 Leitura de Cartao no Sensor 1
1. O RC522 #1 detecta um cartao.
2. A ESP32 envia `rfid` e `action=checkin` para `POST /api/scan`.
3. Se o RFID nao existir em `users`, o backend cria ou atualiza a pendencia e responde para executar o estado LED-07, com duas piscadas laranja de 40 ms dentro de 1 segundo.
4. Assim que o padrao do LED-07 termina, a ESP32 volta ao estado online, retoma o pulso branco de prontidao e libera uma nova leitura.
5. Se o RFID existir e `users.checkin` ja estiver `true`, a API nao reenvia ao Forms: ela apenas atualiza `users.local`, mantem o usuario em Check-In e responde para a ESP32 executar o estado LED-06, com quatro piscadas verdes de 20 ms dentro de 1 segundo.
6. Se o RFID existir e `users.checkin` estiver `false`, a propria API preenche o Microsoft Forms e busca os elementos do formulario em etapas de ate 10 segundos: chave, confirmacao da chave, botao Normal, botao Check-In, botao do projeto e botao Enviar.
7. Para check-in, apenas os projetos P80 e P83 sao validos no formulario.
8. Se qualquer elemento obrigatorio nao for encontrado no tempo definido, a API retorna erro para a ESP32 executar o estado LED-09, com duas piscadas vermelhas de 40 ms dentro de 1 segundo, e voltar ao estado de prontidao.
9. A API aguarda ate 20 segundos pelo elemento de sucesso do formulario.
10. Em sucesso, o backend grava `users.checkin=true`, atualiza `users.time` e registra o evento.
11. Em sucesso, o usuario deixa de aparecer na aba Check-Out do admin, porque o estado atual passa a ser Check-In.

### 6.3 Leitura de Cartao no Sensor 2
1. O RC522 #2 detecta um cartao.
2. A ESP32 envia `rfid` e `action=checkout` para `POST /api/scan`.
3. Se o RFID nao existir em `users`, o backend cria ou atualiza a pendencia e responde para executar o estado LED-07, com duas piscadas laranja de 40 ms dentro de 1 segundo.
4. Assim que o padrao do LED-07 termina, a ESP32 volta ao estado online, retoma o pulso branco de prontidao e libera uma nova leitura.
5. Se o usuario existir, mas `users.checkin` estiver `false`, o backend bloqueia o checkout, responde para executar o estado LED-08 por 2 segundos e volta ao estado de prontidao.
6. Se o usuario existir e `users.checkin` estiver `true`, o backend busca os elementos do formulario em etapas de ate 10 segundos: chave, confirmacao da chave, botao Normal, botao Check-Out e botao Enviar.
7. Se qualquer elemento obrigatorio nao for encontrado no tempo definido, a API retorna erro para a ESP32 executar o estado LED-09, com duas piscadas vermelhas de 40 ms dentro de 1 segundo, e voltar ao estado de prontidao.
8. A API aguarda ate 20 segundos pelo elemento de sucesso do formulario.
9. Em sucesso, o backend grava `users.checkin=false`, atualiza `users.time` e registra o evento.

### 6.4 Cadastro
1. Admin abre aba Cadastro e visualiza pendencias.
2. Admin salva Nome, Chave (4 alfanumericos) e Projeto (P80/P83).
3. Sistema grava em `users` e remove a pendencia.

## 7. Endpoints
- GET /api/health
- POST /api/device/heartbeat
- POST /api/scan
- GET /api/admin/checkin
- GET /api/admin/checkout
- GET /api/admin/pending
- POST /api/admin/users
- GET /api/admin/events

## 8. Contrato de Leitura do Dispositivo
Payload esperado em `POST /api/scan`:

```json
{
	"rfid": "A1B2C3D4",
	"action": "checkin",
	"device_id": "ESP32-S3-01",
	"request_id": "ESP32-S3-01-sensor-1-12345-A1B2C3D4",
	"shared_key": "segredo-do-dispositivo"
}
```

Valores validos para `action`:
- `checkin`
- `checkout`

## 9. Timezone e formato de horario
- Timezone operacional: Asia/Singapore.
- Persistencia: datetime timezone-aware.

## 10. Requisitos de Operacao
- Deploy 100% nuvem (API + DB + automacao + admin).
- Monitorar falhas de XPath para manutencao da automacao.
- Validar estabilidade do barramento SPI com os dois RC522 conectados.
- Definir politica de retencao e auditoria de eventos.

## 11. Auditoria de Eventos
- A aba Eventos funciona como trilha operacional da API.
- O sistema registra heartbeats, scans recebidos, pendencias, bloqueios, tentativas de envio ao Forms, falhas, sucessos e operacoes administrativas de escrita.
- Cada evento pode incluir origem, device, local, RFID, projeto, rota da requisicao, codigo HTTP, numero de tentativas, mensagem e detalhes adicionais.
