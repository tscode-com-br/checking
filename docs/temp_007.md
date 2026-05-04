# Plano robusto e minucioso para eliminar o erro 504 de forma profissional

## 1. Objetivo deste documento

Este documento deixa de ser um plano primariamente investigativo e passa a ser um plano de solucao, endurecimento e validacao operacional para eliminar a recorrencia do erro `504 Gateway Time-out` no ambiente publico do projeto.

O objetivo nao e apenas reduzir a chance de novo incidente. O objetivo e conduzir uma correcao estrutural, com sequenciamento tecnico, rollback controlado, criterios de aceite objetivos e validacao sob carga realista.

Este plano parte do entendimento atual do sistema e do incidente mais recente e assume que ainda pode haver fatores secundarios nao completamente medidos. Por isso, o plano combina:

1. mitigacao imediata de risco;
2. desacoplamento dos componentes que hoje compartilham blast radius;
3. endurecimento do runtime HTTP e do edge;
4. reducao de burst gerado pelos clientes;
5. revisao de banco, filas e integracoes externas;
6. reproducao controlada e validacao sob carga;
7. operacionalizacao com alertas, runbook e rollback.

## 2. Baseline tecnico atualizado

Os fatos abaixo devem ser tratados como baseline operacional atualizado para o plano:

1. Em `2026-05-04`, houve indisponibilidade publica com erro `504`.
2. O Nginx do host registrou `upstream timed out (110: Connection timed out) while reading response header from upstream`.
3. O upstream observado nos logs do incidente foi `http://127.0.0.1:8000`.
4. O container do app ficou `unhealthy`, mas sem evidencia de `OOMKilled`.
5. O reboot do droplet restaurou o servico.
6. O banco ficou `healthy` durante a janela observada.
7. A IA de transporte ainda nao esta em producao no provedor DigitalOcean e nao deve ser tratada como causa principal deste incidente.
8. O incidente ocorreu logo apos uma apresentacao para a equipe, quando muitos usuarios escanearam o QR Code e passaram a usar a superficie web em `sistema/app/static/check`.
9. Nessa janela houve uso concorrente de cadastro, login, consulta de estado, localizacao e check-in/check-out.
10. O backend de producao hoje sobe com `alembic upgrade head && uvicorn sistema.app.main:app --host 0.0.0.0 --port 8000`.
11. O fluxo de check web e os fluxos afins ja enfileiram submissao ao Forms, mas o consumidor da fila roda no mesmo servico da API.
12. O worker de Forms usa Playwright/Chromium e portanto disputa CPU, memoria e estabilidade com o runtime HTTP.
13. A SPA de check executa bootstrap de autenticacao, historico, catalogo de projetos e localizacao, e ainda reage a eventos de `focus`, `pageshow` e `visibilitychange`.
14. O backend usa um unico processo `uvicorn` no comando atual do container, salvo configuracao externa nao versionada no host.

## 3. Leitura tecnica atual do problema

Com o material hoje disponivel, a leitura de trabalho mais forte e a seguinte:

1. o incidente teve alta probabilidade de nascer na camada de runtime da API, e nao no host ou no Nginx em si;
2. o gatilho mais plausivel foi burst legitimo na superficie web de check, com muita autenticacao, bootstrap, consulta de estado e submissao quase simultaneos;
3. o sistema atual permite que o processamento pesado do Forms contamine o mesmo processo/container que deveria continuar respondendo HTTP;
4. o runtime HTTP atual parece fragil para burst moderado, por operar com topologia de processo unica ou insuficiente;
5. a superficie `sistema/app/static/check` provavelmente gera mais chamadas do que o necessario durante inicializacao, restauracao de sessao e eventos de foco/retorno a tela;
6. o problema pode ter sido agravado por custo de CPU em autenticacao, competicao por conexoes de banco, filas locais sem isolamento e ausencia de auto-recuperacao forte quando o app entra em estado ruim.

Esta leitura e suficiente para orientar a implementacao. Ela nao elimina a necessidade de medir, mas elimina a necessidade de continuar postergando correcoes estruturais obvias.

## 4. Principios obrigatorios deste programa de correcao

Toda fase deste plano deve obedecer aos principios abaixo:

1. Nenhuma correcao deve aumentar blast radius entre API HTTP, worker de fila e integracoes externas.
2. Toda mudanca deve ser observavel em producao por metricas, logs ou healthchecks melhores do que os atuais.
3. Toda mudanca de producao deve ter criterio de rollback explicito.
4. O caminho critico de request deve permanecer o mais curto possivel.
5. Trabalho pesado, bloqueante ou sujeito a dependencia externa deve sair do processo que responde as rotas publicas.
6. Clientes web, mobile e admin nao devem depender de polling ou bootstrap mais agressivo do que o dominio exige.
7. O desenho final precisa suportar burst legitimo de equipe sem exigir reboot manual para recuperar o servico.
8. O repo deve voltar a ser a fonte de verdade do runtime, do edge e dos playbooks operacionais.

## 5. Criterio de problema resolvido

Este incidente so deve ser considerado resolvido quando todos os criterios abaixo forem satisfeitos:

1. bursts de uso da superficie web de check deixam de derrubar o acesso global a `/checking/user`, `/checking/admin` e `/api/*`;
2. falha, lentidao ou backlog do Forms nao torna a API indisponivel;
3. o runtime HTTP tem capacidade concorrente, healthchecks e auto-recuperacao compativeis com o trafego real;
4. o frontend de check deixa de disparar chamadas redundantes ou agressivas em bootstrap, foco e retorno a tela;
5. o ambiente tem metricas suficientes para identificar rapidamente pressao de CPU, banco, fila, edge e latencia por rota;
6. o sistema passa por um teste de carga reproduzindo o caso de apresentacao sem degradacao publica equivalente;
7. existe runbook claro para degradacao parcial, backlog elevado, edge inconsistente e rollback.

## 6. Estrutura do programa

O programa esta dividido em quatro blocos:

1. Contencao imediata de risco.
2. Correcao estrutural da arquitetura de execucao.
3. Endurecimento de edge, banco, clientes e deploy.
4. Validacao, rollout controlado e operacao continua.

Cada fase abaixo contem objetivo, entregas, riscos, dependencias e criterio de saida.

## 7. Fases de implementacao

## Fase 0 - Congelamento do baseline operacional e definicao da linha de comando de producao

### Objetivo

Transformar o estado atual do ambiente em baseline versionado antes de iniciar mudancas estruturais.

### Entregas obrigatorias

1. Registrar a topologia efetiva em producao: container app, container db, Nginx ativo, upstreams reais e healthchecks reais.
2. Registrar o comando efetivamente usado para subir o app em producao.
3. Registrar a configuracao ativa do Nginx com `nginx -T` e comparar com o repo.
4. Registrar `docker inspect` relevante do container do app, incluindo `State`, `Health` e `RestartCount`.
5. Registrar configuracao real de banco exposta pelo compose e pelo host.
6. Registrar timezone e timestamps do host, do container app e do Postgres.

### Resultado esperado

Ao fim desta fase, o time para de trabalhar com inferencias difusas e passa a ter um baseline operacional verificavel.

### Dependencias

1. Acesso ao host DigitalOcean.
2. Acesso aos arquivos ativos do Nginx e ao runtime Docker do host.

### Riscos que esta fase reduz

1. Corrigir o repo enquanto a producao roda outra topologia.
2. Endurecer o app sem perceber divergencia de edge ou startup.

### Criterio de saida

Existe um snapshot operacional confiavel e versionavel do ambiente atual.

## Fase 1 - Instrumentacao minima para nunca mais depender de reboot como diagnostico

### Objetivo

Adicionar observabilidade suficiente para distinguir rapidamente degradacao de edge, runtime HTTP, banco, fila e integracao externa.

### Entregas obrigatorias

1. Adicionar logs estruturados por rota com latencia, status, request id e superficie cliente.
2. Adicionar metricas de latencia e volume por rota critica.
3. Adicionar metricas da fila do Forms: pendentes, processando, sucesso, falha, idade do item mais antigo e tempo medio de processamento.
4. Adicionar metricas de pool de banco e numero de conexoes ativas, se viavel na stack atual.
5. Adicionar metricas de processo e container: CPU, memoria, reinicios, health status e tempo de resposta do health endpoint.
6. Registrar backlog e falhas do worker separado quando ele existir.
7. Definir retention minima e local de consulta para logs de Nginx, app e Docker.

### Resultado esperado

Na proxima degradacao, o time deve identificar em poucos minutos se o problema nasceu em fila, worker, banco, runtime HTTP, cliente ou edge.

### Dependencias

1. Fase 0 concluida.

### Riscos que esta fase reduz

1. Corrigir sintomas sem saber onde a pressao realmente nasce.
2. Repetir reboot manual por ausencia de evidencias.

### Criterio de saida

O ambiente passa a expor sinais operacionais suficientes para diagnostico rapido e comparacao pre e pos-fix.

## Fase 2 - Contencao imediata do blast radius do Forms

### Objetivo

Parar de permitir que backlog ou execucao pesada do Forms degradem o mesmo processo responsavel pelas respostas HTTP.

### Entregas obrigatorias

1. Extrair o consumo da fila do Forms para um worker separado da API.
2. Garantir que a API apenas grave o job ou o item de fila e retorne rapidamente.
3. Garantir que lentidao, falha ou crescimento de backlog do Forms nao derrubem login, historico, estado, admin ou mobile.
4. Definir mecanismo de start, stop, observabilidade e restart do worker separado.
5. Definir politica de retentativa e backoff do worker fora do request path.

### Resultado esperado

Mesmo com pico de check-ins/check-outs, a fila pode crescer sem arrastar a API inteira para degradacao.

### Dependencias

1. Fase 1 parcialmente pronta para medir o efeito da separacao.

### Riscos que esta fase reduz

1. CPU e memoria do Chromium/Playwright competindo com o runtime HTTP.
2. API indisponivel por backlog de trabalho assincroono local.

### Criterio de saida

O container ou processo HTTP passa a ser operacionalmente independente do consumidor do Forms.

## Fase 3 - Endurecimento do runtime HTTP da API

### Objetivo

Fazer o runtime HTTP suportar burst legitimo sem colapsar com processo unico, pouca concorrencia ou travamento silencioso.

### Entregas obrigatorias

1. Substituir o modo de execucao atual por topologia apropriada para producao, com numero de workers/processos explicitamente definido.
2. Revisar timeouts internos, keepalive e configuracoes do ASGI server.
3. Adicionar mecanismo de dump de stacks ou diagnostico do processo em degradacao sustentada.
4. Revisar se o startup deve continuar acoplado a `alembic upgrade head` ou se migracao deve ser separada do processo HTTP.
5. Revisar limites de concorrencia do servidor HTTP e documentar a decisao.

### Resultado esperado

O processo HTTP deixa de ser fragil por default e passa a ter capacidade coerente com uso de producao.

### Dependencias

1. Fase 0 para confirmar a topologia atual.
2. Fase 1 para medir impacto.

### Riscos que esta fase reduz

1. Worker unico saturando tudo.
2. Processo vivo, mas silenciosamente incapaz de responder.

### Criterio de saida

Existe runtime HTTP explicitamente endurecido, versionado e validado localmente e em staging ou ambiente de prova.

## Fase 4 - Healthcheck, readiness e auto-recuperacao reais

### Objetivo

Fazer com que o ambiente reaja automaticamente a degradacao real e pare de depender de reboot manual para retornar.

### Entregas obrigatorias

1. Diferenciar readiness e liveness, mesmo que a stack atual exija uma aproximacao pratica.
2. Revisar o endpoint `/api/health` para refletir degradacao relevante do app.
3. Definir criterio para `healthy`, `degraded` e `failed`.
4. Ajustar healthcheck do container para detectar silencio util, e nao apenas processo vivo.
5. Definir estrategia de restart automatico para estado ruim sustentado.
6. Garantir que falha do worker de Forms nao derrube o health principal da API, mas tambem nao passe invisivel.

### Resultado esperado

O sistema passa a sair de estados ruins de forma automatica e observavel.

### Dependencias

1. Fase 1 para sinais de diagnostico.
2. Fase 3 para runtime HTTP mais previsivel.

### Riscos que esta fase reduz

1. Container `unhealthy` sem recuperacao.
2. Health superficial mascarando degradacao real.

### Criterio de saida

O ambiente consegue diferenciar degradacao de indisponibilidade e reage de forma automatica, ou ao menos alerta cedo e de forma confiavel.

## Fase 5 - Reducao de burst gerado pela SPA de check

### Objetivo

Diminuir drasticamente a pressao desnecessaria causada pelo cliente web de check, especialmente em bootstrap, autenticacao, localizacao e eventos de foco.

### Entregas obrigatorias

1. Revisar o bootstrap da SPA em `sistema/app/static/check` para remover chamadas redundantes.
2. Reduzir ou reestruturar chamadas em `focus`, `pageshow` e `visibilitychange`.
3. Revisar a verificacao automatica de senha para evitar tempestade de logins silenciosos sob burst.
4. Revisar bootstrap autenticado para decidir o que realmente precisa carregar imediatamente.
5. Introduzir debounce, cache local, invalidez controlada e politicas mais conservadoras de refresh.
6. Garantir que localizacao e historico nao sejam reconsultados agressivamente sem necessidade de dominio.

### Resultado esperado

O numero de chamadas geradas por usuario na abertura e retomada da tela cai de forma material sem degradar a UX.

### Dependencias

1. Fase 1 para medicao por rota e por evento.

### Riscos que esta fase reduz

1. Burst legitimo de equipe se transformando em tempestade de requests.
2. Cliente bem intencionado pressionando a API acima do necessario.

### Criterio de saida

Existe diff comprovavel de volume de requests por usuario e por minuto na superficie web de check.

## Fase 6 - Hot paths do backend para web check, admin e mobile

### Objetivo

Encurtar o caminho critico dos endpoints mais afetados e remover trabalho desnecessario por request.

### Entregas obrigatorias

1. Revisar os hot paths de `/api/web/check/state`, `/api/mobile/state`, `/api/admin/checkin`, `/api/admin/checkout`, `/api/admin/projects` e rotas HTML associadas.
2. Identificar e corrigir serializacao pesada, consultas repetidas, N+1 e trabalho de agregacao desnecessario.
3. Extrair leitura cara de bootstrap para endpoints mais especializados quando isso reduzir custo por request.
4. Aplicar caching curto onde o dominio permitir.
5. Medir latencia p50, p95 e p99 antes e depois de cada subcorrecao.

### Resultado esperado

As rotas quentes passam a responder de forma previsivel mesmo sob concorrencia mais alta.

### Dependencias

1. Fase 1 para metricas.
2. Fase 5 para reduzir ruido do cliente.

### Riscos que esta fase reduz

1. Custo interno exagerado por request em rotas muito chamadas.
2. Colapso por concentracao de poucas rotas quentes.

### Criterio de saida

As principais rotas sob burst apresentam melhora material de latencia e estabilidade.

## Fase 7 - Banco, pool de conexoes e consultas quentes

### Objetivo

Garantir que o app nao fique preso aguardando banco, conexao livre, lock ou query lenta em horario de burst.

### Entregas obrigatorias

1. Revisar configuracao de `create_engine`, pool, overflow, timeout e reciclagem de conexoes.
2. Medir concorrencia real de conexoes do app versus `max_connections=40` do Postgres.
3. Revisar consultas quentes identificadas na fase anterior.
4. Criar indices, revisar planos e corrigir pontos de lock ou varredura completa quando necessario.
5. Restringir a exposicao externa do Postgres se ela ainda estiver aberta ou frouxa demais.
6. Medir impacto de autenticacao em massa e de leituras simultaneas sobre o banco.

### Resultado esperado

O banco deixa de ser gargalo oculto ou amplificador de degradacao durante bursts legitimos.

### Dependencias

1. Fase 1 para metricas.
2. Fase 6 para focar nas queries certas.

### Riscos que esta fase reduz

1. Pool exhaustion.
2. Espera de conexao contaminando o app inteiro.
3. Pressao externa indevida na porta `5432`.

### Criterio de saida

Existe configuracao de pool e banco coerente com o padrao de carga esperado e validada sob teste.

## Fase 8 - Edge Nginx e protecao por superficie

### Objetivo

Fazer o edge refletir a topologia correta, proteger superfices distintas e parar de ser configuracao manual fragil.

### Entregas obrigatorias

1. Reconciliar configuracao ativa do host com os arquivos versionados do repo.
2. Confirmar upstreams corretos e explicitos para API, admin, user e demais superfices.
3. Revisar `proxy_read_timeout`, `proxy_connect_timeout`, buffering, keepalive e cabecalhos conforme a topologia final.
4. Aplicar protecao por rota ou superficie quando fizer sentido: autenticacao, health, streaming, polling e HTML.
5. Introduzir rate limiting ou burst control no edge para superficies mais sensiveis, sem quebrar uso legitimo.
6. Remover drift operacional do host sempre que possivel.

### Resultado esperado

O edge deixa de ser uma camada opaca e passa a aplicar politicas coerentes com o risco de cada superficie.

### Dependencias

1. Fase 0 para entender o estado atual.
2. Fase 3 para conhecer a topologia HTTP final.

### Riscos que esta fase reduz

1. Drift entre repo e host.
2. Timeouts ou buffering inadequados para o padrao real.
3. Burst local derrubando superficies menos criticas junto com as essenciais.

### Criterio de saida

O Nginx ativo do host e o repo passam a estar alinhados e testaveis por diff claro.

## Fase 9 - Protecao contra burst legitimo e abuso acidental

### Objetivo

Garantir que o sistema suporte picos de apresentacao, onboarding e uso de equipe sem permitir avalanche de requests por comportamento bem intencionado.

### Entregas obrigatorias

1. Definir limites por rota e por classe de cliente.
2. Aplicar backoff, debounce e cache onde o cliente puder ajudar.
3. Aplicar rate limiting no edge ou backend nas superficies apropriadas.
4. Proteger endpoints de autenticacao, status e polling contra tempestade acidental.
5. Diferenciar politicas entre admin, web check e mobile.

### Resultado esperado

Burst legitimo continua funcionando, mas deixa de ter poder de colapsar o backend por excesso de repeticao.

### Dependencias

1. Fase 5 para reducao no cliente.
2. Fase 8 para politicas de edge.

### Riscos que esta fase reduz

1. Colapso por uso massivo, mas legitimo.
2. Regressao futura quando novas telas adicionarem polling ou bootstrap pesado.

### Criterio de saida

Existe politica clara de controle de burst por superficie e ela foi exercitada em ambiente controlado.

## Fase 10 - Startup, migracao, readiness e deploy sem janelas frageis

### Objetivo

Remover fragilidade de boot e rollout que possa deixar a aplicacao parcialmente viva, mas nao saudavel de verdade.

### Entregas obrigatorias

1. Revisar se `alembic upgrade head` deve continuar no mesmo `CMD` do processo HTTP.
2. Separar, quando necessario, migracao do runtime de request.
3. Definir readiness real antes de expor trafego.
4. Garantir que deploy e reboot nao recriem uma janela de fragilidade parecida com a do incidente.
5. Documentar e automatizar rollback de deploy quando readiness falhar.

### Resultado esperado

O sistema deixa de depender de sequencing manual ou de startup monolitico fragil.

### Dependencias

1. Fase 3 para topologia HTTP final.
2. Fase 4 para modelo de health/readiness.

### Riscos que esta fase reduz

1. Janelas de indisponibilidade em reboot e deploy.
2. Processo HTTP recebendo trafego cedo demais.

### Criterio de saida

O ciclo de deploy e reboot fica previsivel, testavel e alinhado com a topologia final.

## Fase 11 - Harness de reproducao e teste de carga recorrente

### Objetivo

Parar de validar a solucao apenas por intuicao e passar a reproduzir o padrao de burst que causou o incidente.

### Entregas obrigatorias

1. Criar cenarios de carga para a superficie web de check reproduzindo cadastro, login, historico, localizacao e check-in/check-out.
2. Criar cenarios de carga concorrente para admin e mobile quando isso fizer sentido no baseline atual.
3. Incluir simulacao de backlog do Forms com worker separado.
4. Incluir medicao de latencia, erro, uso de CPU, memoria, conexoes de banco e backlog de fila durante o teste.
5. Definir criterios de sucesso, degradacao aceitavel e falha.

### Resultado esperado

O time consegue provar que a arquitetura corrigida suporta o caso real de apresentacao e uso simultaneo.

### Dependencias

1. Fases 2 a 10 suficientemente maduras para teste integrado.

### Riscos que esta fase reduz

1. Declarar sucesso sem reproduzir o incidente.
2. Descobrir regressao apenas em producao.

### Criterio de saida

Existe um harness repetivel que aproxima o caso real do incidente e passa apos as correcoes.

## Fase 12 - Rollout progressivo e validacao em producao

### Objetivo

Levar as correcoes para producao sem trocar um problema por outro e com checkpoints claros de seguranca.

### Entregas obrigatorias

1. Definir ordem de rollout das mudancas por risco e acoplamento.
2. Separar entregas reversiveis de entregas mais estruturais.
3. Definir checklist de verificacao imediata pos-deploy.
4. Definir thresholds que disparam rollback automatico ou manual.
5. Garantir que metricas, logs e healthchecks estejam prontos antes de mover a carga real.

### Resultado esperado

As mudancas entram em producao de forma controlada, com rollback simples e observabilidade suficiente para confirmar saude.

### Dependencias

1. Fase 1 concluida.
2. Fases estruturais entregues e validadas fora de producao.

### Riscos que esta fase reduz

1. Correcao estrutural quebrando UX ou disponibilidade.
2. Falta de rollback claro em alteracoes de runtime e edge.

### Criterio de saida

Existe plano de rollout, janela de observacao e criterio de rollback por subentrega.

## Fase 13 - Runbook, alertas e operacao continua

### Objetivo

Fechar a lacuna entre resolver o incidente e operar o sistema corretamente depois da correcao.

### Entregas obrigatorias

1. Criar runbook de degradacao parcial da API.
2. Criar runbook de backlog elevado do Forms.
3. Criar runbook de verificacao de Nginx, runtime HTTP, banco e worker.
4. Definir alertas para latencia por rota, fila, health, erro 5xx, restart anormal, CPU e conexoes de banco.
5. Definir quando reiniciar worker, quando reiniciar API e quando escalar investigacao para host.
6. Definir coleta minima de evidencias antes de qualquer reboot manual.

### Resultado esperado

O time passa a ter operacao repetivel, menos heroica e menos dependente de memoria informal.

### Dependencias

1. Fase 1 concluida.
2. Arquitetura final das fases anteriores estabilizada.

### Riscos que esta fase reduz

1. Reboot como primeira reacao.
2. Perda de evidencias na proxima degradacao.

### Criterio de saida

Existe runbook aprovado e alertas suficientes para uso cotidiano.

## Fase 14 - Aceite final e encerramento tecnico

### Objetivo

Formalizar que o problema foi resolvido de forma tecnicamente defensavel, e nao apenas mitigado superficialmente.

### Entregas obrigatorias

1. Comparativo antes/depois de latencia, erro, throughput e backlog.
2. Evidencia de que burst da superficie web de check deixou de derrubar o app inteiro.
3. Evidencia de que Forms desacoplado nao contamina o runtime HTTP.
4. Evidencia de que rollout, health e rollback estao operacionais.
5. Registro das decisoes tecnicas e dos tradeoffs aceitos.

### Resultado esperado

O incidente fica fechado com justificativa tecnica, evidencias e novo baseline operacional.

### Dependencias

1. Todas as fases anteriores relevantes concluidas.

### Riscos que esta fase reduz

1. Considerar o incidente resolvido sem prova suficiente.
2. Perder o aprendizado estrutural apos a urgencia.

### Criterio de saida

O projeto passa a ter baseline atualizado, operacionalizacao clara e defesa tecnica de que a recorrencia foi materialmente reduzida.

## 8. Ordem recomendada de execucao

Para manter coerencia tecnica e reduzir retrabalho, a ordem recomendada e:

1. Fase 0
2. Fase 1
3. Fase 2
4. Fase 3
5. Fase 4
6. Fase 5
7. Fase 6
8. Fase 7
9. Fase 8
10. Fase 9
11. Fase 10
12. Fase 11
13. Fase 12
14. Fase 13
15. Fase 14

Motivo desta ordem:

1. primeiro consolida-se o baseline e cria-se observabilidade;
2. depois elimina-se o maior acoplamento estrutural entre fila pesada e runtime HTTP;
3. em seguida endurece-se o servidor, o health e o edge;
4. depois reduz-se burst do cliente e custo dos hot paths;
5. por fim valida-se sob carga, realiza-se rollout progressivo e formaliza-se a nova operacao.

## 9. Regras de mudanca para cada fase

Cada fase executada deve produzir, no minimo:

1. uma descricao objetiva do problema que aquela fase ataca;
2. a superficie exata alterada;
3. o risco que a mudanca reduz;
4. a estrategia de validacao local e integrada;
5. o criterio de rollback;
6. a metrica ou evidencia que definira sucesso.

Nenhuma fase deve ser considerada concluida apenas porque o codigo foi alterado. Ela so fecha quando a validacao correspondente passar.

## 10. Artefatos obrigatorios por bloco

### Bloco A - Baseline e observabilidade

1. snapshot do ambiente;
2. diff entre runtime real e repo;
3. painel minimo ou relatorio de metricas essenciais;
4. formato de logs estruturados.

### Bloco B - Correcao estrutural

1. topologia final do app e do worker;
2. comando final de startup versionado;
3. healthchecks finais;
4. documentacao da fila e de sua operacao.

### Bloco C - Endurecimento de clientes, banco e edge

1. lista de rotas protegidas;
2. politicas de burst, debounce, rate limit e cache;
3. configuracao final do pool de banco;
4. reconciliacao do Nginx com o repo.

### Bloco D - Validacao e operacao

1. harness de carga;
2. relatorio antes/depois;
3. checklist de rollout;
4. runbook de degradacao e coleta de evidencias.

## 11. Criterios de priorizacao quando houver disputa de escopo

Se houver conflito entre velocidade e profundidade, a priorizacao correta e:

1. primeiro isolar o Forms do processo HTTP;
2. depois endurecer o runtime HTTP e o health;
3. depois reduzir burst do cliente web de check;
4. depois otimizar hot paths e banco;
5. depois sofisticar edge, rate limit e deploy;
6. por ultimo refinar ergonomia e melhorias nao essenciais.

## 12. Resultado esperado ao final do programa

Ao final deste programa, o projeto deve ter:

1. API HTTP protegida contra contaminacao por worker pesado;
2. runtime de producao compativel com burst legitimo de usuarios;
3. SPA de check menos agressiva e mais eficiente em bootstrap e retomada;
4. observabilidade suficiente para diagnosticar degradacao sem reboot manual imediato;
5. edge e deploy alinhados com o repo;
6. fila, banco e integracoes externas com blast radius controlado;
7. teste de carga que reproduz o caso real de uso da equipe;
8. runbook e alertas para operacao profissional e recorrente.
