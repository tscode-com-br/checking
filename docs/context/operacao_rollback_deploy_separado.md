# Operacao e rollback de deploy separado

## Objetivo

Centralizar os runbooks operacionais que exigem janela controlada, validacao host-side e rollback parcial sem perda de dados operacionais sensiveis.

## Runbooks ativos nesta pasta

### Transport AI por projeto

- Runbook detalhado: `docs/context/transport_ai_project_rollout.md`
- Artefatos operacionais relacionados:
  - `deploy/.env.production.example`
  - `scripts/export_transport_ai_legacy_llm_settings.py`
  - `scripts/backfill_transport_ai_project_llm_settings.py`
  - `tests/test_transport_ai_rollout_scripts.py`

Regras adicionais:

1. manter `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY` estavel durante toda a janela de migracao;
2. nunca replicar o singleton legado automaticamente para todos os projetos;
3. preservar a tabela nova e os dados criptografados mesmo em rollback parcial;
4. remover o caminho legado global apenas depois de homologacao e decisao operacional explicita;
5. se o rollback atingir apenas o modal `IA Settings` ou o smoke opt-in, reverter somente essa superficie sem reintroduzir fallback global implicito.

### Hardening do edge

- Documento de incidente e endurecimento: `docs/incidents/2026-05-05-504-phase7-edge-surface-hardening.md`

## Checklist minimo para qualquer rollout separado

1. preparar artefato de rollback antes do deploy;
2. registrar pre-condicoes e variaveis de ambiente criticas;
3. definir smoke test objetivo e curto;
4. evitar rollback destrutivo de dados quando a mudanca introduzir nova estrutura persistida;
5. deixar claro o que depende de execucao host-side e o que ja esta coberto no repositório;
6. quando o frontend estatico mudar contrato, registrar a versao coordenada dos assets servidos no deploy.