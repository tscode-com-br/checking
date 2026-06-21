# Acesso ao projeto na DigitalOcean

Status deste documento: validado em 2026-06-09; topologia de deploy e estado de workflows
reconciliados com o modelo MONOLITO (ver Secao 5.1 e, para o fluxo completo de commit/push/deploy, a **Secao 0** de
`instrucoes_acesso_repositórios_github.md`).

Este arquivo consolida o que ja esta confirmado para acessar e operar o projeto no provedor DigitalOcean sem expor segredos no repositório.

## 1. Acesso confirmado hoje

| Item | Valor confirmado | Observacao |
| --- | --- | --- |
| Provedor | DigitalOcean | Droplet Linux em producao |
| Host SSH | `157.230.35.21` | Acesso por SSH confirmado |
| Usuario SSH | `root` | Usado no fluxo operacional atual |
| Chave local de deploy | `deploy/keys/do_checkcheck` | Arquivo local sensivel; nao commitar nem copiar para docs externas |
| Diretorio remoto da aplicacao | `/root/checkcheck` | Raiz operacional da stack |
| Health local da API | `http://127.0.0.1:8000/api/health` | Ja respondeu `{"status":"ok","app":"checking-sistema"}` |
| Health publico | `https://tscode.com.br/api/health` | Usado para smoke externo |

Observacao importante:

- acesso SSH ao host esta confirmado;
- credenciais do painel web da DigitalOcean nao estao documentadas neste repo;
- este documento cobre o acesso operacional confirmado ao projeto no droplet.

## 2. Comandos basicos de acesso

Observacao importante sobre o ambiente Windows:

O OpenSSH nativo do Windows PowerShell nao consegue ler a chave `do_checkcheck` quando o arquivo esta em uma pasta NTFS (problemas de permissao e formato de path). Usar **WSL** e o metodo confiavel. Todos os comandos abaixo devem ser executados no PowerShell invocando WSL.

Abrir shell remoto interativo:

```powershell
wsl bash -c "cp /mnt/c/dev/projetos/checkcheck/deploy/keys/do_checkcheck /tmp/do_ck && chmod 600 /tmp/do_ck && ssh -o StrictHostKeyChecking=no -i /tmp/do_ck root@157.230.35.21; rm -f /tmp/do_ck"
```

Executar um comando remoto sem abrir shell interativo:

```powershell
wsl bash -c "cp /mnt/c/dev/projetos/checkcheck/deploy/keys/do_checkcheck /tmp/do_ck && chmod 600 /tmp/do_ck && ssh -o StrictHostKeyChecking=no -i /tmp/do_ck root@157.230.35.21 'cd /root/checkcheck && docker compose ps'; rm -f /tmp/do_ck"
```

Validar saude local da API sem abrir shell interativo:

```powershell
wsl bash -c "cp /mnt/c/dev/projetos/checkcheck/deploy/keys/do_checkcheck /tmp/do_ck && chmod 600 /tmp/do_ck && ssh -o StrictHostKeyChecking=no -i /tmp/do_ck root@157.230.35.21 'curl -fsS http://127.0.0.1:8000/api/health'; rm -f /tmp/do_ck"
```

Ver containers e servicos da stack:

```powershell
wsl bash -c "cp /mnt/c/dev/projetos/checkcheck/deploy/keys/do_checkcheck /tmp/do_ck && chmod 600 /tmp/do_ck && ssh -o StrictHostKeyChecking=no -i /tmp/do_ck root@157.230.35.21 'cd /root/checkcheck && docker compose ps'; rm -f /tmp/do_ck"
```

Ver status de disco e uso do diretorio do app:

```powershell
wsl bash -c "cp /mnt/c/dev/projetos/checkcheck/deploy/keys/do_checkcheck /tmp/do_ck && chmod 600 /tmp/do_ck && ssh -o StrictHostKeyChecking=no -i /tmp/do_ck root@157.230.35.21 'df -h && du -sh /root/checkcheck'; rm -f /tmp/do_ck"
```

Padrao geral para qualquer comando remoto:

```powershell
wsl bash -c "cp /mnt/c/dev/projetos/checkcheck/deploy/keys/do_checkcheck /tmp/do_ck && chmod 600 /tmp/do_ck && ssh -o StrictHostKeyChecking=no -i /tmp/do_ck root@157.230.35.21 'COMANDO_AQUI'; rm -f /tmp/do_ck"
```

## 3. Estrutura remota relevante

Itens operacionais esperados dentro de `/root/checkcheck`:

- `docker-compose.yml` e arquivos auxiliares de compose do projeto;
- `.env` real de producao;
- `.deploy-release`, quando o workflow ou deploy local registram o release implantado;
- codigo sincronizado do repo principal `checkcheck`.

Politica do `.env`:

- o `.env` real de producao fica no servidor;
- ele nao deve ser commitado no GitHub;
- o arquivo pode ser mantido manualmente no host ou materializado por GitHub Actions a partir de secret;
- em 2026-05-05 foi confirmado backup remoto em `/root/checkcheck/.env.backup-20260505-224827` antes da reconciliacao segura do bloco de IA.

## 4. Estado operacional confirmado em 2026-05-05

Ja foi validado no host:

- conectividade SSH com a chave `deploy/keys/do_checkcheck`;
- existencia do diretorio `/root/checkcheck`;
- health local da API com retorno `ok`;
- reconciliacao segura do `.env` para incluir defaults da IA mantendo `TRANSPORT_AI_ENABLED=false` em producao;
- a base de producao ainda possui a tabela legada `transport_ai_llm_settings` e ainda nao possui `transport_ai_project_llm_settings`.

Consequencia pratica:

- o host esta preparado para continuar operando com a IA de transporte desabilitada;
- nao e seguro considerar a IA pronta para habilitacao em producao so porque o acesso SSH existe.

## 5. Fluxos de deploy disponiveis

### 5.1 GitHub Actions no repo principal

O deploy de producao pertence ao repositório principal `checkcheck`.

> **Topologia de serving em producao (verificado em 2026-06-09) — importante para nao deployar pelo caminho errado:**
>
> | Rota publica | Quem serve | Como deployar |
> | --- | --- | --- |
> | `/checking/user` (Check Web) | monolito `checkcheck-app` (:8000), estatico do repo root | este workflow (`deploy-oceandrive.yml`) |
> | `/checking/transport` (Transport) | monolito `checkcheck-app` (:8000) | este workflow (`deploy-oceandrive.yml`) |
> | `/api/...` | monolito `checkcheck-app` (:8000) | este workflow |
> | `/checking/admin` (Admin v2) | container `admin2-web` (:18084) | sub-repo `checking-admin2` (`git push origin main` em `sistema\app\static\admin2`) — deploy automatico |
>
> Os containers `user-web` (:18082) e `transport-web` (:18083) NAO servem o dominio publico (o edge
> cutover do nginx so foi aplicado ao admin).

**Estado real dos workflows (auditado com `gh workflow list --all` em 2026-06-09):**

| Repo | Workflow | Estado | Efeito operacional hoje |
| --- | --- | --- | --- |
| `checking` | `Deploy OceanDrive` | `active` | deploy efetivo de producao (API + Check Web + Transport + infra) |
| `checking` | `Deploy to DigitalOcean` | `active` | job fica `skipped` por guarda de repositorio (`if: github.repository == 'tscode-com-br/checking-api'`) |
| `checking-admin2` | `Deploy to DigitalOcean` | `active` | deploy efetivo do Admin v2 |
| `checking-api` | `Deploy to DigitalOcean` | `disabled_manually` | sem deploy automatico efetivo |
| `checking-api` | `Deploy OceanDrive*` | `active` | runs `skipped` (workflows nao sao o caminho canonico desse repo) |
| `checking-webapp` | `Deploy to DigitalOcean` | `disabled_manually` | sem deploy automatico efetivo |
| `checking-transport` | `Deploy to DigitalOcean` | `disabled_manually` | sem deploy automatico efetivo |
| `checking_app_flutter` | (sem workflow) | n/a | nao deploya no Droplet |

Consequencia pratica (coerente com `instrucoes_acesso_repositórios_github.md`):

- Modelo vigente = **MONOLITO** para API/Check/Transport: publicar via repo root `checking` (`git push origin main`).
- Admin publica via sub-repo `checking-admin2`.
- Push em `checking-api`, `checking-webapp` e `checking-transport` nao e caminho de publicacao efetiva no dominio publico atual.

Workflow relevante:

- `.github/workflows/deploy-oceandrive.yml` (repo `checking`, caminho canonico de producao)
- `.github/workflows/deploy.yml` em `checking-admin2` (somente Admin v2)

Gatilhos atuais do workflow:

- `push` em `main`;
- `workflow_dispatch` para fallback manual.

Secrets ja visiveis no repo:

- `OCEAN_APP_DIR`
- `OCEAN_HOST`
- `OCEAN_HOST_FINGERPRINT`
- `OCEAN_PORT`
- `OCEAN_SSH_KEY`
- `OCEAN_USER`

Secret opcional suportado pelo workflow, mas ainda ausente:

- `OCEAN_APP_ENV_B64`

Uso do `OCEAN_APP_ENV_B64`:

- permite materializar ou atualizar o `.env` de producao no host sem commitar segredos no repo;
- e opcional; se nao existir, o workflow reutiliza o `.env` ja presente no servidor.

### 5.2 Deploy local via PowerShell

Script operacional do repo:

- `deploy/deploy_do_ssh.ps1`

Exemplo:

```powershell
.\deploy\deploy_do_ssh.ps1 -ServerHost "157.230.35.21" -User "root" -KeyPath "C:\dev\projetos\checkcheck\deploy\keys\do_checkcheck" -RemoteDir "/root/checkcheck"
```

O script ja contem guardas para impedir habilitacao parcial da IA quando `TRANSPORT_AI_ENABLED=true` sem os gates obrigatorios.

## 6. Validacoes minimas apos acesso ou deploy

No host (via WSL):

```powershell
wsl bash -c "cp /mnt/c/dev/projetos/checkcheck/deploy/keys/do_checkcheck /tmp/do_ck && chmod 600 /tmp/do_ck && ssh -o StrictHostKeyChecking=no -i /tmp/do_ck root@157.230.35.21 'cd /root/checkcheck && docker compose ps'; rm -f /tmp/do_ck"
wsl bash -c "cp /mnt/c/dev/projetos/checkcheck/deploy/keys/do_checkcheck /tmp/do_ck && chmod 600 /tmp/do_ck && ssh -o StrictHostKeyChecking=no -i /tmp/do_ck root@157.230.35.21 'curl -fsS http://127.0.0.1:8000/api/health'; rm -f /tmp/do_ck"
```

Publicamente:

```powershell
curl.exe --ssl-no-revoke -fsS https://tscode.com.br/api/health
curl.exe --ssl-no-revoke -sI https://tscode.com.br/checking/admin
curl.exe --ssl-no-revoke -s -o NUL -w "%{http_code}" https://tscode.com.br/checking/user
curl.exe --ssl-no-revoke -s -o NUL -w "%{http_code}" https://tscode.com.br/checking/transport
```

Observacao importante:

- `HEAD` em `/checking/user` e `/checking/transport` pode retornar `405` no edge atual; para essas duas rotas, validar com `GET` (status `200`) e/ou comparar `etag/content-length` dos assets.

### 6.1 Verificacao funcional apos deploy de um frontend (Check Web / Transport)

Health verde nao prova que o estatico mudou. Apos um deploy que alterou Check Web ou Transport,
confirme que o arquivo SERVIDO ao publico realmente mudou — compare `content-length`/`etag` antes
e depois, ou procure um marcador unico do seu codigo:

```powershell
# tamanho/etag do arquivo servido em producao
curl.exe --ssl-no-revoke -s -D - -o NUL "https://tscode.com.br/checking/user/automatic-activities.js" | Select-String -Pattern "content-length|etag"

# (opcional) confirmar que a imagem do app no host e o seu commit
wsl bash -c "cp /mnt/c/dev/projetos/checkcheck/deploy/keys/do_checkcheck /tmp/do_ck && chmod 600 /tmp/do_ck && ssh -o StrictHostKeyChecking=no -i /tmp/do_ck root@157.230.35.21 'docker inspect checkcheck-app-1 --format {{.Config.Image}}'; rm -f /tmp/do_ck"
```

Se o tamanho/etag NAO mudou, a alteracao nao chegou ao publico (provavelmente deployada pelo
caminho errado — sub-repo em vez de root/oceandrive). Ver `instrucoes_acesso_repositórios_github.md`, Secao 0.

### 6.2 Anotacao "Process completed with exit code 1" no `deploy-oceandrive.yml`

Essa anotacao pode ser **nao-fatal** (vem de um pos-passo, ex.: SSD cleanup) e NAO significa,
sozinha, que o deploy falhou. Confirme a conclusao real antes de declarar falha:

```powershell
gh run view <run-id> --repo tscode-com-br/checking --json conclusion --jq .conclusion   # esperado: success
gh run view <run-id> --repo tscode-com-br/checking --log-failed                          # vazio = nenhum step falhou
```

Se `conclusion=success` e `--log-failed` vier vazio, o deploy esta OK; trate a anotacao como ruido
do pos-processamento.

### 6.3 Qual run monitorar para evitar falso diagnostico

No repo `checking`, para cada push em `main`, monitorar **sempre** `Deploy OceanDrive`:

```powershell
$run = gh run list --repo tscode-com-br/checking --workflow "Deploy OceanDrive" --limit 1 --json databaseId --jq ".[0].databaseId"
gh run watch $run --repo tscode-com-br/checking --exit-status
gh run view $run --repo tscode-com-br/checking --json status,conclusion --jq '{status,conclusion}'
```

Cheque esperado no mesmo commit:

- `Deploy OceanDrive` => `conclusion=success` (deploy efetivo);
- `Deploy to DigitalOcean` no repo `checking` pode aparecer como `skipped` e isso e comportamento esperado no modelo atual.

## 7. Regras de seguranca

- nao expor conteudo da chave privada `deploy/keys/do_checkcheck`;
- nao commitar `.env` de producao;
- nao assumir que acesso SSH ao droplet concede acesso automatico a GitHub Actions Secrets;
- nao habilitar a IA de transporte em producao sem passar pelos gates operacionais e pela migracao de dados correspondente;
- sempre preferir backup do `.env` antes de alteracoes remotas.

## 8. O que ainda depende de permissao externa

Ainda dependem de permissao explicita ou credencial nao documentada no repo:

- acesso ao painel web da DigitalOcean, se for necessario resize manual do droplet, networking ou snapshots pelo painel;
- alteracao de GitHub Actions Secrets, embora o acesso administrativo ao repositório GitHub ja esteja confirmado no ambiente atual;
- preenchimento do eventual `OCEAN_APP_ENV_B64` com conteudo real de producao.