# Plano detalhado para adicionar IA Settings no dashboard transport

## 1. Objetivo

Adicionar ao dashboard `transport` um fluxo administrativo para configurar, pela propria UI, o provedor de LLM e a chave de API usada pelo agente de IA do transporte, sem depender de troca manual de variaveis de ambiente a cada alteracao operacional.

O resultado esperado dessa entrega e:

1. O menu `IA` ganha uma terceira opcao `IA Settings`.
2. Ao clicar nessa opcao, o admin abre um widget pequeno com:
   - dropdown `Provedor` com `OpenAI` e `DeepSeek`;
   - input `Chave API`;
   - botoes `Cancelar` e `Salvar`.
3. O backend passa a salvar de forma segura:
   - provedor selecionado;
   - modelo derivado do provedor;
   - configuracao de reasoning em nivel maximo;
   - chave da API correspondente.
4. O runtime do agente de IA deixa de depender apenas de `OPENAI_API_KEY` e `OPENAI_MODEL` globais e passa a resolver a configuracao salva no dashboard.

## 2. Estado atual do codigo

O plano abaixo parte das superficies reais ja existentes:

1. O menu `IA` ja existe em `sistema/app/static/transport/index.html` com as acoes `Calculate Routes` e `Implement Modifications`.
2. O controller do dashboard ja controla esse menu em `sistema/app/static/transport/app.js` com os hooks `data-ai-menu-trigger`, `data-ai-menu` e `data-ai-menu-action="..."`.
3. O i18n do dashboard ja possui namespace `ai.*` em `sistema/app/static/transport/i18n.js`.
4. O dashboard ja possui o padrao de configuracao protegida por sessao em `GET /api/transport/settings` e `PUT /api/transport/settings`.
5. O runtime atual da IA ainda assume OpenAI diretamente em `sistema/app/services/transport_ai_agent.py`, na factory `build_transport_ai_chat_model`, que hoje instancia `ChatOpenAI` usando `settings.openai_api_key` e `settings.openai_model`.
6. A configuracao operacional persistida do dashboard hoje mora em `MobileAppSettings`, mas esse payload atual nao foi desenhado para guardar segredos e e devolvido integralmente ao frontend por `GET /api/transport/settings`.

Isso significa que a entrega nao deve simplesmente enfiar `api_key` dentro de `TransportSettingsResponse`, porque esse caminho atual faria o segredo voltar cru para o navegador e para qualquer cliente autenticado que carregue o payload de settings.

## 3. Decisoes funcionais recomendadas

### 3.1 Escopo do widget

O widget `IA Settings` deve ser pequeno e focado, separado do modal grande `Dashboard Settings`.

Regras do widget:

1. Ele abre a partir de uma terceira opcao no menu `IA`.
2. Ele nao reaproveita o payload de `transport/settings` para leitura/escrita do segredo.
3. Ele mostra apenas os controles pedidos pelo requisito:
   - `Provedor`;
   - `Chave API`;
   - `Cancelar`;
   - `Salvar`.
4. O modelo e o reasoning nao aparecem como campos editaveis; eles sao derivados automaticamente do provedor escolhido.
5. O widget deve exibir um texto auxiliar curto, nao editavel, abaixo do dropdown, por exemplo:
   - `OpenAI -> gpt-5.4-2026-03-05 | reasoning: high`
   - `DeepSeek -> deepseek-v4-pro | reasoning: high`

### 3.2 Mapeamento fixo provedor -> modelo

O requisito pediu um mapeamento fechado. Portanto o plano deve assumir:

1. `OpenAI` -> modelo `gpt-5.4-2026-03-05`
2. `DeepSeek` -> modelo `deepseek-v4-pro`
3. Ambos com `reasoning_effort="high"`

Esses valores devem ser derivados no backend e nao depender de texto digitado pelo navegador.

### 3.3 Semantica de salvamento da chave

Para evitar vazamento de segredo no carregamento do widget:

1. `GET` de settings nunca devolve a chave em claro.
2. O frontend recebe apenas:
   - `provider` atual;
   - `resolved_model` atual;
   - `reasoning_effort` atual;
   - `has_api_key`;
   - `api_key_hint`, por exemplo `***abcd`.
3. O input `Chave API` abre vazio a cada carregamento.
4. Regra de `Salvar`:
   - se o campo vier preenchido, substitui a chave atual;
   - se o campo vier vazio e ja existir chave salva, preserva a chave atual;
   - se o campo vier vazio e nao existir chave salva, retorna erro de validacao.

Essa decisao permite troca de provedor sem forcar redisplay do segredo e sem precisar de um terceiro botao `Limpar`, que nao foi pedido nesta entrega.

### 3.4 Escopo da configuracao

Nesta primeira versao, a configuracao deve ser global por ambiente do dashboard `transport`, e nao por usuario.

Justificativa:

1. O agente de IA do transporte hoje e um recurso operacional do dashboard, nao uma preferencia pessoal.
2. Runs e sugestoes ja sao globais por `service_date`/`route_kind`.
3. Misturar provider/chave por usuario complicaria reproduzibilidade, auditoria e troubleshooting.

## 4. Arquitetura recomendada

## 4.1 Nao reutilizar `transport/settings` para o segredo

Recomendacao forte: criar um contrato separado para `IA Settings`, com endpoints dedicados em `/api/transport/ai/settings`.

Motivos:

1. `GET /api/transport/settings` hoje devolve o payload inteiro para o frontend; isso e inadequado para segredo.
2. `MobileAppSettings` hoje concentra horarios, assentos e pricing; misturar segredo com esse payload aumenta risco de vazamento e dificulta mascaramento.
3. O fluxo de IA precisa de auditoria especifica (`provider`, `model`, `reasoning`, `updated_by`) diferente do resto das configuracoes operacionais.

### 4.2 Persistencia recomendada

Criar uma tabela nova, por exemplo `transport_ai_runtime_settings`, em vez de reaproveitar `mobile_app_settings`.

Campos recomendados:

1. `id` fixo (`1`) para manter o modelo singleton ja usado no projeto.
2. `provider` (`openai`, `deepseek`).
3. `model_name` (`gpt-5.4-2026-03-05`, `deepseek-v4-pro`).
4. `reasoning_effort` (`high`).
5. `api_key_ciphertext`.
6. `api_key_last4`.
7. `api_key_is_configured` ou derivado de `api_key_ciphertext is not null`.
8. `updated_by_admin_id`.
9. `created_at`.
10. `updated_at`.

Opcionalmente, para auditoria futura:

1. `provider_base_url` se DeepSeek for acessado por endpoint OpenAI-compatible configuravel.
2. `version`/`revision` para controle de concorrencia otimista.

### 4.3 Criptografia em repouso

Nao armazenar a chave em texto puro no banco.

Decisao fechada para a implementacao:

1. Adicionar uma chave mestra de aplicacao no ambiente, por exemplo `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY`.
2. Introduzir a dependencia `cryptography` e usar `cryptography.fernet.Fernet` como mecanismo padrao de criptografia simetrica em repouso nesta primeira iteracao.
3. Criar um pequeno service, por exemplo `sistema/app/services/transport_ai_llm_settings.py`, com:
   - `encrypt_transport_ai_api_key(...)`
   - `decrypt_transport_ai_api_key(...)`
   - `mask_transport_ai_api_key(...)`
4. Persistir apenas o token cifrado e metadados nao sensiveis, como `api_key_last4`, sem inventar algoritmo caseiro nem manter fallback em texto puro.
5. Nunca registrar a chave descriptografada em logs, eventos, `raw_model_response_json`, diagnosticos ou responses.

### 4.4 Contratos HTTP recomendados

Adicionar endpoints protegidos por `require_transport_session` no router `transport_ai.py`:

1. `GET /api/transport/ai/settings`
2. `PUT /api/transport/ai/settings`

`GET` deve responder algo como:

```json
{
  "provider": "openai",
  "resolved_model": "gpt-5.4-2026-03-05",
  "reasoning_effort": "high",
  "has_api_key": true,
  "api_key_hint": "***abcd"
}
```

`PUT` deve aceitar algo como:

```json
{
  "provider": "deepseek",
  "api_key": "...opcional quando ja existe chave salva..."
}
```

Regras server-side do `PUT`:

1. Validar provider como enum fechado.
2. Derivar `resolved_model` e `reasoning_effort` no backend.
3. Validar que a chave exista no create inicial ou quando o provider mudar sem haver chave anterior reaproveitavel.
4. Persistir a chave cifrada.
5. Retornar o payload mascarado de `GET`, nunca a chave em claro.

### 4.5 Refatoracao do runtime LLM

Hoje a factory `build_transport_ai_chat_model` e OpenAI-only. O plano deve convertela em uma factory orientada a provider, por exemplo:

1. `resolve_transport_ai_llm_runtime_settings(db)`
2. `build_transport_ai_chat_model_for_provider(...)`

Contrato interno recomendado:

```python
@dataclass(slots=True)
class TransportAILlmRuntimeSettings:
    provider: str
    model_name: str
    reasoning_effort: str
    api_key: str
    base_url: str | None = None
```

Integracao recomendada:

1. O runner da IA resolve a configuracao LLM antes de instanciar o cliente.
2. A run salva snapshot do provider/modelo/reasoning usados naquele momento.
3. Runs ja iniciadas nao mudam de provedor/modelo se o admin alterar o widget depois.

### 4.6 OpenAI e DeepSeek no client builder

Decisao fechada para a compatibilidade inicial:

1. `OpenAI` continua usando `ChatOpenAI`, mas deixa de ler apenas `settings.openai_api_key` e `settings.openai_model`; passa a usar a configuracao resolvida do banco.
2. `DeepSeek` entra na primeira entrega pelo mesmo factory, via adapter OpenAI-compatible baseado em `ChatOpenAI`, com `base_url`, `api_key`, `model` e payload complementar resolvidos por provider.
3. Nao sera introduzido um SDK dedicado de DeepSeek nesta fase; se isso mudar no futuro, a substituicao continua isolada nessa factory.
4. O contrato funcional do dashboard continua provider-agnostic, mesmo que o adapter concreto mude depois.

Quanto ao reasoning:

1. O contrato interno deve normalizar `reasoning_effort="high"`.
2. A factory converte isso para o formato exato aceito por `ChatOpenAI` e pelo endpoint OpenAI-compatible configurado para cada provider.
3. Se algum provider nao aceitar o parametro exatamente com esse nome, o adapter faz a traducao local sem quebrar o contrato funcional do dashboard.

## 5. Mudancas de backend por arquivo

### 5.1 `sistema/app/models.py`

Adicionar o model novo `TransportAILlmSettings` ou nome equivalente.

Responsabilidades:

1. Persistir provider/model/reasoning.
2. Persistir ciphertext da chave.
3. Persistir `updated_by_admin_id`.
4. Expor timestamps.

### 5.2 `alembic/versions/...`

Criar migration para a nova tabela.

Boas praticas para esta migration:

1. `revision` com 32 caracteres ou menos.
2. `CheckConstraint` para provider permitido.
3. `ForeignKey` para `admin_users.id`.
4. Defaults server-side razoaveis para o singleton inicial, se forem usados.

### 5.3 `sistema/app/schemas.py`

Adicionar schemas dedicados:

1. `TransportAILlmProvider = Literal["openai", "deepseek"]`
2. `TransportAISettingsResponse`
3. `TransportAISettingsUpdateRequest`

Campos recomendados do response:

1. `provider`
2. `resolved_model`
3. `reasoning_effort`
4. `has_api_key`
5. `api_key_hint`

Campos recomendados do request:

1. `provider`
2. `api_key`

### 5.4 `sistema/app/services/transport_ai_llm_settings.py`

Criar service novo para concentrar:

1. load do singleton;
2. create inicial;
3. update do provider;
4. cifra/decifra da chave;
5. masking;
6. derivacao `provider -> model_name -> reasoning_effort`.

Funcoes recomendadas:

1. `get_transport_ai_llm_settings(db)`
2. `get_transport_ai_llm_settings_payload(db)`
3. `upsert_transport_ai_llm_settings(db, *, provider, api_key, actor_admin_user_id)`
4. `resolve_transport_ai_llm_runtime_settings(db)`
5. `build_transport_ai_provider_defaults(provider)`

### 5.5 `sistema/app/routers/transport_ai.py`

Adicionar duas rotas novas:

1. `GET /settings`
2. `PUT /settings`

Regras adicionais:

1. Continuar protegidas por sessao de transporte.
2. Responder `409` para combinacoes invalidas de save.
3. Nao expor a chave em `detail` nem em qualquer shape de erro.
4. Idealmente registrar auditoria sanitizada indicando troca de provedor/modelo sem incluir o segredo.

### 5.6 `sistema/app/services/transport_ai_agent.py`

Refatorar o runtime para usar `TransportAILlmRuntimeSettings` em vez de depender apenas de `settings.openai_*`.

Mudancas recomendadas:

1. substituir `build_transport_ai_chat_model(...)` por uma factory multi-provider ou mantela como wrapper delegando para `build_transport_ai_chat_model_for_provider(...)`;
2. injetar `db` ou runtime settings resolvidos no ponto em que a run e executada;
3. salvar `llm_provider`, `llm_model` e `llm_reasoning_effort` na run/suggestion.

### 5.7 `sistema/app/services/transport_ai_runtime.py`

Atualizar o preflight para validar a configuracao LLM vinda do banco.

Hoje ele valida `settings_obj.openai_model` e `settings_obj.openai_api_key`. O plano deve evoluir para:

1. validar que existe configuracao LLM persistida quando `transport_ai_enabled=true` e `agent_mode=agent`;
2. validar provider suportado;
3. validar que existe chave descriptografavel para o provider salvo;
4. devolver issues explicitas como:
   - `transport_ai_llm_settings_missing`
   - `transport_ai_llm_provider_invalid`
   - `transport_ai_llm_api_key_missing`

### 5.8 `sistema/app/services/transport_ai_sanitization.py`

Garantir que a nova chave salva no banco tambem entre na lista de segredos redigidos quando for carregada em runtime.

Requisito importante:

1. qualquer valor descriptografado usado para construir o client deve ser elegivel a redacao pelos helpers de sanitizacao.

## 6. Mudancas de frontend por arquivo

### 6.1 `sistema/app/static/transport/index.html`

Adicionar a terceira opcao no menu `IA`, por exemplo:

1. `data-ai-menu-action="settings"`

Adicionar o widget/dialog pequeno de configuracao, com hooks dedicados, por exemplo:

1. `data-ai-settings-modal`
2. `data-ai-settings-provider`
3. `data-ai-settings-api-key`
4. `data-ai-settings-provider-note`
5. `data-ai-settings-cancel`
6. `data-ai-settings-save`
7. `data-ai-settings-feedback`

Recomendacao de UX:

1. usar `role="dialog"`;
2. largura pequena;
3. ancoragem visual proxima ao menu `IA` no desktop;
4. fallback de modal centralizado no mobile;
5. `aria-describedby` apontando para nota de modelo/reasoning e feedback.

### 6.2 `sistema/app/static/transport/app.js`

Adicionar estado novo, por exemplo:

1. `aiSettingsModalOpen`
2. `aiSettingsLoading`
3. `aiSettingsSaving`
4. `aiSettingsDraft`
5. `aiSettingsSnapshot`

Funcoes recomendadas:

1. `openAiSettingsModal()`
2. `closeAiSettingsModal()`
3. `getDefaultAiSettingsDraft()`
4. `loadAiSettings()`
5. `readAiSettingsDraft()`
6. `validateAiSettingsDraft()`
7. `syncAiSettingsControls()`
8. `saveAiSettings()`
9. `resolveAiProviderModelNote(provider)`

Comportamento esperado:

1. clicar em `IA Settings` fecha o menu e abre o widget;
2. abrir o widget dispara `GET /api/transport/ai/settings`;
3. o dropdown ja vem com o provider salvo;
4. o input de chave fica vazio, mas com placeholder/nota do estado atual se houver chave configurada;
5. trocar o provider atualiza dinamicamente a nota do modelo fixo e do reasoning;
6. `Cancelar` fecha o widget sem `PUT`;
7. `Salvar` faz `PUT`, mostra loading e feedback localizado;
8. em sucesso, atualiza o snapshot local e fecha o widget;
9. em erro, mantem o widget aberto e mostra feedback inline.

### 6.3 `sistema/app/static/transport/i18n.js`

Adicionar chaves novas em todos os idiomas suportados.

Conjunto minimo sugerido:

1. `ai.settingsMenuLabel`
2. `ai.settingsTitle`
3. `ai.settingsProvider`
4. `ai.settingsApiKey`
5. `ai.settingsCancel`
6. `ai.settingsSave`
7. `ai.settingsSaving`
8. `ai.settingsSaved`
9. `ai.settingsLoadFailed`
10. `ai.settingsSaveFailed`
11. `ai.settingsProviderOpenAIHint`
12. `ai.settingsProviderDeepSeekHint`
13. `ai.settingsMissingApiKey`
14. `ai.settingsMaskedKeyHint`

### 6.4 `sistema/app/static/transport/styles.css`

Adicionar estilos para o widget pequeno:

1. shell compacto;
2. layout em coluna;
3. labels e inputs coerentes com o resto do dashboard;
4. nota de provider/model/reasoning;
5. area de feedback;
6. responsividade mobile;
7. estados disabled/loading.

## 7. Mudancas de contrato e auditoria da IA

### 7.1 Persistir o provider/modelo efetivos em cada run

Hoje a run ja guarda `openai_model`, mas isso nao cobre DeepSeek nem o raciocinio configurado.

Plano recomendado:

1. adicionar campos genericos novos em `TransportAIRun`, por exemplo:
   - `llm_provider`
   - `llm_model`
   - `llm_reasoning_effort`
2. adicionar os mesmos campos, quando fizer sentido, em `TransportAISuggestion` ou no audit trail gerado a partir da run.
3. manter `openai_model` apenas enquanto houver compatibilidade legada, com plano de depreciacao posterior.

Motivo:

1. uma suggestion salva precisa carregar o contexto real do modelo usado;
2. o diagnostico administrativo e o export de auditoria devem refletir OpenAI/DeepSeek corretamente;
3. a troca futura de provider nao pode sobrescrever o historico de runs antigas.

### 7.2 Auditoria sanitizada

Ao salvar as configuracoes LLM:

1. registrar evento administrativo do tipo `transport_ai_settings_updated` ou acao equivalente;
2. persistir apenas provider/model/reasoning e hint mascarado da chave;
3. nunca persistir o valor completo da chave em logs/eventos.

## 8. Plano de implementacao por fases

### Fase 0 - Confirmacao tecnica curta

Esta fase foi concluida como uma etapa de fechamento de decisoes tecnicas e alinhamento do proprio plano, sem ainda introduzir endpoints, migrations ou UI novos.

O que foi confirmado e registrado durante a implementacao desta fase:

1. O runtime atual foi revisado e permaneceu evidente que a integracao existente esta centralizada em `langchain-openai` e `ChatOpenAI`, com dependencia direta de `settings.openai_api_key` e `settings.openai_model`.
2. A decisao de adapter foi fechada em favor de uma integracao inicial de `DeepSeek` por endpoint OpenAI-compatible, reutilizando `ChatOpenAI` com `base_url`, `api_key`, `model` e traducao local dos parametros especificos do provider. Nenhum SDK dedicado de DeepSeek sera introduzido na primeira entrega.
3. A decisao de criptografia em repouso foi fechada em favor da dependencia `cryptography`, usando `cryptography.fernet.Fernet` com uma chave mestra de ambiente (`TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY`). A implementacao futura deve persistir apenas o ciphertext e metadados nao sensiveis, sem fallback em texto puro.
4. A decisao de escopo foi mantida como configuracao global por ambiente do dashboard `transport`, e nao por usuario, para preservar reproducibilidade operacional e auditoria coerente por run.
5. A decisao de UX foi fechada para manter apenas os campos editaveis pedidos (`Provedor` e `Chave API`) e exibir um hint nao editavel logo abaixo do seletor, mostrando o modelo resolvido e `reasoning: high` para o provider escolhido.
6. Como resultado direto desta fase, o plano foi ajustado nas secoes anteriores para deixar explicito que o hint visual passa a ser esperado no widget, que a criptografia adotada sera `Fernet`, e que a compatibilidade inicial de `DeepSeek` sera tratada pelo mesmo factory de `ChatOpenAI`.

### Fase 1 - Persistencia e seguranca

Esta fase foi concluida com a implantacao da base persistente e dos mecanismos de seguranca necessarios para guardar configuracoes LLM do dashboard `transport`, sem ainda expor rotas HTTP novas nem entrar na auditoria da Fase 2.

O que foi alterado durante a implementacao desta fase:

1. Foi adicionada a dependencia `cryptography==47.0.0` em `requirements.txt`, consolidando a escolha de `Fernet` como mecanismo de criptografia simetrica em repouso para as chaves de API.
2. Foi adicionada em `sistema/app/core/config.py` a configuracao `transport_ai_settings_encryption_key`, que passa a representar a chave mestra obrigatoria para cifrar e decifrar os segredos persistidos.
3. Foi criado em `sistema/app/models.py` o model `TransportAILlmSettings`, com persistencia singleton (`id=1`) para `provider`, `model_name`, `reasoning_effort`, `api_key_ciphertext`, `api_key_last4`, `updated_by_admin_id`, `created_at` e `updated_at`, incluindo `CheckConstraint` para restringir `provider` a `openai|deepseek` e `reasoning_effort` a `high`.
4. Foi criada a migration `alembic/versions/0050_transport_ai_llm_settings.py`, que introduz a tabela `transport_ai_llm_settings` no banco seguindo o padrao existente de migrations idempotentes do projeto.
5. Foram adicionados em `sistema/app/schemas.py` os contratos `TransportAILlmProvider`, `TransportAISettingsResponse` e `TransportAISettingsUpdateRequest`, cobrindo leitura mascarada e atualizacao validada da configuracao LLM.
6. Foi criado o service `sistema/app/services/transport_ai_llm_settings.py`, centralizando a logica desta fase em um unico modulo com:
   - mapeamento fixo `provider -> model_name -> reasoning_effort`;
   - helpers `encrypt_transport_ai_api_key`, `decrypt_transport_ai_api_key` e `mask_transport_ai_api_key`;
   - leitura do singleton por `get_transport_ai_llm_settings`;
   - montagem do payload mascarado por `get_transport_ai_llm_settings_payload`;
   - persistencia segura por `upsert_transport_ai_llm_settings`;
   - resolucao do segredo descriptografado para uso futuro no runtime por `resolve_transport_ai_llm_runtime_settings`.
7. A semantica de persistencia fechada nesta fase ficou implementada no service da seguinte forma:
   - criacao inicial exige chave de API;
   - update no mesmo provider pode preservar a chave anterior quando `api_key` vier vazia;
   - troca de provider exige chave nova;
   - o payload de leitura retorna apenas `provider`, `resolved_model`, `reasoning_effort`, `has_api_key` e `api_key_hint`, sem nunca devolver o segredo em claro.
8. Foram adicionados testes focados em `tests/test_transport_ai_llm_settings.py`, cobrindo migration em SQLite, defaults fixos de provider/modelo, cifra/decifra/masking, falha quando a chave mestra esta ausente ou invalida, payload mascarado, preservacao de chave no mesmo provider e obrigatoriedade de nova chave na troca de provider.
9. A validacao automatizada desta fase foi executada com sucesso via `pytest tests/test_transport_ai_llm_settings.py -q`, com 7 testes verdes para a fatia de persistencia e seguranca.
10. Esta fase foi encerrada propositalmente antes da adicao dos endpoints `/api/transport/ai/settings` e da auditoria sanitizada, que permanecem reservados para a Fase 2 do plano.

### Fase 2 - Endpoints e auditoria

Esta fase foi concluida com a exposicao controlada do contrato HTTP de `IA Settings` no router da IA e com a implantacao da trilha de auditoria sanitizada para alteracoes administrativas de provider/chave, sem ainda acoplar o runtime do agente a essas configuracoes persistidas.

O que foi alterado durante a implementacao desta fase:

1. Foram adicionadas em `sistema/app/routers/transport_ai.py` as rotas `GET /api/transport/ai/settings` e `PUT /api/transport/ai/settings`, ambas sob o mesmo `APIRouter` ja protegido por `require_transport_session`, mantendo o contrato isolado do endpoint geral `transport/settings`.
2. A rota `GET /api/transport/ai/settings` passou a responder com `TransportAISettingsResponse`, lendo o singleton persistido via `get_transport_ai_llm_settings_payload(db)` e devolvendo apenas `provider`, `resolved_model`, `reasoning_effort`, `has_api_key` e `api_key_hint`, sem nunca expor a chave em claro.
3. A rota `PUT /api/transport/ai/settings` passou a aceitar `TransportAISettingsUpdateRequest`, reutilizando `ensure_transport_ai_actor_admin_user(...)` para converter o `User` autenticado da sessao de transporte em `AdminUser` compativel com a auditoria e com o `updated_by_admin_id` da tabela nova.
4. O `PUT` foi ligado ao service da Fase 1 por meio de `upsert_transport_ai_llm_settings(...)`, com retorno do mesmo payload mascarado do `GET` apos a persistencia bem-sucedida.
5. O mapeamento de erro do `PUT` foi fechado desta forma:
   - `TransportAILlmSettingsValidationError` retorna `409 Conflict`, cobrindo combinacoes invalidas de salvamento, como create inicial sem chave ou troca de provider sem nova chave;
   - `TransportAILlmSettingsEncryptionError` retorna `503 Service Unavailable`, cobrindo indisponibilidade da chave mestra de criptografia sem expor detalhe sensivel.
6. Foi adicionada em `sistema/app/services/transport_ai_observability.py` a funcao `record_transport_ai_settings_update(...)`, dedicada a registrar a alteracao administrativa de settings da IA em `check_events` com `source="transport_ai"`, `action="settings_update"`, `status="success"`, `request_path`, `http_status` e payload JSON sanitizado.
7. A auditoria desta fase foi implementada para registrar somente dados nao sensiveis e operacionais: `actor_admin_user_id`, `actor_admin_key`, `provider`, `resolved_model`, `reasoning_effort`, `has_api_key`, `api_key_hint`, `previous_provider`, `provider_changed` e `request_path`. O segredo descriptografado nao entra nem na mensagem nem em `details`.
8. Durante a validacao desta fase foi identificado que o redator generico de `sistema/app/services/transport_ai_sanitization.py` mascarava tambem `api_key_hint`, o que apagava o hint ja seguro que deveria permanecer na auditoria. O comportamento foi corrigido para preservar campos `*_hint`, mantendo a redacao normal de chaves, tokens, segredos e passwords reais.
9. A cobertura automatizada desta fase foi adicionada em `tests/test_transport_ai_router.py`, incluindo:
   - protecao por sessao de transporte para as rotas novas;
   - exposicao de `/api/transport/ai/settings` e dos schemas correspondentes no OpenAPI;
   - `GET` inicial com defaults mascarados;
   - `PUT` bem-sucedido retornando hint mascarado e persistindo ciphertext;
   - `PUT` invalido retornando `409` ao tentar trocar provider sem nova chave;
   - verificacao explicita de que `check_events.message` e `check_events.details` nao vazam a chave bruta.
10. A validacao executada para esta fase foi `pytest tests/test_transport_ai_router.py -q`, com 6 testes verdes cobrindo a superficie HTTP e a auditoria sanitizada do slice implementado.
11. Esta fase foi encerrada deliberadamente antes da refatoracao do runtime multi-provider e antes do consumo dessas configuracoes pelo executor do agente, que continuam reservados para a Fase 3.

### Fase 3 - Runtime multi-provider

Esta fase foi concluida com a troca efetiva do runtime da IA de transporte para um fluxo orientado a configuracao persistida no banco, incluindo snapshot de provider/model/reasoning na run, preflight baseado em `IA Settings` e factory multi-provider com adapter inicial de `DeepSeek` sobre `ChatOpenAI`.

O que foi alterado durante a implementacao desta fase:

1. Foi estendido em `sistema/app/models.py` o model `TransportAIRun` com os campos `llm_provider`, `llm_model` e `llm_reasoning_effort`, mantendo `openai_model` por compatibilidade legada, mas passando a espelhar o modelo efetivo usado pela run mesmo quando o provider salvo nao e OpenAI.
2. Foi criada a migration `alembic/versions/0051_add_transport_ai_run_llm_snapshot.py`, que adiciona as tres colunas de snapshot em `transport_ai_runs` e faz backfill dos registros existentes com `llm_provider='openai'`, `llm_model=openai_model` e `llm_reasoning_effort='high'`.
3. Foi atualizado em `sistema/app/routers/transport_ai.py` o fluxo de `POST /api/transport/ai/route-calculations` para resolver `resolve_transport_ai_llm_runtime_settings(db)` quando o modo da IA esta em `agent`, e gravar esse snapshot diretamente na `TransportAIRun` recem-criada antes da execucao do agente.
4. Como parte dessa mesma mudanca, o evento observavel `run_created` passou a carregar tambem `llm_provider`, `llm_model` e `llm_reasoning_effort` nos `extra_details`, preservando a trilha factual de qual configuracao LLM foi congelada no inicio da run.
5. Em `sistema/app/services/transport_ai_llm_settings.py` o contrato interno `TransportAILlmRuntimeSettings` passou a carregar tambem `base_url`, e o mapeamento fixo de provider ganhou a resolucao inicial de endpoint OpenAI-compatible para `DeepSeek` (`https://api.deepseek.com/v1`).
6. Em `sistema/app/services/transport_ai_agent.py` foi introduzida a factory `build_transport_ai_chat_model_for_provider(...)`, que centraliza a construcao do `ChatOpenAI` com base no provider resolvido do banco, usando:
   - `provider='openai'` com `model_kwargs={"reasoning": {"effort": "high"}}`;
   - `provider='deepseek'` com `base_url` OpenAI-compatible e `model_kwargs={"reasoning_effort": "high"}`.
7. A antiga factory `build_transport_ai_chat_model(...)` foi mantida apenas como wrapper legada para OpenAI, enquanto o caminho real do runtime em `agent` passou a usar a nova factory multi-provider baseada em `TransportAILlmRuntimeSettings`.
8. O executor `run_transport_ai_agent(...)` deixou de depender apenas de `settings.openai_model` e `settings.openai_api_key` no fluxo real de `agent`, passando a:
   - resolver a configuracao persistida do banco quando a run foi criada com snapshot LLM ou quando a execucao precisa construir o model real;
   - usar `run.llm_model` como modelo efetivo da run quando presente;
   - reconstruir o client sem temperatura apenas no mesmo provider quando o backend do modelo rejeita esse parametro.
9. A sanitizacao do runtime foi reforcada para aceitar segredos literais extras em memoria, de forma que a chave descriptografada recuperada do banco possa ser redigida de `raw_model_response_json` e de mensagens de erro mesmo quando ela nao existe em nenhuma variavel de ambiente global. Isso fecha o requisito de nao vazar a chave persistida durante a execucao do agente.
10. Em `sistema/app/services/transport_ai_runtime.py` o preflight de `agent_mode='agent'` deixou de validar apenas `openai_model` e `openai_api_key` do ambiente e passou a validar `IA Settings` persistido, emitindo os codigos:
   - `transport_ai_llm_settings_missing` quando a configuracao LLM nao existe no banco;
   - `transport_ai_llm_provider_invalid` quando o provider salvo nao pertence ao conjunto suportado;
   - `transport_ai_llm_api_key_missing` quando a chave persistida esta ausente ou nao pode ser descriptografada.
11. O comportamento em `deterministic` foi preservado: a execucao continua sem depender de configuracao LLM persistida, e o preflight ainda permite esse modo sem chave/API de provider configurada.
12. A cobertura automatizada desta fase foi ampliada em `tests/test_transport_ai_runtime.py` e `tests/test_transport_ai_agent_runtime.py`, incluindo:
   - migration head com presenca de `llm_provider`, `llm_model` e `llm_reasoning_effort` em `transport_ai_runs`;
   - preflight falhando sem `IA Settings` persistido, mas aceitando configuracao persistida valida inclusive com `DeepSeek`;
   - factory multi-provider verificando o adapter OpenAI-compatible de `DeepSeek`;
   - execucao do agente usando snapshot `deepseek` na run, com redacao da chave descriptografada em `raw_model_response_json`;
   - falha controlada do agente quando a configuracao persistida nao existe em `agent_mode='agent'`.
13. A validacao executada para esta fase foi concluida com sucesso via:
   - `pytest tests/test_transport_ai_runtime.py tests/test_transport_ai_agent_runtime.py -q` com 16 testes verdes;
   - `pytest tests/test_transport_ai_route_calculations.py -q` com 3 testes verdes para confirmar que o start da run continua funcionando apos o snapshot LLM no router.
14. Esta fase foi encerrada antes da entrega de UI/Widget da Fase 4 e antes de qualquer remodelagem do payload de diagnostico administrativo para expor explicitamente `llm_provider`, `llm_model` e `llm_reasoning_effort`, o que permanece como trabalho adjacente das fases seguintes.

### Fase 4 - Widget e menu no frontend

Esta fase foi concluida com a entrega do widget `IA Settings` no frontend do dashboard `transport`, conectado aos endpoints dedicados da Fase 2 e com comportamento de UI compatível com as regras de segredo mascarado, troca de provider e feedback inline.

O que foi alterado durante a implementacao desta fase:

1. Em `sistema/app/static/transport/index.html` o menu `IA` ganhou a terceira acao `AI Settings`, com `data-ai-menu-action="settings"`, `aria-haspopup="dialog"` e `aria-controls="transport-ai-settings-modal"`, preservando o mesmo shell de menu ja existente para `Calculate Routes` e `Implement Modifications`.
2. No mesmo arquivo foi adicionado o modal pequeno `transport-ai-settings-modal`, com estrutura propria para:
   - select de provider (`OpenAI` e `DeepSeek`);
   - input protegido de `API Key`;
   - nota nao editavel com `provider -> model | reasoning`;
   - hint mascarado da chave salva;
   - feedback inline com `aria-live="polite"`;
   - botoes `Cancel` e `Save`.
3. Em `sistema/app/static/transport/app.js` foi criado um slice dedicado de estado para `IA Settings`, separado do modal de agent settings, incluindo draft, provider carregado, hint mascarado, flags de `loading`/`saving` e feedback inline proprio.
4. O frontend passou a espelhar explicitamente o mapeamento fechado de provider da entrega: `openai -> gpt-5.4-2026-03-05 | high` e `deepseek -> deepseek-v4-pro | high`, usando esse contrato apenas para copy do widget e para atualizar a nota auxiliar em tempo real quando o provider muda no select.
5. A abertura do widget foi ligada a `GET ../api/transport/ai/settings` a cada abertura do modal. O payload carregado preenche somente o provider atual e o hint mascarado; o campo `API Key` sempre volta vazio no reload do widget, evitando reexibicao do segredo em claro no navegador.
6. O salvamento foi ligado a `PUT ../api/transport/ai/settings`, enviando apenas `provider` e `api_key` trimado quando houver texto no input. O fluxo fecha o modal em sucesso, mantem o modal aberto em erro e exibe feedback inline traduzido para falhas de validacao e indisponibilidade de criptografia.
7. O comportamento visual e interativo do widget foi fechado desta forma em `app.js`:
   - `Cancel` fecha o modal sem disparar `PUT`;
   - troca de provider com campo vazio mostra aviso local de que uma nova chave sera exigida;
   - save pendente marca o modal como `aria-busy`, desabilita os controles e impede fechamento por `Cancel`, clique no backdrop ou `Escape`;
   - o widget convive corretamente com os demais modais, fechando ou sendo fechado pelos fluxos vizinhos (`Dashboard Settings`, `AI Agent Settings` e `Changes`) sem sobreposicao residual.
8. O mapeamento de mensagens em `localizeTransportApiMessage(...)` foi ampliado para traduzir os detalhes server-side do backend de `IA Settings`, cobrindo pelo menos: chave obrigatoria no create inicial, chave obrigatoria na troca de provider e indisponibilidade da criptografia dos settings.
9. Em `sistema/app/static/transport/i18n.js` foram adicionadas chaves novas em todos os idiomas suportados para rotulo do menu, titulo do modal, labels, hint mascarado, aviso de troca de provider, estados de carregamento/salvamento e mensagens de sucesso/erro do widget.
10. Em `sistema/app/static/transport/styles.css` foi criado o bloco visual proprio do modal `transport-ai-settings-modal`, mantendo o padrao neon/dark do dashboard, com layout compacto, hint tonalizado para aviso e responsividade alinhada aos breakpoints ja usados pelos outros modais do transport.
11. A cobertura automatizada desta fase foi adicionada e expandida em `tests/transport_page_date.test.js`, incluindo:
   - presenca estaticamente testada da terceira acao `AI Settings`, do modal e dos hooks de traducao;
   - harness fake-DOM com o novo modal e seus controles;
   - mock de fetch cobrindo `GET` e `PUT /ai/settings` sem conflitar com o endpoint generico `/settings`;
   - abertura do widget e carga do estado mascarado;
   - cancelamento sem request de save;
   - save bem-sucedido com payload trimado;
   - erro de validacao mantendo o modal aberto com feedback inline;
   - bloqueio de fechamento do modal enquanto o save ainda esta pendente.
12. A validacao executada para esta fase foi `node --test tests/transport_page_date.test.js`, encerrando com 95 testes verdes e cobrindo tanto a superficie estatica quanto o comportamento do widget novo no harness de frontend.

### Fase 5 - Integracao com runs e regressao

1. Em `sistema/app/schemas.py` o contrato `TransportAIRunDiagnosticsEntry` foi ampliado para expor `llm_provider`, `llm_model` e `llm_reasoning_effort`, mantendo `openai_model` no payload por compatibilidade com consumidores e testes legados do diagnostico administrativo.
2. Em `sistema/app/routers/transport_ai.py` o builder `_build_transport_ai_runs_diagnostics_entries(...)` passou a publicar explicitamente o snapshot LLM salvo na `TransportAIRun`, em vez de expor apenas `openai_model`.
3. No mesmo builder foi adicionado fallback controlado para runs antigas/fixtures sem `llm_*` preenchidos: quando necessario, o diagnostico deriva `llm_provider=openai`, `llm_model=openai_model` e `llm_reasoning_effort=high`, evitando quebrar a leitura historica e mantendo o payload auditavel.
4. Em `sistema/app/services/transport_exports.py` o export operacional ganhou uma leitura explicita da `TransportAIRun` associada a `TransportAISuggestion`, sem alterar a regra existente de so anexar as abas de IA quando `proposal.origin == "agent"` e existe suggestion persistida com o mesmo `proposal_key`.
5. O sheet `AI Summary` passou a incluir as linhas `LLM Provider`, `LLM Model` e `LLM Reasoning Effort`, refletindo o snapshot efetivamente usado pela run da sugestao exportada.
6. O contrato legado do workbook foi preservado para propostas manuais/system e para propostas `agent` sem suggestion correspondente: a lista de abas continua identica fora do fluxo ja coberto de export com IA.
7. A regressao de diagnostico foi reforcada em `tests/test_transport_ai_router.py`, cobrindo dois cenarios distintos:
   - run nova com snapshot explicito `deepseek / deepseek-v4-pro / high`, validando que o endpoint `/api/transport/ai/runs` mostra o provider correto;
   - run legada sem `llm_*`, validando o fallback para `openai / gpt-5-2025-08-07 / high` e mantendo a sanitizacao de segredos em `error_message`.
8. A regressao de export foi reforcada em `tests/test_api_flow.py`, sem mudar a estrutura das abas, para verificar que o `AI Summary` de uma proposta `agent` exportada inclui `LLM Provider=deepseek`, `LLM Model=deepseek-v4-pro` e `LLM Reasoning Effort=high`.
9. A validacao executada para esta fase foi focada nas duas superficies alteradas:
   - `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_router.py::test_transport_ai_runs_endpoint_lists_recent_runs_filters_and_redacts_sensitive_fields tests/test_api_flow.py::test_transport_operational_plan_export_includes_ai_suggestion_tabs_for_agent_proposal -q`
   - resultado: 2 testes verdes, confirmando o diagnostico administrativo e o export operacional com o snapshot LLM novo.

## 9. Casos de borda que o plano precisa cobrir

1. Em `sistema/app/services/transport_ai_llm_settings.py` foi criada uma fonte unica de verdade para providers suportados por meio de `get_supported_transport_ai_llm_providers()`, evitando que o conjunto aceito pelo runtime/preflight diverja do conjunto aceito pelo service de `IA Settings`.
2. No mesmo service foi introduzida uma resolucao controlada para providers persistidos que deixaram de ser suportados: quando o provider salvo nao existe mais no mapa atual de defaults, o backend passa a levantar a mensagem factual `The configured Transport AI LLM provider is no longer supported. Select OpenAI or DeepSeek and save the AI settings again.`, em vez de explodir com um erro generico ou tentar fazer fallback silencioso para outro provider.
3. Em `sistema/app/services/transport_ai_runtime.py` o preflight deixou de depender de uma lista hardcoded (`openai|deepseek`) e passou a consultar o conjunto dinamico devolvido pelo service. Com isso, um provider removido em nova versao do backend agora gera corretamente a issue `transport_ai_llm_provider_invalid` durante a validacao operacional.
4. Em `sistema/app/routers/transport_ai.py` o `GET /api/transport/ai/settings` passou a capturar esse caso de provider persistido e responder `409 Conflict` com `detail` controlado, em vez de permitir que a excecao chegue como falha interna sem contexto para o widget administrativo.
5. O comportamento ja existente para troca de provider sem chave nova foi preservado: `PUT /api/transport/ai/settings` continua exigindo nova chave quando o provider muda e continua bloqueando create inicial sem segredo, cobrindo os casos de borda de `OpenAI -> DeepSeek` com campo vazio e de configuracao inicial vazia.
6. O comportamento ja existente para indisponibilidade da chave mestra tambem foi preservado e reafirmado: `PUT /api/transport/ai/settings` continua devolvendo `503` com a mensagem controlada `Transport AI settings encryption is unavailable.`, enquanto o preflight segue emitindo issue clara quando a chave persistida nao pode ser decriptada.
7. Em `sistema/app/static/transport/app.js` o mapeamento `localizeTransportApiMessage(...)` foi ampliado em dois pontos para que o widget mostre feedback controlado em vez de texto bruto do backend:
   - a nova mensagem de provider nao suportado foi ligada a `ai.settingsProviderUnsupported`;
   - a mensagem portuguesa de sessao expirada `Sessao de transporte invalida ou expirada` foi ligada a `status.sessionExpired`, eliminando a exibicao crua da string do servidor no modal.
8. Em `sistema/app/static/transport/i18n.js` foi adicionada a chave `ai.settingsProviderUnsupported` em todos os idiomas suportados pelo dashboard, garantindo copy localizado para o caso em que um provider salvo deixou de ser aceito pela versao atual do backend.
9. A cobertura automatizada desta secao foi ampliada em `tests/test_transport_ai_runtime.py`, `tests/test_transport_ai_router.py` e `tests/transport_page_date.test.js`, cobrindo explicitamente:
   - preflight acusando `transport_ai_llm_provider_invalid` quando um provider antes suportado e removido do mapa de defaults;
   - `GET /api/transport/ai/settings` devolvendo `409` controlado para provider salvo nao suportado e permitindo recuperacao por `PUT` com provider valido e nova chave;
   - widget `IA Settings` reagindo com feedback controlado a `401` durante load, `409` de provider nao suportado durante load e `503` de criptografia indisponivel durante save.
10. A validacao executada para esta secao foi concluida com sucesso via:
   - `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_llm_settings.py tests/test_transport_ai_runtime.py tests/test_transport_ai_router.py -q` com 23 testes verdes;
   - `node --test tests/transport_page_date.test.js` com 98 testes verdes no harness do frontend.

## 10. Plano de testes

### 10.1 Backend unitario

1. A cobertura unitária desta seção foi consolidada em `tests/test_transport_ai_llm_settings.py` e `tests/test_transport_ai_runtime.py`, mantendo o foco no service de settings LLM e no preflight do runtime, sem depender dos endpoints HTTP do router.
2. Em `tests/test_transport_ai_llm_settings.py` foi mantido e reforçado o teste de derivação fixa dos providers, validando explicitamente o contrato fechado da entrega:
   - `openai -> gpt-5.4-2026-03-05 + high` com `base_url=None`;
   - `deepseek -> deepseek-v4-pro + high` com `base_url=https://api.deepseek.com/v1`.
3. No mesmo arquivo foi mantida a cobertura unitária de cifra, decifra e masking da chave com `Fernet`, incluindo falhas controladas quando a chave mestra está ausente ou inválida.
4. O caso de `GET` sem vazamento de segredo foi reforçado no teste do payload mascarado: além de validar `provider`, `resolved_model`, `reasoning_effort`, `has_api_key` e `api_key_hint`, o teste agora serializa o `TransportAISettingsResponse` e verifica explicitamente que nem a chave em claro nem o ciphertext persistido aparecem no payload devolvido pelo helper de leitura.
5. A semântica unitária de `PUT` sobre o service foi mantida coberta por dois fluxos focados:
   - preservação da chave criptografada anterior quando o provider não muda e o `api_key` vem vazio;
   - obrigatoriedade de nova chave no create inicial e também na troca de provider (`openai -> deepseek`).
6. Em `tests/test_transport_ai_runtime.py` foi mantida a cobertura unitária do preflight em `agent_mode='agent'`, validando que a ausência de `IA Settings` persistido gera exatamente a issue `transport_ai_llm_settings_missing`, mesmo quando ainda existem `openai_api_key` e `openai_model` legados no ambiente.
7. Como cobertura adjacente útil para este mesmo bloco unitário, o arquivo de runtime também continua validando o caso positivo de configuração persistida completa e o caso de provider removido do mapa suportado, o que ajuda a manter o contrato do preflight coerente com o service de settings.
8. A validação executada para esta subseção foi:
   - `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_llm_settings.py tests/test_transport_ai_runtime.py -q`
   - resultado: 16 testes verdes, cobrindo a fatia unitária de derivação, criptografia, masking, payload mascarado, preservação/troca de chave e preflight sem configuração persistida.

### 10.2 Backend integracao

1. A cobertura de integracao desta subsecao ficou consolidada em `tests/test_transport_ai_router.py` e `tests/test_transport_ai_route_calculations.py`, mantendo o foco nos endpoints HTTP reais e no persist snapshot do provider/modelo dentro de `TransportAIRun`.
2. Em `tests/test_transport_ai_router.py`, o teste `test_transport_ai_router_requires_transport_session_and_exposes_openapi` foi ampliado para validar explicitamente que `GET /api/transport/ai/settings` devolve `401` antes da autenticacao, usando a mesma mensagem controlada de sessao invalida ja exercitada no restante do router.
3. No mesmo arquivo, o teste `test_transport_ai_settings_endpoint_saves_masked_configuration_and_audits_safely` continuou cobrindo o `PUT /api/transport/ai/settings` com persistencia de `provider=openai` e resposta mascarada, mas agora tambem verifica de forma explicita que nenhuma das respostas HTTP do fluxo (`PUT` inicial, `GET` subsequente e tentativa invalida de troca de provider sem nova chave) contem a chave em claro nem o ciphertext persistido no banco.
4. Em `tests/test_transport_ai_route_calculations.py`, o helper subprocessado de integracao foi estendido com suporte a `agent_mode='agent'`, chave mestra de criptografia para os settings persistidos e seed opcional de `TransportAILlmSettings`, sem alterar os cenarios deterministas ja existentes.
5. Ainda nesse arquivo, foi adicionado o teste `test_route_calculations_agent_mode_uses_persisted_llm_snapshot`, que persiste `provider=deepseek` com chave criptografada, executa `POST /api/transport/ai/route-calculations` e valida que a run criada congela `llm_provider='deepseek'`, `llm_model='deepseek-v4-pro'`, `llm_reasoning_effort='high'` e `openai_model='deepseek-v4-pro'`, alem de confirmar a criacao da suggestion associada.
6. O mesmo teste de `route-calculations` tambem reforca a seguranca do fluxo HTTP e de auditoria: a resposta do endpoint nao contem a chave em claro, e os eventos `transport_ai` registram `llm_provider` e `llm_model` no payload sanitizado sem expor o segredo persistido nem o token de mapa.
7. A parte de diagnostico de `GET /api/transport/ai/runs` permaneceu coberta pelo teste de integracao existente `test_transport_ai_runs_endpoint_lists_recent_runs_filters_and_redacts_sensitive_fields`, que ja valida a presenca de `llm_provider` e `llm_model` no payload de runs e a redacao de campos sensiveis; esse teste foi incluido na validacao final desta subsecao.
8. A validacao executada para esta subsecao foi:
   - `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_router.py::test_transport_ai_router_requires_transport_session_and_exposes_openapi tests/test_transport_ai_router.py::test_transport_ai_settings_endpoint_saves_masked_configuration_and_audits_safely tests/test_transport_ai_router.py::test_transport_ai_runs_endpoint_lists_recent_runs_filters_and_redacts_sensitive_fields tests/test_transport_ai_route_calculations.py::test_route_calculations_agent_mode_uses_persisted_llm_snapshot -q`
   - resultado: 4 testes verdes, cobrindo autenticacao do `GET`, persistencia mascarada do `PUT`, snapshot LLM da run, reflexo em `/ai/runs` e ausencia de segredo completo nas respostas HTTP exercitadas.

### 10.3 Frontend Node tests

1. A cobertura Node desta subsecao permaneceu concentrada em `tests/transport_page_date.test.js`, usando a combinacao ja existente de verificacoes estaticas em HTML/CSS/i18n e fluxo interativo com harness fake-DOM do dashboard `transport`.
2. O teste estatico `transport ai settings modal keeps dedicated menu, request, and feedback hooks` foi reforcado para validar a ordem real das tres acoes do menu `IA` no HTML de `sistema/app/static/transport/index.html`, confirmando explicitamente a sequencia `calculate-routes -> implement-modifications -> settings` antes de checar os hooks dedicados do widget.
3. No fluxo interativo `transport ai settings modal opens from the AI menu, loads masked state, and cancel closes without save request`, a cobertura foi reforcada para verificar de forma explicita que o widget renderiza os dois controles pedidos pela secao: um `select` de provider e um `input` `type="password"` para a chave, alem de continuar validando a abertura pelo menu, o `GET /api/transport/ai/settings`, o estado mascarado carregado e o fechamento por `Cancel` sem `PUT`.
4. O teste `transport ai settings save flow updates the provider note, posts the trimmed payload, and closes on success` continuou cobrindo o caso positivo completo do widget: troca de provider para `deepseek`, atualizacao da nota `provider -> model/reasoning`, serializacao trimada do payload e chamada real de `PUT /api/transport/ai/settings`, com fechamento do modal e feedback global de sucesso.
5. O teste `transport ai settings save errors keep the modal open with inline feedback` permaneceu cobrindo o caminho de erro funcional do `Save`, validando que o modal fica aberto e exibe feedback inline quando o backend exige nova chave na troca de provider.
6. Como reforco adjacente da mesma superficie de feedback, os testes `transport ai settings modal shows a controlled warning when the session expires during load`, `transport ai settings modal keeps a controlled message when the saved provider is no longer supported` e `transport ai settings save surfaces the encryption-unavailable error without closing the modal` continuam cobrindo mensagens controladas para `401`, `409` e `503` sem expor texto bruto inseguro nem fechar o widget indevidamente.
7. O requisito de lock durante save pendente permaneceu coberto por `transport ai settings modal does not close while a save request is still pending`, que valida bloqueio de fechamento por `Cancel` e por clique no backdrop enquanto a promise do `PUT` ainda nao foi resolvida.
8. A validacao executada para esta subsecao foi:
   - `node --test tests/transport_page_date.test.js --test-name-pattern "transport ai settings"`
   - resultado: 98 testes verdes no arquivo Node, incluindo toda a fatia de `AI Settings` com presenca da terceira opcao do menu, abertura do widget, render dos controles, cancelamento sem request, `PUT` no save, feedback de sucesso/erro, troca de provider atualizando a nota e bloqueio de fechamento durante save pendente.

### 10.4 Validacao manual

Checklist manual recomendado:

1. autenticar em `/transport`;
2. abrir o menu `IA`;
3. confirmar a terceira opcao `IA Settings`;
4. abrir o widget;
5. selecionar `OpenAI`, colar chave, salvar;
6. reabrir o widget e confirmar `provider=openai`, modelo derivado correto e chave mascarada/nao reenviada;
7. trocar para `DeepSeek`, informar nova chave, salvar;
8. disparar uma run de IA e confirmar que a auditoria/run mostra o provider correto;
9. verificar que nenhum log ou response expoe a chave.

## 11. Riscos e mitigacoes

### 11.1 Guardar segredo no mesmo payload de `transport/settings`

1. A mitigacao estrutural desta secao foi consolidada em cima do contrato ja separado entre `GET/PUT /api/transport/settings` e `GET/PUT /api/transport/ai/settings`, mas agora com endurecimento explicito do schema geral de settings para falhar quando um cliente tentar misturar campos de segredo da IA no payload operacional comum.
2. Em `sistema/app/schemas.py`, o request model `TransportSettingsUpdateRequest` passou a usar `ConfigDict(extra="forbid")`, fazendo com que `provider`, `api_key`, `api_key_hint`, `resolved_model` e quaisquer outros campos estranhos ao contrato de settings operacionais sejam rejeitados com `422`, em vez de serem aceitos silenciosamente pelo endpoint geral.
3. Essa mudanca fecha o risco de um cliente reutilizar por engano o payload de `IA Settings` dentro de `/api/transport/settings`: mesmo que o segredo nao fosse persistido no slice operacional, ele agora tambem nao pode mais ser enviado com sucesso para esse endpoint por acidente.
4. A superficie de leitura permaneceu separada e restrita ao contrato operacional existente: `TransportSettingsResponse` continua expondo apenas horarios, assentos, tolerancia e pricing, sem carregar `provider`, `api_key`, `api_key_hint`, `resolved_model` ou `reasoning_effort`.
5. A regressao executavel desta secao foi adicionada em `tests/test_api_flow.py` por meio do teste `test_transport_settings_endpoint_keeps_ai_secret_on_dedicated_contract`, que:
   - salva uma chave real de `IA Settings` via `PUT /api/transport/ai/settings` e confirma que a resposta dedicada continua mascarada;
   - valida que `GET /api/transport/settings` nao devolve nenhum campo de `IA Settings` no payload JSON;
   - tenta enviar um payload misto para `PUT /api/transport/settings` contendo tanto campos validos de configuracao operacional quanto `provider` e `api_key`, e confirma a rejeicao com `422` e erros `extra_forbidden`;
   - verifica que, apos essa rejeicao, o contrato dedicado `/api/transport/ai/settings` continua intacto e mascarado.
6. A validacao executada para esta secao foi:
   - `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py::test_transport_settings_endpoint_keeps_ai_secret_on_dedicated_contract -q`
   - `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py::test_transport_settings_endpoint_updates_work_to_home_boarding_time tests/test_api_flow.py::test_transport_settings_endpoint_keeps_ai_secret_on_dedicated_contract -q`
   - resultado: 2 testes verdes, confirmando tanto a separacao do segredo em contrato dedicado quanto a ausencia de regressao no fluxo normal de update de `transport/settings`.

### 11.2 DeepSeek nao ser 100% compativel com o adapter inicial

1. A mitigacao desta secao foi reforcada em `sistema/app/services/transport_ai_agent.py`, mantendo `DeepSeek` isolado na mesma factory multi-provider baseada em `ChatOpenAI`, mas agora com uma trilha explicita de compatibilidade para o caso em que o endpoint OpenAI-compatible rejeita o payload de `reasoning`/`reasoning_effort`.
2. A factory `build_transport_ai_chat_model_for_provider(...)` passou a expor o parametro interno `include_reasoning_effort`, permitindo que o adapter continue montando o payload completo por padrao, mas consiga reconstruir o client sem o campo de reasoning quando o provider concreto nao for totalmente compativel com esse detalhe de contrato.
3. A logica de traducao de provider permaneceu centralizada nessa mesma factory: `openai` continua recebendo `{"reasoning": {"effort": ...}}`, enquanto `deepseek` continua recebendo `{"reasoning_effort": ...}` e `base_url` dedicado, preservando a interface interna estavel do runtime mesmo se o adapter concreto precisar mudar depois.
4. No mesmo modulo foi adicionada a deteccao `_is_transport_ai_reasoning_unsupported_error(...)` e o helper `_build_transport_ai_compatible_chat_model(...)`, que concentram a mitigacao de compatibilidade em um unico lugar e evitam espalhar condicionais de provider pelo restante do executor do agente.
5. Em `run_transport_ai_agent(...)`, quando o runtime esta construindo o model real a partir dos settings persistidos e o provider rejeita o payload de reasoning, o fluxo agora faz retry automatico reconstruindo o model sem esse parametro, de forma similar ao fallback ja existente para `temperature`. Isso reduz o risco de falha operacional por uma incompatibilidade pontual do adapter sem quebrar o contrato funcional do dashboard.
6. A cobertura automatizada desta secao foi ampliada em `tests/test_transport_ai_agent_runtime.py` em dois pontos complementares:
   - `test_build_transport_ai_chat_model_for_deepseek_can_omit_reasoning_payload_for_compatibility`, validando que a factory ainda monta o adapter OpenAI-compatible de `DeepSeek` corretamente mesmo quando precisa omitir `model_kwargs` de reasoning;
   - `test_run_transport_ai_agent_retries_without_reasoning_payload_when_deepseek_rejects_it`, simulando uma falha real de compatibilidade (`reasoning_effort is not supported`) na primeira tentativa e confirmando que o runtime reconstrói o model sem o payload de reasoning e conclui a run com sucesso.
7. Como validacao adjacente para garantir ausencia de regressao, os testes existentes do mesmo arquivo continuaram cobrindo o adapter `DeepSeek` com payload completo e o fluxo normal do agente com snapshot persistido do provider/modelo.
8. A validacao executada para esta secao foi:
   - `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_agent_runtime.py::test_build_transport_ai_chat_model_for_deepseek_uses_openai_compatible_adapter tests/test_transport_ai_agent_runtime.py::test_build_transport_ai_chat_model_for_deepseek_can_omit_reasoning_payload_for_compatibility tests/test_transport_ai_agent_runtime.py::test_run_transport_ai_agent_retries_without_reasoning_payload_when_deepseek_rejects_it -q`
   - `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_agent_runtime.py::test_build_transport_ai_chat_model_for_deepseek_uses_openai_compatible_adapter tests/test_transport_ai_agent_runtime.py::test_build_transport_ai_chat_model_for_deepseek_can_omit_reasoning_payload_for_compatibility tests/test_transport_ai_agent_runtime.py::test_run_transport_ai_agent_returns_valid_plan_with_fake_model tests/test_transport_ai_agent_runtime.py::test_run_transport_ai_agent_uses_run_llm_snapshot_and_sanitizes_persisted_api_key tests/test_transport_ai_agent_runtime.py::test_run_transport_ai_agent_retries_without_reasoning_payload_when_deepseek_rejects_it -q`
   - resultado: 5 testes verdes, confirmando o isolamento do adapter, o fallback de compatibilidade para reasoning e a preservacao do fluxo normal do agente.

### 11.3 Vazar a chave em logs/auditoria

1. A mitigacao desta secao foi consolidada no slice de `IA Settings` entre `sistema/app/routers/transport_ai.py` e `sistema/app/services/transport_ai_observability.py`, cobrindo explicitamente dois pontos de vazamento que ainda podiam carregar o segredo submetido pelo admin: o `detail` devolvido pelo endpoint em falhas controladas e a ausencia de uma auditoria sanitizada quando o save falhava.
2. Em `sistema/app/routers/transport_ai.py` foi introduzido o helper `_sanitize_transport_ai_router_message(...)`, que agora sanitiza mensagens antes de truncar o texto de erro devolvido ao cliente. O ponto importante desta secao e que o helper passou a aceitar `extra_literal_secrets`, permitindo redigir tambem segredos que nao estao em variaveis globais e nao seguem o padrao `sk-...`, como a chave submetida no proprio request do widget `IA Settings`.
3. O handler `PUT /api/transport/ai/settings` deixou de devolver `str(exc)` cru em falhas de validacao. Quando `upsert_transport_ai_llm_settings(...)` levanta erro, o endpoint agora sanitiza a mensagem usando a chave recebida em `payload.api_key` como literal secreto extra, evitando que o segredo reapareca em `detail` mesmo se a excecao carregar a chave bruta.
4. O mesmo endurecimento foi aplicado ao caminho de erro de criptografia do `PUT` e ao `GET /api/transport/ai/settings`: o detalhe HTTP passou a sair do router ja sanitizado, em vez de depender apenas do texto bruto retornado pela exception.
5. Para cobrir a parte de auditoria desta secao, foi adicionada em `sistema/app/services/transport_ai_observability.py` a trilha `record_transport_ai_settings_failure(...)`, usando o mesmo `action="settings_update"`, mas com `status="failed"`, mensagem curta mascarada e `details` JSON sanitizado. O payload auditado agora registra apenas metadados seguros como `requested_provider`, `submitted_api_key_hint`, `previous_provider`, `request_path`, `failure_detail` e `response_detail`, sem persistir a chave completa.
6. No router foi adicionado `_record_transport_ai_settings_failure_event(...)` para tornar esse caminho seguro tambem do ponto de vista transacional: antes de registrar o evento de falha, o request faz `rollback()` da sessao para descartar qualquer `TransportAILlmSettings` parcial que pudesse ter sido adicionado ao `Session`; depois reconstitui o ator administrativo e grava apenas o evento auditavel sanitizado. Isso fecha o risco de a auditoria de falha acabar comitando estado incompleto junto com o log.
7. A cobertura automatizada desta secao foi ampliada em `tests/test_transport_ai_router.py` com o teste `test_transport_ai_settings_endpoint_sanitizes_failed_update_details_and_audit`, que monkeypatcha `upsert_transport_ai_llm_settings(...)` para levantar uma excecao contendo a chave bruta `deepseek-secret-5678` e `Bearer top-secret`, e entao valida simultaneamente que:
   - a resposta `409` nao devolve nem a chave nem o bearer token no `detail`;
   - o evento `check_events` de `transport_ai/settings_update` com `status=failed` tambem nao vaza esses valores;
   - a auditoria passa a registrar apenas `submitted_api_key_hint='***5678'` e os detalhes sanitizados do erro.
8. O teste existente do caminho feliz `test_transport_ai_settings_endpoint_saves_masked_configuration_and_audits_safely` foi ajustado para consultar explicitamente o evento `status='success'`, porque o fluxo desta secao agora registra tambem eventos `settings_update` com `status='failed'` quando o save falha de forma controlada.
9. A validacao executada para esta secao foi:
   - `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_router.py::test_transport_ai_settings_endpoint_sanitizes_failed_update_details_and_audit -q`
   - `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_router.py::test_transport_ai_router_requires_transport_session_and_exposes_openapi tests/test_transport_ai_router.py::test_transport_ai_settings_endpoint_saves_masked_configuration_and_audits_safely tests/test_transport_ai_router.py::test_transport_ai_settings_endpoint_returns_controlled_error_when_saved_provider_is_no_longer_supported tests/test_transport_ai_router.py::test_transport_ai_settings_endpoint_sanitizes_failed_update_details_and_audit -q`
   - resultado: 4 testes verdes, confirmando sanitizacao do `detail`, auditoria mascarada de falha e preservacao dos fluxos existentes de autenticacao, sucesso e provider nao suportado.

### 11.4 Alterar provider enquanto existe suggestion salva

1. A mitigacao desta secao foi concluida no contrato de revisao de suggestions salvas: o snapshot `llm_provider`, `llm_model` e `llm_reasoning_effort`, que ja era congelado em `TransportAIRun`, passou a ser exposto explicitamente tambem em `TransportAgentRunStatusResponse`, evitando que o admin precise inferir o provider de uma suggestion salva a partir das `IA Settings` atuais do ambiente.
2. Em `sistema/app/schemas.py`, `TransportAgentRunStatusResponse` foi ampliado com os campos `llm_provider`, `llm_model` e `llm_reasoning_effort`. Com isso, qualquer endpoint que devolve o status de uma run/suggestion (`/route-calculations/{run_key}`, `/suggestions/latest`, `/suggestions/{suggestion_key}/save`, `/suggestions/{suggestion_key}/apply`, `/suggestions/{suggestion_key}/cancel`) passa a carregar o contexto LLM congelado da run no proprio payload de resposta.
3. Em `sistema/app/routers/transport_ai.py`, o helper que resolvia os campos LLM do diagnostico foi generalizado para `_resolve_transport_ai_run_llm_snapshot_fields(run)`, e o builder `_build_transport_ai_run_status_response(...)` passou a usalo antes de montar a resposta. Isso centraliza a leitura do snapshot da run em um unico lugar e evita que o fluxo de review de suggestion salve qualquer dependencia acidental do provider atualmente configurado no dashboard.
4. O comportamento legado para runs antigas foi preservado no mesmo helper: quando `llm_provider`/`llm_model`/`llm_reasoning_effort` nao estao preenchidos, o router continua derivando fallback compativel a partir de `openai_model`, sem quebrar a leitura historica de runs criadas antes do snapshot completo.
5. O efeito pratico da mitigacao desta secao e que, se uma suggestion ficar em estado `saved` e o admin trocar depois o provider global de `IA Settings`, os endpoints de review continuam mostrando o provider/modelo/reasoning originalmente usados para gerar aquela suggestion, em vez de refletirem o provider atual do ambiente e confundirem reproducao, triagem ou auditoria operacional.
6. A cobertura automatizada foi ampliada em `tests/test_transport_ai_router.py` com o teste `test_transport_ai_latest_suggestion_keeps_run_llm_snapshot_after_provider_changes`, que semeia uma run/suggestion salva com snapshot `deepseek / deepseek-v4-pro / high`, altera as `IA Settings` atuais para `openai` via `PUT /api/transport/ai/settings` e valida que tanto `GET /api/transport/ai/suggestions/latest` quanto o re-save idempotente da suggestion continuam devolvendo `llm_provider='deepseek'`, `llm_model='deepseek-v4-pro'` e `llm_reasoning_effort='high'`.
7. Como validacao adjacente do mesmo contrato, os testes de status de run e o fluxo integrado de `start -> save -> latest -> apply` tambem continuaram verdes apos a mudanca, confirmando que a ampliacao do schema de status nao regrediu os endpoints ja existentes que reutilizam `TransportAgentRunStatusResponse`.
8. A validacao executada para esta secao foi:
   - `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_router.py::test_transport_ai_latest_suggestion_keeps_run_llm_snapshot_after_provider_changes -q`
   - `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_router.py::test_transport_ai_run_status_returns_proposed_suggestion tests/test_transport_ai_router.py::test_transport_ai_run_status_returns_failed_error_message tests/test_transport_ai_router.py::test_transport_ai_latest_suggestion_keeps_run_llm_snapshot_after_provider_changes tests/test_api_flow.py::test_transport_ai_api_flow_start_suggestion_save_latest_apply -q`
   - resultado: 4 testes verdes, confirmando que a suggestion salva continua presa ao snapshot LLM da run mesmo depois de o provider atual do dashboard ser alterado.

## 12. Checklist de aceite

1. O item 1 foi verificado no frontend estatico entre `sistema/app/static/transport/index.html` e `sistema/app/static/transport/app.js`: o menu `IA` expõe exatamente as acoes `calculate-routes`, `implement-modifications` e `settings`, e o teste `transport ai settings modal opens from the AI menu, loads masked state, and cancel closes without save request` confirma em runtime que a ordem renderizada e `Calcular Rotas`, `Implementar Modifications` e `IA Settings`.
2. O item 2 foi verificado pela separacao estrutural entre o modal grande `transport-settings-modal` e o shell dedicado `transport-ai-settings-modal`, estilizado por `.transport-ai-settings-modal` em `sistema/app/static/transport/styles.css`. O teste `transport ai settings modal keeps dedicated menu, request, and feedback hooks` garante que `IA Settings` usa o widget dedicado, e nao o modal geral de configuracoes.
3. O item 3 foi confirmado no markup do widget dedicado, que expõe os hooks `data-ai-settings-provider`, `data-ai-settings-api-key`, `data-ai-settings-cancel` e `data-ai-settings-save`, e no teste `transport ai settings modal opens from the AI menu, loads masked state, and cancel closes without save request`, que valida em runtime o `SELECT` de provider, o `INPUT password` da chave e os botoes de cancelar/salvar.
4. O item 4 foi verificado nos defaults sincronizados entre frontend e backend: `TRANSPORT_AI_SETTINGS_PROVIDER_DEFAULTS.openai` em `sistema/app/static/transport/app.js` e `TRANSPORT_AI_LLM_PROVIDER_DEFAULTS['openai']` em `sistema/app/services/transport_ai_llm_settings.py` resolvem `gpt-5.4-2026-03-05` com `reasoning_effort='high'`. O teste frontend de save confirma tambem que o note do provider mostra esse contrato quando `OpenAI` esta selecionado.
5. O item 5 foi verificado pelos mesmos defaults sincronizados para `deepseek`, tanto no widget quanto no backend persistido: `deepseek-v4-pro` com `reasoning_effort='high'`. O teste frontend `transport ai settings save flow updates the provider note, posts the trimmed payload, and closes on success` valida a troca visual do note para `DeepSeek`, e os testes backend de runtime/route calculation confirmam que esse snapshot e realmente usado na execucao.
6. O item 6 foi confirmado pelo fluxo de cancelamento do widget: `closeAiSettingsModal(...)` fecha o shell sem emitir `PUT`, e o teste frontend `transport ai settings modal opens from the AI menu, loads masked state, and cancel closes without save request` conta explicitamente as chamadas antes/depois do clique em `Cancelar` para garantir que nada e persistido.
7. O item 7 foi verificado no backend pelo endpoint `PUT /api/transport/ai/settings` e pelo teste `test_transport_ai_settings_endpoint_saves_masked_configuration_and_audits_safely`: o save persiste `provider`, `model_name`, `reasoning_effort`, `api_key_last4` e `api_key_ciphertext` em `TransportAILlmSettings`, mantendo a chave apenas cifrada em repouso, nunca em claro, e auditando apenas metadados seguros como `api_key_hint='***1234'`.
8. O item 8 foi confirmado no mesmo teste de router e tambem no `GET /api/transport/ai/settings`: a resposta publica devolve somente `provider`, `resolved_model`, `reasoning_effort`, `has_api_key` e `api_key_hint`, sem ecoar a chave bruta nem o ciphertext. O teste ainda valida que a tentativa de trocar provider sem nova chave devolve erro controlado sem vazar o segredo anterior.
9. O item 9 foi verificado por dois caminhos complementares. Em `tests/test_transport_ai_runtime.py`, `test_validate_transport_ai_runtime_configuration_reports_missing_persisted_llm_settings` prova que o runtime nao aceita mais cair no legado sem settings persistidos; e `test_validate_transport_ai_runtime_configuration_accepts_complete_configuration` confirma que a configuracao persistida completa habilita a execucao. Em `tests/test_transport_ai_route_calculations.py`, `test_route_calculations_agent_mode_uses_persisted_llm_snapshot` comprova que uma run real em modo `agent` usa o provider salvo no dashboard (`deepseek`) e nao um valor legado do ambiente.
10. O item 10 foi confirmado no mesmo teste de route calculation: a `TransportAIRun` criada pela execucao passa a registrar `llm_provider='deepseek'`, `llm_model='deepseek-v4-pro'` e `llm_reasoning_effort='high'`. Esse snapshot tambem foi exposto no contrato de resposta por `TransportAgentRunStatusResponse` em `sistema/app/schemas.py` e pelo builder `_build_transport_ai_run_status_response(...)` em `sistema/app/routers/transport_ai.py`, garantindo que as runs novas reportem exatamente o LLM usado.
11. O item 11 foi verificado em quatro superficies. Primeiro, `test_transport_ai_settings_endpoint_saves_masked_configuration_and_audits_safely` e `test_transport_ai_settings_endpoint_sanitizes_failed_update_details_and_audit` confirmam que sucesso e falha de `IA Settings` nao vazam a chave nem na resposta HTTP nem na auditoria. Segundo, `test_run_transport_ai_agent_uses_run_llm_snapshot_and_sanitizes_persisted_api_key` confirma que ate o `raw_model_response_json` gravado pela run sai redigido com `[REDACTED]`. Terceiro, `test_route_calculations_agent_mode_uses_persisted_llm_snapshot` confirma que o audit trail operacional carrega `llm_provider`/`llm_model` mas nao a chave nem o token do route provider. Quarto, `test_transport_operational_plan_export_includes_ai_suggestion_tabs_for_agent_proposal` valida que o export `AI Summary` mostra apenas `LLM Provider`, `LLM Model` e `LLM Reasoning Effort`, sem qualquer material secreto.
12. O item 12 foi confirmado na rodada final desta secao com execucao automatizada dedicada no frontend e no backend. O frontend passou com `node --test tests/transport_page_date.test.js --test-name-pattern="transport ai settings"`, cobrindo menu, widget, cancel/save, mensagens controladas e estados de erro/pending. O backend passou com `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_router.py tests/test_transport_ai_route_calculations.py::test_route_calculations_agent_mode_uses_persisted_llm_snapshot tests/test_transport_ai_runtime.py tests/test_transport_ai_agent_runtime.py tests/test_api_flow.py::test_transport_operational_plan_export_includes_ai_suggestion_tabs_for_agent_proposal -q`, totalizando 98 testes frontend verdes e 30 testes backend verdes nesta verificacao final.

A validacao executada para esta secao foi:
- `node --test tests/transport_page_date.test.js --test-name-pattern="transport ai settings"`
- `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_router.py tests/test_transport_ai_route_calculations.py::test_route_calculations_agent_mode_uses_persisted_llm_snapshot tests/test_transport_ai_runtime.py tests/test_transport_ai_agent_runtime.py tests/test_api_flow.py::test_transport_operational_plan_export_includes_ai_suggestion_tabs_for_agent_proposal -q`
- resultado: 98 testes frontend verdes e 30 testes backend verdes, cobrindo a checklist completa de `IA Settings` do menu/widget ate persistencia segura, runtime, snapshot de runs e export operacional.

## 13. Ordem recomendada de execucao

Para minimizar retrabalho, executar nesta ordem:

1. Fase 0 de confirmacao do adapter DeepSeek e da estrategia de criptografia.
2. Persistencia segura + endpoints backend.
3. Refatoracao do runtime da IA para multi-provider.
4. Widget/frontend.
5. Ajustes de auditoria e diagnostico.
6. Regressao automatizada.
7. Validacao manual em preview local.

Essa ordem evita implementar a UI antes de existir um contrato seguro para guardar e ler a configuracao, e evita reescrever o frontend depois por causa de detalhes de masking ou semantica de troca de provider.