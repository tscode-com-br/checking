# Descritivo Completo do Sistema - Checking

## 1. Objetivo
Sistema de controle de presenca com ESP32 + 1 leitor PN532, integrado a backend FastAPI e banco de dados, com envio automatizado para Microsoft Forms e tela administrativa.

## 2. Regra Principal do Leitor Unico
- Existe apenas um leitor RFID.
- A ESP32 envia somente o RFID para a API.
- A API decide a acao automaticamente usando users.checkin:
	- se users.checkin = false: faz check-in.
	- se users.checkin = true: faz check-out.

## 3. Escopo Funcional
- Usuarios nao cadastrados vao para pendencia de cadastro.
- Administracao via pagina web com abas Check-In, Check-Out, Cadastro e Eventos.
- Operacao inicial sem usuarios pre-cadastrados e sem CSV.

## 4. Componentes
- Firmware: ESP32-S3 N16R8.
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

### 6.2 Leitura de Cartao (fluxo unico)
1. ESP32 envia RFID para POST /api/scan.
2. Se RFID nao existe em users: cria/atualiza pendencia e responde LED amarelo (2 piscadas).
3. Se RFID existe:
	 - users.checkin=false -> acao check-in.
	 - users.checkin=true -> acao check-out.
4. API envia formulario, atualiza users.checkin e users.time, registra evento e responde LED verde (2s) em sucesso.

### 6.3 Cadastro
1. Admin abre aba Cadastro e visualiza pendencias.
2. Admin salva Nome, Chave (4 alfanumericos) e Projeto (P80/P82/P83).
3. Sistema grava em users e remove pendencia.

## 7. Endpoints
- GET /api/health
- POST /api/device/heartbeat
- POST /api/scan
- GET /api/admin/checkin
- GET /api/admin/checkout
- GET /api/admin/pending
- POST /api/admin/users
- GET /api/admin/events

## 8. Timezone e formato de horario
- Timezone operacional: Asia/Singapore.
- Persistencia: datetime timezone-aware.

## 9. Requisitos de Operacao
- Deploy 100% nuvem (API + DB + automacao + admin).
- Monitorar falhas de XPath para manutencao da automacao.
- Definir politica de retencao e auditoria de eventos.
