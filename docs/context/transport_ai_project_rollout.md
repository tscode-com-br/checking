# Rollout operacional da migracao de IA Settings por projeto

## Objetivo

Subir a migracao de `Transport AI Settings` de singleton global para configuracao por `project_id` sem perder rastreabilidade do legado, sem sobrescrita ambigua entre projetos e sem quebrar a leitura historica das runs ja gravadas.

## Artefatos desta rodada

- `deploy/.env.production.example`
- `scripts/export_transport_ai_legacy_llm_settings.py`
- `scripts/backfill_transport_ai_project_llm_settings.py`
- `tests/test_transport_ai_rollout_scripts.py`
- `tests/test_transport_ai_openai_smoke.py`

## Pre-condicoes obrigatorias

1. Definir `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY` no ambiente real antes do rollout funcional.
2. Manter a mesma chave Fernet durante toda a janela de migracao e backfill.
3. Confirmar quais `project_id` realmente devem receber backfill do legado.
4. Validar que o legado singleton nao sera replicado automaticamente para todos os projetos.
5. Preparar uma sessao `transport` autenticada para os smokes de modal e runtime.

## Contrato operacional consolidado

1. O catalogo do modal `IA Settings` deve ser carregado do endpoint autoritativo `GET /api/transport/projects`.
2. `TransportDashboardResponse.projects` continua servindo apenas como bootstrap visual local, nunca como fonte final para gravacao.
3. `PUT /api/transport/ai/settings` exige `project_id`; sem ele, a resposta esperada e `422` sanitizado com mensagem funcional clara.
4. Chaves OpenAI reais so podem ser usadas em smoke opt-in fora do CI, via `TRANSPORT_AI_TEST_OPENAI_API_KEY`.
5. Se o contrato estatico do modal mudar de forma incompatível, versionar `styles.css`, `i18n.js` e `app.js` em `sistema/app/static/transport/index.html`. A versao coordenada atual do `transport` e `20260506b`.
6. O caminho legado global continua apenas para consulta, export e rollback controlado ate remocao futura; ele nao deve voltar a ser fallback implicito de save nem de runtime.

## Como gerar a chave Fernet

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Preencha o segredo no host real e nao rotacione essa chave durante migracao parcial.

## Sequencia recomendada de rollout

### 1. Exportar o legado antes de qualquer alteracao operacional

Sanitizado:

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/export_transport_ai_legacy_llm_settings.py --redact-ciphertext --output artifacts/transport-ai-legacy-sanitized.json
```

Completo, apenas para cofre operacional controlado:

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/export_transport_ai_legacy_llm_settings.py --output artifacts/transport-ai-legacy-full.json
```

Resultado esperado:

- `legacy_settings_present=true`
- hint mascarado em `api_key_hint`
- ciphertext presente apenas no artefato completo

### 2. Rodar migration do banco

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m alembic upgrade head
```

Nao remova a tabela singleton antiga nesta janela. O legado continua servindo como fonte de export e rollback controlado.

### 3. Identificar projetos de destino

Use `GET /api/transport/projects` como catalogo autoritativo para mapear os `project_id` aprovados pela operacao.
Nao trate `TransportDashboardResponse.projects` como fonte final para save ou backfill; ele serve apenas como bootstrap visual local.

### 4. Rodar backfill explicito por `project_id`

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/backfill_transport_ai_project_llm_settings.py --project-id 12 --project-id 18 --output artifacts/transport-ai-backfill.json
```

Observacoes:

- o script falha fechado se nao houver legado exportavel;
- o script falha fechado se o projeto ja possuir configuracao por projeto;
- use `--overwrite-existing` apenas com aprovacao operacional explicita.

### 5. Smoke test do modal

1. Abrir `Transport > IA Settings`.
2. Confirmar em rede que a dropdown foi recarregada de `GET /api/transport/projects`.
3. Confirmar que `Save` fica bloqueado sem `project_id` valido e so habilita quando o catalogo estiver `ready`.
4. Selecionar um projeto com backfill aplicado.
5. Confirmar que `provider`, `model` e `api_key_hint` pertencem ao projeto correto.
6. Trocar para outro projeto e verificar isolamento de hint, provider e feedback.
7. Se o contrato do modal mudou nesta janela, confirmar que o HTML servido referencia `styles.css?v=20260506b`, `i18n.js?v=20260506b` e `app.js?v=20260506b`.
8. Salvar uma mudanca pequena e confirmar que o modal preserva o projeto selecionado em caso de erro.

### 6. Smoke test de runtime por provedor

1. Executar `Calculate Routes` para um projeto com OpenAI configurado.
2. Executar `Calculate Routes` para um projeto com DeepSeek configurado.
3. Confirmar que falhas de preflight apontam projeto sem configuracao, nao provedor errado.
4. Confirmar que auditoria e snapshots nao exibem segredo bruto.

### 7. Smoke OpenAI opt-in fora do CI

Use uma chave real apenas via `TRANSPORT_AI_TEST_OPENAI_API_KEY` e apenas fora do CI padrao.

```powershell
$env:TRANSPORT_AI_TEST_OPENAI_API_KEY = '<secret>'
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_openai_smoke.py -q
```

Regras:

- se a variavel nao estiver definida, o teste deve pular automaticamente;
- o segredo nao deve entrar em `.env.example`, docs versionadas, fixtures, asserts ou logs;
- apos o smoke, remova a variavel do ambiente atual e descarte o preview temporario usado no teste.

## Conferencia dos criterios de aceite

1. Dropdown nao vazia quando ha projetos e sessao valida. Status: concluido. Evidencia: os testes de frontend cobrem tanto a abertura com bootstrap local quanto a recuperacao quando `dashboard.projects` vem vazio e `GET /api/transport/projects` volta preenchido; na validacao manual real, o preview local respondeu `AI14 Preview Apply` e `AI14 Preview Cancel` em `/api/transport/projects`.
2. Catalogo consistente e diagnosticavel. Status: concluido. Evidencia: o contrato consolidado deste runbook fixa `/api/transport/projects` como fonte autoritativa e os testes de frontend cobrem erro de catalogo, estado vazio controlado e bloqueio de `Save` quando o refresh autoritativo falha.
3. `Save` bloqueado sem `project_id`. Status: concluido. Evidencia: o frontend cobre o bloqueio local sem selecao valida e o backend devolve `422` sanitizado com `Transport AI project is required.` e `api_key` redigido como `[REDACTED]`.
4. Persistencia apenas no projeto correto. Status: concluido. Evidencia: `tests/test_transport_ai_llm_settings.py` e `tests/test_transport_ai_router.py` cobrem ciphertext e `api_key_last4` por projeto; na validacao manual real, o banco confirmou `project_id=6`, `provider=openai`, ciphertext preenchido e diferente do segredo bruto.
5. Ausencia de heranca de hint ou chave entre projetos. Status: concluido. Evidencia: o frontend cobre isolamento de `provider`, `api_key_hint` e draft ao trocar projeto; na validacao manual real, o projeto de controle retornou `has_api_key=false` e `api_key_hint=null`.
6. Runtime coerente. Status: concluido. Evidencia: os testes de runtime e agent snapshot mantem `llm_runtime_projects` coerente sem serializar segredos; na validacao manual real, a run `transport-ai-run:f1e4930df3e54dd6b1234fabb0429d6a` terminou `proposed` com `llm_provider=openai` e `llm_model=gpt-5.4-2026-03-05`.
7. Alocacao de passageiros em veiculos sem placa e cor. Status: concluido. Evidencia: `is_transport_vehicle_ready_for_allocation` exige apenas `tipo`, `lugares` e `tolerance`; `tests/test_api_flow.py` confirma assignment manual com `placa=None` e `color=None`, e `tests/test_transport_ai_agent_tools.py` confirma que o planner/solver mantem o veiculo existente sem placa e cor.
8. Testes automatizados cobrindo frontend e backend. Status: concluido. Evidencia: o recorte Node do modal/asset contract passou com `113 pass / 0 fail`; os testes focados de persistencia/runtime/sanitizacao adicionados nesta rodada passaram com `4 passed`; o smoke opt-in existe em arquivo proprio e nao depende do CI padrao.
9. Smoke OpenAI opt-in executado sem vazamento. Status: concluido. Evidencia: `tests/test_transport_ai_openai_smoke.py` roda apenas com `TRANSPORT_AI_TEST_OPENAI_API_KEY` e pula sem a variavel; na validacao manual real, o hint mascarado, a linha criptografada, a run `suggestion_ready` e a ausencia de segredo/ciphertext em logs e auditoria foram confirmados.
10. Runbook suficiente para repeticao do processo. Status: concluido com um gap residual de evidencia visual. Evidencia: este arquivo e `README.md` documentam catalogo autoritativo, `project_id` obrigatorio, smoke opt-in, versionamento de assets e rollback minimo. Gap residual nao bloqueante: a validacao manual real nao gerou captura visual automatizada do modal porque a ferramenta de browser falhou ao abrir `/transport`. Menor proximo passo: rerodar um smoke curto da UI real em browser funcional ou Playwright e anexar uma screenshot/trace do modal carregado com a lista autoritativa.

## Troubleshooting rapido

### Erro de criptografia ao salvar

Sintoma:

- resposta operacional indicando indisponibilidade da criptografia de IA Settings.

Verificar:

1. `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY` existe no processo real do backend.
2. a chave tem formato Fernet valido.
3. a chave nao foi trocada entre save e leitura do mesmo banco.

### Backfill falha porque o projeto ja possui configuracao

Sintoma:

- erro `already have project-scoped Transport AI settings`.

Acao:

1. revisar se o projeto ja foi migrado manualmente;
2. so usar `--overwrite-existing` quando a substituicao for intencional e auditada.

### Backfill falha porque nao existe legado exportavel

Sintoma:

- erro `Legacy Transport AI LLM settings do not exist` ou equivalente.

Acao:

1. confirmar se o ambiente ainda tem o singleton legado;
2. se o ambiente ja nasceu apenas com configuracao por projeto, nao execute backfill.

## Evidencias minimas para concluir o rollout host-side

1. artefato de export do legado salvo fora do banco.
2. resultado JSON do backfill com os `project_id` aprovados.
3. smoke do modal documentado apos deploy.
4. smoke de runtime por provedor documentado apos deploy.

## Rollback minimo planejado

1. Se a regressao estiver apenas no modal ou no catalogo, reverta somente a superficie estatica do `transport` (`app.js` e, se necessario, o versionamento em `index.html`) sem tocar na persistencia por `project_id`.
2. Se a regressao estiver apenas no save UX ou no mapeamento de erros, reverta somente a logica de formulario/feedback do modal; mantenha o contrato backend com `project_id` e os dados por projeto intactos.
3. Se a regressao estiver apenas no smoke opt-in, reverta somente `tests/test_transport_ai_openai_smoke.py` e a documentacao correspondente; nao apague rows de `transport_ai_project_llm_settings` nem snapshots de runtime.
4. Nao apagar a tabela por projeto durante rollback parcial.
5. Nao rotacionar `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY` no meio da reversao.
6. Preservar o singleton legado apenas como referencia/export, nunca como reaplicacao automatica em massa.
7. Nunca reintroduzir fallback global implicito para save ou runtime durante rollback.