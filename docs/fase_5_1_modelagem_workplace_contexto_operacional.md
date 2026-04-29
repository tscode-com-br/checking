# Fase 5.1 - Enriquecimento de workplace e restricoes operacionais

## Objetivo

Esta fase amplia o papel de `Workplace` no dominio de transporte. O objetivo deixa de ser apenas armazenar um nome e endereco de referencia e passa a incluir informacoes operacionais que podem influenciar decisao, agrupamento e revisao futura de propostas.

## O que foi implementado

1. O modelo `Workplace` em `sistema/app/models.py` passou a suportar campos opcionais de contexto operacional.
2. Os contratos `TransportWorkplaceUpsert`, `TransportWorkplaceUpdate` e `WorkplaceRow` em `sistema/app/schemas.py` passaram a carregar os novos campos com validacao explicita.
3. O backend passou a expor `PUT /api/transport/workplaces/{workplace_id}` para enriquecer workplaces ja existentes sem recriar o cadastro.
4. A listagem de workplaces usada pelo dashboard e pelo snapshot passou a devolver o contexto operacional junto do cadastro basico.

## Campos adicionados ao workplace

Os workplaces agora podem carregar, de forma opcional:

1. `transport_group`: agrupamento operacional relevante para planejamento;
2. `boarding_point`: ponto operacional de referencia para embarque ou encontro;
3. `transport_window_start` e `transport_window_end`: janela operacional de atendimento;
4. `service_restrictions`: restricoes textuais especificas do atendimento; e
5. `transport_work_to_home_time`: horario contextual de retorno associado ao workplace.

## Impacto estrutural

Com isso, `Workplace` deixa de ser apenas um rotulo usado em formulario e passa a se comportar como fonte de contexto operacional leve, reutilizavel por dashboard, snapshots, proposal review e futuros fluxos de planejamento.

## Validacao executada

Foi validado o ciclo de criacao, atualizacao e listagem de workplaces com os novos campos operacionais, confirmando que a modelagem enriquecida entra no backend sem quebrar o cadastro existente.