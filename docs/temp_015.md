# Plano mestre de particionamento dos repositorios Checking

## 1. Objetivo

Este plano define como particionar o projeto atual em repositorios independentes, cada um com deploy automatico proprio apos commit e push, preservando o comportamento de producao e reduzindo o blast radius de cada alteracao.

Repositorios alvo:

- `tscode-com-br/checking_api`
- `tscode-com-br/checking_transport`
- `tscode-com-br/checking_webapplication`
- `tscode-com-br/checking_admin`
- `tscode-com-br/checking_app_flutter`

Objetivos obrigatorios:

- permitir alterar e publicar um repositorio sem redesplegar os demais;
- manter a topologia publica atual: `/api`, `/assets`, `/checking/admin`, `/checking/user`, `/checking/transport`;
- manter a IA do dashboard Transport operacional depois da separacao;
- manter o deploy automatico por `push` na branch `main` de cada repositorio;
- impedir que um deploy parcial apague arquivos ou volumes de outro componente.

## 2. Fatos tecnicos ja confirmados

### 2.1 Backend ainda e monolitico no codigo

- `sistema/app/main.py` ainda monta os sites estaticos de admin, user e transport dentro da API.
- O backend ainda serve `/assets`.
- Portanto, hoje o repositorio raiz `checking` ainda e o dono real de toda a publicacao.

### 2.2 Os frontends estaticos dependem da API atual

- `sistema/app/static/transport/app.js` usa `../api/transport` e `../assets`.
- O admin e a Checking Web usam `/api/...` e `/assets/...`.
- Logo, os repositorios estaticos poderao ser independentes somente se a API continuar dona de `/api` e `/assets`.

### 2.3 A topologia split ja existe no repositorio

Ja existe material versionado para a topologia final desejada:

- `docker-compose.api.yml` publica a API em `18080`.
- `docker-compose.websites.yml` publica `admin-web`, `user-web` e `transport-web` em `18081`, `18082` e `18083`.
- `deploy/nginx/checking-edge-routes.conf` ja roteia:
  - `/api` e `/assets` -> `127.0.0.1:18080`
  - `/checking/admin` -> `127.0.0.1:18081`
  - `/checking/user` -> `127.0.0.1:18082`
  - `/checking/transport` -> `127.0.0.1:18083`

### 2.4 Ja existem workflows parciais no repo raiz, mas eles nao bastam sozinhos

O repo raiz ja possui workflows `api-only`, `admin-only`, `user-only` e `transport-only`, mas eles ainda tem limitacoes para o cenario final:

- eles vivem no repo monolitico, nao nos repositorios alvo;
- sao `workflow_dispatch`, nao `push` automatico em `main`;
- usam `rsync --delete`, entao nao podem compartilhar o mesmo diretorio remoto entre repositorios diferentes;
- o fluxo parcial atual assume `.env` ja presente no host;
- o workflow monolitico sabe materializar `.env` a partir de `OCEAN_APP_ENV_B64`, mas os parciais nao.

### 2.5 O compose de API atual tem dois riscos criticos para a separacao

O `docker-compose.api.yml` atual precisa ser reforcado antes de virar fonte de verdade do repo `checking_api`:

- ele nao sobe o `forms-worker`, embora o runtime operacional atual dependa dele;
- ele declara `pgdata` e `event_archives` como volumes locais do projeto Compose.

Se o diretorio remoto mudar sem nome fixo de volume, o Docker Compose criara novos volumes com outro prefixo, o que pode parecer um banco vazio ou um storage de eventos novo. Isso e inaceitavel.

### 2.6 A IA do Transport nao pertence ao repo estatico do dashboard

A funcionalidade de IA do Transport depende da API e do estado persistido:

- `HERE_API_KEY`;
- `TRANSPORT_AI_ENABLED`;
- `TRANSPORT_AI_AGENT_MODE`;
- `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY`;
- `TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE`;
- banco de dados existente;
- configuracoes persistidas de `transport_ai_llm_settings` quando o modo e `agent`.

Conclusao obrigatoria: o repo `checking_transport` sera dono apenas do shell estatico do dashboard. O runtime da IA continua no repo `checking_api`.

## 3. Decisoes de arquitetura que nao sao opcionais

### 3.1 `/assets` permanece com a API nesta fase

Nao deve existir um sexto repositorio de assets nesta onda. Os tres sites estaticos continuam consumindo `/assets` publicado pela API.

Motivo:

- e o menor delta operacional;
- evita triplicar assets ou introduzir CDN nova durante a particionamento;
- preserva as URLs ja embutidas no frontend.

### 3.2 Cada repo precisa de diretorio remoto proprio

Como os workflows usam `rsync --delete`, cada repositorio precisa de um `OCEAN_APP_DIR` diferente.

Diretorios recomendados:

- `checking_api` -> `/root/checking_api`
- `checking_admin` -> `/root/checking_admin`
- `checking_webapplication` -> `/root/checking_webapplication`
- `checking_transport` -> `/root/checking_transport`
- `checking_app_flutter` -> `/root/checking_app_flutter_artifacts`

Se dois repositorios compartilharem o mesmo diretorio remoto, o deploy de um deles apagara arquivos do outro.

### 3.3 O repo raiz `checking` nao pode continuar mandando em producao por `push`

Depois do cutover:

- o deploy monolitico por `push` no repo raiz deve ser desativado ou convertido para `workflow_dispatch` manual;
- o repo raiz passa a ser repo de integracao e infraestrutura, nao de deploy diario de aplicacao;
- qualquer automacao que ainda faça publish do monolito vira risco de sobrescrever o split.

### 3.4 A topologia publica final deve ser a split `18080/18081/18082/18083`

Nao e aceitavel operar com mistura instavel entre upstream monolitico em `8000` e edge split em `18080-18083`.

Antes de declarar o projeto particionado, o host real precisa confirmar a mesma topologia que ja esta versionada no repositorio.

### 3.5 O repo `checking_api` precisa carregar mais do que apenas `sistema/app` sem `static`

O pedido de ownership de codigo esta correto, mas o repo executavel da API precisa levar tambem os artefatos minimos de runtime:

- `assets/`;
- `alembic.ini`;
- `alembic/`;
- `requirements.txt` e `requirements-dev.txt`;
- Dockerfile e compose da API;
- scripts de smoke/validacao;
- testes da API, realtime, health, forms e Transport AI.

Sem isso, o repo teria o codigo-fonte da API, mas nao seria autoimplantavel.

### 3.6 O repo `checking_api` deve assumir o `forms-worker`

O worker do Forms faz parte do backend operacional. Se ele nao migrar com a API, o sistema perde comportamento ja homologado.

Regra de ouro:

- `checking_api` sobe `api`, `db`, `migrate` e `forms-worker`;
- `checking_admin`, `checking_webapplication` e `checking_transport` sobem somente um Nginx estatico cada;
- `checking_app_flutter` publica artefatos, nao runtime web.

## 4. Topologia final desejada

| Repo | Dono funcional | URL publica | Porta local | Artefato de deploy | Observacao critica |
| --- | --- | --- | --- | --- | --- |
| `checking_api` | API, assets, IA do Transport, forms-worker, migracoes | `/api`, `/assets` | `18080` | imagem Python + compose proprio | continua dono de todos os segredos e estados da IA |
| `checking_admin` | site do administrador | `/checking/admin` | `18081` | imagem Nginx estatica | depende de `/api` e `/assets` |
| `checking_webapplication` | Checking Web | `/checking/user` | `18082` | imagem Nginx estatica | depende de `/api` e `/assets` |
| `checking_transport` | dashboard Transport | `/checking/transport` | `18083` | imagem Nginx estatica | depende de `/api/transport`, `/api/transport/ai` e `/assets` |
| `checking_app_flutter` | app Flutter | sem rota publica de edge nesta fase | n/a | APK/AAB publicados em diretorio remoto | deploy aqui significa publicacao de artefato, nao cutover web |
| `checking` | repo de integracao, docs, edge, runbooks, smoke cruzado | sem deploy automatico de aplicacao | n/a | n/a | deve parar de publicar o monolito no dia a dia |

## 5. Conteudo minimo que cada repositorio precisa carregar

### 5.1 `checking_api`

Escopo de codigo:

- todo `sistema/app` exceto `sistema/app/static`.

Artefatos operacionais minimos adicionais:

- `assets/`
- `alembic.ini`
- `alembic/`
- `requirements.txt`
- `requirements-dev.txt`
- `deploy/docker/Dockerfile.api`
- compose proprio da API
- script de smoke da API
- testes da API e da IA do Transport

Adaptacoes obrigatorias neste repo:

- incluir `forms-worker` no compose local;
- fixar nomes dos volumes persistentes ou usar `external: true`;
- manter `SERVE_ADMIN_SITE_IN_API=false`;
- manter `SERVE_USER_SITE_IN_API=false`;
- manter `SERVE_TRANSPORT_SITE_IN_API=false`;
- manter `/assets` publicado pela API;
- manter a imagem e o entrypoint compatveis com `python -m sistema.app.http_runtime`.

### 5.2 `checking_transport`

Escopo de codigo:

- todo `sistema/app/static/transport`.

Artefatos operacionais minimos adicionais:

- Dockerfile estatico do Transport;
- `deploy/nginx/static-site.conf` ou equivalente local;
- compose proprio com um unico servico `transport-web`;
- smoke test estatico do dashboard;
- teste de contrato do frontend com a API atual.

Regras obrigatorias:

- nao carregar codigo de backend da IA;
- manter consumo de `/api/transport` e `/api/transport/ai`;
- manter consumo de `/assets`;
- qualquer mudanca de contrato precisa ser primeiro aditiva na API.

### 5.3 `checking_webapplication`

Escopo de codigo:

- todo `sistema/app/static/check`.

Artefatos operacionais minimos adicionais:

- Dockerfile estatico proprio;
- `deploy/nginx/static-site.conf` ou equivalente local;
- compose proprio com um unico servico `user-web`;
- smoke test da home e do fluxo principal.

### 5.4 `checking_admin`

Escopo de codigo:

- todo `sistema/app/static/admin`.

Artefatos operacionais minimos adicionais:

- Dockerfile estatico proprio;
- `deploy/nginx/static-site.conf` ou equivalente local;
- compose proprio com um unico servico `admin-web`;
- smoke test da shell do admin.

### 5.5 `checking_app_flutter`

Escopo de codigo:

- todo `checking_android_new`.

Artefatos operacionais minimos adicionais:

- workflow de CI para `flutter analyze`, `flutter test`, `flutter build apk --debug` e `flutter build appbundle --release`;
- rotina de upload dos artefatos para o host da DigitalOcean;
- diretorio remoto versionado por SHA ou tag;
- manifesto simples contendo nome do build, SHA e hash do arquivo.

Observacao importante:

- para o app Flutter, "deploy" nesta fase significa publicar artefatos em um diretorio remoto controlado;
- nao existe hoje rota publica no edge da DigitalOcean equivalente ao deploy dos sites web;
- portanto, a meta realista e ter build automatico e publicacao automatica de artefato, sem tocar o runtime de producao web/API.

## 6. Segredos e variaveis por repositorio

### 6.1 Segredos comuns a todos os repositorios com automacao na DigitalOcean

Esses podem ser organizados como org secrets ou repetidos por repo:

- `OCEAN_HOST`
- `OCEAN_USER`
- `OCEAN_PORT`
- `OCEAN_SSH_KEY`
- `OCEAN_HOST_FINGERPRINT`

### 6.2 Variaveis/segredos especificos por repo

#### `checking_api`

- `OCEAN_APP_DIR=/root/checking_api`
- `OCEAN_APP_ENV_B64=<.env da API em base64>`
- `CHECKCHECK_API_IMAGE=ghcr.io/tscode-com-br/checkcheck-api`
- `COMPOSE_PROJECT_NAME=checking_api`
- `CHECKCHECK_PGDATA_VOLUME=checkcheck_pgdata`
- `CHECKCHECK_EVENT_ARCHIVES_VOLUME=checkcheck_event_archives`

#### `checking_admin`

- `OCEAN_APP_DIR=/root/checking_admin`
- `CHECKCHECK_ADMIN_WEB_IMAGE=ghcr.io/tscode-com-br/checkcheck-admin-web`
- `COMPOSE_PROJECT_NAME=checking_admin`

#### `checking_webapplication`

- `OCEAN_APP_DIR=/root/checking_webapplication`
- `CHECKCHECK_USER_WEB_IMAGE=ghcr.io/tscode-com-br/checkcheck-user-web`
- `COMPOSE_PROJECT_NAME=checking_webapplication`

#### `checking_transport`

- `OCEAN_APP_DIR=/root/checking_transport`
- `CHECKCHECK_TRANSPORT_WEB_IMAGE=ghcr.io/tscode-com-br/checkcheck-transport-web`
- `COMPOSE_PROJECT_NAME=checking_transport`

#### `checking_app_flutter`

- `OCEAN_APP_DIR=/root/checking_app_flutter_artifacts`
- `CHECKING_FLUTTER_ARTIFACT_SUBDIR=android`

### 6.3 Segredos adicionais de smoke por repositorio

Para validar o sistema real apos deploy, o ideal e ter contas tecnicas de smoke independentes dos segredos da DigitalOcean.

Recomendados:

- `CHECKING_SMOKE_BASE_URL`
- `CHECKING_TRANSPORT_SMOKE_USER`
- `CHECKING_TRANSPORT_SMOKE_PASSWORD`
- `CHECKING_ADMIN_SMOKE_USER`
- `CHECKING_ADMIN_SMOKE_PASSWORD`
- `CHECKING_USER_SMOKE_USER`
- `CHECKING_USER_SMOKE_PASSWORD`

### 6.4 Regra obrigatoria para `.env`

O repo `checking_api` precisa ser auto-suficiente para reidratar `.env` no host quando necessario. Portanto:

- o workflow da API deve herdar a logica do deploy monolitico que materializa `.env` a partir de `OCEAN_APP_ENV_B64`;
- nao e aceitavel depender de um `.env` criado manualmente uma unica vez e depois esquecido;
- os sites estaticos nao dependem desse `.env`, mas a API depende.

## 7. Workflows de GitHub Actions desejados

### 7.1 Gatilho padrao de cada repo

Cada repo operacional deve publicar com:

```yaml
on:
  push:
    branches: [main]
  workflow_dispatch:
```

### 7.2 Estrutura minima do workflow da API

Passos obrigatorios:

1. `checkout`
2. validacao de segredos
3. build e push da imagem `checkcheck-api`
4. sincronizacao do repo para `/root/checking_api`
5. materializacao ou atualizacao do `.env`
6. `docker compose up -d` de `db`, `migrate`, `api` e `forms-worker`
7. validacao de health local em `http://127.0.0.1:18080/api/health`
8. validacao de readiness em `http://127.0.0.1:18080/api/health/ready`
9. validacao adicional do worker e dos endpoints do Transport AI
10. rollback automatico para a imagem anterior se algum smoke critico falhar

### 7.3 Estrutura minima dos workflows dos sites estaticos

Cada repo de site (`checking_admin`, `checking_webapplication`, `checking_transport`) deve:

1. buildar sua propria imagem Nginx;
2. sincronizar apenas o proprio repo para o seu diretorio remoto;
3. executar `docker compose up -d --no-build --force-recreate` do unico servico daquele repo;
4. validar a URL local da porta correspondente;
5. validar a URL publica por meio do edge;
6. encerrar com falha se a shell HTML abrir, mas `/assets` ou `/api` estiverem quebrados.

### 7.4 Estrutura minima do workflow do Flutter

O repo `checking_app_flutter` deve:

1. executar `flutter analyze`;
2. executar `flutter test`;
3. gerar `apk --debug` e `appbundle --release`;
4. publicar os artefatos no host, em pasta versionada por SHA;
5. atualizar um ponteiro `latest` apenas quando a publicacao terminar sem erro;
6. gravar manifestos com hashes dos artefatos gerados.

### 7.5 Concurrency obrigatoria

Cada repo deve ter um `concurrency.group` proprio. Exemplo:

- `deploy-checking-api-production`
- `deploy-checking-admin-production`
- `deploy-checking-webapplication-production`
- `deploy-checking-transport-production`
- `deploy-checking-app-flutter-production`

Isso evita dois deploys simultaneos brigando pelo mesmo recurso.

## 8. Ajustes operacionais obrigatorios antes de qualquer cutover

### 8.1 Confirmar a topologia real do host

Antes da primeira extracao real, precisa existir evidencia do host ativo:

- `nginx -T` salvo integralmente;
- `docker ps`;
- `docker compose ps` dos stacks relevantes;
- `docker volume ls`;
- `docker volume inspect` dos volumes de banco e de `event_archives`;
- resultado do script `deploy/nginx/verify_checking_edge_cutover.sh`.

Se o host ainda estiver roteando parcialmente para `127.0.0.1:8000`, esse drift precisa ser resolvido antes do split.

### 8.2 Congelar nomes de volumes persistentes

No repo `checking_api`, os volumes persistentes precisam deixar de depender do nome do diretorio do projeto.

Meta recomendada:

- volume de banco com nome fixo `checkcheck_pgdata`;
- volume de arquivos de evento com nome fixo `checkcheck_event_archives`.

Sem isso, mudar de `/root/checkcheck` para `/root/checking_api` pode criar volumes novos e aparentar perda de dados.

### 8.3 Reintroduzir o `forms-worker` no stack da API separada

O stack final da API deve ter:

- `db`
- `migrate`
- `api`
- `forms-worker`

Tambem deve preservar:

- healthcheck do worker;
- acesso ao mesmo `event_archives`;
- parametros de pool e timeouts ja endurecidos.

### 8.4 Desligar o deploy automatico monolitico por `push`

No momento em que o primeiro repo separado assumir deploy real, o workflow monolitico do repo raiz nao pode mais publicar automaticamente por `push` em `main`.

Ele deve ficar em um destes modos:

- `workflow_dispatch` manual apenas para emergencia controlada;
- ou removido, se o repo raiz deixar de participar de producao.

## 9. Sequencia de implementacao recomendada

### Fase 0. Baseline e congelamento operacional

Objetivo: capturar o estado real antes de mexer na topologia.

Checklist:

1. salvar `nginx -T` do host;
2. salvar `docker ps`, `docker compose ps`, `docker volume ls`;
3. validar publicamente `/api/health`, `/checking/admin`, `/checking/user`, `/checking/transport`;
4. salvar o SHA atualmente em producao para API e para cada site, se ja existirem imagens separadas;
5. confirmar o valor e a presenca de `TRANSPORT_AI_ENABLED`, `TRANSPORT_AI_AGENT_MODE`, `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY`, `HERE_API_KEY` e `TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE` no host;
6. capturar um smoke do dashboard Transport com a IA funcionando;
7. capturar um backup do `.env` atual da API;
8. capturar backup do banco e de `event_archives`.

Saida obrigatoria da fase:

- um pacote de evidencia que permita provar que qualquer regressao veio da separacao, e nao de um estado anterior desconhecido.

### Fase 1. Bootstrap dos repositorios e segredos

Objetivo: preparar repositorios vazios sem risco de deploy prematuro.

Checklist:

1. inicializar todos os repositorios novos com um commit em `main`;
2. confirmar que cada repo tem branch default `main` configurada no GitHub;
3. adicionar segredos comuns da DigitalOcean;
4. adicionar `OCEAN_APP_DIR` diferente em cada repo;
5. adicionar segredos/variaveis de imagem e de smoke;
6. adicionar workflows inicialmente com `workflow_dispatch` para o bootstrap;
7. executar um deploy manual de scaffold para cada repo, ainda sem cutover publico.

Regra de seguranca:

- nao habilitar o gatilho automatico em `push` antes de cada repo provar que consegue buildar, sincronizar e validar o proprio diretorio remoto.

### Fase 2. Extracao do repo `checking_api`

Objetivo: separar o backend sem perder banco, assets, worker e IA do Transport.

Checklist:

1. extrair o codigo da API preservando historico relevante;
2. levar `assets`, `alembic`, `requirements`, Dockerfile, compose e testes;
3. criar compose proprio com `db`, `migrate`, `api` e `forms-worker`;
4. fixar volumes persistentes com nomes estaveis;
5. herdar a logica de materializacao do `.env` a partir de `OCEAN_APP_ENV_B64`;
6. publicar a imagem `ghcr.io/tscode-com-br/checkcheck-api`;
7. subir o stack em `/root/checking_api`;
8. validar `http://127.0.0.1:18080/api/health` e `.../ready`;
9. validar `forms-worker` `healthy`;
10. validar `/assets/...`;
11. validar endpoints do Transport AI.

Regra de aceite:

- a API separada so pode ser considerada pronta quando ela, sozinha, sustentar `/api` e `/assets` sem depender do monolito antigo.

### Fase 3. Extracao de `checking_admin`

Objetivo: separar o site admin, que e o frontend menos acoplado a IA do Transport.

Checklist:

1. extrair `sistema/app/static/admin`;
2. criar imagem Nginx propria;
3. criar compose de um servico apenas;
4. publicar para `/root/checking_admin`;
5. validar `http://127.0.0.1:18081/`;
6. validar publicamente `/checking/admin`;
7. validar requests para `/api/admin/...` e `/assets/...` via browser real ou smoke automatizado.

### Fase 4. Extracao de `checking_webapplication`

Objetivo: separar a Checking Web mantendo o mesmo backend.

Checklist:

1. extrair `sistema/app/static/check`;
2. criar imagem Nginx propria;
3. criar compose de um servico apenas;
4. publicar para `/root/checking_webapplication`;
5. validar `http://127.0.0.1:18082/`;
6. validar publicamente `/checking/user`;
7. validar requests para `/api/web/...` e `/assets/...`.

### Fase 5. Extracao de `checking_transport`

Objetivo: separar o dashboard Transport por ultimo, porque ele e o frontend com maior acoplamento funcional a IA.

Checklist:

1. extrair `sistema/app/static/transport`;
2. criar imagem Nginx propria;
3. criar compose de um servico apenas;
4. publicar para `/root/checking_transport`;
5. validar `http://127.0.0.1:18083/`;
6. validar publicamente `/checking/transport`;
7. validar carregamento de `/assets`;
8. validar autenticacao e requests para `/api/transport/...`;
9. validar pelo menos um fluxo real ou controlado de IA;
10. liberar `push` automatico em `main` apenas depois de o pacote completo de smoke passar.

### Fase 6. Extracao de `checking_app_flutter`

Objetivo: tornar o app Flutter independente do repo raiz, sem inventar runtime web na DigitalOcean.

Checklist:

1. garantir que todo `checking_android_new` esta no repo proprio;
2. configurar CI de analise, testes e build;
3. publicar artefatos no host em diretorio versionado;
4. manter o processo isolado do runtime web/API;
5. documentar onde buscar o `latest` e onde buscar o SHA exato.

### Fase 7. Democao controlada do repo raiz `checking`

Objetivo: impedir que o monolito continue sendo a fonte invisivel de publicacao.

Checklist:

1. transformar o deploy monolitico em manual ou aposentado;
2. documentar que o repo raiz passa a ser de integracao/infrastrutura;
3. manter nele apenas o que fizer sentido como ownership comum:
   - docs operacionais;
   - runbooks;
   - templates de edge Nginx;
   - smokes cruzados;
   - automacoes de auditoria operacional;
4. remover a ambiguidade sobre qual repo e dono de cada URL publica.

## 10. Cuidados obrigatorios para commit, push e deploy do dashboard Transport sem perder a IA

### 10.1 Regra principal

O dashboard Transport nao pode ser tratado como dono da IA. Ele e apenas cliente do backend.

Logo:

- mudar apenas `checking_transport` nao deve exigir redesplegar a API se a mudanca for somente visual ou se usar contratos existentes;
- se a mudanca do dashboard depender de endpoint novo, campo novo ou semantica nova, o deploy precisa ocorrer em duas ondas: API primeiro, dashboard depois.

### 10.2 Ordem obrigatoria quando houver mudanca de contrato

Sequencia correta:

1. implementar a mudanca de backend no repo `checking_api` de forma aditiva e retrocompativel;
2. fazer merge/push do repo `checking_api`;
3. esperar o deploy automatico da API terminar verde;
4. rodar smoke da IA do Transport contra a API nova;
5. so entao fazer merge/push do repo `checking_transport`;
6. somente em uma terceira onda remover contratos antigos, se ainda for necessario.

Sequencia proibida:

1. publicar um dashboard que exige resposta nova da API antes de a API suportar essa resposta.

### 10.3 Variaveis e estados que nunca podem ser rotacionados junto com a separacao do Transport

Durante o split do dashboard, nao rotacionar ao mesmo tempo:

- `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY`;
- `HERE_API_KEY`;
- `TRANSPORT_AI_ENABLED`;
- `TRANSPORT_AI_AGENT_MODE`;
- `TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE`;
- `DATABASE_URL`;
- volume de banco;
- volume de `event_archives`.

Se alguma dessas variaveis mudar junto com a troca de repo, o diagnostico de regressao fica ambiguo e o risco de interromper a IA sobe demais.

### 10.4 Regra especifica do modo `agent`

Quando `TRANSPORT_AI_AGENT_MODE=agent`, a inicializacao depende de configuracoes persistidas em `transport_ai_llm_settings`.

Consequencias:

- o deploy do dashboard Transport nao pode pressupor que bastam variaveis de ambiente genericas de LLM;
- a API em producao precisa continuar enxergando o mesmo banco e a mesma chave de criptografia;
- qualquer smoke da IA precisa validar o acesso a configuracao persistida, nao apenas a disponibilidade do HTML.

### 10.5 Smoke obrigatorio apos cada deploy do repo `checking_transport`

Checklist minimo:

1. abrir `/checking/transport` sem erro 5xx;
2. confirmar carregamento de JS e CSS principais;
3. confirmar carregamento de `/assets` usados pela pagina;
4. autenticar com usuario tecnico;
5. confirmar sucesso de chamada para `/api/transport/...`;
6. confirmar sucesso de chamada para `/api/transport/ai/settings`;
7. confirmar exibicao correta do estado da IA no dashboard;
8. executar um fluxo de calculo de rota em ambiente controlado ou projeto de smoke;
9. confirmar polling/consulta do status da execucao;
10. confirmar que nenhum erro de `transport_ai_llm_settings_missing`, `here_api_key_missing`, `approval evidence` ou `encryption key` apareceu nos logs.

### 10.6 Gate de deploy do repo `checking_transport`

O workflow do repo `checking_transport` deve ter um gate de compatibilidade com a API atual.

Esse gate deve bloquear deploy se ocorrer qualquer uma destas situacoes:

- a pagina abrir, mas as chamadas para `/api/transport` falharem;
- a pagina depender de endpoint novo que ainda nao existe na API atual;
- a IA aparecer desabilitada por regressao de contrato;
- `/assets` nao carregar;
- o smoke de IA falhar.

## 11. Matriz de testes obrigatorios

### 11.1 Testes do repo `checking_api`

CI obrigatoria:

1. `pytest` para health, auth, realtime, forms e rotas principais;
2. `pytest` especifico de Transport AI;
3. build da imagem Docker;
4. smoke local do compose da API;
5. validacao dos volumes nomeados;
6. validacao do `forms-worker`;
7. validacao dos endpoints `/api/health`, `/api/health/ready`, `/api/transport/...`, `/api/transport/ai/...`.

Testes especificos que nao podem faltar:

1. configuracao da IA em modo `agent` com settings persistidos;
2. configuracao da IA em modo `deterministic`;
3. health com degradacao do `forms-worker` sem derrubar a API;
4. preservacao de `/assets`.

### 11.2 Testes do repo `checking_admin`

1. build da imagem estatica;
2. smoke local da pagina inicial;
3. smoke publico da URL `/checking/admin`;
4. validacao de requests essenciais para `/api/admin/...` e `/assets/...`.

### 11.3 Testes do repo `checking_webapplication`

1. build da imagem estatica;
2. smoke local da pagina inicial;
3. smoke publico da URL `/checking/user`;
4. validacao de requests essenciais para `/api/web/...` e `/assets/...`.

### 11.4 Testes do repo `checking_transport`

1. build da imagem estatica;
2. smoke local da shell HTML;
3. teste de contrato do frontend com a API;
4. smoke publico da URL `/checking/transport`;
5. smoke autenticado do dashboard;
6. smoke da IA do Transport.

### 11.5 Testes do repo `checking_app_flutter`

1. `flutter analyze`;
2. `flutter test`;
3. `flutter build apk --debug`;
4. `flutter build appbundle --release`;
5. verificacao de hash dos artefatos publicados.

### 11.6 Smoke cruzado obrigatorio apos qualquer deploy

Independente do repo publicado, rodar pelo menos:

1. `GET /api/health`;
2. abrir `/checking/admin`;
3. abrir `/checking/user`;
4. abrir `/checking/transport`;
5. validar `/assets`;
6. rodar `deploy/nginx/verify_checking_edge_cutover.sh` ou equivalente adaptado ao split.

## 12. Estrategia de historico e extracao

Para nao perder historico util, a extracao dos repositorios nao deve ser feita por copia manual cega.

Estrategia recomendada:

- usar `git filter-repo` ou `git subtree split` para levar historico relevante de cada caminho;
- revisar o resultado e adicionar os artefatos operacionais que nao estavam no caminho original;
- fazer um primeiro commit de ajuste estrutural em cada repo separado;
- somente depois habilitar o deploy automatico em `main`.

Ordem recomendada de extracao:

1. `checking_api`
2. `checking_admin`
3. `checking_webapplication`
4. `checking_transport`
5. `checking_app_flutter`

Motivo:

- a API e a base de tudo;
- admin e user tem risco funcional menor que o Transport;
- o Transport deve ser o ultimo frontend a separar por causa da IA.

## 13. Rollback por repositorio

### 13.1 `checking_api`

Rollback padrao:

1. redeploy da imagem anterior da API;
2. restart coordenado de `api` e `forms-worker`;
3. manter o mesmo banco e os mesmos volumes;
4. rerodar smoke de health e IA.

Rollback proibido:

- subir a API em volume novo por acidente;
- restaurar um `.env` incompleto;
- trocar a chave de criptografia da IA durante o rollback.

### 13.2 Repos estaticos

Rollback padrao:

1. redeploy da imagem anterior do site;
2. validar a URL local e publica;
3. confirmar que `/assets` e `/api` seguem integros.

### 13.3 `checking_transport`

Se a regressao estiver apenas na UI:

1. rollback do `checking_transport` sozinho.

Se a regressao vier de incompatibilidade entre UI e API:

1. rollback do dashboard;
2. se necessario, rollback da API para o ultimo par compativel;
3. rerodar o smoke da IA.

### 13.4 `checking_app_flutter`

Rollback padrao:

1. repontar o alias `latest` para o artefato anterior;
2. preservar os builds por SHA para auditoria.

## 14. Critrios de aceite final

O particionamento so pode ser declarado concluido quando todas as condicoes abaixo forem verdadeiras ao mesmo tempo:

1. cada repo faz build e deploy sozinho por `push` na `main`;
2. cada repo usa um `OCEAN_APP_DIR` exclusivo;
3. a API publica `/api` e `/assets` em `18080`;
4. admin, user e transport publicam em `18081`, `18082` e `18083`;
5. o edge publico aponta para `18080/18081/18082/18083` sem drift monolitico residual;
6. o `forms-worker` continua operacional no stack da API;
7. os volumes de banco e `event_archives` continuam sendo os mesmos do ambiente anterior;
8. a IA do Transport continua funcionando em producao;
9. o repo raiz `checking` deixou de publicar a aplicacao por `push` automatico;
10. existe runbook de rollback por repo.

## 15. Resumo executivo da ordem segura de execucao

1. congelar o estado atual e coletar evidencia do host;
2. preparar segredos, branch `main` e diretorios remotos dedicados;
3. separar e estabilizar primeiro `checking_api`, incluindo worker, volumes e `.env`;
4. separar `checking_admin`;
5. separar `checking_webapplication`;
6. separar `checking_transport` por ultimo, com smoke reforcado da IA;
7. separar `checking_app_flutter` como pipeline de artefato;
8. apos todos os repos passarem, retirar o repo raiz do caminho de deploy automatico.

Se esta ordem for respeitada, o projeto passa a ter deploy independente por componente sem perder a funcionalidade da IA do dashboard Transport e sem depender do monolito para publicar URLs publicas.