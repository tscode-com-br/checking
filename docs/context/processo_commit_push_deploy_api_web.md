# Processo de Commit e Push para Deploy da API e do Website

## 1. Objetivo

Este documento registra, de forma detalhada, como realizar o commit e o push do repositorio principal `checkcheck` para que a API FastAPI e o website administrativo sejam atualizados automaticamente no provedor Digital Ocean.

Este e o fluxo usado no commit publicado em `2026-04-08`, que gerou o push para `origin/main` e disparou o deploy automatico.

## 2. Escopo correto deste deploy

O deploy automatico do Digital Ocean e acionado pelo repositorio principal deste projeto, que contem:

- API FastAPI;
- website administrativo;
- firmware ESP32;
- documentacao do repositrio principal.

O app Android `checking_android` nao faz parte deste push, porque possui ciclo de versionamento proprio.

## 3. Premissas antes do push

Antes de comitar e enviar alteracoes, validar estes pontos:

1. estar dentro do repositorio `c:\dev\projetos\checkcheck`;
2. confirmar que a branch atual e `main`;
3. confirmar que o remoto `origin` aponta para o repositrio GitHub correto;
4. verificar se existem arquivos locais nao relacionados que nao devem entrar no commit;
5. garantir que os testes relevantes da alteracao ja foram executados;
6. evitar incluir o repositrio Android separado por engano.

## 4. Comandos de verificacao inicial

Os comandos usados para preparar este push foram:

```powershell
git -C . branch --show-current
git -C . remote -v
git -C . status --short
git -C . status --branch
```

Resultado esperado:

- branch atual: `main`;
- remoto `origin` apontando para `https://github.com/tscode-com-br/checking.git`;
- branch local sincronizada com `origin/main` antes do novo commit.

## 5. Como identificar o que entra no commit

No momento deste processo, o `git status --short` mostrava:

- arquivos modificados do backend, frontend admin, firmware e documentacao;
- a pasta `checking_android/` como item nao rastreado;
- o arquivo `package-lock.json` como item nao rastreado.

Esses dois ultimos itens nao entraram no commit:

- `checking_android/`: repositorio separado, fora do escopo deste deploy da API/web;
- `package-lock.json`: arquivo local nao necessario para o backend FastAPI ou para o painel admin estatico.

Regra pratica:

- incluir apenas arquivos que pertencem ao repositorio principal e fazem parte da entrega desejada;
- deixar fora arquivos locais, repositorios aninhados e artefatos soltos sem impacto real no deploy da API/web.

## 6. Arquivos staged neste push

O stage foi montado de forma explicita, sem usar `git add .`, para evitar incluir itens fora do escopo.

Comando utilizado:

```powershell
git -C . add README.md docs/Instrucoes.txt docs/descritivo_sistema.md docs/esp32_firmware_troubleshooting.md docs/esquematico_esp32_rc522_duplo.md docs/context firmware/esp32_checking/esp32_checking.ino sistema/app/routers/admin.py sistema/app/static/admin/app.js sistema/app/static/admin/index.html tests/test_api_flow.py docs/contexto_login_admin.md
```

Observacao importante:

- `docs/contexto_login_admin.md` foi incluido no stage porque o Git detectou o movimento para `docs/context/contexto_login_admin.md` como `rename`.

## 7. Como revisar o stage antes do commit

Depois do `git add`, os comandos usados para revisar o stage foram:

```powershell
git -C . status --short
git -C . diff --cached --stat
```

Objetivo dessa revisao:

1. confirmar que apenas os arquivos desejados entraram no commit;
2. confirmar que `checking_android/` e `package-lock.json` continuaram fora;
3. verificar se houve `rename` correto dos arquivos de contexto;
4. ter uma visao resumida do volume da mudanca antes de gravar o commit.

## 8. Commit realizado

O commit foi criado com:

```powershell
git -C . commit -m "Update admin events cleanup and ESP32 docs"
```

Hash gerado:

```text
8fa0445
```

Motivo desse commit:

- corrigir a limpeza da aba `Eventos` no admin;
- remover a aba `Inativos` do frontend admin;
- atualizar documentacao e firmware relacionados ao comportamento atual do sistema.

## 9. Push que dispara o deploy

O push foi feito com:

```powershell
git -C . push origin main
```

Resultado esperado:

- o GitHub recebe o commit na branch `main`;
- o workflow de deploy do projeto e acionado automaticamente;
- o servidor no Digital Ocean atualiza a API e o website administrativo.

Neste caso, o retorno confirmou:

```text
To https://github.com/tscode-com-br/checking.git
   561a065..8fa0445  main -> main
```

## 10. O que este push atualiza no Digital Ocean

Ao subir para `main`, o fluxo automatico do projeto deve:

1. sincronizar o codigo no servidor;
2. atualizar containers com `docker compose up -d --build --remove-orphans`;
3. manter a API FastAPI acessivel no dominio de producao;
4. servir a versao nova do website administrativo;
5. validar o health check da aplicacao.

## 11. Verificacao apos o push

Depois do push, e recomendavel validar rapidamente:

### 11.1 Estado local do Git

```powershell
git -C . status --short
```

Neste caso, restaram apenas:

- `checking_android/`
- `package-lock.json`

Ou seja, nada adicional do repositorio principal ficou pendente apos o push.

### 11.2 Health check em producao

Validar:

```text
https://tscode.com.br/api/health
```

O retorno esperado deve indicar que a API esta saudavel.

### 11.3 Validacao funcional minima do admin

Validar no website administrativo:

1. login do admin;
2. carregamento das abas;
3. funcionamento da aba `Eventos`;
4. funcionamento do botao `Limpar`;
5. atualizacao normal das tabelas.

## 12. Cuidados importantes para repetir este processo

### 12.1 Nao usar `git add .` cegamente

Neste projeto, isso pode incluir:

- `checking_android/`;
- artefatos locais;
- arquivos auxiliares nao relacionados;
- arquivos de configuracao ou segredo que nao deveriam subir.

### 12.2 Conferir sempre o remoto

O remoto correto deste repositorio principal deve apontar para `tscode-com-br/checking`.

### 12.3 Fazer push na branch certa

O deploy automatico esperado depende de push em `main`.

### 12.4 Rodar testes relevantes antes do push

Neste caso, antes do push foram executados testes focados no fluxo de arquivamento de eventos, para garantir que a mudanca principal nao quebrasse o contrato da API/admin.

### 12.5 Separar o repositrio Android do repositrio principal

Mesmo que a pasta `checking_android` exista dentro do workspace, ela nao deve ser misturada com o commit da API/web quando a entrega for apenas do backend e do painel administrativo.

## 13. Passo a passo resumido

Fluxo enxuto para repetir exatamente este processo:

1. Entrar no repositorio `checkcheck`.
2. Rodar:

```powershell
git -C . branch --show-current
git -C . remote -v
git -C . status --short
```

3. Adicionar apenas os arquivos corretos ao stage.
4. Revisar com:

```powershell
git -C . status --short
git -C . diff --cached --stat
```

5. Criar o commit:

```powershell
git -C . commit -m "Update admin events cleanup and ESP32 docs"
```

6. Enviar para producao:

```powershell
git -C . push origin main
```

7. Validar `https://tscode.com.br/api/health` e o painel admin.

## 14. Resumo deste caso especifico

O processo realizado agora foi:

1. verificar branch e remoto;
2. revisar arquivos alterados;
3. excluir do escopo `checking_android/` e `package-lock.json`;
4. montar stage manualmente;
5. revisar o stage;
6. criar o commit `8fa0445`;
7. fazer push para `origin/main`;
8. disparar o deploy automatico da API e do website no Digital Ocean.

Esse e o procedimento recomendado para futuras publicacoes do repositorio principal quando a entrega envolver backend, painel admin, firmware e documentacao correlata.