# Phase 0 / Prompt 0.1 — Snapshot operacional da fila `forms_submissions`

> **Status:** observação somente; nenhum código foi alterado no host ou no repo durante esta coleta.
>
> **Quando:** 2026-05-19 12:59:08 UTC (≡ 2026-05-19 20:59:08 SGT, `Asia/Singapore`).
>
> **Onde:** droplet DigitalOcean `157.230.35.21:/root/checkcheck`, deploy `docker-compose.api.yml` (ver §2).

## 1. Resumo executivo

| Item | Valor |
|---|---|
| `forms-worker` rodando? | **Não.** Apenas `checkcheck-app-1` e `checkcheck-db-1` ativos. |
| Backlog `pending` | **1287** |
| `pending` com idade > 24 h | **1161** |
| `processing` travados | **2** (ids 934 e 1131) |
| `success` históricos | 1177 |
| `failed` históricos | 1 |
| Pending mais antigo | **2026-05-06 00:42:01 UTC** |
| Pending mais recente | **2026-05-19 12:59:19 UTC** (i.e. ~10 s antes do snapshot) |
| Último `processed_at` com `success` | **2026-05-06 00:36:15 UTC** |
| Último `processed_at` com `failed` | 2026-04-10 05:30:42 UTC |
| `/api/health` → `forms_worker.status` | **`disabled`** (não `unhealthy`) |
| `FORMS_QUEUE_ENABLED` no container `app` | `false` |
| Diagnóstico do plano confirmado? | **Sim** — worker ausente + enqueue continua mesmo com flag `false` |

**Janela do incidente:** o worker processou pela última vez em 2026-05-06 ~00:36 UTC. Backlog tem crescido a ~100 pendings/dia desde então (≈ 13 dias até hoje).

**Surpresa não prevista pelo plano:** o `app` está acumulando erros `sqlalchemy.exc.TimeoutError: QueuePool limit of size 6 overflow 2 reached` (ver §6). Pode interagir mal com o backlog quando o worker voltar. Investigar antes do Deploy A.

## 2. `docker compose ps` / `docker ps`

```
NAME               IMAGE                                                                           SERVICE   STATUS
checkcheck-app-1   ghcr.io/tscode-com-br/checkcheck-app:f58b551ebbb92932596b7c22267d6d5c8db7f05d   app       Up 5 hours (healthy)   0.0.0.0:8000->8000/tcp
checkcheck-db-1    postgres:16-alpine                                                              db        Up 13 days (healthy)   127.0.0.1:5432->5432/tcp
```

**Observações:**

- Nome de serviço é `app` (não `api`). O container expõe `8000` (não `18080` como o plano sugeriu). A configuração efetiva difere do que está em `docker-compose.api.yml` neste repo — provável drift entre os arquivos locais e os do host. Item a verificar no Prompt 1.1.
- A imagem é `ghcr.io/tscode-com-br/checkcheck-app:f58b551…` — corresponde ao último commit `f58b551 fix(check-web): repair accident-hook regression…`.
- Tempo "Up 5 hours" → último restart há ~5 h, coerente com um deploy recente.
- Nenhum container chamado `forms-worker` ou similar.

## 3. Contagem por `status` em `forms_submissions`

```sql
select status, count(*) from forms_submissions group by status order by 1;
```

| `status` | `count` |
|---|---|
| `failed` | 1 |
| `pending` | 1287 |
| `processing` | 2 |
| `success` | 1177 |

## 4. Idade do `pending`

```sql
select min(created_at), max(created_at) from forms_submissions where status='pending';
```

```
oldest_pending                | newest_pending
2026-05-06 00:42:01.980486+00 | 2026-05-19 12:59:19.542678+00
```

Pending > 24 h:

```sql
select count(*) from forms_submissions where status='pending' and created_at < now() - interval '24 hours';
```

→ **1161**

Backlog por dia (últimos 10 dias):

| dia (UTC) | count |
|---|---|
| 2026-05-19 | 70 (dia parcial) |
| 2026-05-18 | 130 |
| 2026-05-17 | 51 |
| 2026-05-16 | 16 |
| 2026-05-15 | 75 |
| 2026-05-14 | 124 |
| 2026-05-13 | 123 |
| 2026-05-12 | 132 |
| 2026-05-11 | 141 |
| 2026-05-10 | 50 |

## 5. Itens travados em `processing`

```sql
select id, chave, status, created_at, processed_at, last_error from forms_submissions where status='processing' order by created_at;
```

| id | chave | created_at | processed_at | last_error |
|---|---|---|---|---|
| 934 | UQW2 | 2026-05-04 05:14:11 UTC | (null) | (null) |
| 1131 | I002 | 2026-05-05 17:15:41 UTC | (null) | (null) |

Ambos travados antes do último `success` (2026-05-06 00:36) — provavelmente reservados por uma instância antiga do worker que morreu sem liberá-los. Precisarão de reset manual (`UPDATE … SET status='pending'`) antes que o worker reabra a fila, ou serão ignorados pelo `_reserve_next_submission_id` se o critério for `WHERE status='pending'`. **Não atuei sobre eles — decisão fica para o Prompt 9.3.**

## 6. `/api/health` — payload completo

```json
{
  "status": "ok",
  "app": "checking-sistema",
  "ready": true,
  "overall_status": "ok",
  "components": {
    "database": {"status": "ok", "detail": "database reachable"},
    "static_sites": {"status": "ok", "detail": "static sites ready: admin, user, transport"},
    "transport_ai_operational_readiness": {"status": "ok", "detail": "transport ai operational readiness approved"},
    "transport_ai_settings_encryption": {"status": "disabled", "detail": "transport ai settings encryption not required in deterministic mode"},
    "forms_worker": {"status": "disabled", "detail": "forms worker disabled"}
  }
}
```

**Notar:** `forms_worker.status = "disabled"` (não `degraded`/`unhealthy` como o plano previu). Causa: variável `FORMS_QUEUE_ENABLED=false` definida no container `app`. Apesar disso, o enqueue continua acontecendo (ver §7), confirmando a fragilidade documentada no plano: `enqueue_forms_submission` não consulta `settings.forms_queue_enabled`.

`.env` real do host **não contém** `FORMS_QUEUE_ENABLED` — o valor `false` deve vir de default do container/compose. Auditar em qual camada o `false` é injetado é prudente antes de virar para `true` (Prompt 1.1).

## 7. Logs do `app` (`docker logs checkcheck-app-1 --tail 1000 | grep -iE 'forms|enqueue|queue'`)

Filtro semântico (`forms`/`enqueue`) **não retornou nada** nos últimos 1000 lines — provável que o app logue enqueue em nível DEBUG ou usando outro prefixo. A fila continua sendo populada (item 2467 com `created_at` quase coincidente com o snapshot), portanto o enqueue acontece silenciosamente.

Mas o filtro casou com erros recorrentes de pool de conexões:

```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 6 overflow 2 reached,
connection timed out, timeout 5.00
```

(7 ocorrências nos últimos 1000 lines). Esse erro não é o assunto do plano `temp002`, mas é uma comorbidade a registrar:

- pode estar causando 5xx esporádicos em `/api/web/check` ou `/api/scan`;
- quando o worker subir e começar a chamar `commit()`/`refresh()` na mesma DB, o pool pode estourar mais ainda;
- recomenda-se subir `DATABASE_POOL_SIZE` no container `app` antes ou junto com a reativação do worker.

## 8. Últimos 5 `pending` (mostra que o tráfego está ativo)

```sql
select id, chave, action, projeto, ontime, request_id, created_at
from forms_submissions where status='pending' order by created_at desc limit 5;
```

| id | chave | action | projeto | ontime | request_id | created_at |
|---|---|---|---|---|---|---|
| 2467 | UPF6 | checkout | P83 | t | web-check-1779195558676-x4mh1sn1 | 2026-05-19 12:59:19 |
| 2466 | EMJM | checkout | P80 | t | web-check-1779189242656-iw4ksm1v | 2026-05-19 11:14:02 |
| 2465 | CYZ7 | checkout | P80 | t | web-check-1779188132508-c7otnxzk | 2026-05-19 10:55:32 |
| 2464 | URUS | checkout | P80 | t | web-check-1779188061112-i10d69zj | 2026-05-19 10:54:24 |
| 2463 | NS0U | checkout | P83 | t | web-check-1779188061112-i10d69zj | 2026-05-19 10:54:24 |

Todos com `request_id` prefixado `web-check-…` → origem é o Check Web (rota `/api/web/check`). Não vi `device-…` nos últimos 5, mas a amostragem é pequena.

## 9. Itens de baseline para decisões posteriores

Para alimentar os Prompts 1.x / 9.3:

1. **Backlog total** = 1287 (+ 2 stuck) = **1289 itens** a tratar quando o worker subir.
2. **Idade do mais antigo pending:** 13 dias e 12 h (de 2026-05-06 00:42 até 2026-05-19 12:59 UTC).
3. **Tráfego típico:** ~100 pendings/dia (média dos últimos 10 dias completos).
4. **Replay vs. expurgo (Prompt 9.3):** se o worker subir com 1289 itens, ele vai enviar 13 dias de check-ins/check-outs como se fossem novos para o dashboard gerencial. **Decisão precisa ser tomada com o dono do form antes de habilitar o worker em prod.**
5. **Pool exhaustion do app:** comorbidade não coberta pelo plano. Recomendo abrir issue separada e considerar `DATABASE_POOL_SIZE` antes do Deploy A.
6. **Health reporta "disabled", não "unhealthy":** o Prompt 1.2 (Validate health) precisará verificar a transição `disabled → ok`, não `unhealthy → ok` como o plano sugere.

## 10. Comandos exatos executados (para reprodutibilidade)

```bash
ssh -i ./deploy/keys/do_checkcheck root@157.230.35.21 \
  "cd /root/checkcheck && date -u && TZ=Asia/Singapore date \
   && docker compose -f docker-compose.api.yml ps \
   && docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'"

ssh -i ./deploy/keys/do_checkcheck root@157.230.35.21 \
  "cd /root/checkcheck && \
   docker compose -f docker-compose.api.yml exec -T db \
     psql -U postgres -d checking -c \
     \"select status, count(*) from forms_submissions group by status order by 1;\" && \
   docker compose -f docker-compose.api.yml exec -T db \
     psql -U postgres -d checking -c \
     \"select min(created_at), max(created_at) from forms_submissions where status='pending';\" && \
   docker compose -f docker-compose.api.yml exec -T db \
     psql -U postgres -d checking -c \
     \"select count(*) from forms_submissions where status='pending' and created_at < now() - interval '24 hours';\" && \
   docker compose -f docker-compose.api.yml exec -T db \
     psql -U postgres -d checking -c \
     \"select status, max(processed_at), count(*) from forms_submissions where status in ('success','failed') group by status order by 1;\""

ssh -i ./deploy/keys/do_checkcheck root@157.230.35.21 \
  "cd /root/checkcheck && \
   curl -sS http://127.0.0.1:8000/api/health | python3 -m json.tool && \
   docker compose -f docker-compose.api.yml exec -T db \
     psql -U postgres -d checking -c \
     \"select id, chave, status, created_at, processed_at, last_error from forms_submissions where status='processing' order by created_at;\""

ssh -i ./deploy/keys/do_checkcheck root@157.230.35.21 \
  "cd /root/checkcheck && \
   grep -iE '^FORMS_|^TZ_' .env && \
   docker compose -f docker-compose.api.yml exec -T app sh -c 'env | grep -iE \"^FORMS_|^TZ_\"' && \
   docker logs checkcheck-app-1 --tail 1000 2>&1 | grep -iE 'forms|enqueue|queue' | tail -20"
```

Nenhum comando teve efeito de escrita no host ou no banco. Snapshot validado.
