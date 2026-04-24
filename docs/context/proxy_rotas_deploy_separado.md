# Ajuste Manual de Proxy e Rotas para Deploy Separado

Status deste documento: preparacao operacional inicial, criada em 2026-04-24.

## 1. Objetivo

Este documento define o ajuste manual e reversivel do proxy de borda para a arquitetura de deploy separado dentro do monorepo.

O objetivo desta etapa e:

- manter o dominio publico atual;
- preservar as URLs publicas ja usadas em producao;
- encaminhar cada caminho para o alvo dedicado ja preparado;
- evitar qualquer troca automatica de trafego nesta fase.

## 2. Premissas confirmadas

- a API separada responde em `127.0.0.1:18080`;
- `admin-web` responde em `127.0.0.1:18081`;
- `user-web` responde em `127.0.0.1:18082`;
- `transport-web` responde em `127.0.0.1:18083`;
- os websites continuam chamando a API publica pelo mesmo dominio em caminhos `/api/...`;
- os websites usam URL canonica sem barra final em `/checking/admin`, `/checking/user` e `/checking/transport`.

Essa ultima regra importa porque os `index.html` atuais usam `base href` relativo. Se o proxy mantiver a barra final nesses tres caminhos, a resolucao de assets pode quebrar.

## 3. Artefato versionado

O template versionado desta etapa e:

- `deploy/nginx/checking-edge-routes.conf`
- `deploy/nginx/manage_checking_edge_cutover.sh`

Ele foi escrito para ser incluido dentro do bloco `server` HTTPS ja existente no host e nao tenta definir certificado, `server_name` nem redirect HTTP, porque esses pontos dependem da configuracao ja ativa no droplet.

## 4. Roteamento previsto

O template encaminha:

- `/api` e `/api/*` para `127.0.0.1:18080`;
- `/assets` e `/assets/*` para `127.0.0.1:18080`;
- `/checking/admin` e `/checking/admin/*` para `127.0.0.1:18081`;
- `/checking/user` e `/checking/user/*` para `127.0.0.1:18082`;
- `/checking/transport` e `/checking/transport/*` para `127.0.0.1:18083`.

Tambem foi definido redirect `308` de:

- `/checking/admin/` -> `/checking/admin`
- `/checking/user/` -> `/checking/user`
- `/checking/transport/` -> `/checking/transport`

## 5. Aplicacao manual sugerida

Aplicar somente quando os quatro alvos manuais ja estiverem disponiveis no servidor.

Passos sugeridos no droplet:

1. fazer backup do arquivo atual do `server` publico do dominio;
2. aplicar o bloco gerenciado com `deploy/nginx/manage_checking_edge_cutover.sh apply --server-config <arquivo-do-server>` ou, se preferir, copiar manualmente o conteudo de `deploy/nginx/checking-edge-routes.conf` para dentro do bloco `server` HTTPS atual;
3. revisar se nao existe regra anterior conflitante para `/api`, `/assets` ou `/checking/`;
4. validar a configuracao com `nginx -t`;
5. recarregar com `systemctl reload nginx`.

Exemplo de aplicacao assistida no droplet:

```bash
bash deploy/nginx/manage_checking_edge_cutover.sh apply --server-config /etc/nginx/sites-enabled/tscode.com.br.conf --reload
```

O script cria um backup timestamped, insere ou atualiza um bloco gerenciado delimitado por marcadores e executa `nginx -t` antes do reload.

Verificacao local recomendada no droplet, antes ou logo apos o reload:

```bash
bash deploy/nginx/verify_checking_edge_cutover.sh --mode local --nginx-test
```

## 6. Validacao imediata apos o cutover

Depois do reload, validar no servidor ou externamente:

```bash
curl -I https://tscode.com.br/api/health
curl -I https://tscode.com.br/checking/admin
curl -I https://tscode.com.br/checking/user
curl -I https://tscode.com.br/checking/transport
bash deploy/nginx/verify_checking_edge_cutover.sh --mode full
```

Validacoes funcionais minimas:

- `https://tscode.com.br/api/health` retorna sucesso;
- `https://tscode.com.br/checking/admin` carrega o HTML do admin;
- `https://tscode.com.br/checking/user` carrega o HTML do user;
- `https://tscode.com.br/checking/transport` carrega o HTML do transport;
- login admin continua funcionando pela mesma origem;
- stream SSE do admin continua operando sem buffering indevido.

Se o dominio publico de verificacao for outro, como `https://www.tscode.com.br`, o script pode ser executado assim:

```bash
bash deploy/nginx/verify_checking_edge_cutover.sh --mode full --public-base-url https://www.tscode.com.br
```

Se for necessario rollback imediato do arquivo do proxy, usar o backup emitido no `apply`:

```bash
bash deploy/nginx/manage_checking_edge_cutover.sh rollback --server-config /etc/nginx/sites-enabled/tscode.com.br.conf --backup-file /etc/nginx/sites-enabled/tscode.com.br.conf.bak.YYYYMMDDHHMMSS --reload
```

## 7. Observacoes de risco

- este arquivo ainda nao altera o workflow oficial de producao;
- esta etapa so prepara um corte manual e reversivel no proxy;
- `/assets` continua ancorado na API para evitar ampliar o escopo nesta onda;
- o rollback operacional detalhado deve ser documentado no item especifico posterior da lista.