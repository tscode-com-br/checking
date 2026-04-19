# Processo de Commit e Push para Deploy da API e do Website

## 1. Objetivo

Este documento registra, de forma detalhada, como realizar o commit e o push do repositório principal `checkcheck` para que a API FastAPI e o website administrativo sejam atualizados automaticamente no provedor DigitalOcean.

Este é o fluxo usado no commit publicado em `2026-04-08`, que gerou o push para `origin/main` e disparou o deploy automático.

Atualizacao operacional validada em `2026-04-19`:

- o workspace contem dois repositorios Git distintos: `checkcheck` e `checking_android_new`;
- o procedimento oficial de commit/push do projeto existe apenas para o repositorio principal `checkcheck`;
- o app Flutter permanece fora do fluxo oficial de publicacao por Git, mesmo mantendo `.git` proprio no workspace.

## 2. Escopo correto deste deploy

O deploy automático do DigitalOcean é acionado pelo repositório principal deste projeto, que contém:

- API FastAPI;
- website administrativo;
- firmware ESP32;
- documentação do repositório principal.

O app Android atual em `checking_android_new` tem Git proprio no workspace, mas não participa do deploy automático da API/web nem do procedimento oficial de commit/push.

Por decisão operacional atual, não existe fluxo oficial de publicação por Git para o app Flutter. Não usar `git subtree` nem push direto do repositório aninhado como parte da rotina do projeto.

## 3. Premissas antes do push

Antes de comitar e enviar alterações, valide estes pontos:

1. estar dentro do repositório `c:\dev\projetos\checkcheck`;
2. confirmar que a branch atual é `main`;
3. confirmar que o remoto `origin` aponta para o repositório GitHub correto;
4. verificar se existem arquivos locais não relacionados que não devem entrar no commit;
5. garantir que os testes relevantes da alteração já foram executados;
6. evitar incluir artefatos locais fora do escopo por engano.

## 4. Comandos de verificação inicial

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

- arquivos modificados do backend, frontend admin, firmware e documentação;
- o arquivo `package-lock.json` como item não rastreado.

Observação histórica:

- na execução original também havia uma pasta local do app Android antigo fora do controle do repositório principal; ela já foi removida do workspace atual.

Esses itens locais não entraram no commit:

- `package-lock.json`: arquivo local não necessário para o backend FastAPI ou para o painel admin estático.

Regra prática:

- incluir apenas arquivos que pertencem ao repositório principal e fazem parte da entrega desejada;
- deixar fora arquivos locais, repositórios aninhados e artefatos soltos sem impacto real no deploy da API/web.

## 6. Arquivos staged neste push

O stage foi montado de forma explícita, sem usar `git add .`, para evitar incluir itens fora do escopo.

Comando utilizado:

```powershell
git -C . add README.md docs/Instrucoes.txt docs/context firmware/esp32_checking/esp32_checking.ino sistema/app/routers/admin.py sistema/app/static/admin/app.js sistema/app/static/admin/index.html tests/test_api_flow.py
```

Observação importante:

- O diretório `docs/context` foi incluído diretamente no stage porque a reorganização e a revisão documental já estavam concentradas nessa pasta.

## 7. Como revisar o stage antes do commit

Depois do `git add`, os comandos usados para revisar o stage foram:

```powershell
git -C . status --short
git -C . diff --cached --stat
```

Objetivo dessa revisão:

1. confirmar que apenas os arquivos desejados entraram no commit;
2. confirmar que `package-lock.json` e outros itens locais continuaram fora;
3. verificar se houve `rename` correto dos arquivos de contexto;
4. ter uma visão resumida do volume da mudança antes de gravar o commit.

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
- atualizar documentação e firmware relacionados ao comportamento atual do sistema.

## 9. Push que dispara o deploy

O push foi feito com:

```powershell
git -C . push origin main
```

Resultado esperado:

- o GitHub recebe o commit na branch `main`;
- o workflow de deploy do projeto é acionado automaticamente;
- o servidor no DigitalOcean atualiza a API e o website administrativo.

Neste caso, o retorno confirmou:

```text
To https://github.com/tscode-com-br/checking.git
   561a065..8fa0445  main -> main
```

## 10. O que este push atualiza no DigitalOcean

Ao subir para `main`, o fluxo automático do projeto deve:

1. sincronizar o código no servidor;
2. atualizar containers com `docker compose up -d --build --remove-orphans`;
3. manter a API FastAPI acessível no domínio de produção;
4. servir a versão nova do website administrativo;
5. validar o health check da aplicação.

## 11. Verificação após o push

Depois do push, é recomendável validar rapidamente:

### 11.1 Estado local do Git

```powershell
git -C . status --short
```

Neste caso, restaram apenas:

- `package-lock.json`

Ou seja, nada adicional do repositório principal ficou pendente após o push.

### 11.2 Health check em produção

Valide:

```text
https://tscode.com.br/api/health
```

O retorno esperado deve indicar que a API está saudável.

### 11.3 Validação funcional mínima do admin

Valide no website administrativo:

1. login do admin;
2. carregamento das abas;
3. funcionamento da aba `Eventos`;
4. funcionamento do botão `Limpar`;
5. atualização normal das tabelas.

## 12. Cuidados importantes para repetir este processo

### 12.1 Não usar `git add .` cegamente

Neste projeto, isso pode incluir:

- artefatos locais;
- arquivos auxiliares não relacionados;
- arquivos de configuração ou segredo que não deveriam subir.

### 12.2 Conferir sempre o remoto

O remoto correto deste repositório principal deve apontar para `tscode-com-br/checking`.

### 12.3 Fazer push na branch certa

O deploy automático esperado depende de push em `main`.

### 12.4 Rodar testes relevantes antes do push

Neste caso, antes do push, foram executados testes focados no fluxo de arquivamento de eventos, para garantir que a mudança principal não quebrasse o contrato da API/admin.

### 12.5 Separar o escopo do commit

Mesmo quando o workspace contiver artefatos locais ou projetos auxiliares, eles não devem ser misturados com o commit da API/web quando a entrega for apenas do backend e do painel administrativo.

### 12.6 Não publicar o app Flutter via Git

O diretório `checking_android_new` continua no workspace com `.git` próprio, mas isso não faz parte do processo oficial atual.

Não usar:

- `git subtree split --prefix checking_android_new ...`;
- `git push` dentro de `checking_android_new`;
- qualquer rotina de publicação do app Flutter acoplada ao deploy da API/web.

## 13. Passo a passo resumido

Fluxo enxuto para repetir exatamente este processo:

1. Entrar no repositório `checkcheck`.
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

6. Enviar para produção:

```powershell
git -C . push origin main
```

7. Validar `https://tscode.com.br/api/health` e o painel admin.

## 14. Resumo deste caso específico

O processo realizado agora foi:

1. verificar branch e remoto;
2. revisar arquivos alterados;
3. excluir do escopo `package-lock.json` e demais itens locais fora da entrega;
4. montar stage manualmente;
5. revisar o stage;
6. criar o commit `8fa0445`;
7. fazer push para `origin/main`;
8. disparar o deploy automático da API e do website no DigitalOcean.

Esse é o procedimento recomendado para futuras publicações do repositório principal quando a entrega envolver backend, painel admin, firmware e documentação correlata.

## 15. Atualizações operacionais validadas em 2026-04-08

Depois da criação inicial deste documento, o fluxo real de produção foi validado novamente com dois commits adicionais relevantes:

- `8ae0af0` - ajuste do workflow para podar artefatos Docker não utilizados após deploy saudável;
- `b749fc0` - redução do contexto de build da imagem da aplicação e separação entre dependências de runtime e dependências de testes.

Esses dois pontos foram confirmados diretamente no servidor.

Estado validado em produção após as intervenções:

- `.deploy-release` apontando para o commit implantado mais recente;
- `docker compose ps` com `app` e `db` em estado `healthy`;
- `GET /api/health` respondendo `{"status":"ok","app":"checking-sistema"}`.

## 16. O que foi comprovado sobre uso de SSD e imagens

Na investigação do servidor DigitalOcean, os dados observados foram:

- antes da limpeza, o disco raiz estava em aproximadamente `17G / 24G` (`73%`);
- o maior consumo estava em `/var/lib/containerd` e no cache de build do Docker;
- o projeto em si e os volumes da aplicação ocupavam muito pouco espaço útil;
- após limpeza segura de cache Docker, cache `apt` e journals antigos, o disco caiu para aproximadamente `4.7G / 24G` (`20%`);
- o cache de build do Docker caiu de `13.08GB` para `0B`;
- `/var/lib/containerd` caiu de aproximadamente `15G` para `2.6G`.

Também ficou comprovado que o tamanho residual da imagem principal da aplicação não estava sendo inflado principalmente pelo código copiado do repositório.

Análise de camadas da imagem em produção:

- camada `playwright install --with-deps chromium`: aproximadamente `1.33GB`;
- camada `pip install -r requirements.txt`: aproximadamente `241MB`;
- camada de cópia do código da aplicação: apenas alguns megabytes.

Conclusão prática:

- o crescimento perigoso de SSD foi resolvido pela poda automática de cache e artefatos não utilizados;
- o tamanho ainda elevado da imagem da aplicação decorre majoritariamente do runtime do Playwright/Chromium, necessário para a automação do Microsoft Forms.

## 17. Regra de segurança para produção sem risco

Se a exigência for não afetar a aplicação em hipótese alguma, existe uma regra objetiva:

- não fazer novo push em `main`, nem mesmo de documentação.

Motivo:

- qualquer push em `main` dispara o workflow `.github/workflows/deploy-oceandrive.yml`;
- esse workflow sincroniza o código no servidor e executa `docker compose up -d --build --remove-orphans`;
- portanto, mesmo um commit apenas de documentação gera um novo deploy de produção.

Quando a orientação for risco zero absoluto, o procedimento correto é:

1. documentar localmente sem enviar para `main`;
2. testar alterações de infraestrutura ou imagem fora da produção;
3. somente depois, se houver aprovação explícita, publicar o novo commit.

## 18. Próximo passo seguro para reduzir a imagem sem afetar a aplicação atual

Qualquer tentativa adicional de reduzir a imagem da aplicação deve ser feita fora da produção ativa.

O caminho seguro recomendado é:

1. criar um ambiente de validação separado, local ou em outro host;
2. testar ali alternativas de runtime do Playwright/Chromium;
3. validar explicitamente o fluxo real do Microsoft Forms, que é o ponto mais sensível do sistema;
4. comparar `docker history`, `docker system df` e health check nesse ambiente isolado;
5. somente depois considerar promover a mudança para `main`.

Enquanto essa validação isolada não existir, a estratégia correta em produção é manter o estado atual, que já está limpo, estável e saudável.
