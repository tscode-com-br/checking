# Procedimento Oficial de Repositorios do Projeto Checking

## 1. Objetivo

Este documento registra o estado Git real do workspace e define o procedimento oficial de operacao por repositorio.

Estado validado em 2026-04-19.

## 2. Topologia Git atual do workspace

Hoje o workspace contem dois repositorios Git distintos:

### 2.1 Repositorio principal

- Pasta: `c:\dev\projetos\checkcheck`
- Remote `origin`: `tscode-com-br/checking`
- Escopo: API FastAPI, website admin, firmware ESP32, documentacao e demais arquivos do sistema principal.
- Impacto de push em `main`: dispara o workflow `.github/workflows/deploy-oceandrive.yml` e atualiza producao.

### 2.2 Repositorio local do app Flutter

- Pasta: `c:\dev\projetos\checkcheck\checking_android_new`
- Remote `origin`: `tscode-com-br/checking_app_flutter`
- Escopo: codigo do aplicativo Android em Flutter.
- Estado operacional atual: fora do fluxo oficial de commit/push do projeto.

### 2.3 Isolamento entre os dois repositorios

- O `.gitignore` do repositorio principal ignora `checking_android_new/`.
- Isso impede que alteracoes do app Flutter entrem por engano em commits do sistema principal.
- O fato de o app ter `.git` proprio nao significa que ele deva ser publicado no fluxo operacional atual.

## 3. Regra operacional oficial

1. O unico repositorio com commit/push oficial do projeto e o repositorio principal `checkcheck`.
2. O app Flutter permanece no workspace apenas para leitura, manutencao local, build e testes quando necessario.
3. Nao existe mais procedimento oficial de publicacao por Git para `checking_android_new`.
4. Nao usar `git subtree` para tentar publicar o app Flutter.
5. Nao fazer `git push` dentro de `checking_android_new` como parte da rotina operacional do projeto.

## 4. Procedimento oficial por repositorio

### 4.1 Repositorio principal `checkcheck`

Este e o unico fluxo oficial de commit/push.

Passo a passo:

1. Entrar em `c:\dev\projetos\checkcheck`.
2. Confirmar branch, remote e status:

```powershell
git -C . branch --show-current
git -C . remote -v
git -C . status --short
git -C . status --branch
```

3. Adicionar apenas os arquivos corretos ao stage, sem usar `git add .` cegamente.
4. Revisar o stage:

```powershell
git -C . status --short
git -C . diff --cached --stat
```

5. Criar o commit.
6. Fazer `git -C . push origin main` apenas quando a intencao for publicar e disparar deploy.
7. Validar `https://tscode.com.br/api/health` e o painel admin apos o push.

Regra critica:

- qualquer push em `main` do repositorio principal gera deploy de producao;
- portanto, nao fazer push nem mesmo de documentacao se a orientacao for risco zero.

### 4.2 Repositorio local do app Flutter `checking_android_new`

Este repositorio nao participa mais do procedimento oficial de publicacao do projeto.

Regra pratica:

- nao fazer `git commit` neste diretorio como parte da rotina operacional oficial;
- nao fazer `git push` deste diretorio;
- nao usar `git subtree split --prefix checking_android_new ...` no repositorio principal.

Uso permitido:

- leitura de codigo;
- manutencao local;
- build local de APK/AAB;
- testes locais do app, quando necessario.

Uso nao permitido no fluxo oficial:

- sincronizacao Git do app Flutter;
- publicacao por subtree;
- qualquer rotina de deploy baseada no repositorio do app.

## 5. Resumo executivo

- Existem dois repositorios Git no workspace.
- Apenas um deles participa do fluxo oficial: `checkcheck`.
- O repositorio Flutter continua existindo localmente, mas esta fora da rotina oficial de commit/push.
- O projeto deve ser operado, publicado e versionado oficialmente apenas pelo repositorio principal.