# Descritivo Completo do Sistema - Checking

## 1. Objetivo
Sistema de controle de presença com ESP32-S3 N16R8 e 2 leitores RFID-RC522 v133, integrado a backend FastAPI e banco de dados, com envio automatizado para Microsoft Forms e tela administrativa.

## 2. Regra Principal dos Dois Leitores
- Existem 2 leitores RFID fisicamente separados.
- O leitor 1 representa a ação de check-in.
- O leitor 2 representa a ação de check-out.
- A ESP32 envia para a API o RFID lido e a ação explícita.
- A API não infere mais a ação automaticamente a partir de `users.checkin`.

## 3. Escopo Funcional
- Usuários não cadastrados vão para pendência de cadastro.
- Administração via página web com abas Check-In, Check-Out, Cadastro e Eventos.
- Operação inicial sem usuários pré-cadastrados e sem CSV.
- O estado `users.checkin` continua sendo atualizado para refletir a última operação bem-sucedida.

## 4. Componentes
- Firmware: ESP32-S3 N16R8 identificada na COM5.
- Leitores: 2x RFID-RC522 v133 operando em SPI compartilhado com CS dedicado por sensor.
- Backend: FastAPI.
- Banco: SQLite para ambiente local e PostgreSQL para produção.
- Automação: worker Playwright para envio do formulário.

## 5. Modelo de Dados
- users(rfid PK, chave, nome, projeto, checkin, time).
- pending_registrations(id, rfid único, first_seen_at, last_seen_at, attempts).
- check_events(id, rfid nullable, action, status, message, project, event_time).
- device_heartbeats(id, device_id, is_online, last_seen_at).

## 6. Fluxos de Negócio
### 6.1 Heartbeat
1. ESP32 envia heartbeat a cada 3 minutos.
2. Backend registra sinal de vida e responde status operacional.
3. Cada heartbeat recebido ou rejeitado também gera registro detalhado na aba Eventos.

### 6.1.1 Sinalização visual de inicialização e conectividade
1. Ao energizar, a ESP32 entra no estado de conexão e passa a piscar o LED azul 3 vezes a cada 1500 ms, com pulsos de 40 ms.
2. Enquanto estiver conectando ao Wi-Fi e validando resposta positiva da API na nuvem, o LED azul continua nesse padrao.
3. Quando o heartbeat recebe resposta positiva, a ESP32 entra no estado online de prontidao e o LED verde passa a piscar 1 vez a cada 2 segundos, com pulso de 20 ms.
4. A cada 3 minutos, a ESP32 envia novo heartbeat para manter a verificação operacional.
5. Se o heartbeat falhar ou a conectividade for perdida, o LED vermelho passa a piscar 1 vez a cada 2 segundos, com pulso de 40 ms.
6. Enquanto o LED vermelho estiver ativo por indisponibilidade da nuvem, a leitura de cartões fica bloqueada.
7. Se a indisponibilidade persistir por 30 segundos, a ESP32 reinicia para refazer a conexão Wi-Fi e o handshake com o sistema.

### 6.1.2 Tabela oficial de estados do LED interno

| ID | Estado | Cor / padrão | Duração | Gatilho principal |
|---|---|---|---|---|
| LED-01 | Inicializando / conectando nuvem | Azul piscando | 3 piscadas a cada 1500 ms, 40 ms cada | Boot da placa e inicio do handshake |
| LED-02 | Online em repouso | Verde piscando | 1 piscada a cada 2 segundos, 20 ms cada | Nuvem online e dispositivo pronto |
| LED-03 | Intervalo do repouso online | Apagado | ~1980 ms entre pulsos | Parte normal do ciclo de pisca verde |
| LED-04 | Processando leitura | Azul fixo | Até a resposta da API | Cartão lido e requisição em andamento |
| LED-05 | Sucesso de operação | Verde contínuo | 1000 ms | `submitted` com `green_1s` ou `green_2s` |
| LED-06 | Local atualizado | Verde contínuo | 1000 ms | `local_updated` com `green_blink_3x_1s` |
| LED-07 | Cadastro pendente | Laranja 3 piscadas | 3 x 40 ms dentro de 1500 ms | `pending_registration` com `orange_4s` |
| LED-08 | Erro de regra de negócio | Vermelho 3 piscadas | 3 x 40 ms dentro de 1500 ms | `failed` com `red_2s` |
| LED-09 | Erro operacional forte | Vermelho fixo | 1500 ms | `red_blink_5x_1s` |
| LED-10 | Offline | Vermelho piscando | 1 piscada a cada 2 segundos, 40 ms cada | Falha de Wi-Fi, API ou heartbeat |
| LED-11 | Fallback de resposta inválida | Vermelho 2 piscadas | 2 x 40 ms dentro de 1000 ms | Resposta da API não reconhecida |

Observações:
- O LED-03 é a fase apagada do LED-02. Como o pulso verde tem 20 ms em um ciclo total de 2000 ms, a fase apagada fica em aproximadamente 1980 ms.
- Os estados LED-05, LED-06, LED-07, LED-09 e LED-11 são efeitos bloqueantes no firmware atual; durante esses efeitos, o loop principal aguarda o término do padrão antes de voltar ao estado de prontidão.
- O LED-10 representa indisponibilidade operacional da nuvem. Enquanto esse estado estiver ativo, a ESP32 não processa leituras de cartão.
- Sempre que uma leitura de cartão terminar em falha (`red_2s`, `red_blink_5x_1s` ou fallback de resposta inválida), a ESP32 segura o `RST` compartilhado dos RC522 em nível baixo por 2 segundos e depois reinicia.

### 6.2 Leitura de Cartão no Sensor 1
1. O RC522 #1 detecta um cartão.
2. A ESP32 envia `rfid` e `action=checkin` para `POST /api/scan`.
3. Se o RFID não existir em `users`, o backend cria ou atualiza a pendência e responde para executar o estado LED-07, com duas piscadas laranja de 40 ms dentro de 1 segundo.
4. Assim que o padrão do LED-07 termina, a ESP32 volta ao estado online, retoma o pulso branco de prontidão e libera uma nova leitura.
5. Se o RFID existir e `users.checkin` já estiver `true`, a API não reenvia ao Forms: ela apenas atualiza `users.local`, mantém o usuário em Check-In e responde para a ESP32 executar o estado LED-06, com verde contínuo por 1000 ms.
6. Se o RFID existir e `users.checkin` estiver `false`, a própria API preenche o Microsoft Forms e busca os elementos do formulário em etapas de até 10 segundos: chave, confirmação da chave, botão Normal, botão Check-In, botão do projeto e botão Enviar.
7. Para check-in, apenas os projetos P80 e P83 são válidos no formulário.
8. Se qualquer elemento obrigatório não for encontrado no tempo definido, a API retorna erro para a ESP32 executar o estado LED-09, com LED vermelho fixo por 1500 ms, e voltar ao estado de prontidão.
9. A API aguarda até 20 segundos pelo elemento de sucesso do formulário.
10. Em sucesso, o backend grava `users.checkin=true`, atualiza `users.time` e registra o evento.
11. Em sucesso, o usuário deixa de aparecer na aba Check-Out do admin, porque o estado atual passa a ser Check-In.

### 6.3 Leitura de Cartão no Sensor 2
1. O RC522 #2 detecta um cartão.
2. A ESP32 envia `rfid` e `action=checkout` para `POST /api/scan`.
3. Se o RFID não existir em `users`, o backend cria ou atualiza a pendência e responde para executar o estado LED-07, com três piscadas laranja de 40 ms dentro de 1500 ms.
4. Assim que o padrão do LED-07 termina, a ESP32 volta ao estado online, retoma o pulso branco de prontidão e libera uma nova leitura.
5. Se o usuário existir, mas `users.checkin` estiver `false`, o backend bloqueia o checkout, responde para executar o estado LED-08, com três piscadas vermelhas de 40 ms dentro de 1500 ms, e a ESP32 reinicia ao final do padrão.
6. Se o usuário existir e `users.checkin` estiver `true`, o backend busca os elementos do formulário em etapas de até 10 segundos: chave, confirmação da chave, botão Normal, botão Check-Out e botão Enviar.
7. Se qualquer elemento obrigatório não for encontrado no tempo definido, a API retorna erro para a ESP32 executar o estado LED-09, com LED vermelho fixo por 1500 ms, e reiniciar ao final do padrão.
8. A API aguarda até 20 segundos pelo elemento de sucesso do formulário.
9. Em sucesso, o backend grava `users.checkin=false`, atualiza `users.time` e registra o evento.

### 6.4 Cadastro
1. O admin abre a aba Cadastro e visualiza pendências.
2. O admin salva Nome, Chave (4 alfanuméricos) e Projeto (P80/P83).
3. O sistema grava em `users` e remove a pendência.

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

Valores válidos para `action`:
- `checkin`
- `checkout`

## 9. Timezone e formato de horário
- Timezone operacional: Asia/Singapore.
- Persistência: datetime timezone-aware.

## 10. Requisitos de Operação
- Deploy 100% nuvem (API + DB + automação + admin).
- Monitorar falhas de XPath para manutenção da automação.
- Validar estabilidade do barramento SPI com os dois RC522 conectados.
- Definir política de retenção e auditoria de eventos.

## 11. Auditoria de Eventos
- A aba Eventos funciona como trilha operacional da API.
- O sistema registra heartbeats, scans recebidos, pendências, bloqueios, tentativas de envio ao Forms, falhas, sucessos e operações administrativas de escrita.
- No fluxo administrativo autenticado, a trilha inclui criação do admin bootstrap inicial, login, logout, solicitação de acesso administrativo, aprovação, rejeição, pedido de recadastro de senha, redefinição de senha, revogação de administrador e falhas relevantes desses mesmos endpoints.
- O módulo de arquivos de eventos também registra criação de CSV consolidado, download individual, download em lote e remoção de arquivo arquivado, sem reprocessar em cascata os próprios logs técnicos desse módulo.
- Cada evento pode incluir origem, device, local, RFID, projeto, rota da requisição, código HTTP, número de tentativas, mensagem e detalhes adicionais.
