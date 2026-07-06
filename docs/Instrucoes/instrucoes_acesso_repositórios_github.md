# Guia Didatico de Commit, Push e Deploy por Repositorio

Status: revisado e validado em 2026-06-09. Secoes 1.7 e 2.6 (app Kotlin, repo `checking-kotlin`) adicionadas em 2026-06-17.

Objetivo deste guia:

1. explicar, sem ambiguidade, onde fazer commit e push para cada parte do projeto;
2. explicar quais repositorios realmente fazem deploy automatico hoje;
3. ensinar como monitorar cada deploy no GitHub Actions;
4. ensinar como diagnosticar e corrigir falhas direto no servidor DigitalOcean.

---

## 0) Resumo executivo (leia primeiro)

Hoje, producao publica em dois caminhos:

1. Repo `tscode-com-br/checking` (root monolito): publica API + Check Web + Transport + infra no Droplet.
2. Repo `tscode-com-br/checking-admin2`: publica somente o Admin v2.

Diagnostico real do estado atual dos workflows (auditado via CLI em 2026-06-09):

| Repo | Workflow de deploy | Estado atual | Publica em producao hoje? |
| --- | --- | --- | --- |
| `checking` | `Deploy OceanDrive` | `active` | **SIM** |
| `checking-admin2` | `Deploy to DigitalOcean` | `active` | **SIM** |
| `checking-api` | `Deploy to DigitalOcean` | `disabled_manually` | **NAO** |
| `checking-webapp` | `Deploy to DigitalOcean` | `disabled_manually` | **NAO** |
| `checking-transport` | `Deploy to DigitalOcean` | `disabled_manually` | **NAO** |
| `checking_app_flutter` | (sem workflow) | n/a | **NAO** (nao deploya Droplet) |
| `checking-kotlin` | (sem workflow de deploy) | n/a | **NAO** (app mobile nativo; distribui via Play Store, nao deploya Droplet) |

Ponto que mais confunde:

- No repo `checking`, existe tambem um workflow chamado `Deploy to DigitalOcean`.
- Ele aparece como `active`, mas o job fica `skipped` por condicao de repositorio (`if: github.repository == 'tscode-com-br/checking-api'`).
- O workflow correto para monitorar deploy de producao no root e **sempre** `Deploy OceanDrive`.

---

## 1) Mapa de ownership: o que commitar em cada repositorio

### 1.1 Root monolito (`c:\dev\projetos\checkcheck`)

Use este repo para:

1. backend Python (API, routers, services, models, migrations);
2. frontend Check Web em `sistema/app/static/check`;
3. frontend Transport em `sistema/app/static/transport`;
4. infra (docker-compose, nginx, deploy scripts, workflows, docs do root).

Push correto para publicar producao:

- `git push origin main`

### 1.2 Admin v2 (`c:\dev\projetos\checkcheck\sistema\app\static\admin2`)

Use este sub-repo para:

1. frontend Admin v2 (JS/CSS/HTML proprio do admin2).

Push correto para publicar admin:

- `git push origin main`

### 1.3 Check Web sub-repo (`c:\dev\projetos\checkcheck\sistema\app\static\check`)

Hoje este repo existe, mas o deploy automatico dele esta desativado (`disabled_manually`) e o dominio publico nao e servido por `user-web`.

Conclusao pratica:

1. push aqui pode servir como espelho historico;
2. **nao** e o caminho para publicar usuarios finais;
3. para publicar Check Web, commite no root e push em `origin/main` do root.

### 1.4 Transport sub-repo (`c:\dev\projetos\checkcheck\sistema\app\static\transport`)

Mesmo caso do Check Web:

1. workflow do sub-repo esta desativado;
2. dominio publico nao sai de `transport-web`;
3. para publicar Transport, commite no root e push em `origin/main` do root.

### 1.5 API remote (`api`) dentro do root

No root existe `remote api -> checking-api`, mas o deploy efetivo do repo `checking-api` esta desativado.

Conclusao pratica:

1. `git push api main` hoje nao e caminho canonico de publicacao;
2. API publica via root monolito (`git push origin main` no root).

### 1.6 Flutter (`c:\dev\projetos\checkcheck\checking_android_new`)

Este repo tem ownership proprio, mas nao possui workflow de deploy para o Droplet.

Conclusao pratica:

1. push publica codigo mobile no GitHub;
2. nao publica servicos no servidor DigitalOcean.

### 1.7 App Kotlin (`c:\dev\projetos\checkcheck\checking_kotlin`)

Aplicativo mobile nativo (Kotlin + Jetpack Compose). Repositorio proprio: `tscode-com-br/checking-kotlin`.

Topologia (entenda ANTES de commitar):

1. `checking_kotlin` e um repositorio git **independente** (tem o seu proprio `.git`), apenas aninhado dentro da pasta do root.
2. O root monolito **ignora** `checking_kotlin` (ha uma entrada `checking_kotlin` no `.gitignore` do root). Logo, os arquivos do app NAO aparecem no `git status` do root e NUNCA sao publicados pelo root.
3. Remotes deste repo:
   - `origin` -> `https://github.com/tscode-com-br/checking-kotlin.git` (ativo e canonico).
   - `archived-origin` -> `https://github.com/tscode-com-br/checking_app_kotlin.git` (historico antigo do codebase `com.br.checkingnative`; nao usar para publicar).
4. Nao possui workflow de **deploy**: push nao publica em servidor. A distribuicao para usuarios e via Play Store (AAB), processo separado.
5. **Possui, porem, um workflow de CI** (`.github/workflows/android.yml`, nome "Android CI") que roda a CADA push/PR em `main` — NAO faz deploy, mas executa o job `build` (testes unitarios + Android lint + `assembleDebug`). Falha de CI gera e-mail do GitHub para os watchers. Pontos praticos:
   - Os testes instrumentados em emulador (job `instrumented`) rodam **sob demanda**: incluir `[ci-instrumented]` na mensagem do commit.
   - O job `release` (gera AAB) so dispara em tag `v*`.
   - As actions sao pinadas por SHA; um SHA invalido faz TODOS os jobs morrerem em 2-3s na fase "Prepare all required actions" (resolver o SHA correto com `gh api repos/<owner>/<action>/commits/<tag> --jq .sha`).
   - O gatilho noturno `schedule` (cron diario) foi **removido em 2026-06-24** por gerar e-mails de falha diarios; o gate de `ktlint` esta desabilitado no CI ate uma limpeza dedicada (`./gradlew ktlintFormat`), pois ha ~4,7k violacoes de estilo pre-existentes.

Segredos que NUNCA podem ser commitados (ja cobertos pelo `.gitignore` do app):

1. `keystore.properties` (credenciais de assinatura) — ha `keystore.properties.example` versionado como modelo.
2. `local.properties` (caminho do SDK Android).
3. `*.jks` / `*.keystore` (keystore de assinatura).

Artefatos que tambem ficam de fora do commit: `app/build/` (saida de build, centenas de MB), `.gradle/`, `.kotlin/`, `/.idea/`.

---

## 2) Playbook de commit e push por parte do projeto

## 2.1 API, Check Web, Transport ou Infra (sempre no root)

Passo a passo completo:

1. Abrir o repo root.

   Set-Location c:\dev\projetos\checkcheck

2. Auditar contexto antes de stage.

   git status -sb
   git branch --show-current
   git remote -v

3. Fazer stage explicito (nao use `git add .` no root).

   git add sistema/app/routers/admin.py
   git add sistema/app/static/check/app.js
   git add docker-compose.yml

4. Validar stage.

   git diff --cached --stat
   git diff --cached

5. Commitar.

   git commit -m "fix: descricao objetiva da mudanca"
   git rev-parse HEAD

6. Push de producao.

   git push origin main

7. Monitorar o workflow correto (ver Secao 3).

Observacoes importantes:

1. Se alterou arquivos em `sistema/app/static/check/*.js` ou `*.css`, faca cache-busting no `sistema/app/static/check/index.html` (parametro `?v=`).
2. Mesmo com `.gitignore`, arquivos ja rastreados em `sistema/app/static/check` e `sistema/app/static/transport` devem ser stageados explicitamente no root quando a publicacao for monolito.

## 2.2 Admin v2 (sub-repo admin2)

Passo a passo completo:

1. Entrar na pasta do sub-repo.

   Set-Location c:\dev\projetos\checkcheck\sistema\app\static\admin2

2. Auditar contexto.

   git status -sb
   git branch --show-current
   git remote -v

3. Stage, commit e push.

   git add src/main.js
   git commit -m "admin2: descricao objetiva"
   git rev-parse HEAD
   git push origin main

4. Monitorar workflow do `checking-admin2` (Secao 3).

## 2.3 Check Web sub-repo (espelho, sem publicacao efetiva)

Use somente se voce quer manter historico no repo `checking-webapp`.

1. Set-Location c:\dev\projetos\checkcheck\sistema\app\static\check
2. git status -sb
3. git add <arquivos>
4. git commit -m "webapp-mirror: descricao"
5. git push origin main

Importante: isto **nao** publica para `https://tscode.com.br/checking/user` no modelo atual.

## 2.4 Transport sub-repo (espelho, sem publicacao efetiva)

Use somente para espelho no repo `checking-transport`.

1. Set-Location c:\dev\projetos\checkcheck\sistema\app\static\transport
2. git status -sb
3. git add <arquivos>
4. git commit -m "transport-mirror: descricao"
5. git push origin main

Importante: isto **nao** publica para `https://tscode.com.br/checking/transport` no modelo atual.

## 2.5 Flutter

1. Set-Location c:\dev\projetos\checkcheck\checking_android_new
2. git status -sb
3. git add <arquivos>
4. git commit -m "flutter: descricao objetiva"
5. git push origin main

Importante: push de Flutter nao faz deploy no Droplet da aplicacao web/API.

## 2.6 App Kotlin (sub-repo checking_kotlin)

Este playbook publica SOMENTE o app Kotlin no repo `checking-kotlin`. Como e um repositorio git proprio, TODOS os comandos rodam DENTRO de `checking_kotlin` (nunca no root).

Setup do remote (ja configurado; refazer so se necessario):

   git remote add origin https://tscode-com-br@github.com/tscode-com-br/checking-kotlin.git

Passo a passo completo:

1. Entrar na pasta do app (que e o repositorio git).

   Set-Location c:\dev\projetos\checkcheck\checking_kotlin

2. Auditar contexto (confirmar que esta no repo certo).

   git status -sb
   git branch --show-current        # esperado: main
   git remote -v                    # esperado: origin -> checking-kotlin.git

3. Verificacao de seguranca: garantir que nenhum segredo esta rastreado.

   git ls-files | Select-String -Pattern "keystore.properties$|local.properties$|\.jks$|\.keystore$"
   # Esperado: VAZIO. Se aparecer algo, PARE e remova do rastreio antes de seguir:
   #   git rm --cached <arquivo>   (e confirme que esta no .gitignore)

4. Stage da entrega. Preferir caminhos explicitos; `git add -A` so para snapshot completo
   (o `.gitignore` ja exclui segredos e `app/build/`).

   git add app/src/main/java/br/com/tscode/checking/...
   # ou, para snapshot completo do app:
   git add -A

5. Validar o stage (confirmar ausencia de segredos e de artefatos de build).

   git diff --cached --stat
   git diff --cached --name-only | Select-String -Pattern "keystore.properties$|local.properties$|^app/build/"
   # Esperado do filtro: VAZIO.

6. (Recomendado) Rodar os testes unitarios antes do push.

   .\gradlew.bat testDebugUnitTest

7. Commitar.

   git commit -m "feat(android): descricao objetiva da mudanca"
   git rev-parse HEAD

8. Push para o repo do app.

   git push origin main
   # No primeiro push de um branch novo: git push -u origin main

9. Validar que o remoto recebeu.

   git ls-remote --heads origin     # o SHA deve bater com git rev-parse HEAD
   git status -sb                    # esperado: main...origin/main, sem 'ahead'

Observacoes importantes:

1. Nunca commitar este app pelo root; o root o ignora de proposito. Sempre commitar de dentro de `checking_kotlin`.
2. Nao confundir com o app Flutter (`checking_android_new` / repo `checking_app_flutter`): sao apps e repositorios diferentes.
3. `archived-origin` aponta para o repo antigo (`checking_app_kotlin`); nao usar para publicacao.
4. Se o repo remoto tiver sido criado com README/licenca pela UI do GitHub, o primeiro push pode ser rejeitado por divergencia. Resolva com `git pull --rebase origin main` e depois `git push origin main`. Evite `--force` salvo certeza absoluta de que nada util sera perdido.

---

## 3) Monitoramento de deploy no GitHub Actions (por repo)

## 3.1 Root monolito (`checking`) - workflow correto

Sempre monitorar `Deploy OceanDrive`.

Comandos:

1. Capturar ultimo run:

   $run = gh run list --repo tscode-com-br/checking --workflow "Deploy OceanDrive" --limit 1 --json databaseId --jq ".[0].databaseId"

2. Acompanhar em tempo real:

   gh run watch $run --repo tscode-com-br/checking --exit-status

3. Validar conclusao:

   gh run view $run --repo tscode-com-br/checking --json conclusion,status --jq '{status,conclusion}'

4. Ver apenas falhas:

   gh run view $run --repo tscode-com-br/checking --log-failed

5. Validar jobs/steps:

   gh run view $run --repo tscode-com-br/checking --json jobs

## 3.2 Admin2 (`checking-admin2`)

Workflow: `Deploy to DigitalOcean`.

1. $run = gh run list --repo tscode-com-br/checking-admin2 --workflow "Deploy to DigitalOcean" --limit 1 --json databaseId --jq ".[0].databaseId"
2. gh run watch $run --repo tscode-com-br/checking-admin2 --exit-status
3. gh run view $run --repo tscode-com-br/checking-admin2 --json conclusion,status --jq '{status,conclusion}'
4. gh run view $run --repo tscode-com-br/checking-admin2 --log-failed

## 3.3 Repos que estao sem deploy automatico efetivo

Para checagem de estado:

1. gh workflow list --repo tscode-com-br/checking-api --all
2. gh workflow list --repo tscode-com-br/checking-webapp --all
3. gh workflow list --repo tscode-com-br/checking-transport --all
4. gh workflow list --repo tscode-com-br/checking_app_flutter --all

Interpretacao:

1. `disabled_manually` = nao dispara automaticamente em push.
2. `no workflows found` = repo sem pipeline definido.
3. `active` + run `skipped` = workflow existe, mas condicao interna impediu execucao do job.

## 3.4 Validacao de publicacao real (nao confiar so no Actions verde)

Depois de um deploy concluido, sempre validar:

1. Health da API publica:

   curl.exe --ssl-no-revoke -fsS https://tscode.com.br/api/health

2. Para Check Web, validar asset servido (bytes/etag):

   curl.exe --ssl-no-revoke -s -D - -o NUL "https://tscode.com.br/checking/user/automatic-activities.js" | Select-String -Pattern "content-length|etag"

3. Para Admin2:

   curl.exe --ssl-no-revoke -sI https://tscode.com.br/checking/admin

---

## 4) Como ter certeza do deploy automatico de cada parte

Esta secao responde objetivamente ao requisito de "certeza".

## 4.1 Comando unico de auditoria de estado

Execute:

1. gh workflow list --repo tscode-com-br/checking --all
2. gh workflow list --repo tscode-com-br/checking-admin2 --all
3. gh workflow list --repo tscode-com-br/checking-api --all
4. gh workflow list --repo tscode-com-br/checking-webapp --all
5. gh workflow list --repo tscode-com-br/checking-transport --all
6. gh workflow list --repo tscode-com-br/checking_app_flutter --all

Resultado esperado no modelo atual:

1. `checking`: deploy automatico ativo para producao (`Deploy OceanDrive`).
2. `checking-admin2`: deploy automatico ativo para admin2.
3. `checking-api`, `checking-webapp`, `checking-transport`: desativados manualmente.
4. `checking_app_flutter`: sem deploy para Droplet.

## 4.2 Se voce quiser reativar deploy dos repos desativados

Somente faca isso se houver decisao operacional formal para sair do modelo monolito.

Comandos:

1. gh workflow enable deploy.yml --repo tscode-com-br/checking-api
2. gh workflow enable deploy.yml --repo tscode-com-br/checking-webapp
3. gh workflow enable deploy.yml --repo tscode-com-br/checking-transport

Depois, validar:

1. gh workflow list --repo tscode-com-br/<repo> --all
2. push de teste em branch `main`
3. gh run list --repo tscode-com-br/<repo> --limit 1

Atencao:

1. Reativar workflow sem mudar roteamento nginx pode gerar "deploy verde" sem efeito publico.
2. O estado de serving publico precisa casar com a topologia de deploy.

---

## 5) Troubleshooting de deploy no servidor DigitalOcean

Esta secao e para quando o workflow falha ou conclui sem efeito esperado.

## 5.1 Acesso SSH confiavel via WSL (Windows)

Abrir shell remoto:

1. wsl bash -c "cp /mnt/c/dev/projetos/checkcheck/deploy/keys/do_checkcheck /tmp/do_ck && chmod 600 /tmp/do_ck && ssh -o StrictHostKeyChecking=no -i /tmp/do_ck root@157.230.35.21; rm -f /tmp/do_ck"

Rodar comando remoto sem shell interativo:

1. wsl bash -c "cp /mnt/c/dev/projetos/checkcheck/deploy/keys/do_checkcheck /tmp/do_ck && chmod 600 /tmp/do_ck && ssh -o StrictHostKeyChecking=no -i /tmp/do_ck root@157.230.35.21 'cd /root/checkcheck && docker compose ps'; rm -f /tmp/do_ck"

## 5.2 Diagnostico inicial obrigatorio no host

1. cd /root/checkcheck
2. docker compose ps
3. docker compose logs --tail=200 app
4. docker compose logs --tail=200 forms-worker
5. docker compose -f docker-compose.websites.yml ps
6. docker compose -f docker-compose.websites.yml logs --tail=200 admin2-web
7. curl -fsS http://127.0.0.1:8000/api/health
8. curl -I http://127.0.0.1:18084/
9. df -h
10. du -sh /root/checkcheck

## 5.3 Falhas comuns e correcao rapida

### Caso A: migration falhou

1. cd /root/checkcheck
2. docker compose run --rm --no-deps migrate
3. se sucesso, subir runtime:

   docker compose up -d --no-build --force-recreate --remove-orphans app forms-worker

### Caso B: app subiu, mas health falha

1. docker compose logs --tail=300 app
2. validar `.env` presente e coerente em `/root/checkcheck/.env`
3. validar DB:

   docker compose ps db
   docker compose logs --tail=150 db

### Caso C: forms-worker unhealthy

1. docker compose logs --tail=300 forms-worker
2. docker compose restart forms-worker
3. testar health interno:

   docker compose exec -T forms-worker python -m sistema.app.forms_worker_healthcheck

### Caso D: Admin2 indisponivel apos deploy

1. docker compose -f docker-compose.websites.yml logs --tail=300 admin2-web
2. docker compose -f docker-compose.websites.yml up -d --no-build --force-recreate admin2-web
3. curl -I http://127.0.0.1:18084/

### Caso E: Check Web/Transport nao refletiram mudanca

1. confirmar que o commit foi publicado pelo root `checking` (nao apenas pelo sub-repo);
2. confirmar run `Deploy OceanDrive` com `conclusion=success`;
3. comparar `etag/content-length` do asset publico;
4. se necessario, novo deploy no root e validacao de cache-busting no `index.html`.

### Caso F: disco cheio no host

1. docker system df
2. docker image prune -af
3. docker container prune -f
4. docker builder prune -af
5. repetir `df -h`

## 5.4 Rollback manual (somente quando necessario)

### Rollback do monolito app

1. identificar SHA anterior valido no GitHub Actions;
2. no host:

   cd /root/checkcheck
   export CHECKCHECK_APP_IMAGE=ghcr.io/tscode-com-br/checkcheck-app:<SHA_ANTERIOR>
   docker compose pull app
   bash deploy/maintenance/run_app_rollout.sh --phase full --deploy-dir /root/checkcheck --release-id <SHA_ANTERIOR> --public-health-url https://tscode.com.br/api/health

3. validar health local e publico.

### Rollback do admin2

1. escolher SHA anterior do repo `checking-admin2`;
2. no host:

   cd /root/checkcheck
   CHECKCHECK_ADMIN2_WEB_IMAGE=ghcr.io/tscode-com-br/checking-admin2:<SHA_ANTERIOR> docker compose -f docker-compose.websites.yml pull admin2-web
   CHECKCHECK_ADMIN2_WEB_IMAGE=ghcr.io/tscode-com-br/checking-admin2:<SHA_ANTERIOR> docker compose -f docker-compose.websites.yml up -d --no-build --force-recreate admin2-web

3. validar `curl -I http://127.0.0.1:18084/` e endpoint publico.

---

## 6) Checklist operacional (pronto para copiar)

Checklist antes do push:

1. repo/pasta correta;
2. branch correta (`main`);
3. remote correto;
4. stage explicito apenas dos arquivos da entrega;
5. `git diff --cached` revisado;
6. testes relevantes executados.

Checklist depois do push:

1. identificar run correto no repo correto;
2. acompanhar com `gh run watch ... --exit-status`;
3. se falha, coletar `gh run view ... --log-failed`;
4. validar health publico;
5. validar efeito funcional (asset/endpoint da feature).

Checklist de fechamento:

1. SHA enviado;
2. run-id monitorado;
3. conclusao do workflow;
4. evidencias de health e publicacao.

---

## 7) Comandos de referencia rapida

Auditoria de contexto local:

1. git status -sb
2. git branch --show-current
3. git remote -v

Auditoria de workflows (estado):

1. gh workflow list --repo tscode-com-br/checking --all
2. gh workflow list --repo tscode-com-br/checking-admin2 --all
3. gh workflow list --repo tscode-com-br/checking-api --all
4. gh workflow list --repo tscode-com-br/checking-webapp --all
5. gh workflow list --repo tscode-com-br/checking-transport --all
6. gh workflow list --repo tscode-com-br/checking_app_flutter --all

Monitoramento de runs:

1. gh run list --repo tscode-com-br/checking --workflow "Deploy OceanDrive" --limit 5
2. gh run list --repo tscode-com-br/checking-admin2 --workflow "Deploy to DigitalOcean" --limit 5
3. gh run view <run-id> --repo tscode-com-br/<repo> --log-failed

Validacao publica:

1. curl.exe --ssl-no-revoke -fsS https://tscode.com.br/api/health
2. curl.exe --ssl-no-revoke -sI https://tscode.com.br/checking/admin
3. curl.exe --ssl-no-revoke -s -D - -o NUL "https://tscode.com.br/checking/user/automatic-activities.js" | Select-String -Pattern "content-length|etag"
