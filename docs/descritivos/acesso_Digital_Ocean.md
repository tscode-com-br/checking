# Acesso ao projeto na DigitalOcean

Status deste documento: validado em 2026-05-05.

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

Abrir shell remoto a partir da raiz do repo no Windows PowerShell:

```powershell
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21
```

Abrir shell e cair direto no diretorio do app:

```powershell
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 "cd /root/checkcheck && bash"
```

Validar saude local da API sem abrir shell interativo:

```powershell
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 "curl -fsS http://127.0.0.1:8000/api/health"
```

Ver containers e servicos da stack:

```powershell
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 "cd /root/checkcheck && docker compose ps"
```

Ver status de disco e uso do diretorio do app:

```powershell
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 "df -h && du -sh /root/checkcheck"
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

Workflow relevante:

- `.github/workflows/deploy-oceandrive.yml`

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

No host:

```powershell
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 "cd /root/checkcheck && docker compose ps"
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 "curl -fsS http://127.0.0.1:8000/api/health"
```

Publicamente:

```powershell
Invoke-WebRequest https://tscode.com.br/api/health -UseBasicParsing
curl.exe -k -I https://tscode.com.br/checking/admin
curl.exe -k -I https://tscode.com.br/checking/user
```

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