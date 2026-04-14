# Árvore da API e do Website do Administrador

Este documento resume a estrutura principal da API FastAPI e do website administrativo do projeto. O recorte abaixo considera a pasta `sistema/app`, onde ficam o backend e a SPA do admin.

## Árvore de Pastas

```text
sistema/
└── app/
    ├── __init__.py
    ├── database.py
    ├── main.py
    ├── models.py
    ├── schemas.py
    ├── core/
    │   └── config.py
    ├── routers/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── device.py
    │   ├── health.py
    │   └── mobile.py
    ├── services/
    │   ├── admin_auth.py
    │   ├── admin_updates.py
    │   ├── event_archives.py
    │   ├── event_logger.py
    │   ├── forms_queue.py
    │   ├── forms_worker.py
    │   ├── location_settings.py
    │   ├── managed_locations.py
    │   ├── time_utils.py
    │   ├── user_activity.py
    │   └── user_sync.py
    └── static/
        └── admin/
            ├── app.js
            ├── index.html
            └── styles.css
```

## Responsabilidade de Cada Pasta

- `sistema/app`: núcleo da aplicação FastAPI, com backend, serviços de domínio e frontend estático do admin.
- `sistema/app/core`: configurações centrais carregadas do ambiente.
- `sistema/app/routers`: endpoints HTTP da API, separados por domínio funcional.
- `sistema/app/services`: regras de negócio, autenticação, fila do Forms, reconciliação de estado e utilitários operacionais.
- `sistema/app/static/admin`: website administrativo servido pelo próprio FastAPI.

## Responsabilidade de Cada Arquivo

- `sistema/app/__init__.py`: arquivo de pacote Python; não contém lógica operacional.
- `sistema/app/database.py`: cria `engine`, `SessionLocal`, a classe base ORM e a dependência `get_db()` usada pelas rotas para abrir e fechar sessão de banco.
- `sistema/app/main.py`: monta a aplicação FastAPI, configura CORS e sessão admin por cookie, executa o lifecycle de startup/shutdown, registra routers e serve os arquivos estáticos do admin.
- `sistema/app/models.py`: define as tabelas ORM do sistema, incluindo `users`, `pending_registrations`, `check_events`, `forms_submissions`, `user_sync_events`, `admin_users`, `admin_access_requests`, `locations` e `mobile_app_settings`.
- `sistema/app/schemas.py`: concentra os modelos Pydantic de entrada e saída da API, com validações de payload para device, mobile, admin, eventos e localizações.

- `sistema/app/core/config.py`: centraliza as configurações do sistema via `pydantic-settings`, como banco, segredos compartilhados, sessão admin, bootstrap do admin e parâmetros do Forms.

- `sistema/app/routers/__init__.py`: arquivo de pacote dos routers; não contém lógica operacional.
- `sistema/app/routers/admin.py`: implementa toda a API administrativa: login/logout/sessão, SSE, listagens de presença, inatividade, pendências, usuários, administradores, localizações, configurações mobile e arquivamento de eventos.
- `sistema/app/routers/device.py`: expõe os endpoints usados pela ESP32, incluindo heartbeat e `POST /api/scan`, com validação da chave do dispositivo, pendências RFID, atualização de estado e enfileiramento do Forms.
- `sistema/app/routers/health.py`: expõe o health check simples da aplicação para monitoramento e validação de deploy.
- `sistema/app/routers/mobile.py`: expõe a API consumida pelo app Android, incluindo leitura de estado, catálogo de localizações e envio ou sincronização de eventos mobile.

- `sistema/app/services/admin_auth.py`: implementa hash e verificação de senha, seed do administrador bootstrap, leitura da sessão administrativa e os guards de autenticação usados nas rotas protegidas.
- `sistema/app/services/admin_updates.py`: mantém o broker de atualização em tempo real do admin, com publicação de eventos para o stream SSE.
- `sistema/app/services/event_archives.py`: gera, lista, baixa, compacta e remove os arquivos CSV de arquivamento da aba Eventos.
- `sistema/app/services/event_logger.py`: padroniza a criação de registros em `check_events`, incluindo idempotência, metadados e notificação do painel quando necessário.
- `sistema/app/services/forms_queue.py`: implementa a fila persistente de submissões do Microsoft Forms, a reserva de itens pendentes e o worker em thread que processa a fila.
- `sistema/app/services/forms_worker.py`: executa a automação Playwright do Microsoft Forms, carregando XPaths, validando cada etapa, clicando nos campos corretos e retornando auditoria detalhada do processamento.
- `sistema/app/services/location_settings.py`: gerencia as configurações globais do app mobile relacionadas a localização, incluindo erro máximo aceito e a grade de frequência de atualização por dia e faixa horária.
- `sistema/app/services/managed_locations.py`: serializa e desserializa as múltiplas coordenadas de cada localização administrativa.
- `sistema/app/services/time_utils.py`: fornece utilitários de data e hora no timezone operacional de Singapura.
- `sistema/app/services/user_activity.py`: calcula dias úteis de inatividade, identifica ausência de checkout após a virada do dia e sincroniza o campo `inactivity_days` dos usuários.
- `sistema/app/services/user_sync.py`: concentra a reconciliação do estado do usuário entre RFID e mobile, criação de usuários oriundos do app, escrita de `user_sync_events` e resolução da atividade mais recente.

- `sistema/app/static/admin/index.html`: define a estrutura da SPA administrativa, com shell de login, barra de sessão, abas, tabelas, botões e modais.
- `sistema/app/static/admin/app.js`: contém toda a lógica do frontend admin em JavaScript puro, incluindo autenticação, navegação por abas, renderização das tabelas, edição inline, SSE, polling e chamadas para a API.
- `sistema/app/static/admin/styles.css`: define o visual do painel, layout responsivo, estilos das tabelas, modais, estados de erro/sucesso e identidade visual do website administrativo.

## Observação de Escopo

Este arquivo descreve apenas a estrutura da API e do website do administrador. Não inclui o app Flutter em `checking_android_new`, o firmware em `firmware/esp32_checking` nem as migrações do banco em `alembic`.