# Operacao e Rollback do Deploy Separado

Status deste documento: preparacao operacional inicial, criada em 2026-04-24.

## 1. Objetivo

Este documento define como operar o deploy separado da API e dos websites `admin`, `user` e `transport` durante a fase de transicao.

O foco aqui e:

- manter o workflow global atual como fallback seguro;
- descrever a rotina operacional dos alvos separados;
- registrar o rollback mais rapido por tipo de incidente;
- deixar explicita a condicao para reabrir workflows automaticos por caminho.

## 2. Estado operacional atual

No estado atual do projeto:

- o workflow oficial `.github/workflows/deploy-oceandrive.yml` foi mantido apenas como fallback manual via `workflow_dispatch`;
- os workflows `.github/workflows/deploy-oceandrive-api-only.yml`, `.github/workflows/deploy-oceandrive-admin-only.yml`, `.github/workflows/deploy-oceandrive-user-only.yml` e `.github/workflows/deploy-oceandrive-transport-only.yml` existem apenas para operacao manual e isolada;
- o template de proxy `deploy/nginx/checking-edge-routes.conf` ainda nao foi ativado automaticamente;
- os smoke tests minimos por alvo foram centralizados em `deploy/smoke/validate_target.sh`.

Conclusao operacional: a producao continua podendo voltar ao modelo atual porque o caminho global validado ainda existe e nao foi substituido.

## 3. Alvos, portas e marcadores

### 3.1 Alvos dedicados

- API separada: `docker-compose.api.yml`, servico `api`, porta local `18080`
- Admin separado: `docker-compose.websites.yml`, servico `admin-web`, porta local `18081`
- User separado: `docker-compose.websites.yml`, servico `user-web`, porta local `18082`
- Transport separado: `docker-compose.websites.yml`, servico `transport-web`, porta local `18083`

### 3.2 Marcadores de release no servidor

- workflow global: `.deploy-release`
- API separada: `.deploy-release-api`
- admin separado: `.deploy-release-admin-web`
- user separado: `.deploy-release-user-web`
- transport separado: `.deploy-release-transport-web`

Esses arquivos ajudam a confirmar qual commit foi implantado por cada caminho.

## 4. Rotina operacional padrao

### 4.1 Quando usar o workflow global de fallback

Usar o workflow global apenas como fallback manual quando houver mudanca que:

- misture backend e frontend no mesmo pacote de entrega;
- altere partes compartilhadas sem estrategia fina validada;
- envolva migracoes sensiveis;
- exija o retorno mais rapido ao caminho ja conhecido em producao.

### 4.2 Quando usar um workflow manual por alvo

Usar um workflow manual por alvo quando a alteracao estiver claramente isolada e houver janela controlada para isso.

Exemplos:

- ajuste apenas da API: `Deploy OceanDrive API Only`
- ajuste apenas do painel admin: `Deploy OceanDrive Admin Only`
- ajuste apenas do site user: `Deploy OceanDrive User Only`
- ajuste apenas do site transport: `Deploy OceanDrive Transport Only`

### 4.3 Verificacao minima apos qualquer deploy manual

Verificar no servidor ou externamente:

```bash
curl -I https://tscode.com.br/api/health
curl -I https://tscode.com.br/checking/admin
curl -I https://tscode.com.br/checking/user
curl -I https://tscode.com.br/checking/transport
```

Se o alvo separado ainda nao estiver recebendo trafego publico, validar tambem a porta local correspondente no droplet.

## 5. Operacao do proxy por caminho

Quando houver janela para o cutover manual do proxy, a aplicacao recomendada continua sendo a descrita em `docs/context/proxy_rotas_deploy_separado.md`.

Resumo operacional:

1. fazer backup do bloco `server` HTTPS atual;
2. aplicar `deploy/nginx/checking-edge-routes.conf` pelo helper `deploy/nginx/manage_checking_edge_cutover.sh` ou, se necessario, por edicao manual controlada;
3. revisar conflitos com regras antigas de `/api`, `/assets` e `/checking/`;
4. validar com `nginx -t`;
5. recarregar com `systemctl reload nginx`;
6. executar os checks publicos e funcionais minimos.

Verificacao recomendada nesse momento:

```bash
bash deploy/nginx/manage_checking_edge_cutover.sh apply --server-config /etc/nginx/sites-enabled/tscode.com.br.conf --reload
bash deploy/nginx/verify_checking_edge_cutover.sh --mode local --nginx-test
bash deploy/nginx/verify_checking_edge_cutover.sh --mode full
```

O ponto critico desse corte e que a reversao mais rapida nao e rebuild de container: e restaurar a configuracao anterior do proxy.

## 6. Rollback por cenario

### 6.1 Falha logo apos o cutover do proxy

Sintomas tipicos:

- `404`, `502` ou pagina incorreta em `/checking/admin`, `/checking/user` ou `/checking/transport`;
- assets quebrados por problema de barra final;
- `/api` ou `/assets` respondendo no alvo errado.

Rollback mais rapido:

1. restaurar o backup do bloco `server` anterior ao cutover com `deploy/nginx/manage_checking_edge_cutover.sh rollback --server-config <arquivo> --backup-file <backup> --reload` ou copiar manualmente o backup salvo antes do corte;
2. validar `nginx -t`;
3. recarregar `systemctl reload nginx`;
4. validar novamente `https://tscode.com.br/api/health` e as URLs publicas criticas.

Observacao: enquanto o workflow global seguir disponivel como fallback e a aplicacao monolitica continuar como baseline, esse rollback tende a ser o retorno mais rapido ao estado conhecido.

### 6.2 Falha da API separada

Sintomas tipicos:

- health check em `127.0.0.1:18080/api/health` falhando;
- rotas `/api/*` respondendo erro apos o proxy apontar para `18080`.

Resposta inicial:

1. inspecionar `docker compose -f docker-compose.api.yml ps`;
2. inspecionar `docker compose -f docker-compose.api.yml logs --tail=120 api`;
3. confirmar o commit implantado em `.deploy-release-api`.

Rollback rapido durante a transicao:

1. voltar o proxy de `/api` e `/assets` para o caminho anterior;
2. se necessario, rerodar manualmente o workflow global oficial para restaurar o baseline conhecido;
3. corrigir o problema antes de nova tentativa isolada.

### 6.3 Falha de um website separado

Sintomas tipicos:

- apenas `admin`, `user` ou `transport` falha;
- a API continua saudavel;
- o erro fica restrito a um caminho publico especifico.

Resposta inicial:

1. inspecionar `docker compose -f docker-compose.websites.yml ps`;
2. inspecionar `docker compose -f docker-compose.websites.yml logs --tail=120 <servico>`;
3. confirmar o commit implantado no marcador `.deploy-release-<alvo>`.

Rollback rapido durante a transicao:

1. apontar apenas o caminho afetado de volta para o baseline anterior no proxy;
2. manter os demais caminhos no estado atual se estiverem saudaveis;
3. corrigir o alvo com problema antes de nova ativacao.

Esse rollback parcial e uma das principais vantagens operacionais da separacao por caminho.

### 6.4 Incidente geral apos fallback manual do root

Se o problema surgir apos a execucao manual do workflow global, manter o fluxo rapido ja validado em `docs/commitpush.md`:

1. confirmar se o erro publico e real;
2. checar o estado do workflow no GitHub Actions;
3. revisar migracoes recentes, especialmente Alembic;
4. validar `https://tscode.com.br/api/health` e os caminhos publicos criticos;
5. enviar hotfix para `main` se a causa exigir correcao de codigo.

## 7. Comandos uteis de operacao

### 7.1 Inspecao do GitHub Actions

```powershell
gh run list -R tscode-com-br/checking --limit 5
gh run view <RUN_ID> -R tscode-com-br/checking --log-failed
```

### 7.2 Inspecao dos alvos separados no servidor

```bash
cat .deploy-release-api
cat .deploy-release-admin-web
cat .deploy-release-user-web
cat .deploy-release-transport-web
docker compose -f docker-compose.api.yml ps
docker compose -f docker-compose.websites.yml ps
```

### 7.3 Execucao manual do smoke test remoto

```bash
bash deploy/smoke/validate_target.sh --label API --compose-file docker-compose.api.yml --service api --url http://127.0.0.1:18080/api/health
bash deploy/smoke/validate_target.sh --label admin-web --compose-file docker-compose.websites.yml --service admin-web --url http://127.0.0.1:18081/ --contains "Checking Admin"
bash deploy/smoke/validate_target.sh --label user-web --compose-file docker-compose.websites.yml --service user-web --url http://127.0.0.1:18082/ --contains "Checking Mobile Web"
bash deploy/smoke/validate_target.sh --label transport-web --compose-file docker-compose.websites.yml --service transport-web --url http://127.0.0.1:18083/ --contains "Checking Transport"
```

### 7.4 Verificacao do cutover do proxy

```bash
bash deploy/nginx/manage_checking_edge_cutover.sh apply --server-config /etc/nginx/sites-enabled/tscode.com.br.conf --reload
bash deploy/nginx/verify_checking_edge_cutover.sh --mode local --nginx-test
bash deploy/nginx/verify_checking_edge_cutover.sh --mode full
```

## 8. Condicao para reabrir workflows por caminho

Os workflows automaticos por caminho so devem ser reabertos quando todas as condicoes abaixo forem verdadeiras ao mesmo tempo:

1. o proxy por caminho ja estiver implantado com rollback validado;
2. os workflows manuais por alvo tiverem execucoes saudaveis e repetiveis;
3. o workflow global `.github/workflows/deploy-oceandrive.yml` permanecer manual/fallback ou ficar mutual-exclusivo em relacao aos futuros gatilhos automaticos por caminho;
4. a nova estrategia de gatilho automatico for aceita pelo validador do GitHub Actions usado neste repositório;
5. este runbook continuar coerente com a topologia real do droplet.

Sem isso, a reabertura da automacao por caminho volta a introduzir risco de deploy duplo.

## 9. O que nao fazer durante a transicao

- nao remover o workflow global antes do cutover do proxy estabilizar;
- nao reativar automacao por caminho enquanto o desenho final dos gatilhos automaticos ainda puder competir com o workflow global de fallback;
- nao mover `/assets` para outro alvo sem nova revisao operacional;
- nao assumir rollback por rebuild quando o problema real estiver no proxy.

## 10. Referencias

- `docs/context/arquitetura_alvo_deploy_separado_monorepo.md`
- `docs/context/proxy_rotas_deploy_separado.md`
- `docs/commitpush.md`
- `deploy/nginx/checking-edge-routes.conf`
- `deploy/nginx/manage_checking_edge_cutover.sh`
- `deploy/nginx/verify_checking_edge_cutover.sh`
- `deploy/smoke/validate_target.sh`