# Rollout operacional do multi-projeto por usuario

## Objetivo

Consolidar a validacao final da migracao para `user_project_memberships`, mantendo `users.projeto` apenas como projeto operacional ativo legado durante a janela de compatibilidade.

Este runbook cobre duas frentes:

1. o pacote final de regressao da entrega multi-projeto;
2. as checagens minimas de rollout para detectar inconsistencias de memberships, escopo administrativo e falhas HTTP nas rotas mais sensiveis.

## Pacote final de regressao

### JS estatico e harnesses de UI

```powershell
node --test tests/check_admin_auth_ui.test.js tests/check_admin_project_scope_ui.test.js tests/check_admin_project_timezone_ui.test.js tests/check_admin_location_projects_ui.test.js tests/check_user_location_ui.test.js tests/check_registration_widget.test.js tests/web_client_state.test.js
```

Esse comando cobre:

1. tabelas e payloads do admin com memberships plurais;
2. ausencia dos controles legados `projectSelect` e `registrationProjectSelect` nas superficies novas;
3. estado persistido do Checking Web com `projects` e `activeProject`.

### Backend fundacao e compatibilidade

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_user_project_memberships.py tests/test_admin_membership_backfill.py tests/test_api_flow_key_contracts.py
```

Esse comando cobre:

1. helpers de membership e preservacao do projeto ativo;
2. backfill/migracao conservadora de administradores;
3. contratos HTTP chave do runtime apos a migracao plural.

### Backend integracao multi-projeto

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k "test_admin_plural_user_contract_returns_memberships_and_active_project or test_admin_project_delete_preserves_users_with_remaining_memberships or test_web_user_self_registration_accepts_plural_memberships_and_seeds_active_project or test_web_project_update_preserves_existing_memberships or test_scoped_admin_user_update_preserves_memberships_outside_visible_scope or test_profile_nine_runtime_scope_uses_memberships_for_users_events_reports_and_database_events or test_mobile_sync_keeps_existing_memberships_across_sequential_legacy_project_switches or test_provider_submit_keeps_existing_memberships_when_legacy_event_changes_active_project or test_mobile_forms_submit_keeps_plural_memberships_while_queueing_single_operational_project"
```

Esse recorte confirma os criterios finais de aceite sem exigir o custo do arquivo inteiro de integracao.

## Diagnosticos minimos para rollout

### Endpoints operacionais recomendados

1. `GET /api/health/ready`
2. `GET /api/health`
3. `GET /api/admin/forms/queue/diagnostics`
4. `GET /api/admin/diagnostics/database`

Leitura esperada:

1. `health/ready` deve permanecer `200`.
2. `health` nao deve degradar por banco ou Forms worker.
3. `forms/queue/diagnostics` nao deve mostrar backlog preso ou worker `stale`.
4. `diagnostics/database` nao deve apontar latencia anomala nem saturacao de conexoes.

### SQL de conferencia

#### 1. Usuarios com zero memberships

```sql
select u.id, u.chave, u.nome, u.projeto
from users u
left join user_project_memberships upm on upm.user_id = u.id
group by u.id, u.chave, u.nome, u.projeto
having count(upm.id) = 0;
```

Resultado esperado: zero linhas.

#### 2. Usuarios cujo `users.projeto` nao pertence ao conjunto de memberships

```sql
select distinct u.id, u.chave, u.nome, u.projeto
from users u
left join user_project_memberships upm on upm.user_id = u.id
left join projects p on p.id = upm.project_id and p.name = u.projeto
where trim(coalesce(u.projeto, '')) <> ''
  and p.id is null;
```

Resultado esperado: zero linhas.

#### 3. Administradores com escopo efetivo vazio

```sql
select u.id, u.chave, u.nome, u.perfil, u.projeto
from users u
left join user_project_memberships upm on upm.user_id = u.id
where (
    coalesce(u.perfil, 0) = 0
    or cast(u.perfil as text) like '%1%'
    or cast(u.perfil as text) like '%9%'
)
group by u.id, u.chave, u.nome, u.perfil, u.projeto
having count(upm.id) = 0;
```

Resultado esperado: zero linhas.

## Rotas HTTP para observabilidade na janela de rollout

Monitorar picos de `4xx` e `5xx` nas rotas abaixo:

1. `POST /api/admin/users`
2. `POST /api/web/auth/register-user`
3. `GET /api/web/user-projects`
4. `PUT /api/web/user-projects`
5. `PUT /api/web/project`

Regras operacionais:

1. `PUT /api/web/project` continua apenas como compatibilidade e nao deve ser removido nesta etapa.
2. Qualquer aumento sustentado de `4xx` ou `5xx` nessas rotas bloqueia a continuidade do rollout ate analise.
3. Se houver erro combinado com inconsistencias nas queries SQL acima, tratar como regressao de contrato e nao apenas como ruido operacional.

Query sugerida sobre `check_events`:

```sql
select request_path, http_status, count(*) as total
from check_events
where request_path in (
    '/api/admin/users',
    '/api/web/auth/register-user',
    '/api/web/user-projects',
    '/api/web/project'
)
  and http_status >= 400
group by request_path, http_status
order by request_path, http_status;
```

Resultado esperado: sem crescimento inesperado de linhas novas para `4xx` e `5xx` durante a janela monitorada.

## Matriz de cobertura dos criterios de aceite

### 8.1 Cadastro administrativo

Coberto por:

1. `tests/check_admin_auth_ui.test.js`
2. `tests/check_admin_project_scope_ui.test.js`
3. `tests/test_api_flow.py`

### 8.2 Visualizacao administrativa

Coberto por:

1. `tests/check_admin_project_timezone_ui.test.js`
2. `tests/check_admin_location_projects_ui.test.js`
3. `tests/check_admin_auth_ui.test.js`

### 8.3 Regra de escopo do administrador

Coberto por:

1. `tests/check_admin_project_scope_ui.test.js`
2. `tests/test_api_flow.py`
3. `tests/test_user_project_memberships.py`

### 8.4 Checking Web

Coberto por:

1. `tests/check_user_location_ui.test.js`
2. `tests/check_registration_widget.test.js`
3. `tests/web_client_state.test.js`
4. `tests/test_api_flow.py`
5. `tests/test_api_flow_key_contracts.py`

### 8.5 Compatibilidade operacional

Coberto por:

1. `tests/test_user_project_memberships.py`
2. `tests/test_admin_membership_backfill.py`
3. `tests/test_api_flow.py`

## Gap residual explicito

Nao ha gap residual bloqueante nos criterios de aceite da entrega multi-projeto.

O residual conhecido e deliberado desta fase e apenas de compatibilidade controlada:

1. aliases e rotas singulares temporarias ainda permanecem para rollout seguro;
2. a remocao desse legado ficou explicitamente adiada para o Prompt 14, depois de estabilidade comprovada.