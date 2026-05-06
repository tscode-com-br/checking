# Acesso aos repositorios GitHub do projeto

Status deste documento: reconciliado com a conta GitHub, com os remotes locais e com o fluxo operacional de commit/push em 2026-05-06.

Este arquivo substitui o antigo guia `instrucoes_commit_push.md` e consolida tres coisas diferentes que nao devem mais ser misturadas:

1. as pastas Git locais que ainda existem no workspace;
2. os repositorios que ainda existem de fato na conta GitHub `tscode-com-br`;
3. qual repositorio realmente aciona deploy de producao.

## 1. Realidade atual: workspace local versus conta GitHub

Hoje o workspace ainda possui quatro pastas que sao repositorios Git locais, mas a conta GitHub `tscode-com-br` acessivel neste ambiente expõe apenas dois repositorios confirmados.

| Escopo | Pasta local | Branch local confirmada | Remote local atual | Estado atual no GitHub | Impacto operacional |
| --- | --- | --- | --- | --- | --- |
| Sistema principal | `c:\dev\projetos\checkcheck` | `main` | `origin = https://github.com/tscode-com-br/checking.git` | Existe | Dono da API, websites, docs do sistema, deploy e GitHub Actions de producao |
| App Flutter | `c:\dev\projetos\checkcheck\checking_android_new` | `main` | `origin = https://github.com/tscode-com-br/checking_app_flutter.git` | Existe | Publica apenas o app Flutter |
| App Kotlin legado | `c:\dev\projetos\checkcheck\checking_kotlin` | `main` | `archived-origin = https://github.com/tscode-com-br/checking_app_kotlin.git` | Nao existe mais | Repo local-only; push foi neutralizado e o remote antigo ficou apenas como referencia historica |
| App Kotlin novo | `c:\dev\projetos\checkcheck\checking_kotlin_new` | `web-parity-spa-baseline` | `archived-origin = https://github.com/tscode-com-br/checking_kotlin_new.git` | Nao existe mais | Repo local-only; push foi neutralizado e o remote antigo ficou apenas como referencia historica |

Confirmacao feita neste ambiente:

- `gh repo list tscode-com-br --limit 200` retornou apenas `tscode-com-br/checking` e `tscode-com-br/checking_app_flutter`;
- `gh repo view tscode-com-br/checking_app_kotlin` falhou porque o repositorio nao existe mais;
- `gh repo view tscode-com-br/checking_kotlin_new` falhou porque o repositorio nao existe mais.
- nos dois repositorios Kotlin locais, o `origin` morto foi renomeado para `archived-origin`;
- as branches Kotlin locais ficaram sem upstream configurado para impedir `git push` acidental para destino inexistente.

Consequencias praticas:

- o repositorio principal continua sendo o unico dono do deploy de producao da API e dos websites;
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

Cada mudanca deve ser commitada apenas no repositorio dono do escopo local.

Regra operacional:

- sistema principal: commit e push em `checkcheck`;
- Flutter: commit e push em `checking_android_new`;
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

### 3.2 Repositorios moveis

Estado atual na conta GitHub:

- `checking_android_new` continua representado pelo repositorio `tscode-com-br/checking_app_flutter`;
- `checking_kotlin` e `checking_kotlin_new` nao possuem hoje repositorio correspondente confirmado na conta GitHub `tscode-com-br`;
- nenhum repositorio movel faz deploy automatico da API ou dos websites da DigitalOcean.

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

## 5. Repositorios GitHub confirmados hoje

Repositorios confirmados na conta `tscode-com-br` acessivel neste ambiente:

- `https://github.com/tscode-com-br/checking.git`
- `https://github.com/tscode-com-br/checking_app_flutter.git`

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
5. stage apenas do escopo desejado;
6. testes relevantes executados;
7. ausencia de `.env`, chaves, bancos locais e artefatos de build no commit.

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

## 7. Como fazer commit e push em cada repositorio

As sequencias abaixo assumem PowerShell no Windows e stage explicito por arquivo ou pasta.

Regra importante:

- no root, prefira `git add <arquivos>` em vez de `git add .` quando houver outras mudancas locais nao relacionadas;
- nos repositorios Kotlin, o commit local funciona hoje, mas o push depende primeiro de recriar um `origin` valido.

### 7.1 Sistema principal `checkcheck`

Quando usar:

- API
- websites do sistema
- deploy
- documentacao do repo principal

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

### 7.3 App Kotlin legado `checking_kotlin`

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

### 7.4 App Kotlin novo `checking_kotlin_new`

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