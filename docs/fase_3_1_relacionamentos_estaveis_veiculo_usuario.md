# Fase 3.1 - Migração de vínculos mutáveis para identificadores estáveis

## Objetivo

Esta etapa inicia a substituição do vínculo entre usuário e veículo, que antes dependia diretamente de `User.placa`, por um relacionamento técnico baseado em `User.vehicle_id -> Vehicle.id`. A placa continua existindo no modelo e nas respostas atuais como atributo compatível, mas deixa de ser a referência principal de integridade relacional.

## O que foi implementado

1. O modelo `User` passou a incluir `vehicle_id` como chave estrangeira opcional para `vehicles.id`.
2. A coluna `placa` em `users` foi mantida como espelho compatível, mas deixou de carregar o FK para `vehicles.placa`.
3. A migration `alembic/versions/0041_add_user_vehicle_id_link.py` adiciona a nova coluna, cria o FK técnico, faz backfill a partir das placas já salvas e remove o FK legado por placa.
4. O módulo `sistema/app/services/transport_vehicle_base.py` passou a concentrar a resolução e a sincronização do vínculo `User <-> Vehicle`, inclusive com fallback para linhas legadas que ainda só possuem `placa`.
5. O endpoint `POST /api/admin/users` agora aceita continuar operando por `placa`, mas também aceita `vehicle_id` como referência estável; quando um veículo é resolvido, o backend persiste `vehicle_id` e atualiza `placa` como espelho.
6. O endpoint `GET /api/admin/users` passou a expor `vehicle_id`, permitindo que consumidores futuros deixem de depender de placa textual para relacionar usuários a veículos.
7. Os fluxos `PUT /api/transport/vehicles/{vehicle_id}` e `DELETE /api/transport/vehicles/{schedule_id}` passaram a sincronizar ou limpar o vínculo dos usuários por `vehicle_id` e, quando necessário, por fallback de `placa` para compatibilidade com registros ainda não migrados em memória de aplicação.

## Impacto estrutural

Com esta mudança, editar a placa de um veículo deixa de exigir que o vínculo principal do usuário seja refeito por texto. O identificador estável do veículo permanece o mesmo, e `placa` passa a acompanhar a mudança apenas como atributo derivado compatível para a superfície administrativa já existente.

## Compatibilidade preservada

1. O payload atual do admin que envia apenas `placa` continua funcionando.
2. As respostas administrativas continuam trazendo `placa`.
3. Registros legados em que `User.vehicle_id` ainda não estava preenchido continuam sendo reconciliados pelos fluxos de atualização e remoção de veículo.

## Validação executada

Foram validados slices focados do backend cobrindo:

1. upsert/listagem de usuário com vínculo de transporte no admin;
2. atualização de veículo preservando assignments e sincronizando o vínculo do usuário;
3. remoção de veículo limpando o vínculo do usuário e retornando requests para pendência.

## Limite desta fase

Esta fase trata especificamente do vínculo `User -> Vehicle`. Outros relacionamentos ainda baseados em chaves mutáveis, como partes do acoplamento por `workplace` nominal, permanecem para etapas seguintes da Fase 3.