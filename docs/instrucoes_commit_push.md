# Commit e Push no Projeto Checking

Status deste documento: validado em 2026-04-24.

Este arquivo registra o procedimento recomendado para commits e pushes no workspace atual do projeto Checking. O objetivo é servir como contexto operacional de alta confiabilidade para manutenção, publicação e recuperação rápida em caso de incidente.

Este documento deve ser lido como a referência principal quando houver dúvida sobre:

- em qual repositório uma alteração deve ser commitada;
- qual ação manual dispara deploy de produção;
- como montar stage sem misturar escopos;
- como validar o resultado depois do push e do deploy manual;
- quais erros recorrentes devem ser evitados.

Alguns documentos antigos em `docs/context/` ainda refletem uma topologia anterior do workspace. Quando houver conflito, este arquivo deve ser considerado a fonte mais atual para o procedimento de commit e push.

## 1. Topologia Git real do workspace

Em 2026-04-24, o workspace possui três repositórios Git distintos:

| Repositório | Pasta local | Remote principal | Escopo | Push em `main` faz deploy automático na DigitalOcean? |
| --- | --- | --- | --- | --- |
| Sistema principal | `c:\dev\projetos\checkcheck` | `https://github.com/tscode-com-br/checking.git` | API FastAPI, websites, firmware, docs do sistema, migrações, testes do backend/web | Não |
| App Flutter | `c:\dev\projetos\checkcheck\checking_android_new` | `https://github.com/tscode-com-br/checking_app_flutter.git` | Aplicativo Flutter | Não |
| App Kotlin | `c:\dev\projetos\checkcheck\checking_kotlin` | `https://github.com/tscode-com-br/checking_app_kotlin.git` | Aplicativo Kotlin nativo | Não |

Consequências práticas:

- o repositório principal continua sendo o dono do deploy da API e dos websites;
- push em `main` do repositório principal publica código no GitHub, mas não reinicia produção sozinho;
- o deploy de produção passou a depender de execução manual do workflow global de fallback ou dos workflows manuais por alvo;
- os apps Flutter e Kotlin têm histórico, commit e push próprios;
- os apps móveis não devem entrar em commits do repositório principal;
- o repositório principal ignora `checking_android_new/` e `checking_kotlin/`.

## 2. Regra de ouro

Antes de qualquer commit, responda primeiro:

1. A mudança é da API/web/firmware/docs do sistema principal?
2. A mudança é do app Flutter?
3. A mudança é do app Kotlin?

Cada alteração deve ser commitada apenas no repositório dono daquele escopo.

Regra operacional:

- alterações do sistema principal: commit e push em `checkcheck`;
- alterações do Flutter: commit e push em `checking_android_new`;
- alterações do Kotlin: commit e push em `checking_kotlin`;
- não usar `git subtree`;
- não tentar publicar Flutter ou Kotlin a partir do root;
- não misturar arquivos de repositórios aninhados no commit do root.

## 3. O que cada push faz e como o deploy é acionado

### 3.1 Repositório principal `checkcheck`

Push em `main` no repo principal publica o código no GitHub e dispara o deploy automático de produção.

O mesmo workflow também continua disponível para reexecução manual de fallback:

- `.github/workflows/deploy-oceandrive.yml`

Esse workflow:

1. valida secrets de deploy;
2. prepara verificação SSH;
3. garante que o diretório remoto existe;
4. sincroniza o projeto com `rsync`;
5. executa `docker compose up -d db`;
6. executa `docker compose up -d --build --remove-orphans`;
7. valida `http://127.0.0.1:8000/api/health` no servidor;
8. instala ou atualiza a automação periódica de limpeza de SSD no droplet;
9. faz prune de artefatos Docker não utilizados e remove temporários antigos.

Resumo: push em `main` do root publica o código e envia o deploy para a DigitalOcean automaticamente.

### 3.2 Repositório Flutter `checking_android_new`

Push em `main` desse repo publica apenas o código do app Flutter no GitHub. Não existe deploy automático da API/web a partir dele.

### 3.3 Repositório Kotlin `checking_kotlin`

Push em `main` desse repo publica apenas o código do app Kotlin no GitHub. Não existe deploy automático da API/web a partir dele.

## 4. Pré-condições antes de qualquer commit

Antes de comitar em qualquer um dos três repositórios, valide:

1. pasta atual correta;
2. branch correta;
3. remote correto;
4. status limpo exceto pelas mudanças desejadas;
5. testes relevantes executados;
6. ausência de artefatos locais desnecessários no stage.

Checklist mínimo:

```powershell
git branch --show-current
git remote -v
git status --short
```

Se o repositório for o principal, valide também:

```powershell
git status --branch
```

## 5. Configuração mínima de Git

Se a máquina local ainda não tiver identidade Git configurada, use:

```powershell
git config user.name "tscode-com-br"
git config user.email "tscode.com.br@gmail.com"
```

Pode ser feito globalmente ou por repositório.

Se push por SSH falhar com erro de chave, use remote HTTPS.

Exemplo:

```powershell
git remote set-url origin https://github.com/tscode-com-br/checking.git
```

O mesmo princípio vale para Flutter e Kotlin.

## 6. Procedimento oficial para o repositório principal

### 6.1 Quando usar

Use o repo principal para:

- API FastAPI;
- websites servidos pela API;
- firmware ESP32;
- migrações Alembic;
- documentação do sistema principal;
- testes do backend/web.

### 6.2 Entrar no repositório correto

```powershell
Set-Location c:\dev\projetos\checkcheck
```

### 6.3 Verificação inicial

```powershell
git branch --show-current
git remote -v
git status --short
git status --branch
```

Resultado esperado:

- branch `main`;
- remote `origin` apontando para `tscode-com-br/checking`;
- nenhuma alteração inesperada fora do escopo da entrega.

### 6.4 Como montar o stage

Regra importante: prefira stage explícito. Não use `git add .` cegamente.

Exemplo para uma mudança de backend e web:

```powershell
git add alembic sistema tests docs/commitpush.md
```

Ou ainda mais específico:

```powershell
git add sistema/app/routers/web_check.py
git add sistema/app/static/check/app.js
git add tests/test_api_flow.py
```

### 6.5 Como revisar o stage

```powershell
git status --short
git diff --cached --stat
git diff --cached
```

Objetivo da revisão:

1. garantir que apenas arquivos do escopo desejado entraram;
2. evitar subir artefatos locais;
3. evitar misturar correções não relacionadas;
4. confirmar que repositórios aninhados não apareceram no stage.

### 6.6 Como criar o commit

Use mensagens claras, curtas e orientadas a resultado.

Exemplos reais do projeto:

- `Add project-specific auto checkout distances`
- `Shorten Alembic revision id`
- `Ignore dedicated Kotlin app repository`

Padrão recomendado:

- verbo no imperativo;
- escopo técnico claro;
- sem mensagem vaga como `update`, `fixes`, `misc`.

### 6.7 Como fazer o push

```powershell
git push origin main
```

Impacto:

- esse comando publica o código no GitHub e dispara o workflow global de deploy na DigitalOcean;
- `main` continua sendo branch sensível, porque qualquer push nela provoca rollout de produção;
- se a orientação for risco zero, não faça push em `main` sem aprovação explícita.

### 6.8 Como disparar o deploy manual de fallback

Pelo GitHub CLI:

```powershell
gh workflow run deploy-oceandrive.yml -R tscode-com-br/checking
```

Com diretório remoto explícito, se necessário:

```powershell
gh workflow run deploy-oceandrive.yml -R tscode-com-br/checking -f deploy_dir=/root/checkcheck
```

Esse é o caminho recomendado quando for necessário redeployar o pacote completo sem criar novo commit.

### 6.9 Validação obrigatória depois do deploy

Validação mínima pública:

```text
https://tscode.com.br/api/health
https://tscode.com.br/checking/admin
https://tscode.com.br/checking/user
https://www.tscode.com.br/api/health
```

Comandos úteis no Windows:

```powershell
Invoke-WebRequest https://tscode.com.br/api/health -UseBasicParsing
Invoke-WebRequest https://tscode.com.br/checking/admin -UseBasicParsing
Invoke-WebRequest https://www.tscode.com.br/api/health -UseBasicParsing
```

Se quiser inspecionar apenas headers:

```powershell
curl.exe -k -I https://tscode.com.br/api/health
curl.exe -k -I https://tscode.com.br/checking/admin
curl.exe -k -I https://www.tscode.com.br/api/health
```

Resposta esperada da API:

```json
{"status":"ok","app":"checking-sistema"}
```

## 7. Procedimento para o repositório Flutter

### 7.1 Quando usar

Use `checking_android_new` apenas para mudanças do app Flutter.

### 7.2 Entrar no repo

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_android_new
```

### 7.3 Verificação inicial

```powershell
git branch --show-current
git remote -v
git status --short
```

Esperado:

- branch `main`;
- remote `origin` apontando para `tscode-com-br/checking_app_flutter`.

### 7.4 Stage, commit e push

Exemplo:

```powershell
git add lib/src/features/checking
git diff --cached --stat
git commit -m "Support project-specific auto checkout distances"
git push origin main
```

### 7.5 O que não fazer

- não comitar Flutter a partir do root;
- não usar `git subtree`;
- não esperar deploy na DigitalOcean após push do Flutter.

### 7.6 Validação sugerida

Exemplos úteis:

```powershell
flutter analyze
flutter test
```

Se houver task pronta no workspace, pode usar a task correspondente.

## 8. Procedimento para o repositório Kotlin

### 8.1 Quando usar

Use `checking_kotlin` apenas para mudanças do app Kotlin nativo.

### 8.2 Entrar no repo

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin
```

### 8.3 Verificação inicial

```powershell
git branch --show-current
git remote -v
git status --short
```

Esperado:

- branch `main`;
- remote `origin` apontando para `tscode-com-br/checking_app_kotlin`.

### 8.4 Stage, commit e push

Exemplo:

```powershell
git add app/src/main app/src/test
git diff --cached --stat
git commit -m "Support project-specific auto checkout distances"
git push origin main
```

### 8.5 Validação sugerida

Exemplo real usado no projeto:

```powershell
.\gradlew.bat testDebugUnitTest --tests "com.br.checkingnative.domain.logic.CheckingLocationLogicTest"
```

### 8.6 O que não fazer

- não tentar publicar Kotlin via repo principal;
- não remover o `.git` do app Kotlin;
- não adicionar `checking_kotlin/` de volta ao índice do root.

## 9. Regras de stage e exclusão

Itens que normalmente não devem entrar em commit:

- `.env`
- `.venv/`
- bancos locais `*.db`, `*.sqlite`, `*.sqlite3`
- `deploy/keys/`
- caches locais
- artefatos de build
- arquivos temporários como `tmp_*.png`
- qualquer arquivo de repositório aninhado quando você estiver no root

Regra prática:

- no root, o stage deve conter apenas arquivos do sistema principal;
- no Flutter, apenas arquivos do Flutter;
- no Kotlin, apenas arquivos do Kotlin.

## 10. Ordem recomendada quando a entrega envolve mais de um repo

Se uma mudança envolve API, Flutter e Kotlin, não crie um commit único para tudo. O correto é trabalhar por repositório.

Ordem recomendada:

1. concluir a mudança em cada repo;
2. validar localmente em cada repo;
3. comitar cada repo separadamente;
4. publicar primeiro os apps móveis, se quiser apenas registrar o código no GitHub;
5. publicar o root quando o código estiver pronto no GitHub;
6. disparar manualmente o deploy global ou o deploy isolado do alvo correto.

Se a mudança do app depender de contrato novo da API:

- idealmente mantenha compatibilidade retroativa na API;
- se isso não for possível, trate a janela de deploy como operação coordenada.

## 11. Gotchas operacionais importantes

### 11.1 Push em `main` do root tem risco direto de produção

Push em `main` do root gera deploy automático, e a execução manual do workflow global também tem impacto direto em produção.

### 11.2 Alembic: `revision` deve ter no máximo 32 caracteres

Esse ponto já derrubou a produção em 2026-04-24.

Contexto técnico:

- em produção, o Postgres mantém `alembic_version.version_num` como `VARCHAR(32)`;
- `revision` acima de 32 caracteres pode quebrar o startup da aplicação;
- quando isso acontece, o container entra em falha e o Nginx responde `502 Bad Gateway`.

Regra obrigatória para novas migrações:

- use `revision` com 32 caracteres ou menos.

Exemplo seguro:

```python
revision = "0038_proj_auto_checkout_dist"
```

### 11.3 Não confiar apenas no fetch do navegador embutido para validar 502

Durante o incidente de 2026-04-24, as verificações por `fetch_webpage` ficaram inconsistentes em alguns momentos. Para validação de rede, prefira:

- `Invoke-WebRequest`
- `curl.exe -k -I`
- `gh run list` e `gh run view` para o workflow de deploy

### 11.4 O deploy pode demorar alguns minutos

O passo `Rebuild and restart services` costuma levar cerca de 5 a 5m30 em execuções saudáveis. Não assuma travamento cedo demais.

### 11.5 O workflow faz prune de cache Docker depois de deploy saudável

Isso existe para controlar crescimento de disco em `/var/lib/containerd`.

### 11.6 O deploy reinstala a automação periódica de limpeza do SSD

Além da poda ao final do workflow, o deploy instala e mantém um timer `systemd` que executa limpeza periódica de cache Docker, journals antigos, cache `apt` e temporários antigos do projeto.

### 11.7 O arquivo `.env` de produção fica somente no servidor

Ele não vai para o GitHub, não vai no rsync e não deve entrar em commit.

## 12. Como inspecionar o deploy pelo GitHub CLI

Comandos úteis:

```powershell
gh run list -R tscode-com-br/checking --limit 5
gh run list -R tscode-com-br/checking --limit 5 --json databaseId,displayTitle,status,conclusion,headSha,createdAt
gh run view <RUN_ID> -R tscode-com-br/checking --log-failed
```

Quando usar:

- depois de um push em `main` do root, de um deploy manual do root ou de um deploy isolado por alvo;
- quando a API não sobe;
- quando o health check falha;
- quando as URLs públicas retornam 502.

## 13. Fluxo de resposta rápida para incidente após deploy do root

Se depois de um push em `main` ou da execução manual do workflow global a produção responder `502 Bad Gateway`, siga esta sequência:

1. confirmar se é 502 real com `Invoke-WebRequest` ou `curl.exe -k -I`;
2. validar `gh run list` para ver se o deploy está em andamento, falhou ou concluiu;
3. se houve migração nova, revisar imediatamente o `revision` do Alembic;
4. validar `https://tscode.com.br/api/health`;
5. validar também `https://tscode.com.br/checking/admin` e `https://www.tscode.com.br/api/health`;
6. se identificar causa no código, corrigir, reenviar hotfix para `main` e rerodar manualmente o workflow necessário.

Observação importante:

- o commit `8d15db4` foi um hotfix real usado para corrigir um 502 causado por `revision` longo de Alembic.

## 14. Padrões de mensagem de commit

Boas mensagens no projeto seguem estes princípios:

- explicam o resultado da mudança;
- são curtas;
- não usam prefixos desnecessários;
- podem ser em inglês técnico simples.

Boas mensagens:

- `Add project-specific auto checkout distances`
- `Shorten Alembic revision id`
- `Ignore dedicated Kotlin app repository`
- `Support project-specific auto checkout distances`

Mensagens fracas:

- `update files`
- `fix`
- `changes`
- `ajustes`

## 15. Baseline operacional atual

Estado validado em 2026-04-24:

- `checkcheck` ignora `checking_android_new/` e `checking_kotlin/`;
- `checking_android_new` tem repo próprio e remoto próprio;
- `checking_kotlin` tem repo próprio e remoto próprio;
- `push` em `main` do repo `checkcheck` dispara o workflow global de deploy na DigitalOcean;
- o hotfix `8d15db4` restaurou a produção após incidente de 502 por migration;
- as URLs públicas críticas responderam `200 OK` após o hotfix.

## 16. Passo a passo resumido por repo

### 16.1 Root `checkcheck`

```powershell
Set-Location c:\dev\projetos\checkcheck
git branch --show-current
git remote -v
git status --short
git add <arquivos-do-sistema-principal>
git diff --cached --stat
git commit -m "<mensagem-clara>"
git push origin main
```

Depois validar:

```powershell
Invoke-WebRequest https://tscode.com.br/api/health -UseBasicParsing
Invoke-WebRequest https://tscode.com.br/checking/admin -UseBasicParsing
```

### 16.2 Flutter `checking_android_new`

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_android_new
git branch --show-current
git remote -v
git status --short
git add <arquivos-do-flutter>
git diff --cached --stat
git commit -m "<mensagem-clara>"
git push origin main
```

### 16.3 Kotlin `checking_kotlin`

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin
git branch --show-current
git remote -v
git status --short
git add <arquivos-do-kotlin>
git diff --cached --stat
git commit -m "<mensagem-clara>"
git push origin main
```

## 17. Referências úteis dentro do repo

- `README.md`
- `docs/context/processo_commit_push_deploy_api_web.md`
- `docs/context/procedimento_oficial_repositorios.md`
- `docs/context/deploy_digitalocean_ssh.md`
- `.github/workflows/deploy-oceandrive.yml`

## 18. Conclusão operacional

O procedimento correto de commit e push no projeto Checking depende primeiro de escolher o repositório certo.

Resumo final:

- API/web/firmware/docs principais: `checkcheck`;
- app Flutter: `checking_android_new`;
- app Kotlin: `checking_kotlin`.

O ponto mais sensível e simples de lembrar é este:

- push em `main` do root = publica o código e dispara deploy automático na DigitalOcean;
- execução manual do workflow `.github/workflows/deploy-oceandrive.yml` = fallback para redeploy sem novo commit;
- push em `main` dos apps móveis = apenas publicação do código do app;
- migração Alembic nova exige `revision` com no máximo 32 caracteres.

Se essa regra for respeitada, a chance de erro operacional cai bastante.