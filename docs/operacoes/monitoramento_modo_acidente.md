# Monitoramento pós-deploy — Modo Acidente

## Objetivo

Garantir visibilidade contínua da saúde do Modo Acidente em produção através de 3 alertas automáticos e um script de monitoramento agendável.

---

## Alertas configurados

### Alerta 1 — Taxa de falha de e-mail > 5%

| Atributo | Valor |
|---|---|
| **Check** | `EMAIL_FAIL_RATE` |
| **Query** | `delivery_status = 'failed'` nas últimas 24h |
| **Threshold** | Taxa de falha > 5% do total enviado |
| **Severidade** | `critical` |
| **Impacto** | Usuários com `status=help` não estão sendo notificados |
| **Ação imediata** | Verificar `SMTP_HOST`/`SMTP_PASSWORD`; inspecionar `email_delivery_logs` |

**Query de diagnóstico:**
```sql
SELECT
    delivery_status,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
FROM email_delivery_logs
WHERE queued_at >= NOW() - INTERVAL '24 hours'
GROUP BY delivery_status
ORDER BY count DESC;
```

---

### Alerta 2 — Acidente "esquecido" aberto por > 24h

| Atributo | Valor |
|---|---|
| **Check** | `FORGOTTEN_ACCIDENT` |
| **Query** | `closed_at IS NULL AND opened_at < NOW() - INTERVAL '24 hours'` |
| **Threshold** | Qualquer acidente que satisfaça a condição |
| **Severidade** | `critical` |
| **Impacto** | Modo Acidente ativo impossibilita abertura de novo acidente |
| **Ação imediata** | Admin encerrar o acidente via painel ou `POST /api/admin/accidents/close` |

**Query de diagnóstico:**
```sql
SELECT
    id,
    accident_number,
    project_name_snapshot,
    opened_at,
    ROUND(EXTRACT(EPOCH FROM (NOW() - opened_at)) / 3600.0, 1) AS hours_open
FROM accidents
WHERE closed_at IS NULL
ORDER BY opened_at ASC;
```

---

### Alerta 3 — ZIP de archive > 200 MB

| Atributo | Valor |
|---|---|
| **Check** | `LARGE_ARCHIVE` |
| **Query** | `accident_archives.size_bytes > 209715200` (200 MB) |
| **Threshold** | Qualquer archive que satisfaça a condição |
| **Severidade** | `warning` |
| **Impacto** | Consumo excessivo de DO Spaces; download lento |
| **Ação** | Revisar política de vídeos (limite de duração/tamanho por upload) |

**Query de diagnóstico:**
```sql
SELECT
    aa.id AS archive_id,
    a.accident_number,
    a.project_name_snapshot,
    ROUND(aa.size_bytes / 1024.0 / 1024.0, 1) AS size_mb,
    aa.generated_at
FROM accident_archives aa
JOIN accidents a ON a.id = aa.accident_id
WHERE aa.size_bytes > 209715200
ORDER BY aa.size_bytes DESC;
```

---

## Script de monitoramento: `scripts/monitor_accident_mode.py`

Script Python autônomo que:
1. Conecta ao banco via `--database-url`
2. Executa os 3 checks (queries SQL)
3. Emite linhas de log JSON para stdout
4. Envia e-mail de alerta se houver violações e SMTP configurado

### Uso

```bash
python scripts/monitor_accident_mode.py \
    --database-url "$DATABASE_URL" \
    --alert-email ops-team@example.com \
    --smtp-host smtp.example.com \
    --smtp-port 587 \
    --smtp-user alerts@example.com \
    --smtp-password "$SMTP_PASSWORD" \
    --smtp-from-email alerts@example.com \
    --smtp-from-name "CheckCheck Monitor"
```

### Saída (JSON por linha)

```json
{"ts":"2026-05-18T10:00:00+00:00","level":"INFO","check":"EMAIL_FAIL_RATE","status":"ok","msg":"Email fail rate 0.0% is within threshold.","failed_count":0,"total_count":12,"fail_rate_pct":0.0}
{"ts":"2026-05-18T10:00:00+00:00","level":"INFO","check":"FORGOTTEN_ACCIDENT","status":"ok","msg":"No accidents open > 24h.","forgotten_count":0,"accidents":[]}
{"ts":"2026-05-18T10:00:00+00:00","level":"INFO","check":"LARGE_ARCHIVE","status":"ok","msg":"No archives exceed 200 MB.","large_archive_count":0,"threshold_mb":200,"archives":[]}
```

Em caso de violação:
```json
{"ts":"...","level":"WARNING","check":"FORGOTTEN_ACCIDENT","status":"violation","msg":"1 accident(s) open for more than 24h without being closed.","forgotten_count":1,"accidents":[{"id":7,"accident_number":3,"project":"Obra Norte","hours_open":26.4}]}
```

### Exit codes

| Código | Significado |
|---|---|
| `0` | Todos os checks OK |
| `1` | Uma ou mais violações detectadas |
| `2` | Erro fatal (DB inacessível, args faltando) |

---

## Configuração cron (recomendada: a cada 15 min)

```cron
# Accident Mode monitoring — runs every 15 minutes
*/15 * * * * root /opt/checking/.venv/bin/python \
    /opt/checking/scripts/monitor_accident_mode.py \
    --database-url "postgresql+psycopg://postgres:SENHA@localhost:5432/checking" \
    --alert-email ops-team@example.com \
    --smtp-host smtp.example.com \
    --smtp-port 587 \
    --smtp-user alerts@example.com \
    --smtp-password "SMTP_SENHA" \
    >> /var/log/checking/accident_monitor.log 2>&1
```

Adicionar em `/etc/cron.d/checking-monitor` no servidor de produção.

**Rotação do log** (`/etc/logrotate.d/checking-monitor`):
```
/var/log/checking/accident_monitor.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
}
```

---

## Configuração via Docker (alternativa ao cron)

Se o sistema roda via `docker compose`, adicionar um serviço `monitor` ao `docker-compose.api.yml`:

```yaml
  monitor:
    image: ${API_IMAGE:-checking-api}
    restart: unless-stopped
    environment:
      - DATABASE_URL=${DATABASE_URL}
    command: >
      sh -c "while true; do
        python /app/scripts/monitor_accident_mode.py
          --database-url $$DATABASE_URL
          --alert-email $$SMTP_ACCIDENT_NOTIFY_EMAIL
          --smtp-host $$SMTP_HOST
          --smtp-port $$SMTP_PORT
          --smtp-user $$SMTP_USER
          --smtp-password $$SMTP_PASSWORD
          --smtp-from-email $$SMTP_FROM_EMAIL;
        sleep 900;
      done"
    depends_on:
      - db
```

> Nota: Variáveis de ambiente com `$$` escapam a interpolação do shell no `command`.

---

## Procedimento de resposta a alertas

### EMAIL_FAIL_RATE crítico

1. Verificar variáveis SMTP: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`
2. Testar conectividade: `scripts/monitor_accident_mode.py` com `--database-url` local
3. Inspecionar logs do servidor: `docker compose logs api | grep smtp`
4. Reprocessar e-mails com falha (atualizar `retry_count` e `delivery_status='queued'`):
   ```sql
   UPDATE email_delivery_logs
   SET delivery_status = 'queued', retry_count = 0
   WHERE delivery_status = 'failed'
     AND queued_at >= NOW() - INTERVAL '24 hours';
   ```
5. Reiniciar API para disparar o worker de e-mail

### FORGOTTEN_ACCIDENT crítico

1. Identificar o acidente via query de diagnóstico acima
2. Contatar a equipe responsável pelo projeto para confirmar se o acidente é real
3. Se encerrado fisicamente: fechar via `POST /api/admin/accidents/close`
4. Se não houver admin disponível: fechar diretamente no DB:
   ```sql
   UPDATE accidents
   SET closed_at = NOW(), updated_at = NOW()
   WHERE closed_at IS NULL;
   ```

### LARGE_ARCHIVE warning

1. Identificar os arquivos grandes via query de diagnóstico
2. Verificar quota do DO Spaces bucket
3. Considerar aumentar o limite de tamanho de vídeo aceito pelo endpoint (atualmente `MAX_VIDEO_BYTES` em `web_check.py`)
4. Considerar purgar vídeos do bucket para acidentes antigos já arquivados

---

## Referências

- `scripts/monitor_accident_mode.py` — script de monitoramento
- `sistema/app/services/email_sender.py` — lógica de envio SMTP
- `sistema/app/services/object_storage.py` — lógica de storage
- `docs/descritivos/env_vars_modo_acidente.md` — variáveis de ambiente (M4)
- `docs/descritivos/migration_m3_runbook.md` — runbook de migration (M3)
- `scripts/smoke_test_accident_mode.py` — smoke test pós-deploy (M2)
