# Checklist executavel e priorizado para eliminar o erro 504

## 1. Decisoes obrigatorias antes de iniciar

### Decisao A - IA de transporte entra no programa, mas nao entra no caminho critico do fix imediato

1. A IA de transporte deve entrar neste programa como trilha preventiva e de readiness para producao futura.
2. A IA de transporte nao deve bloquear o fix principal do incidente do web check.
3. A IA de transporte nao deve ser habilitada em producao apenas porque o codigo local existe.
4. Qualquer rollout futuro da IA de transporte deve ficar condicionado a:
   - fila e worker pesado desacoplados do processo HTTP;
   - runtime HTTP endurecido;
   - broker de realtime compativel com multiworker;
   - rate control no dashboard Transport;
   - teste de carga e validacao especificos da superficie `/transport` e `/api/transport/ai/*`.
5. Ate essa trilha preventiva ser concluida, a IA de transporte deve permanecer desabilitada em producao por flag, configuracao ou ausencia deliberada de credenciais e rotas expostas.

### Decisao B - aumentar o droplet ajuda, mas nao substitui a correcao estrutural

1. Aumentar o servidor de `1 GB RAM / 1 vCPU` para `2 GB RAM / 2 vCPU` ajuda de forma material a reduzir o risco imediato de saturacao.
2. Essa ampliacao e recomendada como mitigacao de capacidade e headroom, principalmente porque a stack atual combina Python, Postgres, Nginx, Playwright e Chromium no mesmo host.
3. Esse upgrade nao deve ser tratado como resolucao da causa raiz.
4. Se a arquitetura continuar compartilhando runtime HTTP e trabalho pesado, o sistema ainda pode colapsar em bursts futuros, apenas em um patamar mais alto de carga.
5. Se a IA de transporte vier a ser habilitada depois, `2 GB / 2 vCPU` deve ser tratado como baseline minimo, nao como garantia de folga definitiva.

## 2. Issues tecnicas priorizadas

## Issue P0 - Baseline operacional e coleta forense minima

Ordem de entrega: 1
Prioridade: P0
Objetivo: congelar o estado real do host, do Docker, do Nginx e do runtime antes de qualquer mudanca invasiva.
Rollback: nao aplicavel, porque esta issue e apenas de coleta e comparacao.

## Issue P0A - Mitigacao imediata de capacidade do droplet

Ordem de entrega: 2
Prioridade: P0
Objetivo: adicionar headroom de CPU e RAM para reduzir o risco de nova saturacao enquanto as correcoes estruturais sao implementadas.
Rollback: reverter o tamanho do droplet apenas depois de ao menos uma janela estavel em producao e com comparativo de metricas antes/depois.

## Issue P1 - Observabilidade minima da API, fila e worker

Ordem de entrega: 3
Prioridade: P0
Objetivo: transformar degradacao em algo observavel por rota, fila, banco e container.
Rollback: manter logs e metricas novas; nao remover a instrumentacao, exceto se ela causar regressao funcional comprovada.

## Issue P2 - Desacoplamento do Forms do processo HTTP

Ordem de entrega: 4
Prioridade: P0
Objetivo: impedir que backlog ou lentidao do Forms derrubem login, estado, historico, admin e mobile.
Rollback: voltar temporariamente ao modelo atual apenas se o worker separado impedir processamento de operacao critica e houver fila persistida preservada.

## Issue P3 - Hardening do runtime HTTP e do realtime multiworker

Ordem de entrega: 5
Prioridade: P0
Objetivo: permitir maior concorrencia HTTP sem quebrar SSE, stream e atualizacoes entre workers.
Rollback: voltar para runtime single-process somente se o broker cross-worker nao estiver estavel; se isso ocorrer, manter a reducao de burst e a separacao do Forms ja entregues.

## Issue P4 - Reducao de burst do web check

Ordem de entrega: 6
Prioridade: P0
Objetivo: reduzir a tempestade de requests gerada pela SPA de check em bootstrap, autenticacao, foco e localizacao.
Rollback: reverter apenas os trechos de UX que bloquearem fluxo legitimo; manter toda telemetria de requests criada para comparar antes/depois.

## Issue P5 - Hot paths, pool de banco e firewall do Postgres

Ordem de entrega: 7
Prioridade: P1
Objetivo: reduzir latencia das rotas mais quentes e evitar espera por conexoes ou queries ruins.
Rollback: reverter individualmente query plans, indices ou parametros de pool que mostrem piora de latencia ou bloqueio inesperado.

## Issue P6 - Reconciliacao do edge Nginx e protecao por superficie

Ordem de entrega: 8
Prioridade: P1
Objetivo: alinhar repo e host e aplicar politicas adequadas por rota, classe de cliente e upstream.
Rollback: restaurar imediatamente a configuracao anterior do Nginx a partir de backup validado com `nginx -t` se qualquer mudanca gerar 4xx/5xx anormais ou quebra de roteamento.

## Issue P7 - Hardening preventivo do dashboard Transport e readiness da IA de transporte

Ordem de entrega: 9
Prioridade: P1
Objetivo: impedir que o dashboard Transport ou a futura IA de transporte introduzam novo vetor de saturacao.
Rollback: manter a IA desabilitada em producao e reverter apenas as mudancas de UI que causem regressao operacional no `/transport`.

## Issue P8 - Startup, migracao e deploy sem janelas frageis

Ordem de entrega: 10
Prioridade: P1
Objetivo: remover acoplamento entre migracao, boot HTTP e readiness publica.
Rollback: restaurar o processo anterior de startup apenas se o novo fluxo impedir a subida da stack; nesse caso, manter os artefatos e logs para corrigir o rollout e nao improvisar no host.

## Issue P9 - Harness de reproducao e teste de carga recorrente

Ordem de entrega: 11
Prioridade: P1
Objetivo: provar sob carga que o incidente foi resolvido e nao apenas deslocado.
Rollback: nao aplicavel; a issue produz teste e relatorio, nao altera runtime por si so.

## Issue P10 - Rollout, runbook, alertas e aceite final

Ordem de entrega: 12
Prioridade: P0
Objetivo: colocar as mudancas em producao com checkpoints, rollback e operacao repetivel.
Rollback: executar a matriz de rollback por issue, preservando evidencias e sem rebootar antes da coleta minima definida no runbook.

## 3. Fase 0 - Checklist operacional objetivo para o host DigitalOcean

### Contexto da fase

Objetivo: congelar o baseline do host, do Docker, do Nginx e do runtime efetivo de producao antes das correcoes.

Critero de conclusao: existe um conjunto de evidencias brutas e um resumo consolidado, sem depender de memoria informal.

Critero de rollback: nao aplicavel.

### Prompts executaveis

1. Voce e o agente responsavel por congelar o baseline do incidente no host DigitalOcean. Trabalhe em modo somente coleta: nao reinicie servicos, nao mude configuracoes e nao rode deploy. Acesse o host com o usuario operacional correto e crie um diretorio de evidencias com timestamp, por exemplo `/root/checkcheck_incidents/2026-05-04-504-phase0` ou caminho equivalente aprovado pela equipe. Dentro desse diretorio, salve a saida bruta de `date -u`, `timedatectl`, `uptime`, `hostnamectl`, `uname -a`, `free -m`, `df -h`, `nproc`, `lscpu` e `cat /etc/os-release`. No final, gere um resumo curto explicando timezone ativo, horario de boot, memoria total, CPU total e espaco em disco. Se voce nao tiver acesso SSH neste contexto, nao invente resultados: produza um pacote de comandos pronto para execucao e descreva exatamente quais arquivos de evidencia devem ser devolvidos.

2. Voce e o agente responsavel por congelar o estado do Docker e dos containers de producao. No host, identifique o diretorio real da stack e execute `docker ps --no-trunc`, `docker compose ps`, `docker inspect checkcheck-app-1`, `docker inspect checkcheck-db-1`, `docker logs --tail 500 checkcheck-app-1` e `docker logs --tail 200 checkcheck-db-1`, salvando cada comando em arquivo separado dentro do diretorio de evidencias. Extraia explicitamente de `docker inspect` os campos `State.Status`, `State.Health`, `RestartCount`, `StartedAt`, `FinishedAt`, `OOMKilled` e qualquer detalhe de `Health.Log`. Gere um resumo final dizendo se o app esta `healthy`, `unhealthy`, reiniciando ou apenas vivo sem responder utilmente.

3. Voce e o agente responsavel por congelar a configuracao ativa do Nginx e comparar edge real com repo. No host, execute `nginx -T` e salve a saida integral em arquivo. Em seguida, copie para o relatorio os blocos `server` e `location` que governam `tscode.com.br`, `/api/`, `/checking/user`, `/checking/admin` e `/checking/transport`. Compare essa configuracao ativa com o arquivo versionado `deploy/nginx/checking-edge-routes.conf` do repo. No resultado, responda objetivamente: o host esta roteando para `127.0.0.1:8000`, para `18080/18081/18082/18083`, ou para ambos em configuracoes diferentes? Liste qualquer drift encontrado e marque cada divergencia como `critica`, `importante` ou `cosmetica`.

4. Voce e o agente responsavel por congelar logs e sinais do incidente no edge. Colete a janela relevante dos logs de acesso e erro do Nginx. Salve, no minimo, a saida de comandos equivalentes a `grep ' 504 ' access.log`, `grep 'upstream timed out' error.log`, `tail -n 500 error.log`, `tail -n 500 access.log` e qualquer `journalctl -u nginx` relevante. Se os logs estiverem rotacionados, colete tambem os arquivos rotacionados. Agrupe no relatorio final por rota, host, status, user-agent e IP de origem, destacando especialmente `/checking/user`, `/checking/admin`, `/api/web/check/state`, `/api/mobile/state`, `/api/admin/stream`, `/api/admin/checkin`, `/api/admin/checkout` e `/api/admin/projects`.

5. Voce e o agente responsavel por verificar se a API responde local e publicamente no estado atual do host. Sem alterar nada, execute e salve a saida de `curl -i http://127.0.0.1:8000/api/health`, `curl -i https://tscode.com.br/api/health`, `curl -i https://tscode.com.br/checking/user` e `curl -i https://tscode.com.br/checking/admin`, respeitando cookies ou autenticacao apenas quando a rota exigir. Adicione ao relatorio final a diferenca entre saude local do upstream e saude publica no edge.

6. Voce e o agente responsavel por consolidar a Fase 0 em um unico relatorio versionado no repo, preferencialmente em `docs/incidents/2026-05-04-504-phase0-baseline.md` ou arquivo equivalente aprovado. O relatorio deve conter: linha do tempo minima, topologia ativa, estado dos containers, upstreams reais do Nginx, sinais locais e publicos de saude, e lista objetiva de drifts entre repo e host. Nao proponha correcoes ainda nesta etapa; apenas registre fatos, evidencias e lacunas.

## 4. Fase 0A - Mitigacao imediata de capacidade do droplet

### Contexto da fase

Objetivo: adicionar headroom para reduzir risco enquanto as mudancas estruturais sao implementadas.

Critero de conclusao: existe decisao documentada sobre o resize e validacao tecnica antes/depois.

Critero de rollback: reduzir novamente o tamanho do droplet apenas depois de estabilidade comprovada e com aprovacao operacional.

### Prompts executaveis

1. Voce e o agente responsavel por decidir tecnicamente se o droplet deve ser ampliado imediatamente para `2 GB RAM / 2 vCPU`. Baseie-se nas evidencias da Fase 0, no fato de a stack atual combinar Nginx, Postgres, Python, Playwright e Chromium no mesmo host, e na leitura de risco do incidente. Produza uma nota de decisao curta com tres blocos: `beneficio esperado`, `limite desta mitigacao`, `risco de nao fazer agora`.

2. Voce e o agente responsavel por executar ou preparar a ampliacao do droplet, dependendo do nivel de acesso que tiver. Se tiver acesso ao painel ou CLI da DigitalOcean, documente exatamente o tipo atual do droplet, o tipo alvo, a janela de mudanca, a necessidade ou nao de power cycle, e os passos de validacao pos-mudanca. Se nao tiver acesso, gere um procedimento operacional objetivo para outro executor, incluindo prerequisitos, captura de evidencias antes da mudanca e checklist pos-mudanca.

3. Voce e o agente responsavel por validar o host apos a ampliacao. Depois do resize, repita `free -m`, `nproc`, `lscpu`, `docker compose ps`, `curl -i http://127.0.0.1:8000/api/health` e `curl -i https://tscode.com.br/api/health`, e compare os resultados com a Fase 0. Registre explicitamente se houve efeito colateral em Docker, Nginx, mounts, network ou healthchecks.

## 5. Fase 1 - Observabilidade minima da API, fila, worker e banco

### Contexto da fase

Objetivo: tornar degradacao observavel por rota, fila, processo e banco.

Critero de conclusao: o time consegue identificar rapidamente onde a pressao nasce.

Critero de rollback: reverter apenas instrumentacao que introduzir regressao funcional mensuravel.

### Prompts executaveis

1. Voce e o agente responsavel por adicionar instrumentacao de requests no backend Python. Audite `sistema/app/main.py`, middlewares existentes, routers em `sistema/app/routers/` e o ponto mais apropriado para inserir middleware de request logging estruturado. Implemente logs estruturados contendo, no minimo, `request_id`, `method`, `path`, `status_code`, `latency_ms`, `client_surface`, `authenticated_kind` quando possivel e um marcador se a resposta veio de rota critica. Evite logar segredos, payloads sensiveis ou dados pessoais completos. Depois, descreva como validar a nova telemetria localmente e em producao.

2. Voce e o agente responsavel por adicionar telemetria da fila do Forms e do worker separado ou futuro worker. Audite `sistema/app/services/forms_queue.py`, `sistema/app/services/forms_worker.py`, `sistema/app/main.py` e qualquer model relacionada a `forms_submissions`. Exponha sinais suficientes para responder: quantos itens estao pendentes, quantos estao em processamento, idade do item mais antigo, tempo medio de processamento, total de falhas e total de sucessos. Se a stack atual ainda nao tiver sistema de metricas consolidado, implemente ao menos logs estruturados e endpoints leves de diagnostico que possam ser consultados operacionalmente.

3. Voce e o agente responsavel por expor sinais minimos do banco e do pool de conexoes. Audite `sistema/app/database.py` e as superficies mais quentes da API. Se nao houver sistema pronto de metricas, implemente ao menos logs e um endpoint ou utilitario operacional capaz de reportar saturacao de pool, latencia de query agregada e contagem de conexoes relevantes. Documente quais limites devem virar alerta, mesmo que o alerta final seja configurado em fase posterior.

4. Voce e o agente responsavel por definir o pacote minimo de alertas operacionais que precisa existir antes do rollout principal. Produza uma lista priorizada com thresholds iniciais para `5xx`, latencia p95/p99 por rota critica, backlog da fila do Forms, `unhealthy` do app, `RestartCount` anormal, CPU alta, memoria alta e conexoes de banco elevadas. Se a stack de monitoracao ainda nao estiver pronta, descreva o fallback operacional temporario com comandos e logs a consultar.

## 6. Fase 2 - Desacoplamento do Forms do processo HTTP

### Contexto da fase

Objetivo: retirar Playwright e Chromium do mesmo processo ou container que responde HTTP.

Critero de conclusao: falha ou backlog do Forms nao derruba a API.

Critero de rollback: manter a fila persistida e reverter apenas o wiring entre app e worker se o novo consumo impedir processamento operacional.

### Prompts executaveis

1. Voce e o agente responsavel por mapear o fluxo atual do Forms de ponta a ponta. Audite `sistema/app/routers/device.py`, `sistema/app/routers/mobile.py`, `sistema/app/routers/web_check.py`, `sistema/app/services/forms_submit.py`, `sistema/app/services/forms_queue.py`, `sistema/app/services/forms_worker.py` e `sistema/app/main.py`. Escreva um resumo tecnico objetivo indicando onde a API grava o item de fila, onde o worker e iniciado hoje, quais recursos pesados o worker usa e por que isso amplia blast radius. Nao mude codigo ainda nesta primeira tarefa; apenas documente o desenho atual e o desenho alvo.

2. Voce e o agente responsavel por implementar um worker de Forms separado da API. Escolha a menor mudanca correta que mantenha o contrato atual dos endpoints: a API deve continuar aceitando o evento, persistindo a fila e respondendo rapido, enquanto um processo ou servico separado consome `forms_submissions`. Ajuste `docker-compose.yml`, `Dockerfile` e os entrypoints necessarios para que o worker rode separado do app HTTP. Se a melhor opcao for um novo script de inicializacao ou modulo dedicado, crie-o de forma clara e versionada.

3. Voce e o agente responsavel por revisar a robustez do novo worker. Implemente e valide politica de retentativa, backoff, logs estruturados, reinicio automatico e forma minima de health observavel do worker. O worker nao deve bloquear o app HTTP ao falhar, e o app HTTP nao deve depender do worker para responder rotas criticas. Documente como o backlog deve ser inspecionado em producao.

4. Voce e o agente responsavel por validar a isolacao do Forms. Monte um experimento local ou controlado que gere backlog de `forms_submissions` suficiente para pressionar o worker. Durante esse backlog, prove com evidencias que `/api/health`, login, `/api/web/check/state` e demais rotas quentes continuam respondendo sem degracao comparavel ao incidente. Se a validacao falhar, pare e documente o bloqueador antes de ampliar o escopo.

## 7. Fase 3 - Hardening do runtime HTTP e do realtime multiworker

### Contexto da fase

Objetivo: permitir mais concorrencia HTTP sem quebrar SSE e updates entre workers.

Critero de conclusao: runtime HTTP endurecido e updates cross-worker consistentes.

Critero de rollback: manter single-process temporariamente apenas se o barramento de eventos cross-worker ainda nao estiver seguro.

### Prompts executaveis

1. Voce e o agente responsavel por auditar o runtime HTTP atual e propor o runtime de producao final. Use `Dockerfile`, `docker-compose.yml`, `sistema/app/main.py` e o estado real da producao para responder: quantos workers existem hoje, qual servidor ASGI/WSGI e mais apropriado, como tratar keepalive, timeouts e quantos processos devem existir para `2 GB / 2 vCPU`. Entregue uma proposta objetiva e justificada, com a menor mudanca correta para producao.

2. Voce e o agente responsavel por auditar o realtime atual antes de habilitar multiworker. Leia `sistema/app/services/admin_updates.py`, `sistema/app/routers/admin.py`, `sistema/app/routers/transport.py` e `sistema/app/routers/web_check.py` e identifique toda dependencia de broker em memoria do processo. Se a aplicacao depender hoje de `admin_updates_broker` e `transport_updates_broker` locais ao processo, proponha e implemente um barramento cross-worker adequado, preferencialmente pequeno e operacionalmente simples para a stack do projeto. Se a sua proposta exigir Redis, explicite isso claramente no diff e na documentacao.

3. Voce e o agente responsavel por implementar o novo runtime HTTP de producao de modo compativel com o barramento de eventos escolhido. Ajuste o comando de startup, a imagem, o compose e qualquer documentacao operacional necessaria. Garanta que os fluxos de SSE ou stream do admin, do transport e do web check continuem coerentes quando a aplicacao tiver mais de um processo HTTP.

4. Voce e o agente responsavel por validar consistencia multiworker. Execute um teste controlado com mais de um processo HTTP, abra sessoes do admin e do transport, gere eventos que publiquem updates e prove que as telas continuam recebendo refresh coerente mesmo quando as requests caem em workers diferentes. Se nao conseguir provar isso, nao autorize rollout do multiworker.

## 8. Fase 4 - Healthcheck, readiness e auto-recuperacao reais

### Contexto da fase

Objetivo: detectar degradacao util e sair dela sem reboot manual imediato.

Critero de conclusao: health, readiness e restart passam a representar o estado real da aplicacao.

Critero de rollback: restaurar healthcheck anterior apenas se o novo modelo gerar falso positivo severo e indisponibilidade operacional, preservando logs e evidencias.

### Prompts executaveis

1. Voce e o agente responsavel por redefinir a semantica de saude da aplicacao. Audite o endpoint atual `/api/health`, o `healthcheck` do `docker-compose.yml`, o comando de startup e as dependencias essenciais do app. Proponha um modelo claro de `liveness`, `readiness` e `degraded`, mesmo que a stack atual implemente isso por aproximacao pratica. Seja explicito sobre o que precisa ser considerado indispensavel para o app estar apto a receber trafego.

2. Voce e o agente responsavel por implementar healthchecks mais fieis ao estado real do sistema. Ajuste o endpoint de health e o compose para que o app nao pareca saudavel quando estiver vivo, mas incapaz de responder utilmente. Trate a API HTTP e o worker de Forms como componentes diferentes: a falha do worker nao deve mascarar a saude da API, mas tambem nao pode ficar invisivel.

3. Voce e o agente responsavel por definir a auto-recuperacao operacional. Documente e, quando a stack permitir, implemente a estrategia de restart ou remediacao automatica para estados `unhealthy` sustentados, incluindo limites para evitar loops cegos. O resultado deve dizer claramente quando reiniciar apenas o worker, quando reiniciar a API e quando parar para coleta de evidencias antes de qualquer reboot maior.

## 9. Fase 5 - Reducao de burst da SPA de check

### Contexto da fase

Objetivo: diminuir a tempestade de requests gerada pela superficie `sistema/app/static/check`.

Critero de conclusao: queda material de requests por usuario e por fluxo de uso.

Critero de rollback: reverter apenas ajustes de UX que quebrem uso legitimo; manter telemetria para comparar o impacto real.

### Prompts executaveis

1. Voce e o agente responsavel por mapear o grafo de requests da SPA de check. Audite `sistema/app/static/check/app.js` e identifique, com nomes de funcoes e endpoints, tudo que dispara requests em bootstrap, restauracao de sessao, verificacao de senha, `focus`, `pageshow`, `visibilitychange`, localizacao e submit. Entregue uma matriz `evento -> funcao -> endpoint -> frequencia esperada -> risco de burst` antes de alterar o codigo.

2. Voce e o agente responsavel por reduzir tempestade de autenticacao. Trabalhe sobre `refreshAuthenticationStatus`, `schedulePasswordVerification`, `attemptPasswordLogin`, `loadAuthenticatedApplication` e qualquer fluxo de autofill/autologin equivalente em `sistema/app/static/check/app.js`. A meta e impedir login silencioso repetitivo, validacao parcial agressiva e loops desnecessarios quando muitos usuarios digitam ou retornam a tela. Preserve a UX funcional, mas privilegie estabilidade operacional.

3. Voce e o agente responsavel por reduzir tempestade de lifecycle e localizacao. Trabalhe sobre `runLifecycleUpdateSequence`, `updateLocationForLifecycleSequence`, `ensureLocationReadyForSubmit`, `refreshHistory` e os listeners de `visibilitychange`, `focus` e `pageshow`. Introduza deduplicacao, cooldown mais inteligente, cache local com invalidacao clara, e evite reconsultas redundantes de historico e localizacao quando nao houver mudanca real de estado.

4. Voce e o agente responsavel por validar a reducao de burst da SPA. Monte uma medicao antes/depois com contagem de requests por usuario em pelo menos estes cenarios: abrir o QR Code, autenticar, voltar da tela bloqueada, alternar abas, conceder localizacao e registrar check-in/check-out. O relatorio deve mostrar claramente quais endpoints foram mais aliviados.

## 10. Fase 6 - Hot paths do backend, pool de banco e firewall do Postgres

### Contexto da fase

Objetivo: reduzir custo das rotas quentes e impedir saturacao por pool ou banco.

Critero de conclusao: rotas quentes melhoram de forma mensuravel e o banco deixa de ser amplificador oculto.

Critero de rollback: reverter ajustes isolados de query, indice ou pool que piorarem latencia ou bloqueio.

### Prompts executaveis

1. Voce e o agente responsavel por auditar e otimizar as rotas quentes do backend. Comece por `/api/web/check/state`, `/api/mobile/state`, `/api/admin/checkin`, `/api/admin/checkout` e `/api/admin/projects`. Audite routers, services, serializacao e queries correspondentes. Corrija repeticoes, N+1, joins caros, serializacao excessiva e qualquer trabalho desnecessario por request. Se um endpoint estiver fazendo mais do que o necessario para bootstrap, considere separar leituras especializadas.

2. Voce e o agente responsavel por endurecer o pool de conexoes e a camada de acesso ao banco. Audite `sistema/app/database.py`, a configuracao atual de `create_engine`, o `max_connections=40` do Postgres em `docker-compose.yml` e o padrao real de concorrencia esperado. Proponha e implemente parametros explicitos de pool, overflow, timeout e reciclagem, com justificativa tecnica. Nao escolha valores arbitrarios; conecte a decisao ao tamanho do host e ao numero alvo de workers/processos.

3. Voce e o agente responsavel por reduzir risco operacional do Postgres exposto. Verifique se a porta `5432` esta de fato acessivel externamente, avalie o ruido ja observado com o usuario inexistente `reader` e proponha a menor mudanca correta para fechar ou restringir esse acesso. Se a mudanca envolver host, firewall ou compose, documente exatamente onde o controle deve viver e como validar que o app interno continua funcionando.

4. Voce e o agente responsavel por validar os ganhos de backend e banco. Rode mediacoes de latencia p50, p95 e p99 das rotas quentes, e registre o uso de conexoes de banco antes e depois das mudancas. Se algum ajuste melhorar uma rota e piorar outra, documente o tradeoff explicitamente antes de seguir.

## 11. Fase 7 - Reconciliacao do edge Nginx e protecao por superficie

### Contexto da fase

Objetivo: alinhar repo e host e aplicar politicas de edge coerentes com o novo runtime.

Critero de conclusao: configuracao ativa do host coincide com a configuracao versionada e com a topologia final.

Critero de rollback: restaurar backup da configuracao anterior e validar com `nginx -t` antes de reload se qualquer teste falhar.

### Prompts executaveis

1. Voce e o agente responsavel por reconciliar o Nginx real com o repo. Use o `nginx -T` capturado na Fase 0 e compare com `deploy/nginx/checking-edge-routes.conf`. Defina a topologia final de upstreams e documente explicitamente se a producao deve continuar com `127.0.0.1:8000`, migrar para `18080/18081/18082/18083` ou adotar outra forma clara e versionada. Nao aceite drift manual como estado final.

2. Voce e o agente responsavel por endurecer o edge por classe de superficie. Revise `proxy_read_timeout`, `proxy_connect_timeout`, buffering, keepalive e politicas distintas para API, HTML, SSE/stream e autenticacao. Introduza protecao de burst ou rate limit nas superficies mais sensiveis, sem quebrar uso legitimo da equipe. Toda politica nova deve vir acompanhada de justificativa e plano de validacao.

3. Voce e o agente responsavel por validar o edge final. Gere backup da configuracao anterior, rode `nginx -t`, aplique reload seguro, teste `curl` local e publico para `/api/health`, `/checking/user`, `/checking/admin` e `/checking/transport`, e confirme que a configuracao ativa no host voltou a coincidir com o repo. Registre qualquer dependencia manual que ainda restar e trate isso como debito a eliminar, nao como solucao definitiva.

## 12. Fase 8 - Hardening preventivo do dashboard Transport e readiness da IA de transporte

### Contexto da fase

Objetivo: evitar que o dashboard Transport ou a futura IA introduzam novo vetor de saturacao.

Critero de conclusao: o `/transport` fica mais eficiente e a IA futura permanece sob gate de seguranca.

Critero de rollback: manter a IA desabilitada e reverter apenas mudancas de dashboard que causem regressao funcional comprovada.

### Prompts executaveis

1. Voce e o agente responsavel por auditar o comportamento de rede do dashboard Transport. Trabalhe em `sistema/app/static/transport/app.js` e foque, no minimo, nestas funcoes ou trechos: `requestDashboardRefresh`, `startRealtimeUpdates`, `scheduleTransportVerification`, `loadDashboard`, qualquer `authVerifyTimer`, qualquer `realtimeRefreshTimer` e qualquer `aiRoutePollingTimer`. O objetivo e identificar duplicacao de `loadDashboard`, tempestade de verificacao de credenciais, refresh redundante por SSE e polling de IA desnecessario. Entregue primeiro um mapa `gatilho -> endpoint -> risco -> proposta de mitigacao`.

2. Voce e o agente responsavel por implementar mitigacoes no dashboard Transport sem degradar operacao. Introduza deduplicacao de requests em voo, cancelamento ou coalescencia de refreshs redundantes, pausa de polling quando a aba estiver invisivel, backoff de reconexao para SSE, e guardas para evitar que uma enxurrada de eventos dispare varios `loadDashboard` seguidos. Preserve a funcionalidade do dashboard, mas privilegie estabilidade do backend.

3. Voce e o agente responsavel por endurecer a verificacao de autenticacao do dashboard Transport. Revise os listeners de `authKeyInput` e `authPasswordInput`, a funcao `scheduleTransportVerification` e o fluxo de `bootstrapTransportSession`. Garanta que o dashboard nao dispare verificacoes agressivas por tecla pressionada e que transientes de input nao limpem a sessao de forma precipitada. Se houver risco de burst de `/api/transport/auth/verify`, reduza isso sem quebrar a UX.

4. Voce e o agente responsavel por preparar a IA de transporte para producao futura sem habilita-la prematuramente. Audite `sistema/app/routers/transport_ai.py`, `sistema/app/services/transport_ai_agent.py`, o polling de `route-calculations` no dashboard e qualquer config relacionada. Mantenha a IA desabilitada por default em producao e implemente, se necessario, guardas explicitas para que a superficie `/api/transport/ai/*` nao entre ativa sem: flag operacional habilitada, recursos aprovados, timeouts definidos, limite de concorrencia e validacao de carga dedicada. Se o codigo ja tiver flag existente, reutilize-a; nao crie outra sem motivo forte.

5. Voce e o agente responsavel por validar o dashboard Transport apos o hardening preventivo. Abra multiplas abas do `/transport`, simule eventos de stream, verificacao de auth e refresh de dashboard, e prove que o numero de requests caiu ou se manteve sob controle. Se a IA estiver desabilitada, prove tambem que o dashboard nao fica fazendo polling de rotas de IA por acidente.

## 13. Fase 9 - Startup, migracao e deploy sem janelas frageis

### Contexto da fase

Objetivo: remover acoplamento entre migracao, boot HTTP e exposure do edge.

Critero de conclusao: deploy e reboot ficam previsiveis e seguros.

Critero de rollback: restaurar o processo anterior apenas se o novo fluxo impedir subida da stack, preservando evidencias e corrigindo o mecanismo antes da proxima tentativa.

### Prompts executaveis

1. Voce e o agente responsavel por revisar o startup atual do app. Audite o `Dockerfile`, `docker-compose.yml` e qualquer script de deploy relevante. O comando atual faz `alembic upgrade head && uvicorn ...`; avalie o risco disso e implemente o desenho final mais seguro, preferencialmente separando migracao de processo HTTP ou, no minimo, tornando a readiness publica dependente da conclusao real do boot.

2. Voce e o agente responsavel por endurecer o deploy. Garanta que o fluxo de rollout tenha checkpoints claros: build, migracao, subida do runtime HTTP, validacao local do health, validacao publica do health e so entao exposicao total do trafego. Se existir workflow em `.github/workflows/` ou scripts em `deploy/`, atualize-os para refletir esse desenho e elimine qualquer dependencia manual fora do repo.

3. Voce e o agente responsavel por definir rollback de deploy. Para cada mudanca de runtime, edge, worker e startup, documente o passo exato de reversao, o teste que confirma rollback valido e a evidenca que precisa ser preservada antes de reverter. Nao aceite rollback implicito ou baseado em memoria da equipe.

## 14. Fase 10 - Harness de reproducao e teste de carga recorrente

### Contexto da fase

Objetivo: provar que o incidente foi resolvido sob carga semelhante ao caso real.

Critero de conclusao: teste repetivel aprovado com evidencias antes/depois.

Critero de rollback: nao aplicavel diretamente; o resultado do teste governa rollout e ajustes adicionais.

### Prompts executaveis

1. Voce e o agente responsavel por criar um harness de carga para o caso real do incidente. O foco principal deve ser a superficie web de check, simulando um grupo de usuarios abrindo o QR Code, registrando ou autenticando chave/senha, consultando estado, processando localizacao e realizando check-in/check-out em janelas curtas. Escolha a ferramenta mais apropriada para o repo e para a stack do projeto, mas entregue uma execucao repetivel, documentada e com parametros ajustaveis.

2. Voce e o agente responsavel por criar cenarios complementares de carga para superfices relacionadas. Inclua, quando fizer sentido, consultas simultaneas de admin e dashboard Transport, e um experimento separado de backlog do Forms para comprovar que a API nao degrada mesmo com o worker ocupado. Nao misture tudo num unico teste cego; produza cenarios isolados e um cenario integrado.

3. Voce e o agente responsavel por produzir um relatorio antes/depois. O relatorio deve conter, no minimo, throughput, erro, latencia p50/p95/p99, uso de CPU, memoria, conexoes de banco e backlog de fila para o baseline atual e para a arquitetura corrigida. Se algum cenario ainda falhar, pare o rollout e aponte exatamente em qual fase o bloqueador precisa ser retomado.

## 15. Fase 11 - Rollout, runbook, alertas e aceite final

### Contexto da fase

Objetivo: colocar a correcao em producao com ordem, rollback e operacao repetivel.

Critero de conclusao: producao atualizada, validada e com runbook claro.

Critero de rollback: executar rollback por issue e por onda de rollout, sem improvisar reboot e sem perder evidencias.

### Prompts executaveis

1. Voce e o agente responsavel por montar a ordem final de rollout. Use as issues priorizadas deste documento para propor ondas de entrega pequenas e seguras. A ordem minima recomendada e: `P0`, `P0A`, `P1`, `P2`, `P3`, `P4`, `P5`, `P6`, `P7`, `P8`, `P9`, `P10`. Para cada onda, descreva objetivo, prerequisitos, metricas que devem ficar verdes e criterio de abortar ou reverter.

2. Voce e o agente responsavel por escrever o runbook operacional final. O runbook precisa responder objetivamente: como verificar saude do host, da API, do worker de Forms, do Nginx, do banco e do dashboard Transport; quando reiniciar apenas o worker; quando reiniciar a API; quando coletar evidencias antes de qualquer reboot; como validar se o edge esta em drift; e onde consultar metricas e logs introduzidos nas fases anteriores.

3. Voce e o agente responsavel por definir alertas e thresholds finais. Transforme os sinais criados nas fases anteriores em uma lista operacional de alertas obrigatorios, com severidade, janela, threshold e acao esperada. Inclua, no minimo, `5xx` por rota critica, backlog da fila do Forms, `unhealthy` do app, latencia alta sustentada, CPU alta sustentada, memoria alta sustentada e crescimento de conexoes de banco.

4. Voce e o agente responsavel por emitir o aceite final tecnico. Antes de declarar o problema resolvido, produza um documento curto com: o que mudou, quais evidencias sustentam a resolucao, quais riscos residuais permanecem, qual foi o ganho do upgrade do droplet, por que a IA de transporte continuou desabilitada ou em gate, e qual seria o gatilho tecnico para reabrir este programa.

## 16. Regra de uso desta checklist por outro agente

1. Execute as fases na ordem definida, salvo bloqueio tecnico documentado.
2. Nao pule a Fase 0 nem a Fase 1.
3. Nao habilite multiworker sem tratar o realtime cross-worker.
4. Nao habilite a IA de transporte em producao antes da Fase 8 e da Fase 10.
5. Nao trate o upgrade do droplet como resolucao da causa raiz.
6. Nao use reboot do host como primeiro passo de mitigacao sem coletar as evidencias minimas desta checklist.
7. A cada fase, produza diff, validacao e criterio de rollback no proprio relatorio da fase.

## 17. Resultado esperado ao final desta checklist

1. A API deixa de compartilhar blast radius com o processamento pesado do Forms.
2. O runtime HTTP fica apto a burst legitimo com observabilidade e auto-recuperacao melhores.
3. A SPA de check deixa de gerar tempestade desnecessaria de requests.
4. O dashboard Transport fica endurecido contra polling, refresh redundante e riscos futuros da IA.
5. O banco, o edge e o deploy ficam alinhados com o uso real e com o repo.
6. O time ganha runbook, alertas e harness de reproducao para nao depender de reboot e intuicao.