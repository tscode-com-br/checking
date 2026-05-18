# Estrutura do Banco de Dados

Este documento descreve o schema relacional atual da aplicacao com base em `sistema/app/models.py` e nas migrations Alembic ate `0019_transport_workflow`.

## Banco principal

```text
banco_principal
|-- configuracao -> DATABASE_URL
|-- arquivo local padrao -> checking.db
|-- URL local padrao -> sqlite:///./checking.db
|-- acesso ORM -> SQLAlchemy
|-- migracoes -> Alembic
\-- tabelas -> workplaces, users, vehicles, transport_requests, transport_assignments, transport_bot_sessions, transport_notifications, pending_registrations, check_events, device_heartbeats, forms_submissions, locations, mobile_app_settings, user_sync_events, checkinghistory, admin_users, admin_access_requests
```

## Tabela: users

```text
users
|-- descricao -> cadastro principal de usuarios
|-- campos
|   |-- id -> Integer | nulo: nao | PK | autoincremento
|   |-- rfid -> String(64) | nulo: sim | unico
|   |-- chave -> String(4) | nulo: nao | unico
|   |-- nome -> String(180) | nulo: nao
|   |-- projeto -> String(3) | nulo: nao
|   |-- workplace -> String(120) | nulo: sim | FK -> workplaces.workplace
|   |-- placa -> String(9) | nulo: sim | FK -> vehicles.placa
|   |-- end_rua -> String(255) | nulo: sim
|   |-- zip -> String(10) | nulo: sim
|   |-- cargo -> String(255) | nulo: sim
|   |-- email -> String(255) | nulo: sim
|   |-- local -> String(40) | nulo: sim
|   |-- checkin -> Boolean | nulo: sim
|   |-- time -> DateTime(timezone=True) | nulo: sim
|   |-- last_active_at -> DateTime(timezone=True) | nulo: nao
|   |-- inactivity_days -> Integer | nulo: nao | default: 0
\-- restricoes de tabela
    |-- unique -> rfid
    |-- unique -> chave
    |-- foreign key -> workplace referencia workplaces.workplace
    \-- foreign key -> placa referencia vehicles.placa
```

## Tabela: vehicles

```text
vehicles
|-- descricao -> catalogo de veiculos para transporte associado ao usuario
|-- campos
|   |-- id -> Integer | nulo: nao | PK | autoincremento
|   |-- placa -> String(9) | nulo: nao | unico
|   |-- tipo -> String(16) | nulo: nao
|   |-- color -> String(40) | nulo: sim
|   |-- lugares -> Integer | nulo: nao
|   |-- tolerance -> Integer | nulo: nao | default logico na aplicacao: 0
|   \-- service_scope -> String(16) | nulo: nao | default logico na aplicacao: 'regular'
\-- restricoes de tabela
    |-- unique -> placa
    |-- check -> tipo IN ('carro', 'minivan', 'van', 'onibus')
    |-- check -> lugares >= 1 AND lugares <= 99
    |-- check -> tolerance >= 0 AND tolerance <= 240
    \-- check -> service_scope IN ('regular', 'weekend', 'extra')
```

## Tabela: workplaces

```text
workplaces
|-- descricao -> catalogo de locais de trabalho usados no transporte
|-- campos
|   |-- id -> Integer | nulo: nao | PK | autoincremento
|   |-- workplace -> String(120) | nulo: nao | unico
|   |-- address -> String(255) | nulo: nao
|   |-- zip -> String(10) | nulo: nao
|   \-- country -> String(80) | nulo: nao
\-- restricoes de tabela
    \-- unique -> workplace
```

## Tabela: transport_requests

```text
transport_requests
|-- descricao -> pedidos de transporte recorrentes ou avulsos por usuario
|-- campos
|   |-- id -> Integer | nulo: nao | PK | autoincremento
|   |-- user_id -> Integer | nulo: nao | FK -> users.id
|   |-- request_kind -> String(16) | nulo: nao
|   |-- recurrence_kind -> String(16) | nulo: nao
|   |-- requested_time -> String(5) | nulo: nao | formato logico: HH:MM
|   |-- single_date -> Date | nulo: sim | usado para pedidos do tipo extra
|   |-- created_via -> String(20) | nulo: nao | default logico na aplicacao: 'admin'
|   |-- status -> String(16) | nulo: nao | default logico na aplicacao: 'active'
|   |-- created_at -> DateTime(timezone=True) | nulo: nao
|   |-- updated_at -> DateTime(timezone=True) | nulo: nao
|   \-- cancelled_at -> DateTime(timezone=True) | nulo: sim
\-- restricoes de tabela
    |-- foreign key -> user_id referencia users.id
    |-- check -> request_kind IN ('regular', 'weekend', 'extra')
    |-- check -> recurrence_kind IN ('weekday', 'weekend', 'single_date')
    \-- check -> status IN ('active', 'cancelled')
```

## Tabela: transport_assignments

```text
transport_assignments
|-- descricao -> alocacao efetiva de cada pedido para uma data especifica
|-- campos
|   |-- id -> Integer | nulo: nao | PK | autoincremento
|   |-- request_id -> Integer | nulo: nao | FK -> transport_requests.id
|   |-- service_date -> Date | nulo: nao
|   |-- vehicle_id -> Integer | nulo: sim | FK -> vehicles.id
|   |-- status -> String(16) | nulo: nao | default logico na aplicacao: 'confirmed'
|   |-- response_message -> String(255) | nulo: sim
|   |-- assigned_by_admin_id -> Integer | nulo: sim | FK -> admin_users.id
|   |-- created_at -> DateTime(timezone=True) | nulo: nao
|   |-- updated_at -> DateTime(timezone=True) | nulo: nao
|   \-- notified_at -> DateTime(timezone=True) | nulo: sim
\-- restricoes de tabela
    |-- unique composto -> (request_id, service_date)
    |-- foreign key -> request_id referencia transport_requests.id
    |-- foreign key -> vehicle_id referencia vehicles.id
    |-- foreign key -> assigned_by_admin_id referencia admin_users.id
    \-- check -> status IN ('confirmed', 'rejected', 'cancelled')
```

## Tabela: pending_registrations

```text
pending_registrations
|-- descricao -> RFIDs vistos no dispositivo e ainda nao vinculados a um usuario
|-- campos
|   |-- id -> Integer | nulo: nao | PK | autoincremento
|   |-- rfid -> String(64) | nulo: nao | unico
|   |-- first_seen_at -> DateTime(timezone=True) | nulo: nao
|   |-- last_seen_at -> DateTime(timezone=True) | nulo: nao
|   \-- attempts -> Integer | nulo: nao | default: 1
\-- restricoes de tabela
    \-- unique -> rfid
```

## Tabela: check_events

```text
check_events
|-- descricao -> trilha de eventos e auditoria de check-in/check-out e operacoes relacionadas
|-- campos
|   |-- id -> Integer | nulo: nao | PK | autoincremento
|   |-- idempotency_key -> String(80) | nulo: nao | unico
|   |-- source -> String(20) | nulo: nao | default logico na aplicacao: 'system'
|   |-- rfid -> String(64) | nulo: sim | sem FK ativa
|   |-- action -> String(16) | nulo: nao
|   |-- status -> String(16) | nulo: nao
|   |-- message -> String(255) | nulo: nao
|   |-- details -> String(1000) | nulo: sim
|   |-- project -> String(3) | nulo: sim
|   |-- device_id -> String(80) | nulo: sim
|   |-- local -> String(40) | nulo: sim
|   |-- request_path -> String(120) | nulo: sim
|   |-- http_status -> Integer | nulo: sim
|   |-- ontime -> Boolean | nulo: sim
|   |-- event_time -> DateTime(timezone=True) | nulo: nao
|   |-- submitted_at -> DateTime(timezone=True) | nulo: sim
|   \-- retry_count -> Integer | nulo: nao | default logico na aplicacao: 0
\-- restricoes de tabela
    \-- unique -> idempotency_key
```

## Tabela: device_heartbeats

```text
device_heartbeats
|-- descricao -> heartbeat dos dispositivos fisicos conectados
|-- campos
|   |-- id -> Integer | nulo: nao | PK | autoincremento
|   |-- device_id -> String(80) | nulo: nao
|   |-- is_online -> Boolean | nulo: nao | default: true
|   \-- last_seen_at -> DateTime(timezone=True) | nulo: nao
\-- restricoes de tabela -> sem restricao adicional alem da PK
```

## Tabela: forms_submissions

```text
forms_submissions
|-- descricao -> fila de envio para o Microsoft Forms
|-- campos
|   |-- id -> Integer | nulo: nao | PK | autoincremento
|   |-- request_id -> String(80) | nulo: nao | unico
|   |-- rfid -> String(64) | nulo: sim
|   |-- action -> String(16) | nulo: nao
|   |-- chave -> String(4) | nulo: nao
|   |-- projeto -> String(3) | nulo: nao
|   |-- device_id -> String(80) | nulo: sim
|   |-- local -> String(40) | nulo: sim
|   |-- ontime -> Boolean | nulo: nao | default logico na aplicacao: true
|   |-- status -> String(16) | nulo: nao | default: 'pending'
|   |-- retry_count -> Integer | nulo: nao | default: 0
|   |-- last_error -> String(1000) | nulo: sim
|   |-- created_at -> DateTime(timezone=True) | nulo: nao
|   |-- updated_at -> DateTime(timezone=True) | nulo: nao
|   \-- processed_at -> DateTime(timezone=True) | nulo: sim
\-- restricoes de tabela
    \-- unique -> request_id
```

## Tabela: locations

```text
locations
|-- descricao -> catalogo de locais aceitos pelo app mobile
|-- campos
|   |-- id -> Integer | nulo: nao | PK | autoincremento
|   |-- local -> String(40) | nulo: nao | unico
|   |-- latitude -> Float | nulo: nao
|   |-- longitude -> Float | nulo: nao
|   |-- coordinates_json -> Text | nulo: sim | JSON textual com uma ou mais coordenadas
|   |-- tolerance_meters -> Integer | nulo: nao
|   |-- created_at -> DateTime(timezone=True) | nulo: nao
|   \-- updated_at -> DateTime(timezone=True) | nulo: nao
\-- restricoes de tabela
    \-- unique -> local
```

## Tabela: mobile_app_settings

```text
mobile_app_settings
|-- descricao -> configuracoes globais consumidas pelo app mobile
|-- campos
|   |-- id -> Integer | nulo: nao | PK | sem autoincremento
|   |-- location_update_interval_seconds -> Integer | nulo: nao | default logico: 60
|   |-- location_accuracy_threshold_meters -> Integer | nulo: nao | default: 30
|   |-- coordinate_update_frequency_json -> Text | nulo: sim | JSON textual com frequencias por faixa e dia
|   |-- created_at -> DateTime(timezone=True) | nulo: nao
|   \-- updated_at -> DateTime(timezone=True) | nulo: nao
\-- restricoes de tabela
    \-- observacao -> tabela singleton; a migration inicial cria o registro com id = 1
```

## Tabela: user_sync_events

```text
user_sync_events
|-- descricao -> historico de sincronizacao entre app mobile e estado do usuario
|-- campos
|   |-- id -> Integer | nulo: nao | PK | autoincremento
|   |-- user_id -> Integer | nulo: nao | FK -> users.id
|   |-- chave -> String(4) | nulo: nao
|   |-- rfid -> String(64) | nulo: sim
|   |-- source -> String(20) | nulo: nao
|   |-- action -> String(16) | nulo: nao
|   |-- projeto -> String(3) | nulo: sim
|   |-- local -> String(40) | nulo: sim
|   |-- ontime -> Boolean | nulo: nao | default logico na aplicacao: true
|   |-- event_time -> DateTime(timezone=True) | nulo: nao
|   |-- created_at -> DateTime(timezone=True) | nulo: nao
|   |-- source_request_id -> String(80) | nulo: sim
|   \-- device_id -> String(80) | nulo: sim
\-- restricoes de tabela
    |-- foreign key -> user_id referencia users.id
    \-- unique composto -> (source, source_request_id)
```

## Tabela: checkinghistory

```text
checkinghistory
|-- descricao -> historico consolidado de check-in/check-out, inclusive importacoes de CSV
|-- campos
|   |-- id -> Integer | nulo: nao | PK | autoincremento
|   |-- chave -> String(4) | nulo: nao
|   |-- atividade -> String(16) | nulo: nao
|   |-- projeto -> String(3) | nulo: nao
|   |-- time -> DateTime(timezone=True) | nulo: nao
|   \-- informe -> String(16) | nulo: nao
\-- restricoes de tabela
    |-- unique composto -> (chave, atividade, projeto, time, informe)
    |-- check -> atividade IN ('check-in', 'check-out')
    |-- check -> projeto IN ('P80', 'P82', 'P83')
    \-- check -> informe IN ('normal', 'retroativo')
```

## Tabela: admin_users

```text
admin_users
|-- descricao -> usuarios administrativos autorizados a acessar o painel
|-- campos
|   |-- id -> Integer | nulo: nao | PK | autoincremento
|   |-- chave -> String(4) | nulo: nao | unico
|   |-- nome_completo -> String(180) | nulo: nao
|   |-- password_hash -> String(255) | nulo: sim
|   |-- requires_password_reset -> Boolean | nulo: nao | default: false
|   |-- approved_by_admin_id -> Integer | nulo: sim | sem FK declarada
|   |-- approved_at -> DateTime(timezone=True) | nulo: sim
|   |-- password_reset_requested_at -> DateTime(timezone=True) | nulo: sim
|   |-- created_at -> DateTime(timezone=True) | nulo: nao
|   \-- updated_at -> DateTime(timezone=True) | nulo: nao
\-- restricoes de tabela
    \-- unique -> chave
```

## Tabela: admin_access_requests

```text
admin_access_requests
|-- descricao -> solicitacoes pendentes de acesso administrativo
|-- campos
|   |-- id -> Integer | nulo: nao | PK | autoincremento
|   |-- chave -> String(4) | nulo: nao | unico
|   |-- nome_completo -> String(180) | nulo: nao
|   |-- password_hash -> String(255) | nulo: nao
|   \-- requested_at -> DateTime(timezone=True) | nulo: nao
\-- restricoes de tabela
    \-- unique -> chave
```

## Observacoes

- O banco efetivo depende de `DATABASE_URL`; o arquivo local padrao do projeto e `checking.db`.
- Em ambiente local, o projeto usa SQLite por padrao, mas as migrations tambem tratam diferencas entre SQLite e outros bancos relacionais suportados pelo SQLAlchemy.
- Quando houver divergencia entre defaults do banco e defaults definidos no modelo ORM, este documento destaca como `default logico na aplicacao`.