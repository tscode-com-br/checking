# To-do list robusta para corrigir IA Settings do Transport e migrar a chave por projeto

## 0. Diagnostico confirmado no codigo atual

1. O erro mostrado no modal, `A criptografia dos IA Settings nao esta disponivel.`, nao depende do provedor escolhido. Ele e disparado pelo backend quando a chave mestra de criptografia `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY` nao esta configurada ou esta invalida.
2. A persistencia atual dos IA Settings e global para todo o sistema. O servico usa `db.get(TransportAILlmSettings, 1)`, portanto so existe um unico registro de configuracao compartilhado entre todos os projetos.
3. O contrato atual de API de IA Settings nao recebe `project_id`. Hoje o request aceita apenas `provider` e `api_key`.
4. O runtime atual da IA resolve uma unica credencial por execucao. Isso conflita com a nova exigencia de usar uma chave diferente por projeto.
5. O dashboard Transport ja carrega o catalogo completo de projetos cadastrados em `Admin > Projetos` dentro de `TransportDashboardResponse.projects`, e o backend tambem ja expoe `GET /api/transport/projects`.
6. Nao podemos usar o nome do projeto como chave de vinculacao da configuracao. O projeto pode ser renomeado no Admin, e ja existem outros vinculos operacionais no sistema que sofrem com rename por nome. A referencia estavel para IA Settings deve ser `project_id`.

## 1. Resultado esperado

1. O modal `IA SETTINGS` deve permitir escolher um projeto cadastrado e editar a configuracao daquele projeto.
2. Cada projeto deve armazenar seu proprio provedor e sua propria API key criptografada no banco.
3. Nenhuma API key pode aparecer em texto puro em resposta HTTP, log, auditoria, traceback ou JSON persistido de UI.
4. A IA deve resolver a credencial correta para cada projeto usado durante a execucao.
5. Quando a chave mestra de criptografia estiver ausente ou invalida, o sistema deve falhar de forma controlada e diagnostica, sem aparentar problema no provedor.
6. Renomear um projeto no Admin nao pode quebrar o vinculo da configuracao de IA.

## 2. Decisoes obrigatorias antes de codar

1. Fechar o contrato de selecao do projeto no modal.
   Recomendacao: adicionar um seletor explicito de projeto no modal de IA Settings e sempre enviar `project_id` ao backend.
2. Fechar a politica de runtime para execucoes com multiplos projetos.
   Recomendacao: resolver credencial por particao/projeto durante a execucao da IA, em vez de continuar usando uma credencial global por run.
3. Fechar a politica de auditoria para runs multi-projeto.
   O modelo atual de `TransportAIRun` guarda `llm_provider`, `llm_model` e `llm_reasoning_effort` em nivel de run. Isso deixa de ser suficiente se uma unica execucao puder usar configuracoes diferentes por projeto.
4. Fechar a politica de migracao do legado.
   Recomendacao: nao copiar automaticamente a chave global atual para todos os projetos. Essa copia em massa seria ambigua e insegura. A migracao deve ser explicita por projeto ou via script controlado.
5. Fechar a politica de exclusao de projeto.
   Recomendacao: usar `project_id` com foreign key e definir comportamento claro para delete, preferencialmente limpeza automatica das configuracoes sensiveis daquele projeto e preservacao apenas da auditoria historica.

## 3. Fase 0 - Corrigir a causa imediata do erro de criptografia

### Objetivo

Eliminar o erro atual de ambiente e deixar a falta da chave mestra claramente detectavel antes de o usuario tentar salvar o modal.

### Checklist

- [ ] Confirmar onde `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY` deve ser fornecida em desenvolvimento, teste, homologacao e producao.
- [ ] Garantir que a variavel esteja presente na stack real de execucao do backend que atende `PUT /api/transport/ai/settings`.
- [ ] Documentar como gerar uma chave valida de Fernet para o ambiente.
- [ ] Adicionar validacao de bootstrap, healthcheck ou preflight para detectar chave ausente/invalida antes da tentativa de salvar IA Settings.
- [ ] Revisar a mensagem operacional devolvida ao frontend para diferenciar claramente falha de configuracao do servidor versus erro de provedor.
- [ ] Atualizar deploy docs, `.env` de exemplo, compose, secrets ou pipeline onde a configuracao e injetada.
- [ ] Validar manualmente que OpenAI e DeepSeek deixam de acusar o erro de criptografia quando a chave mestra esta correta.

### Criterio de aceite

1. Com a chave mestra configurada corretamente, o salvamento de IA Settings nao retorna mais `A criptografia dos IA Settings nao esta disponivel.`.
2. Sem a chave mestra, o sistema falha cedo e de forma explicita, sem depender do usuario descobrir isso pelo modal.

## 4. Fase 1 - Redesenhar a persistencia para configuracao por projeto

### Objetivo

Trocar a persistencia global atual por uma persistencia por projeto, criptografada e vinculada por `project_id`.

### Checklist de modelagem

- [ ] Criar uma nova estrutura de persistencia por projeto.
  Recomendacao: criar tabela nova, por exemplo `transport_ai_project_llm_settings`, em vez de reaproveitar a tabela singleton atual sem transicao clara.
- [ ] Incluir no schema persistido, no minimo:
  - `id`
  - `project_id`
  - `provider`
  - `model_name`
  - `reasoning_effort`
  - `api_key_ciphertext`
  - `api_key_last4`
  - `updated_by_admin_id`
  - `created_at`
  - `updated_at`
- [ ] Usar `project_id` com foreign key para `projects.id`.
- [ ] Criar `UNIQUE(project_id)` para garantir uma configuracao ativa por projeto.
- [ ] Decidir se e necessario armazenar `encryption_key_version` para futura rotacao de chave. Se ficar fora do escopo agora, registrar explicitamente como debito tecnico.
- [ ] Definir comportamento de delete do projeto.
  Recomendacao: limpar a configuracao sensivel do projeto ao excluir o projeto, preservando apenas auditoria e historico imutavel.

### Checklist de migracao Alembic

- [ ] Criar migration nova para a tabela por projeto.
- [ ] Nao destruir a tabela global antiga no mesmo passo sem ter uma estrategia de transicao.
- [ ] Se houver necessidade de backfill, criar script controlado que exija mapeamento explicito de projetos de destino.
- [ ] Adicionar downgrade seguro para a migration.
- [ ] Garantir compatibilidade com SQLite de testes e com o banco real de producao.

### Criterio de aceite

1. E possivel persistir dois projetos diferentes com provedores e chaves diferentes sem sobrescrita cruzada.
2. Renomear o projeto no Admin nao quebra o vinculo da configuracao.

## 5. Fase 2 - Refatorar servicos backend para `project_id`

### Objetivo

Fazer o backend tratar IA Settings como recurso por projeto em toda a camada de servico.

### Checklist

- [ ] Refatorar `get_transport_ai_llm_settings` para buscar por `project_id`, nao mais por `id=1`.
- [ ] Refatorar `get_transport_ai_llm_settings_payload` para exigir `project_id` e incluir metadados uteis do projeto quando fizer sentido.
- [ ] Refatorar `upsert_transport_ai_llm_settings` para exigir `project_id` e validar existencia do projeto.
- [ ] Refatorar `resolve_transport_ai_llm_runtime_settings` para exigir `project_id`.
- [ ] Garantir que a criptografia continue sendo feita apenas via Fernet com a chave mestra de ambiente.
- [ ] Preservar a regra atual de exigir nova API key quando o provedor do projeto mudar.
- [ ] Preservar a regra de nao apagar a chave existente quando o provedor nao mudar e o campo vier vazio.
- [ ] Criar erros controlados para:
  - projeto inexistente
  - projeto sem configuracao de IA
  - projeto sem API key configurada
  - chave mestra ausente ou invalida
  - provedor nao suportado
- [ ] Atualizar sanitizacao para nunca vazar `payload.api_key` nem ciphertext em erros por projeto.

### Criterio de aceite

1. O backend consegue salvar, ler e resolver runtime settings de dois projetos independentes no mesmo banco.
2. Um projeto nunca le nem sobrescreve a chave de outro projeto.

## 6. Fase 3 - Atualizar o contrato da API de IA Settings

### Objetivo

Alterar o contrato HTTP para operar explicitamente por projeto.

### Checklist

- [ ] Definir o shape final da API.
  Recomendacao: `GET /api/transport/ai/settings?project_id=<id>` e `PUT /api/transport/ai/settings` com `project_id` no body.
- [ ] Atualizar `TransportAISettingsUpdateRequest` para incluir `project_id`.
- [ ] Avaliar se `TransportAISettingsResponse` deve incluir `project_id` e `project_name` para facilitar sincronizacao do frontend.
- [ ] Garantir validacao de `project_id > 0`.
- [ ] Se o usuario de Transport puder ter escopo limitado no futuro, definir e implementar autorizacao server-side para impedir edicao fora do escopo.
- [ ] Atualizar a OpenAPI gerada e qualquer documentacao interna do contrato.
- [ ] Atualizar mensagens e status HTTP para refletir erros por projeto.

### Criterio de aceite

1. O request de save sempre informa qual projeto esta sendo configurado.
2. O GET de IA Settings sempre retorna a configuracao do projeto solicitado, nunca uma configuracao global implicita.

## 7. Fase 4 - Atualizar o modal `IA SETTINGS` no frontend do Transport

### Objetivo

Permitir que o usuario escolha o projeto certo e visualize/salve a configuracao daquele projeto sem ambiguidade.

### Checklist de UX e estado

- [ ] Adicionar seletor de projeto no modal `IA SETTINGS`.
- [ ] Popular o seletor usando o catalogo ja existente em `state.dashboard.projects` e manter fallback para `GET /api/transport/projects` se necessario.
- [ ] Armazenar no state do frontend o `selectedProjectId` do modal.
- [ ] Carregar a configuracao do projeto selecionado ao abrir o modal e ao trocar o projeto no seletor.
- [ ] Enviar `project_id` no payload de save.
- [ ] Exibir claramente quando o projeto ainda nao possui chave configurada.
- [ ] Exibir o `api_key_hint` mascarado do projeto correto, sem reaproveitar hint de outro projeto.
- [ ] Garantir que trocar de projeto nao reutilize draft, hint ou feedback de outro projeto por engano.
- [ ] Decidir comportamento inicial do seletor.
  Recomendacao: selecionar o primeiro projeto disponivel do catalogo ou o ultimo projeto usado pelo usuario, desde que isso fique explicito na UI.
- [ ] Atualizar traducoes em `i18n.js` para textos por projeto, inclusive erros controlados.
- [ ] Manter o modal aberto em caso de erro e preservar o contexto do projeto selecionado.

### Checklist de UX negativa

- [ ] Tratar catalogo vazio de projetos.
- [ ] Tratar projeto removido enquanto o modal esta aberto.
- [ ] Tratar falha de carga da configuracao do projeto.
- [ ] Tratar falta de permissao ou sessao expirada sem perder o contexto local.

### Criterio de aceite

1. O usuario consegue alternar entre dois projetos e ver feedback/hint diferentes para cada um.
2. Salvar o projeto A nao altera nem o hint nem o provedor do projeto B.

## 8. Fase 5 - Resolver runtime da IA por projeto durante a execucao

### Objetivo

Garantir que a execucao da IA use a credencial correta do projeto correspondente em tempo de runtime.

### Checklist funcional

- [ ] Mapear todos os pontos onde o runtime da IA assume uma unica configuracao global.
- [ ] Propagar `project_id` para a camada de planejamento e para as particoes que ja sao montadas por projeto.
- [ ] Resolver credenciais por projeto durante a execucao, nao apenas no modal.
- [ ] Garantir que cada particao use o provedor/modelo/chave do projeto correspondente.
- [ ] Se algum projeto referenciado na execucao nao tiver configuracao valida, falhar antes de chamar o provedor externo.
- [ ] Criar mensagem de preflight clara para projetos sem IA Settings ou sem API key configurada.

### Checklist de snapshot e historico

- [ ] Revisar `TransportAIRun`, suggestion payloads e endpoints que hoje assumem um unico `llm_provider`, `llm_model` e `llm_reasoning_effort` por run.
- [ ] Definir como persistir o snapshot por projeto/particao.
  Recomendacao: adicionar um campo JSON de snapshot por particao ou estrutura equivalente, em vez de depender apenas dos campos globais atuais.
- [ ] Atualizar payloads de resposta para nao mentirem quando uma run usar mais de um projeto com configuracoes diferentes.
- [ ] Manter a garantia de imutabilidade historica: uma sugestao salva deve continuar mostrando o snapshot efetivamente usado na hora da geracao, mesmo se o projeto trocar a chave depois.

### Criterio de aceite

1. Uma execucao que envolva projetos diferentes usa a credencial certa de cada projeto.
2. O historico da IA continua auditavel e nao perde o snapshot efetivo usado por projeto.

## 9. Fase 6 - Endurecer seguranca, logs e auditoria

### Objetivo

Garantir que o novo fluxo por projeto continue seguro e auditavel.

### Checklist

- [ ] Garantir que nenhuma API key em texto puro apareca em:
  - responses
  - mensagens de erro
  - `check_events`
  - logs estruturados
  - JSON de snapshots
  - exceptions sanitizadas
- [ ] Incluir `project_id` e `project_name` nas auditorias de sucesso e falha de `settings_update`.
- [ ] Manter apenas `api_key_hint` mascarado nas auditorias.
- [ ] Revisar rollback de sessao em caso de excecao durante save para nao persistir linha parcial antes do evento de falha.
- [ ] Atualizar observabilidade para permitir diagnosticar rapidamente qual projeto falhou, sem expor segredo.

### Criterio de aceite

1. Auditorias mostram projeto, provedor e hint mascarado, mas nunca o segredo bruto.
2. Falhas de criptografia e validacao continuam sanitizadas tambem no fluxo por projeto.

## 10. Fase 7 - Testes automatizados e validacao manual

### Testes backend obrigatorios

- [x] Atualizar `tests/test_transport_ai_llm_settings.py` para cobrir persistencia por projeto.
- [x] Adicionar teste de migracao Alembic para a nova tabela por projeto.
- [x] Atualizar `tests/test_transport_ai_router.py` para `GET/PUT /api/transport/ai/settings` com `project_id`.
- [x] Cobrir sucesso, projeto inexistente, provider change, projeto sem chave, projeto sem configuracao e erro de criptografia.
- [x] Adicionar teste de isolamento: salvar projeto A e garantir que projeto B nao foi alterado.
- [x] Adicionar teste de rename de projeto sem perda do vinculo por `project_id`.
- [x] Adicionar teste de delete do projeto conforme a politica definida.

### Testes runtime/agent obrigatorios

- [x] Atualizar `tests/test_transport_ai_runtime.py` e `tests/test_transport_ai_agent_runtime.py` para resolver configuracao por projeto.
- [x] Cobrir execucao com multiplos projetos e chaves diferentes.
- [x] Cobrir falha controlada quando um dos projetos da run nao tiver configuracao valida.
- [x] Atualizar testes que validam snapshot de `llm_provider` para refletir modelo por projeto/particao.

### Testes frontend obrigatorios

- [x] Atualizar `tests/transport_page_date.test.js` para o novo seletor de projeto no modal.
- [x] Cobrir abertura do modal com projetos disponiveis.
- [x] Cobrir troca de projeto carregando hints diferentes.
- [x] Cobrir save enviando `project_id`, `provider` e `api_key` corretamente.
- [x] Cobrir erro de criptografia mantendo modal aberto no projeto atual.
- [x] Cobrir erro de carga ao trocar projeto.
- [x] Cobrir isolamento visual entre projeto A e projeto B.

### Validacao manual obrigatoria

Status desta rodada: validacao manual concluida em previews limpos e isolados. No preview `http://127.0.0.1:8010/transport`, usando `preview_transport_ai_manual.db`, `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY` com chave Fernet valida, `TRANSPORT_AI_ROUTE_PROVIDER=fake` e `MAPBOX_ACCESS_TOKEN=test-mapbox-token`, o seed `scripts/seed_transport_ai_preview_validation.py` criou os projetos `AI14 Preview Apply` e `AI14 Preview Cancel`, o modal `AI Settings` abriu corretamente, a chave OpenAI foi salva com hint mascarado apenas no projeto configurado, a troca para o projeto sem chave nao herdou hint anterior, o fluxo `Calculate Routes` retornou sugestao pronta para revisao e o comando `Apply` respondeu com sucesso. No preview `http://127.0.0.1:8012/transport`, usando `preview_transport_ai_deepseek.db`, a chave DeepSeek temporaria foi salva para `AI14 Preview Cancel` e o hint mascarado `***367a` foi confirmado no projeto correto, sem vazar para os demais. Para fechar a validacao end-to-end do provider DeepSeek com chamada real, o preview `http://127.0.0.1:8013/transport`, usando `preview_transport_ai_deepseek_apply.db` com a mesma chave Fernet e preflight local, salvou a mesma chave temporaria para `AI14 Preview Apply`; o fluxo `Calculate Routes` retornou `201 Created` no backend com sugestao pronta para revisao e o comando `Apply` respondeu com sucesso, refletindo a atribuicao final do request no dashboard.

- [x] Criar ao menos dois projetos de teste no Admin.
- [x] Configurar OpenAI para um projeto e DeepSeek para outro.
- [x] Abrir o modal, alternar entre os dois e confirmar hints/provider independentes.
- [x] Executar fluxo de IA para requests que atinjam cada projeto e validar que o runtime usa a credencial esperada.
- [x] Validar que logs e auditorias nao vazam segredos nas superficies exercitadas desta rodada.

## 11. Fase 8 - Migracao operacional e rollout

### Objetivo

Subir a mudanca sem perder a rastreabilidade do legado e sem deixar projeto aparentemente configurado quando ainda nao estiver.

### Checklist

- [ ] Gerar e configurar `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY` no ambiente real antes do rollout funcional.
- [ ] Rodar migration do banco.
- [ ] Exportar a configuracao global legada apenas para consulta/rollback, sem reaplicar automaticamente em todos os projetos.
- [ ] Executar backfill controlado somente nos projetos aprovados pela operacao.
- [ ] Validar smoke test no modal de IA Settings apos deploy.
- [ ] Validar smoke test de execucao da IA com ao menos um projeto por provedor suportado.
- [ ] Decidir quando remover definitivamente o caminho legado global.
- [x] Atualizar runbook de deploy e de troubleshooting.

Status desta rodada: artefatos operacionais do rollout preparados no repositório. O exemplo de produção em `deploy/.env.production.example` agora documenta a exigência de manter `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY` estável durante a janela de migração; o export do singleton legado ficou automatizado em `scripts/export_transport_ai_legacy_llm_settings.py`; o backfill explícito por `project_id` ficou automatizado em `scripts/backfill_transport_ai_project_llm_settings.py`; e o runbook detalhado foi consolidado em `docs/context/transport_ai_project_rollout.md`, com integração no documento geral `docs/context/operacao_rollback_deploy_separado.md`. A validação automatizada desta rodada executou `pytest tests/test_transport_ai_rollout_scripts.py -q` com `4 passed`. Os itens que ainda dependem de acesso ao ambiente real continuam operacionais: configurar o segredo no host, rodar o deploy/migration produtivo, executar o smoke pós-deploy e decidir a remoção definitiva do caminho legado.

### Rollback minimo planejado

1. Reverter frontend para o contrato antigo apenas se o backend ainda suportar o fluxo legado ou se houver feature flag para desligar o seletor por projeto.
2. Preservar a tabela nova e os dados criptografados mesmo em rollback parcial, evitando perda de configuracao.
3. Nao apagar a tabela antiga ate o rollout estar homologado.

## 12. Riscos que nao podem ser ignorados

1. Se a chave mestra de criptografia nao estiver no ambiente real, qualquer trabalho de frontend ou banco vai continuar falhando no save.
2. Se o vinculo for por nome do projeto, renames no Admin vao quebrar a configuracao.
3. Se a run continuar guardando apenas um `llm_provider` global, o historico pode mentir quando multiplos projetos usarem configuracoes diferentes na mesma execucao.
4. Se a migracao copiar a chave global para todos os projetos automaticamente, o sistema vai mascarar um problema de governanca e pode atribuir segredo ao projeto errado.
5. Se a sanitizacao nao for revisada apos incluir `project_id`, e facil introduzir vazamento de segredo em novos erros, auditorias ou snapshots.

## 13. Definicao de pronto

Considerar esta entrega concluida apenas quando todos os itens abaixo forem verdadeiros:

1. O erro atual de criptografia foi resolvido na configuracao de ambiente e esta coberto por validacao automatica ou preflight.
2. IA Settings opera por `project_id`, com persistencia criptografada no banco.
3. O modal permite selecionar projeto e mostra estado isolado por projeto.
4. O runtime da IA usa a configuracao correta por projeto.
5. Historico, auditoria e snapshots continuam corretos para cenarios multi-projeto.
6. Os testes backend, frontend e de runtime foram atualizados e passaram.
7. O caminho legado global ficou explicitamente migrado, desativado ou documentado para remocao posterior.