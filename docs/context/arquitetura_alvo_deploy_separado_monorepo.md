# Arquitetura-alvo para deploy separado no monorepo

Status deste documento: proposta operacional inicial, criada em 2026-04-24.

## 1. Objetivo

Este documento define a arquitetura-alvo para separar o deploy da API e dos websites `admin`, `user` e `transport` sem separar o repositório principal.

O objetivo operacional é este:

- manter o monorepo `checkcheck` como fonte única de código;
- evitar rebuild e restart do projeto inteiro quando a mudança afetar apenas um website;
- reduzir risco de produção por meio de rollout incremental e rollback simples;
- preservar as URLs públicas já existentes.

Este documento é a referência para os próximos itens da lista:

1. desacoplar sites da API;
2. separar deploy da API;
3. separar deploy de `admin`, `user` e `transport`;
4. ajustar proxy, rotas, workflows, smoke tests e rollback.

## 2. Estado atual confirmado

Hoje o deploy de produção é uma unidade única.

### 2.1 Aplicação

- a API e os websites são servidos pela mesma aplicação FastAPI;
- `sistema/app/main.py` monta os diretórios estáticos `admin`, `check` e `transport` dentro do mesmo processo Python;
- o backend expõe também `/assets` a partir do repositório principal.

### 2.2 Runtime

- `docker-compose.yml` possui hoje apenas `db` e `app`;
- o serviço `app` faz build do `Dockerfile` raiz e sobe `uvicorn sistema.app.main:app`;
- qualquer mudança relevante no root tende a rebuildar a mesma imagem Python.

### 2.3 Deploy

- `.github/workflows/deploy-oceandrive.yml` continua sendo o workflow global do root, disparado em `push` para `main` e também disponível via `workflow_dispatch`;
- ele sincroniza o projeto por `rsync` e depois executa `docker compose up -d --build --remove-orphans`;
- o health check global valida `http://127.0.0.1:8000/api/health`;
- ao final do rollout, ele reinstala a automação periódica de limpeza de SSD e executa uma limpeza imediata de cache Docker e temporários antigos.

Conclusão: o gargalo atual não é o monorepo em si. O gargalo é a unidade única de build e deploy.

## 3. Decisão de arquitetura

A arquitetura-alvo recomendada é:

- manter um único monorepo;
- separar a produção em quatro alvos de deploy independentes dentro do mesmo repositório;
- manter o banco compartilhado e a API como backend central;
- servir cada website como alvo estático independente;
- preservar a camada de entrada pública com roteamento por caminho.

Alvos de deploy:

1. `api`
2. `admin-web`
3. `user-web`
4. `transport-web`

## 4. Arquitetura-alvo

### 4.1 Visão lógica

O estado final desejado é este:

```text
Internet
  -> proxy de borda
    -> /api/*               -> api
    -> /checking/admin*    -> admin-web
    -> /checking/user*     -> user-web
    -> /checking/transport*-> transport-web
    -> /assets/*           -> assets compartilhados

api
  -> FastAPI
  -> Postgres

admin-web
  -> site estático
  -> chama /api/admin/* no mesmo domínio

user-web
  -> site estático
  -> chama /api/web/* no mesmo domínio

transport-web
  -> site estático
  -> chama /api/transport/* no mesmo domínio
```

### 4.2 Decisões específicas

#### API

- continua responsável por regras de negócio, autenticação, banco, SSE, Forms, device e mobile;
- deixa de ser responsável por servir os websites em produção após o cutover completo;
- continua podendo servir `/assets` na fase de transição, se isso reduzir risco.

#### Websites

- `admin`, `user` e `transport` passam a ser publicados como artefatos estáticos independentes;
- cada website terá seu próprio build target e seu próprio processo de deploy;
- todos continuam sob o mesmo domínio público e chamando a mesma API.

#### Proxy de borda

- passa a ser o ponto central de roteamento por caminho;
- mantém as URLs públicas já existentes;
- desacopla publicação de frontend e backend.

## 5. Estratégia de menor risco

Para reduzir risco em produção, a implementação deve seguir este princípio:

- primeiro separar a forma de entrega;
- só depois remover o acoplamento antigo;
- manter rollback rápido para o modelo atual enquanto a nova arquitetura estiver estabilizando.

### 5.1 Fase 1 recomendada

Na primeira fase de implantação real:

- a API continua operacional como hoje;
- os websites passam a poder ser servidos por serviços próprios;
- o proxy escolhe qual alvo responder para cada caminho;
- o workflow atual pode continuar existindo como fallback manual.

### 5.2 Fase 2 recomendada

Depois da estabilização:

- a API deixa de servir `admin`, `user` e `transport` em produção;
- cada website passa a ter deploy próprio por caminho alterado;
- o workflow global deixa de ser o caminho padrão para mudanças só de frontend.

## 6. Modelo recomendado de containers e artefatos

### 6.1 API

- imagem Python dedicada;
- inclui `sistema/app`, `alembic`, `assets` e dependências do backend;
- health check continua em `/api/health`.

### 6.2 Websites

- uma imagem estática por website, preferencialmente baseada em Nginx leve;
- cada imagem copia apenas o diretório estático do site correspondente;
- o conteúdo publicado não precisa incluir código Python nem migrations.

### 6.3 Assets compartilhados

Decisão inicial recomendada:

- manter `/assets` fora do escopo de separação fina na primeira onda;
- opção mais segura: continuar servindo `/assets` pela API no início;
- opção posterior: mover `/assets` para um alvo estático compartilhado, se isso trouxer ganho real.

Essa decisão evita aumentar o escopo logo no primeiro corte de arquitetura.

## 7. Modelo recomendado de workflows

O monorepo continua único, mas o CI/CD passa a reagir por área alterada.

### 7.1 Workflow da API

Deve disparar quando houver mudança em áreas como:

- `sistema/app/routers/**`
- `sistema/app/services/**`
- `sistema/app/models.py`
- `sistema/app/database.py`
- `sistema/app/core/**`
- `alembic/**`
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`

### 7.2 Workflow do Admin

Deve disparar quando houver mudança em:

- `sistema/app/static/admin/**`

### 7.3 Workflow do User

Deve disparar quando houver mudança em:

- `sistema/app/static/check/**`

### 7.4 Workflow do Transport

Deve disparar quando houver mudança em:

- `sistema/app/static/transport/**`

### 7.5 Mudanças compartilhadas

Mudanças em áreas compartilhadas, como `assets/`, podem:

- disparar um workflow específico de assets; ou
- disparar os websites dependentes; ou
- continuar dentro do deploy da API na fase inicial.

A escolha operacional recomendada para a primeira implementação é a terceira, por ser mais segura.

## 8. Critérios de aceitação desta arquitetura

O item "Definir arquitetura de deploy" será considerado concluído quando os próximos passos respeitarem estas decisões:

1. o monorepo continua sendo a fonte única de código;
2. a API passa a ter deploy independente dos websites;
3. `admin`, `user` e `transport` passam a ter deploy independente entre si;
4. as URLs públicas permanecem estáveis;
5. o rollback para o modelo anterior continua possível durante a transição;
6. nenhuma etapa futura assume corte "big bang" em produção.

## 9. Riscos já identificados

### 9.1 Prefixo público `/checking`

As URLs públicas atuais usam `/checking/admin`, `/checking/user` e `/checking/transport`, enquanto a aplicação interna monta `/admin`, `/user` e `/transport`.

Logo, já existe alguma camada de reescrita ou roteamento externo. A implementação do proxy precisa respeitar isso e não quebrar compatibilidade pública.

### 9.2 Sessões e cookies

O website admin depende de sessão autenticada na API. O deploy separado do frontend não pode mudar origem, domínio nem comportamento de cookie sem revisão explícita.

### 9.3 Assets compartilhados

Separar `/assets` cedo demais aumenta a superfície de falha. Por isso, a recomendação inicial é manter esse ponto estável na primeira onda.

### 9.4 Workflow atual em produção

Hoje o workflow global já está validado em produção. Ele não deve ser removido antes de existir:

- deploy alternativo estável;
- smoke tests por alvo;
- rollback operacional documentado.

## 10. Rollout recomendado para os próximos itens

Ordem recomendada:

1. documentar a arquitetura-alvo;
2. introduzir serviços e compose separados sem trocar o tráfego público imediatamente;
3. introduzir proxy por caminho com possibilidade de rollback;
4. criar workflows por alvo;
5. validar cada website separadamente com smoke tests;
6. tornar o workflow global apenas fallback/manual;
7. remover o acoplamento antigo só depois da estabilização.

## 11. O que este item não faz

Este item não altera:

- produção;
- workflow atual;
- docker compose atual;
- rotas atuais da aplicação;
- proxy atual;
- DNS;
- secrets.

Ele apenas define a arquitetura-alvo oficial para as próximas etapas de implementação.