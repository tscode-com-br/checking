# Acesso aos repositorios GitHub do projeto

Status deste documento: reconciliado com a conta GitHub, com os remotes locais e com o fluxo operacional de commit/push apos a remodelagem de repositorios na conta em 2026-05-06.

Este arquivo substitui o antigo guia `instrucoes_commit_push.md` e consolida quatro coisas diferentes que nao devem mais ser misturadas:

1. as pastas Git locais que ainda existem no workspace;
2. os repositorios que ainda existem de fato na conta GitHub `tscode-com-br`;
3. quais repositorios GitHub ja estao ligados a remotes ativos neste workspace;
4. qual repositorio realmente aciona deploy de producao.

## 1. Realidade atual: workspace local versus conta GitHub

Hoje o workspace ainda possui quatro pastas que sao repositorios Git locais. A conta GitHub `tscode-com-br` acessivel neste ambiente agora expõe seis repositorios confirmados, mas apenas dois deles ja estao ligados a remotes ativos no workspace atual.

| Escopo | Pasta local | Branch local confirmada | Remote local atual | Estado atual no GitHub | Impacto operacional |
| --- | --- | --- | --- | --- | --- |
| Sistema principal | `c:\dev\projetos\checkcheck` | `main` | `origin = https://tscode-com-br@github.com/tscode-com-br/checking.git` | Existe | Dono atual da API, transport, admin, webapplication, docs do sistema, deploy e GitHub Actions de producao |
| App Flutter | `c:\dev\projetos\checkcheck\checking_android_new` | `main` | `origin = https://github.com/tscode-com-br/checking_app_flutter.git` | Existe | Publica apenas o app Flutter |
| App Kotlin legado | `c:\dev\projetos\checkcheck\checking_kotlin` | `main` | `archived-origin = https://github.com/tscode-com-br/checking_app_kotlin.git` | Nao existe mais | Repo local-only; push foi neutralizado e o remote antigo ficou apenas como referencia historica |
| App Kotlin novo | `c:\dev\projetos\checkcheck\checking_kotlin_new` | `web-parity-spa-baseline` | `archived-origin = https://github.com/tscode-com-br/checking_kotlin_new.git` | Nao existe mais | Repo local-only; push foi neutralizado e o remote antigo ficou apenas como referencia historica |

Repositorios que existem hoje no GitHub, mas ainda nao possuem pasta Git propria nem `origin` configurado neste workspace:

| Escopo futuro | Repo GitHub | Estado visivel na auditoria | Ligacao local hoje | Impacto operacional hoje |
| --- | --- | --- | --- | --- |
| API particionada | `tscode-com-br/checking_api` | Existe; `defaultBranchRef` veio vazio na consulta atual | Nenhuma | Ainda nao recebe commit/push deste workspace por si so; enquanto o codigo estiver no root, o dono continua sendo `checkcheck` |
| Transport particionado | `tscode-com-br/checking_transport` | Existe; `defaultBranchRef` veio vazio na consulta atual | Nenhuma | Ainda nao recebe commit/push deste workspace por si so; enquanto o codigo estiver no root, o dono continua sendo `checkcheck` |
| Webapplication particionada | `tscode-com-br/checking_webapplication` | Existe; `defaultBranchRef` veio vazio na consulta atual | Nenhuma | Ainda nao recebe commit/push deste workspace por si so; enquanto o codigo estiver no root, o dono continua sendo `checkcheck` |
| Admin particionado | `tscode-com-br/checking_admin` | Existe; `defaultBranchRef` veio vazio na consulta atual | Nenhuma | Ainda nao recebe commit/push deste workspace por si so; enquanto o codigo estiver no root, o dono continua sendo `checkcheck` |

Confirmacao feita neste ambiente:

- `gh repo list tscode-com-br --limit 200` retornou `tscode-com-br/checking`, `tscode-com-br/checking_api`, `tscode-com-br/checking_transport`, `tscode-com-br/checking_webapplication`, `tscode-com-br/checking_admin` e `tscode-com-br/checking_app_flutter`;
- o remote ativo do root continua apontando para `tscode-com-br/checking`;
- o remote ativo do Flutter continua apontando para `tscode-com-br/checking_app_flutter`;
- `gh repo view tscode-com-br/checking_app_kotlin` falhou porque o repositorio nao existe mais;
- `gh repo view tscode-com-br/checking_kotlin_new` falhou porque o repositorio nao existe mais;
- `checking_api`, `checking_transport`, `checking_webapplication` e `checking_admin` existem na conta GitHub, mas ainda nao aparecem como `origin` de nenhum repositorio local neste workspace;
- na consulta atual via `gh repo list`, esses quatro repositorios novos vieram com `defaultBranchRef` vazio; trate-os como destinos ainda nao conectados e valide a branch inicial antes do primeiro push;
- nos dois repositorios Kotlin locais, o `origin` morto foi renomeado para `archived-origin`;
- as branches Kotlin locais ficaram sem upstream configurado para impedir `git push` acidental para destino inexistente.

### 1.1 Modificacoes mapeadas nesta revisao

1. a conta GitHub deixou de ter apenas dois repositorios relevantes e agora expõe seis repositorios confirmados;
2. foram criados os repositorios `checking_api`, `checking_transport`, `checking_webapplication` e `checking_admin`;
3. os remotes locais ativos do workspace nao mudaram: continuam sendo apenas `checkcheck -> checking` e `checking_android_new -> checking_app_flutter`;
4. os repositorios Kotlin locais continuam em modo local-only, com `archived-origin` apontando para repositorios removidos da conta;
5. o particionamento futuro ja esta preparado na conta GitHub, mas a separacao operacional real ainda nao aconteceu no workspace.

Consequencias praticas:

- o repositorio principal continua sendo o unico dono do deploy de producao da API e dos websites;
- os repositorios `checking_api`, `checking_transport`, `checking_webapplication` e `checking_admin` ainda nao isolam commit/push sozinhos, porque o codigo correspondente continua fisicamente dentro do root `checkcheck`;
- enquanto API, transport, admin e webapplication continuarem dentro do root, o commit/push desses escopos ainda acontece em `checkcheck`;
- o app Flutter continua com repositorio GitHub ativo proprio;
- as pastas `checking_kotlin` e `checking_kotlin_new` continuam locais, mas hoje nao correspondem a repositorios existentes na conta GitHub;
- os repositorios Kotlin ficaram sem `origin` ativo e sem upstream local, entao o estado padrao agora e local-only;
- push a partir dos repositorios Kotlin nao deve ser assumido como valido sem antes criar ou redefinir um novo `origin` existente;
- o root continua ignorando `checking_android_new/`, `checking_kotlin/` e `checking_kotlin_new/` no `.gitignore`;
- alteracoes dos apps moveis nao devem entrar em commits do root.

## 2. Regra de ouro

Antes de qualquer commit ou push, responda primeiro:

1. A mudanca pertence ao sistema principal?
2. A mudanca pertence ao app Flutter?
3. A mudanca pertence a uma pasta Kotlin que hoje esta apenas local?
4. A mudanca pertence a um escopo que ja ganhou repo no GitHub, mas ainda nao foi extraido do root?

Cada mudanca deve ser commitada apenas no repositorio dono do escopo local.

Regra operacional:

- sistema principal: commit e push em `checkcheck`, inclusive para API, transport, admin e webapplication enquanto esses escopos ainda estiverem fisicamente dentro do root;
- Flutter: commit e push em `checking_android_new`;
- `checking_api`, `checking_transport`, `checking_webapplication` e `checking_admin`: ainda nao sao repositorios locais ativos neste workspace; nao usar esses repos como destino de push de arquivos do root antes de extrair o codigo e criar/configurar a pasta Git correspondente;
- Kotlin legado: commit local em `checking_kotlin`; o remote antigo ficou arquivado como `archived-origin` e um novo `origin` precisa ser criado antes de qualquer push;
- Kotlin novo: commit local em `checking_kotlin_new`; o remote antigo ficou arquivado como `archived-origin` e um novo `origin` precisa ser criado antes de qualquer push;
- nao usar `git subtree`;
- nao tentar publicar apps moveis a partir do root;
- nao misturar arquivos de repositorios aninhados no stage do root.

## 3. Qual repo aciona producao

### 3.1 Repositorio principal `checkcheck`

Workflow relevante:

- `.github/workflows/deploy-oceandrive.yml`

Gatilhos atuais confirmados no arquivo:

- `push` em `main`;
- `workflow_dispatch` para fallback manual.

Impacto:

- push em `main` do root publica o codigo do sistema principal e dispara o workflow de deploy;
- o mesmo workflow tambem pode ser executado manualmente pelo GitHub Actions;
- este repositorio e o dono dos Actions Secrets operacionais do deploy.

### 3.2 Repositorios nao-produtivos e repositorios de particionamento futuro

Estado atual na conta GitHub:

- `checking_android_new` continua representado pelo repositorio `tscode-com-br/checking_app_flutter`;
- `checking_api`, `checking_transport`, `checking_webapplication` e `checking_admin` existem hoje na conta GitHub, mas ainda nao possuem checkout Git dedicado nem `origin` correspondente no workspace atual;
- `checking_kotlin` e `checking_kotlin_new` nao possuem hoje repositorio correspondente confirmado na conta GitHub `tscode-com-br`;
- nenhum desses repositorios fora do root faz deploy automatico da API ou dos websites da DigitalOcean.

## 4. Como confirmar pasta local, branch, remote e existencia no GitHub antes de publicar

### 4.1 Sistema principal

```powershell
Set-Location c:\dev\projetos\checkcheck
git branch --show-current
git remote -v
git status --short
gh repo view tscode-com-br/checking
```

### 4.2 Flutter

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_android_new
git branch --show-current
git remote -v
git status --short
gh repo view tscode-com-br/checking_app_flutter
```

### 4.3 Kotlin legado local

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin
git branch -vv
git remote -v
git status --short
gh repo view tscode-com-br/checking_app_kotlin
```

Resultado esperado hoje para o ultimo comando:

- falha informando que o repositorio nao existe mais.

Resultado esperado hoje para o estado Git local:

- aparece `archived-origin`, nao `origin`;
- a branch `main` aparece sem `[remote/branch]` ao lado, porque o upstream foi removido.

### 4.4 Kotlin novo local

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin_new
git branch -vv
git remote -v
git status --short
gh repo view tscode-com-br/checking_kotlin_new
```

Resultado esperado hoje para o ultimo comando:

- falha informando que o repositorio nao existe mais.

Resultado esperado hoje para o estado Git local:

- aparece `archived-origin`, nao `origin`;
- a branch `web-parity-spa-baseline` aparece sem `[remote/branch]` ao lado, porque o upstream foi removido.

Observacao importante para o Kotlin novo local:

- a branch local confirmada e `web-parity-spa-baseline`;
- nao assumir `main` sem verificar primeiro.

### 4.5 Repositorios criados no GitHub para particionamento futuro

```powershell
gh repo view tscode-com-br/checking_api
gh repo view tscode-com-br/checking_transport
gh repo view tscode-com-br/checking_webapplication
gh repo view tscode-com-br/checking_admin
```

Resultado esperado hoje:

- os comandos acima devem confirmar que os repositorios existem na conta GitHub;
- nenhum `git remote -v` do workspace atual aponta ainda para esses repositorios;
- a existencia desses repositorios no GitHub nao muda automaticamente o dono dos arquivos atuais do root;
- o primeiro push independente para qualquer um deles so deve acontecer depois de criar ou clonar a pasta Git dedicada e extrair o escopo correspondente do root.

## 5. Repositorios GitHub confirmados hoje

Repositorios confirmados na conta `tscode-com-br` acessivel neste ambiente:

- `https://github.com/tscode-com-br/checking.git`
- `https://github.com/tscode-com-br/checking_api.git`
- `https://github.com/tscode-com-br/checking_transport.git`
- `https://github.com/tscode-com-br/checking_webapplication.git`
- `https://github.com/tscode-com-br/checking_admin.git`
- `https://github.com/tscode-com-br/checking_app_flutter.git`

Repositorios ja conectados a remotes ativos no workspace atual:

- `checkcheck -> https://github.com/tscode-com-br/checking.git`
- `checking_android_new -> https://github.com/tscode-com-br/checking_app_flutter.git`

Repositorios existentes no GitHub, mas ainda sem pasta Git propria conectada neste workspace:

- `checking_api`
- `checking_transport`
- `checking_webapplication`
- `checking_admin`

Remotes ainda configurados localmente, mas sem repositorio correspondente hoje no GitHub:

- `checking_kotlin: archived-origin = https://github.com/tscode-com-br/checking_app_kotlin.git`
- `checking_kotlin_new: archived-origin = https://github.com/tscode-com-br/checking_kotlin_new.git`

Comando de auditoria rapida:

```powershell
gh repo list tscode-com-br --limit 200
```

Se um novo repositorio GitHub for criado para qualquer app Kotlin, a reativacao recomendada e:

```powershell
Set-Location <pasta-do-repo-kotlin>
git remote remove archived-origin
git remote add origin <novo-url-github>
git push -u origin <branch-atual>
```

## 6. Pre-condicoes antes de qualquer push

Checklist minimo:

1. pasta correta;
2. branch correta;
3. remote correto, ou ausencia deliberada de `origin` quando o repo estiver local-only;
4. confirmacao de que o repositorio ainda existe no GitHub, quando houver intencao de push;
5. confirmacao de que o codigo daquele escopo ja saiu do repo antigo e realmente passou a morar no repo que voce pretende publicar;
6. stage apenas do escopo desejado;
7. testes relevantes executados;
8. ausencia de `.env`, chaves, bancos locais e artefatos de build no commit.

Comandos uteis:

```powershell
git branch --show-current
git branch -vv
git remote -v
git status --short
git diff --cached --stat
gh repo list tscode-com-br --limit 200
```

Regra adicional importante:

- se o `gh repo view` do remote falhar, nao tente `git push` antes de criar um novo repositorio ou apontar o remote para um destino valido;
- se existir apenas `archived-origin`, trate o repositorio como local-only ate a criacao de um novo `origin`.
- se o repo existe no GitHub, mas ainda nao ha pasta Git dedicada para ele no workspace, trate o codigo atual como ainda pertencente ao repo antigo.

## 7. Como fazer commit e push em cada repositorio

As sequencias abaixo assumem PowerShell no Windows e stage explicito por arquivo ou pasta.

Regra importante:

- no root, prefira `git add <arquivos>` em vez de `git add .` quando houver outras mudancas locais nao relacionadas;
- nos repositorios Kotlin, o commit local funciona hoje, mas o push depende primeiro de recriar um `origin` valido.

### 7.1 Sistema principal `checkcheck`

Quando usar:

- API
- transport
- admin
- webapplication
- websites do sistema
- deploy
- documentacao do repo principal
- qualquer area que ainda nao tenha sido fisicamente extraida para `checking_api`, `checking_transport`, `checking_webapplication` ou `checking_admin`

Fluxo recomendado:

```powershell
Set-Location c:\dev\projetos\checkcheck
git status --short
git branch --show-current
git remote -v
gh repo view tscode-com-br/checking

git add <arquivo-ou-pasta>
git commit -m "<mensagem>"
git push origin main
```

Observacoes:

- `git push origin main` neste repo aciona o deploy de producao;
- a existencia dos repositorios `checking_api`, `checking_transport`, `checking_webapplication` e `checking_admin` no GitHub nao transfere ownership automaticamente para fora do root;
- se houver outros arquivos modificados no root e eles nao fizerem parte da entrega, nao use `git add .`.

### 7.2 App Flutter `checking_android_new`

Quando usar:

- app Flutter
- testes Flutter
- assets e configuracoes do projeto Flutter

Fluxo recomendado:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_android_new
git status --short
git branch --show-current
git remote -v
gh repo view tscode-com-br/checking_app_flutter

git add <arquivo-ou-pasta>
git commit -m "<mensagem>"
git push origin main
```

Observacoes:

- este push publica apenas o repositorio Flutter;
- ele nao aciona o deploy da API nem do website principal.

### 7.3 Repositorios GitHub criados para particionamento futuro

Estado atual:

- `checking_api`, `checking_transport`, `checking_webapplication` e `checking_admin` existem no GitHub;
- nenhum deles possui hoje pasta Git dedicada nem `origin` configurado neste workspace;
- portanto, ainda nao existe fluxo direto de `git add`/`git commit`/`git push` para esses repositorios a partir da arvore atual.

Regra pratica:

1. enquanto o codigo continuar dentro de `c:\dev\projetos\checkcheck`, o dono operacional continua sendo o root `checkcheck`;
2. a independencia de commit/push so comeca quando o escopo for realmente extraido para uma pasta Git propria;
3. criar o repo no GitHub foi apenas a primeira metade do isolamento; a segunda metade e mover o codigo e ligar o remote certo.

Fluxo recomendado para ativar qualquer um desses repositorios no futuro:

1. criar ou clonar a pasta Git dedicada fora do root atual;
2. mover apenas o escopo daquele repositorio para a nova pasta;
3. configurar `origin` para o repo GitHub correspondente;
4. fazer o primeiro commit/push nesse repo novo;
5. remover do root a ownership operacional daquele escopo para evitar duplicidade.

### 7.4 App Kotlin legado `checking_kotlin`

Estado atual:

- branch local confirmada: `main`
- remote ativo de publicacao: inexistente
- remote historico preservado: `archived-origin`

Commit local hoje:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin
git status --short
git branch -vv
git remote -v

git add <arquivo-ou-pasta>
git commit -m "<mensagem>"
```

Push so depois de recriar `origin`:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin
git remote remove archived-origin
git remote add origin <novo-url-github>
gh repo view <owner>/<repo>
git push -u origin main
```

Observacoes:

- nao tente `git push origin main` antes de recriar `origin`;
- se quiser manter o remote historico apenas como referencia, renomeie em vez de apagar e adapte o comando acima.

### 7.5 App Kotlin novo `checking_kotlin_new`

Estado atual:

- branch local confirmada: `web-parity-spa-baseline`
- remote ativo de publicacao: inexistente
- remote historico preservado: `archived-origin`

Commit local hoje:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin_new
git status --short
git branch -vv
git remote -v

git add <arquivo-ou-pasta>
git commit -m "<mensagem>"
```

Push so depois de recriar `origin`:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin_new
git remote remove archived-origin
git remote add origin <novo-url-github>
gh repo view <owner>/<repo>
git push -u origin web-parity-spa-baseline
```

Observacoes:

- nao trocar a branch por `main` sem confirmar antes o fluxo desejado;
- hoje o caminho seguro e tratar esse repo como local-only ate existir um novo repositorio GitHub.

## 8. O que nao deve entrar em commit

Itens normalmente excluidos:

- `.env`
- `.venv/`
- `deploy/keys/`
- arquivos `*.db`, `*.sqlite`, `*.sqlite3`
- artefatos de build
- caches locais
- qualquer arquivo de repositorio aninhado quando voce estiver no root

## 9. Dono de GitHub Actions e Secrets

O dono operacional de GitHub Actions e Secrets do deploy e o repo principal `checkcheck`.

Estado confirmado no ambiente atual:

- a conta autenticada `tscode-com-br` no GitHub CLI tem permissao `admin` no repo `tscode-com-br/checking`;
- o endpoint `repos/tscode-com-br/checking/actions/secrets/public-key` responde corretamente;
- a leitura da lista de secrets do deploy esta funcionando.

Isso nao muda a regra de escopo:

- Actions e Secrets de deploy pertencem ao repo principal;
- o app Flutter continua fora do fluxo de deploy da DigitalOcean;
- as pastas Kotlin locais nao controlam deploy, nao tem `origin` ativo e hoje tambem nao possuem repositorio GitHub correspondente confirmado.

## 10. Playbook detalhado para quando um agente de IA for fazer commit, push e acompanhar deploy

As secoes anteriores explicam quem e o dono de cada repositorio.

Esta secao nova define o comportamento operacional esperado quando o pedido ao agente de IA incluir explicitamente:

- fazer commit;
- fazer push;
- acompanhar o deploy;
- validar se a publicacao terminou bem.

Regra principal:

- no repo principal, push em `main` e operacao sensivel de producao;
- no repo Flutter, push publica apenas o app Flutter;
- nos repositorios GitHub-only `checking_api`, `checking_transport`, `checking_webapplication` e `checking_admin`, o playbook so passa a valer como repo independente depois que existir pasta Git local propria e o codigo daquele escopo sair do root;
- nos repositorios Kotlin locais, commit local ainda e valido, mas push continua bloqueado ate existir um `origin` real.

### 10.1 Sequencia obrigatoria antes de qualquer stage

Quando um agente de IA receber pedido de commit/push, ele deve comecar sempre pela auditoria abaixo no repositorio correto.

#### Sistema principal

```powershell
Set-Location c:\dev\projetos\checkcheck
git status -sb
git branch --show-current
git remote -v
git diff --stat
git diff --cached --stat
gh repo view tscode-com-br/checking
```

#### Flutter

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_android_new
git status -sb
git branch --show-current
git remote -v
git diff --stat
git diff --cached --stat
gh repo view tscode-com-br/checking_app_flutter
```

#### Kotlin legado local-only

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin
git status -sb
git branch -vv
git remote -v
git diff --stat
git diff --cached --stat
```

#### Kotlin novo local-only

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin_new
git status -sb
git branch -vv
git remote -v
git diff --stat
git diff --cached --stat
```

Saida esperada antes de prosseguir:

1. a pasta atual e o repo dono da mudanca;
2. a branch atual foi confirmada e nao esta sendo assumida por memoria;
3. o `origin` existe quando houver intencao de push;
4. o `archived-origin` isolado continua sendo tratado como local-only;
5. o agente ja sabe quais arquivos mudaram antes de adicionar qualquer coisa ao stage.

### 10.2 Situacoes em que o agente deve parar antes do push

O agente nao deve improvisar push se qualquer um dos pontos abaixo acontecer:

1. a mudanca esta no repo errado;
2. existe mistura de arquivos do root com arquivos de repositorios aninhados;
3. o `gh repo view` falha para um destino que deveria receber push;
4. o repositorio esta local-only e ainda nao existe `origin` valido;
5. ha alteracoes locais nao relacionadas que o usuario nao pediu para publicar;
6. testes relevantes ainda nao foram rodados;
7. a entrega depende tambem de `.env`, secret do GitHub, dado manual de banco ou alteracao de host e isso ainda nao foi tratado.

Em qualquer uma dessas situacoes, o comportamento certo e resolver a pendencia primeiro ou informar claramente que commit/push sozinho nao fecha a entrega.

O mesmo bloqueio vale quando o repo ja existe no GitHub, mas o workspace ainda nao possui checkout Git dedicado para ele.

### 10.3 Como o agente deve montar o stage

Regra geral:

- preferir `git add <arquivo>` ou `git add <pasta-especifica>`;
- evitar `git add .` no root sempre que houver qualquer risco de capturar mudancas nao relacionadas;
- conferir o stage antes do commit;
- conferir tambem os untracked files para garantir que nenhum artefato local entrou por engano.

Sequencia recomendada:

```powershell
git status --short
git add <arquivo-ou-pasta>
git status --short
git diff --cached --stat
git diff --cached
```

Conferencia minima esperada:

1. so os arquivos da entrega aparecem staged;
2. nada de `.env`, `deploy/keys/`, `*.db`, cache, build output ou repositorio aninhado entrou no commit;
3. a diff staged bate com a explicacao funcional da entrega;
4. se houver mudanca de deploy ou infraestrutura, ela foi revisada com mais cuidado do que uma mudanca comum de app.

### 10.4 Como o agente deve escolher a mensagem de commit

A mensagem de commit deve ser curta, especifica e alinhada ao efeito real do change set.

Padrao recomendado:

- usar verbo de acao;
- mencionar o escopo principal;
- evitar mensagens vagas como `update`, `fixes`, `changes` ou `ajustes` sem contexto.

Exemplos bons:

```text
fix(transport-ai): corrige indices da matrix do Mapbox
docs(github): detalha fluxo de commit push e deploy
fix(admin): preserva scroll no refresh automatico
```

Fluxo de commit:

```powershell
git commit -m "<mensagem>"
git rev-parse HEAD
```

O `git rev-parse HEAD` deve ser guardado no relatorio final do agente para facilitar rastreio do deploy.

### 10.5 Como o push deve acontecer em cada repo

#### Sistema principal `checkcheck`

Use apenas quando a mudanca pertence ao repo root e o usuario quer publicar no repo principal.

Fluxo detalhado:

```powershell
Set-Location c:\dev\projetos\checkcheck
git status -sb
git branch --show-current
git remote -v
gh repo view tscode-com-br/checking
git diff --cached --stat
git commit -m "<mensagem>"
git rev-parse HEAD
git push origin main
```

Observacoes obrigatorias:

1. `git push origin main` neste repo aciona o workflow de deploy de producao;
2. se a branch atual nao for `main`, o agente nao deve afirmar que houve deploy automatico de producao so porque houve push;
3. se o agente estiver em branch diferente e o pedido do usuario for acompanhar deploy de producao, ele precisa deixar claro que o deploy automatico depende do update em `main`;
4. se existir sujeira nao relacionada no root, o stage deve continuar explicito por arquivo.

#### Flutter `checking_android_new`

Fluxo detalhado:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_android_new
git status -sb
git branch --show-current
git remote -v
gh repo view tscode-com-br/checking_app_flutter
git diff --cached --stat
git commit -m "<mensagem>"
git rev-parse HEAD
git push origin main
```

Observacoes obrigatorias:

1. esse push nao faz deploy da API;
2. esse push nao publica websites do sistema principal;
3. o agente nao deve prometer deploy na DigitalOcean ao publicar o repo Flutter.

#### Kotlin legado `checking_kotlin`

Fluxo detalhado hoje:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin
git status -sb
git branch -vv
git remote -v
git diff --cached --stat
git commit -m "<mensagem>"
git rev-parse HEAD
```

Push so depois de recriar `origin`:

```powershell
git remote remove archived-origin
git remote add origin <novo-url-github>
gh repo view <owner>/<repo>
git push -u origin main
```

#### Kotlin novo `checking_kotlin_new`

Fluxo detalhado hoje:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin_new
git status -sb
git branch -vv
git remote -v
git diff --cached --stat
git commit -m "<mensagem>"
git rev-parse HEAD
```

Push so depois de recriar `origin`:

```powershell
git remote remove archived-origin
git remote add origin <novo-url-github>
gh repo view <owner>/<repo>
git push -u origin web-parity-spa-baseline
```

### 10.6 O que o agente deve fazer imediatamente depois do push no repo principal

No repo principal, o trabalho nao termina no `git push origin main`.

O agente deve acompanhar o workflow de producao ate conclusao ou falha clara.

Sequencia recomendada:

```powershell
Set-Location c:\dev\projetos\checkcheck
gh run list --workflow deploy-oceandrive.yml --limit 5
gh run watch <run-id> --exit-status
gh run view <run-id> --log-failed
```

Comportamento esperado:

1. identificar o run disparado pelo commit enviado;
2. acompanhar o workflow ate `success` ou `failure`;
3. se falhar, capturar o passo exato que falhou e os logs relevantes;
4. se passar, validar a saude publica antes de encerrar o trabalho.

O agente nao deve parar logo apos o push dizendo apenas que o deploy foi "disparado".

O encerramento correto para o repo principal exige pelo menos:

1. SHA do commit enviado;
2. id ou URL do run do GitHub Actions;
3. conclusao do run;
4. resultado da validacao de health.

### 10.7 Como validar o deploy depois do Actions verde

Validacao minima do sistema principal:

```powershell
curl.exe -fsS https://tscode.com.br/api/health
```

Se houver necessidade de confirmacao no host:

```powershell
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 "curl -fsS http://127.0.0.1:8000/api/health"
```

Se a entrega afetar uma funcionalidade critica, o agente deve fazer tambem uma validacao funcional focada, nao apenas o health.

Exemplos:

- rota HTTP especifica da feature alterada;
- smoke de autenticacao;
- fluxo do Transport AI, quando a entrega mexer nele;
- pagina publica impactada pela mudanca.

Regra importante:

- health verde prova que a aplicacao subiu;
- health verde sozinho nao prova que a funcionalidade alterada ficou correta.

## 11. O que o deploy principal realmente faz no repo root

O fluxo de producao confirmado em `.github/workflows/deploy-oceandrive.yml` faz hoje, em linhas gerais:

1. checkout do repo;
2. build e push da imagem `ghcr.io/tscode-com-br/checkcheck-app:<sha>`;
3. criacao do diretorio remoto;
4. remocao no host de `checking_android_new`, `checking_kotlin` e `checking_kotlin_new` legados;
5. `rsync --delete` do projeto para o host;
6. materializacao do `.env` a partir do secret `OCEAN_APP_ENV_B64`, se esse secret estiver preenchido;
7. pull da imagem no host;
8. migracao do banco;
9. restart do `app`;
10. validacao de health local e publica;
11. limpeza de residuos de deploy e guarda de SSD.

Consequencias praticas para qualquer agente de IA:

1. arquivo apagado do repo pode ser apagado no host por causa do `rsync --delete`;
2. `.env` nao vai pelo `rsync`;
3. se `OCEAN_APP_ENV_B64` estiver configurado, o `.env` do host pode ser sobrescrito no deploy;
4. push de codigo nao garante, sozinho, que uma mudanca manual de ambiente sera preservada;
5. o deploy principal e sensivel e deve ser tratado como publicacao de producao real.

## 12. O que commit e push NAO levam sozinhos para producao

Mesmo com commit correto e Actions verde, ha classes de mudanca que nao sao cobertas apenas pelo push do repo.

### 12.1 Ajustes de `.env` e secrets

Esses itens nao devem ser tratados como automaticamente resolvidos por commit/push:

- `.env` local;
- secret `OCEAN_APP_ENV_B64`;
- quaisquer secrets do GitHub Actions;
- qualquer valor configurado manualmente so no host.

Exemplos reais sensiveis neste projeto:

- `MAPBOX_ACCESS_TOKEN`;
- `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY`;
- `TRANSPORT_AI_AGENT_MODE`;
- `TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE`.

Se uma entrega depende de um desses valores, o agente deve dizer explicitamente no relatorio final se:

1. o valor ja estava sincronizado no secret/fonte de verdade;
2. o valor foi alterado somente no host;
3. o deploy seguinte pode sobrescrever o ajuste.

### 12.2 Ajustes de banco e dados operacionais

O deploy normal preserva o banco porque o Postgres usa volume persistente, mas commit/push nao recria automaticamente uma correcao de dado feita manualmente em producao.

Exemplos:

- correcoes em linhas da tabela `projects`;
- backfills manuais;
- limpeza de dados inconsistentes;
- mudancas em tabelas de configuracao operacional.

Regra esperada do agente:

1. se a entrega depender de dado ajustado manualmente, registrar isso;
2. se possivel, codificar a correcao em migration, seed controlado ou script de saneamento;
3. nao afirmar que "o deploy sozinho resolve" algo que na verdade ainda depende do estado atual do banco.

### 12.3 Ajustes de host e infraestrutura

Esses pontos tambem nao devem ser confundidos com commit/push simples:

- nginx editado manualmente no droplet;
- unit file do systemd;
- arquivos fora do diretorio do app;
- manutencao manual de volumes, caches ou backups.

## 13. Checklists operacionais para agentes de IA

### 13.1 Checklist minimo antes do commit

1. confirmar repo correto;
2. confirmar branch correta;
3. confirmar remote correto;
4. revisar `git status -sb`;
5. revisar `git diff --stat`;
6. rodar testes relevantes;
7. stage explicito apenas dos arquivos desejados;
8. revisar `git diff --cached --stat`;
9. garantir que nenhum artefato local entrou no commit.

### 13.2 Checklist minimo antes do push no root

1. o usuario realmente pediu publicacao no repo principal;
2. o commit staged e o commit final batem com a entrega esperada;
3. `git push origin main` foi entendido como deploy de producao;
4. nao ha dependencia oculta de `.env`, secret ou dado manual nao mencionada;
5. o agente sabe qual validacao funcional devera executar depois do Actions verde.

### 13.3 Checklist minimo depois do push no root

1. obter o `run-id` do workflow;
2. acompanhar o workflow ate terminar;
3. se falhar, coletar o passo e o log;
4. se passar, validar `https://tscode.com.br/api/health`;
5. se a feature exigir, validar tambem o fluxo funcional alterado;
6. relatar SHA, run, resultado e qualquer pendencia de ambiente ou dados.

## 14. Prompt recomendado quando voce pedir a um agente de IA para fazer commit, push e acompanhar deploy

Se quiser maximizar a chance de um agente executar corretamente, use um pedido proximo deste modelo:

```text
Trabalhe apenas no repositorio dono desta mudanca.
Antes de commitar, audite pasta atual, branch, remote, arquivos modificados e arquivos staged.
Faca stage explicito apenas dos arquivos desta entrega.
Nao use git add . no repo root se houver qualquer outro arquivo modificado fora do escopo.
Rode os testes relevantes antes do commit.
Depois faca o commit com mensagem especifica.
Se for o repo principal, faca push em main somente se a entrega estiver pronta para deploy de producao.
Depois acompanhe o workflow deploy-oceandrive.yml ate o fim.
Valide https://tscode.com.br/api/health e, se a feature exigir, rode tambem uma validacao funcional focada.
No final, me informe: repo, branch, SHA, arquivos commitados, run-id ou URL do Actions, resultado do deploy e qualquer ajuste que ainda dependa de .env, secret ou banco.
```

Complemento importante para pedidos envolvendo Transport AI:

```text
Se a entrega depender de configuracao de ambiente, secret ou dado manual de producao, nao trate commit/push como suficiente. Diga explicitamente o que ficou fora do Git e o que precisa ser sincronizado para o proximo deploy nao reverter o comportamento.
```