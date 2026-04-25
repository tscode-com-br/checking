# Como Desfazer os Ajustes de RAM

Status deste documento: validado em 2026-04-25.

Este documento descreve, de forma operacional, como desfazer os 3 ajustes de RAM adotados para o ambiente atual do Checking e retornar o sistema ao estado anterior.

Os 3 ajustes cobertos aqui sao:

1. tuning conservador de memoria do Postgres no arquivo `docker-compose.yml`;
2. desativacao do `multipathd` no droplet;
3. desativacao do `fwupd` e do `fwupd-refresh.timer` no droplet.

Objetivo do rollback:

- restaurar o comportamento operacional anterior do banco e do host;
- voltar o droplet ao mesmo perfil de servicos ativos que existia antes dos ajustes de RAM;
- manter a aplicacao funcionando no mesmo modelo anterior.

Importante:

- execute os passos exatamente na ordem recomendada abaixo;
- se houver urgencia operacional, prefira primeiro restaurar o arquivo `docker-compose.yml` e redeployar o root;
- os ajustes de host podem ser revertidos logo depois, sem depender do deploy da aplicacao;
- estes passos assumem que nenhum outro ajuste de RAM foi aplicado manualmente depois desta mudanca.

## 1. Estado anterior que deve ser restaurado

### 1.1 Postgres no `docker-compose.yml`

Antes dos ajustes de RAM, o servico `db` no arquivo `docker-compose.yml`:

- nao tinha bloco `command:` customizado;
- iniciava apenas com a imagem `postgres:16-alpine` e os defaults do Postgres da imagem.

Valores observados no runtime anterior:

- `shared_buffers = 128MB`
- `work_mem = 4MB`
- `maintenance_work_mem = 64MB`
- `effective_cache_size = 4GB`
- `max_connections = 100`

### 1.2 Servicos do host no droplet

Antes dos ajustes de RAM, o droplet estava assim:

- `multipathd.service`: enabled e active
- `multipathd.socket`: enabled e active
- `fwupd.service`: static e active
- `fwupd-refresh.timer`: enabled e active

Esse e o estado que o rollback deve restaurar.

## 2. Ordem recomendada do rollback

Siga esta ordem:

1. restaurar o `docker-compose.yml` para o estado sem tuning do Postgres;
2. publicar e redeployar o repositório root;
3. reativar `multipathd`;
4. reativar `fwupd` e `fwupd-refresh.timer`;
5. validar que a aplicacao e os servicos do host voltaram ao estado anterior.

## 3. Como desfazer o ajuste do Postgres

Voce tem 2 formas seguras de rollback.

### 3.1 Forma recomendada: rollback pelo Git

No repositório root:

```powershell
Set-Location c:\dev\projetos\checkcheck
git status --short
git log --oneline -n 10
```

Identifique o commit que introduziu os ajustes de RAM no `docker-compose.yml`.

Depois:

```powershell
git revert <COMMIT_DOS_AJUSTES_DE_RAM>
git push origin main
```

Esse push vai disparar o workflow principal de deploy e restaurar a configuracao do Postgres no servidor para o estado anterior, desde que o revert remova o bloco `command:` do servico `db`.

### 3.2 Forma manual: restaurar o arquivo diretamente

Abra `docker-compose.yml` e remova completamente o bloco abaixo do servico `db`:

```yaml
    command:
      - postgres
      - -c
      - shared_buffers=64MB
      - -c
      - work_mem=1MB
      - -c
      - maintenance_work_mem=32MB
      - -c
      - effective_cache_size=256MB
      - -c
      - max_connections=40
```

Depois publique o rollback:

```powershell
Set-Location c:\dev\projetos\checkcheck
git add docker-compose.yml
git commit -m "Restore default Postgres memory settings"
git push origin main
```

## 4. Como confirmar que o Postgres voltou ao estado anterior

Depois que o deploy terminar, rode no droplet:

```powershell
$knownHosts = [System.IO.Path]::GetTempFileName()
Set-Content -Path $knownHosts -Value '157.230.35.21 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILcKvmHEtkkl9nI02Ds50toJUbMM4LFIWF011kR/Sq8k' -Encoding ascii
try {
  $remote = 'bash -lc ''cd /root/checkcheck && echo [shared_buffers]; docker compose exec -T db psql -U postgres -d checking -At -c "show shared_buffers"; echo [work_mem]; docker compose exec -T db psql -U postgres -d checking -At -c "show work_mem"; echo [maintenance_work_mem]; docker compose exec -T db psql -U postgres -d checking -At -c "show maintenance_work_mem"; echo [effective_cache_size]; docker compose exec -T db psql -U postgres -d checking -At -c "show effective_cache_size"; echo [max_connections]; docker compose exec -T db psql -U postgres -d checking -At -c "show max_connections"'''
  ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$knownHosts -i .\deploy\keys\do_checkcheck root@157.230.35.21 $remote
} finally {
  Remove-Item $knownHosts -Force -ErrorAction SilentlyContinue
}
```

Resultado esperado para o estado anterior:

- `shared_buffers = 128MB`
- `work_mem = 4MB`
- `maintenance_work_mem = 64MB`
- `effective_cache_size = 4GB`
- `max_connections = 100`

## 5. Como desfazer a desativacao do `multipathd`

No droplet, execute:

```bash
systemctl unmask multipathd.service multipathd.socket 2>/dev/null || true
systemctl enable --now multipathd.socket
systemctl enable --now multipathd.service
```

Se quiser executar a partir desta maquina Windows:

```powershell
$knownHosts = [System.IO.Path]::GetTempFileName()
Set-Content -Path $knownHosts -Value '157.230.35.21 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILcKvmHEtkkl9nI02Ds50toJUbMM4LFIWF011kR/Sq8k' -Encoding ascii
try {
  $remote = 'bash -lc ''systemctl unmask multipathd.service multipathd.socket 2>/dev/null || true; systemctl enable --now multipathd.socket; systemctl enable --now multipathd.service'''
  ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$knownHosts -i .\deploy\keys\do_checkcheck root@157.230.35.21 $remote
} finally {
  Remove-Item $knownHosts -Force -ErrorAction SilentlyContinue
}
```

## 6. Como desfazer a desativacao do `fwupd`

No droplet, execute:

```bash
systemctl unmask fwupd.service fwupd-refresh.service fwupd-offline-update.service 2>/dev/null || true
systemctl enable --now fwupd-refresh.timer
systemctl start fwupd.service
```

Se quiser executar a partir desta maquina Windows:

```powershell
$knownHosts = [System.IO.Path]::GetTempFileName()
Set-Content -Path $knownHosts -Value '157.230.35.21 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILcKvmHEtkkl9nI02Ds50toJUbMM4LFIWF011kR/Sq8k' -Encoding ascii
try {
  $remote = 'bash -lc ''systemctl unmask fwupd.service fwupd-refresh.service fwupd-offline-update.service 2>/dev/null || true; systemctl enable --now fwupd-refresh.timer; systemctl start fwupd.service'''
  ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$knownHosts -i .\deploy\keys\do_checkcheck root@157.230.35.21 $remote
} finally {
  Remove-Item $knownHosts -Force -ErrorAction SilentlyContinue
}
```

## 7. Como validar que os servicos do host voltaram ao estado anterior

No droplet, confira:

```bash
systemctl is-enabled multipathd.service
systemctl is-enabled multipathd.socket
systemctl is-active multipathd.service
systemctl is-active multipathd.socket

systemctl is-enabled fwupd-refresh.timer
systemctl is-active fwupd-refresh.timer
systemctl is-active fwupd.service
```

Resultado esperado para o estado anterior:

- `multipathd.service` = `enabled`
- `multipathd.socket` = `enabled`
- `multipathd.service` = `active`
- `multipathd.socket` = `active`
- `fwupd-refresh.timer` = `enabled`
- `fwupd-refresh.timer` = `active`
- `fwupd.service` = `active`

## 8. Validacao final da aplicacao depois do rollback completo

Depois de restaurar o compose e reativar os servicos do host, valide a aplicacao publicamente:

```powershell
Invoke-WebRequest https://tscode.com.br/api/health -UseBasicParsing
Invoke-WebRequest https://tscode.com.br/checking/admin -UseBasicParsing
Invoke-WebRequest https://tscode.com.br/checking/user -UseBasicParsing
Invoke-WebRequest https://www.tscode.com.br/api/health -UseBasicParsing
```

Resposta esperada da API:

```json
{"status":"ok","app":"checking-sistema"}
```

## 9. Checklist de rollback completo

Use esta checklist no final:

- o `docker-compose.yml` voltou a nao ter bloco `command:` no servico `db`;
- o deploy do root terminou com sucesso depois do rollback do compose;
- o Postgres voltou aos defaults observados anteriormente;
- `multipathd.service` voltou a `enabled` e `active`;
- `multipathd.socket` voltou a `enabled` e `active`;
- `fwupd-refresh.timer` voltou a `enabled` e `active`;
- `fwupd.service` voltou a `active`;
- `https://tscode.com.br/api/health` respondeu `200`;
- `https://tscode.com.br/checking/admin` respondeu `200`;
- `https://tscode.com.br/checking/user` respondeu `200`.

Se todos os itens acima estiverem corretos, o ambiente voltou ao estado operacional anterior aos ajustes de RAM.