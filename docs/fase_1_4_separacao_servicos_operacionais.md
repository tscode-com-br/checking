# Fase 1.4 - Separação de exportação, cadastro de veículo e persistência de alocação

## Objetivo desta etapa

Esta etapa executa a segunda extração estrutural concreta da reorganização do backend de transporte: separar exportação, operações de veículo e persistência de alocação em serviços internos distintos, sem alterar a superfície pública já consumida pelo roteador e pelos demais fluxos do sistema.

O objetivo desta fase não foi introduzir ainda o fluxo explícito de edição completa de veículo por identificador estável. Esse passo continua pertencendo à fase 2.3. Aqui, a meta foi preparar o terreno para isso, retirando do arquivo `sistema/app/services/transport.py` três blocos operacionais que ainda permaneciam concentrados no mesmo corpo monolítico.

## Implementação realizada

Foram criados três novos módulos internos de serviço:

- `sistema/app/services/transport_exports.py`
- `sistema/app/services/transport_vehicle_operations.py`
- `sistema/app/services/transport_assignment_operations.py`

Esses módulos passaram a concentrar os seguintes grupos de responsabilidade.

### 1. Exportação

O módulo `sistema/app/services/transport_exports.py` passou a concentrar:

- `_build_transport_export_file_name`
- `_resolve_transport_export_path`
- `build_transport_list_export`

Com isso, a geração do arquivo XLSX e a persistência do artefato em disco deixam de disputar espaço com regras de agenda, cadastro de veículo e materialização de assignments.

### 2. Operações de veículo e agenda

O módulo `sistema/app/services/transport_vehicle_operations.py` passou a concentrar:

- `create_transport_vehicle_registration`
- `delete_transport_vehicle_registration`
- `_purge_foreign_key_dependencies`
- `_build_schedule_specs_from_payload`
- `_classify_vehicle_schedules_for_reuse`
- `_build_vehicle_schedule_conflict_details`
- `_format_vehicle_schedule_conflict_entry`
- `_vehicle_has_active_schedule_for_spec`
- `_vehicle_has_active_schedule_on_date`
- `_resolve_regular_vehicle_selected_weekdays`
- `vehicle_schedule_applies_to_date`
- `find_transport_vehicle_schedule`
- `get_paired_route_kind`

Essa extração concentra em um único ponto as regras de reaproveitamento de placa, conflito de agenda, remoção de veículo, resolução de disponibilidade e leitura operacional da agenda do veículo.

### 3. Persistência de alocação e recorrência

O módulo `sistema/app/services/transport_assignment_operations.py` passou a concentrar:

- `update_transport_assignment`
- `_reset_transport_request_assignments_to_pending`
- `upsert_transport_assignment_with_persistence`
- `_propagate_confirmed_recurring_assignment`
- `_materialize_recurring_assignments_for_date`

Com isso, a persistência de alocação deixa de ficar espalhada entre regras de leitura, geração de exportação e cadastro de ativo operacional. O núcleo recorrente de confirmação, retorno a `pending` e materialização por dia agora está localizado em um serviço coerente com seu papel.

## Compatibilidade preservada

O arquivo `sistema/app/services/transport.py` foi mantido como superfície de compatibilidade. Em vez de continuar concentrando toda a implementação desses fluxos, ele agora delega para os novos serviços por meio de wrappers finos.

Essa decisão preserva o contrato já utilizado por:

- roteadores existentes;
- testes já escritos;
- pontos internos do sistema ainda não migrados para importar os novos módulos diretamente.

Também foi preservada a compatibilidade com monkeypatch de tempo usado nos testes, fazendo os serviços extraídos resolverem `now_sgt` a partir do módulo principal de transporte quando necessário.

## Resultado estrutural obtido

Depois desta etapa, o backend de transporte passa a ter uma separação interna mais clara entre quatro zonas:

1. leitura do dashboard, já extraída na fase 1.3;
2. exportação de artefatos administrativos;
3. operações de veículo e agenda operacional;
4. persistência de alocação e recorrência.

Isso reduz a sobreposição de responsabilidade dentro de `sistema/app/services/transport.py` e deixa mais explícito onde cada futura mudança deverá ocorrer.

Essa separação é particularmente importante para a exigência central do plano: permitir, em fase posterior, editar todas as características de um veículo já cadastrado sem depender de exclusão e recriação. A fase 1.4 ainda não entrega esse fluxo final, mas remove parte relevante do acoplamento que dificultava sua implementação segura.

## Arquivos alterados

- `sistema/app/services/transport_exports.py` - novo módulo dedicado à exportação.
- `sistema/app/services/transport_vehicle_operations.py` - novo módulo dedicado a veículo, agenda e disponibilidade operacional.
- `sistema/app/services/transport_assignment_operations.py` - novo módulo dedicado à persistência de assignment e recorrência.
- `sistema/app/services/transport.py` - simplificado com wrappers compatíveis para os grupos extraídos.

## Validação executada

Após a extração, foram executados testes focados em exportação, cadastro de veículo, remoção de veículo e recorrência de assignment.

Casos validados:

- `test_transport_export_endpoint_builds_xlsx_download_and_saves_server_copy`
- `test_transport_vehicle_registration_creates_route_aware_schedules`
- `test_transport_vehicle_delete_purges_vehicle_and_returns_requests_to_pending`
- `test_transport_regular_assignment_persists_across_weekdays_and_routes`
- `test_transport_weekend_assignment_respects_selected_persistent_weekdays`
- `test_transport_dashboard_pending_assignment_returns_request_to_pending_in_dashboard_and_webapp`

Resultado: todos os testes focados executados nesta etapa passaram com sucesso.

## Relação desta etapa com as próximas fases

Esta fase encerra a Fase 1 do plano com duas extrações estruturais concretas: primeiro a leitura do dashboard, depois os principais comandos operacionais restantes.

Com isso, as próximas fases passam a ter uma base mais segura para:

- formalizar o cadastro-base do veículo como entidade separada da agenda;
- criar o fluxo explícito de edição de veículo sem exclusão e recriação;
- revisar o impacto estrutural de mudança de placa, escopo e disponibilidade;
- preparar uma futura camada de proposta e aprovação com fronteiras operacionais menos ambíguas.