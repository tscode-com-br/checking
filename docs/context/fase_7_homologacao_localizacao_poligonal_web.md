# Fase 7 - homologacao funcional da localizacao poligonal no webapp

## 1. Resumo da execucao

- Script executado: `scripts/homologate_phase_7_locations.py`.
- Gerado em: `2026-04-23T16:10:31.241767+00:00`.
- Ambiente: SQLite temporario isolado criado apenas para a homologacao automatizada.
- Resultado automatico: `8/8` cenarios automaveis aprovados.
- Escopo manual pendente: itens `7.9` e `7.10`, que dependem de usuarios de negocio e uso guiado do admin.

## 2. Conjunto controlado preparado

| Projeto | Local | Vertices | Tolerancia (m) | Finalidade |
| --- | --- | ---: | ---: | --- |
| H71 | Homolog Dentro H71 | 4 | 150 | cenario base de usuario claramente dentro da area |
| H72 | Homolog Fora H72 | 4 | 25 | cenario de usuario claramente fora da area expandida |
| H73 | Homolog Borda H73 | 4 | 25 | cenario de tangencia na borda do poligono expandido |
| H74 | Homolog Precisao H74 | 4 | 120 | cenario de rejeicao por baixa qualidade do GPS |
| H75 | Homolog Multiplo A H75 | 4 | 120 | primeiro poligono do cenario de multiplas interseccoes |
| H75 | Homolog Multiplo B H75 | 4 | 120 | segundo poligono do cenario de multiplas interseccoes |
| H76 | Homolog Proximo H76 | 4 | 120 | cenario de localizacao nao cadastrada ainda dentro do ambiente de trabalho |
| H77 | Homolog Trabalho Distante H77 | 4 | 120 | local de trabalho usado para validar a regra acima de 2 km |
| H77 | Zona de CheckOut | 4 | 20 | checkout zone proxima que deve ser ignorada no calculo dos 2 km |
| H7L | Homolog Regular H7L | 4 | 90 | local regular usado para captura de logs detalhados |
| H7L | Zona de CheckOut | 4 | 90 | checkout zone usada para validar logs de decisao geometrica |

## 3. Resultado por item da Fase 7

| Item | Status | Evidencia |
| --- | --- | --- |
| 7.1 | parcial | Conjunto controlado preparado para homologacao: 11 localizacoes validas criadas em banco isolado; o ambiente atual nao expunha um catalogo real revisado para replicar o item com dados operacionais |
| 7.2 | aprovado | Usuario claramente dentro da area: status=matched; label=Homolog Dentro H71; resolved_local=Homolog Dentro H71 |
| 7.3 | aprovado | Usuario claramente fora da area: status=not_in_known_location; label=Localização não Cadastrada; nearest=58.00 m |
| 7.4 | aprovado | Usuario na borda da area expandida: status=matched; label=Homolog Borda H73; resolved_local=Homolog Borda H73 |
| 7.5 | aprovado | Baixa precisao GPS rejeitada pelo limite global: status=accuracy_too_low; label=Precisao insuficiente; threshold=15 |
| 7.6 | aprovado | Multiplos poligonos proximos com desempate deterministico: status=matched; resolved_local=Homolog Multiplo A H75; label=Homolog Multiplo A H75 |
| 7.7 | aprovado | Localizacao nao cadastrada dentro do ambiente de trabalho: status=not_in_known_location; label=Localização não Cadastrada; nearest=530.76 m |
| 7.8 | aprovado | Fora do local de trabalho acima de 2 km: status=outside_workplace; label=Fora do Ambiente de Trabalho; nearest=3096.12 m |
| 7.12 | aprovado | Logs de decisao geometrica revisados durante a homologacao: status=matched; label=Zona de Check-Out; logs_capturados=1 |
| 7.9 | pendente manual | Validacao com usuarios de negocio sobre a area fisica: nao executavel no workspace sem deslocamento em campo e sem operador de negocio acompanhando os casos reais |
| 7.10 | pendente manual | Validacao de compreensao da ordem dos vertices no admin: nao executavel apenas com API e testes automatizados; depende de sessao assistida de UX com quem cadastra localizacoes |
| 7.11 | parcial | Correcao de localizacoes problematica antes da ativacao: auditoria do conjunto controlado retornou errors=0 e warnings=0; o catalogo real do ambiente alvo segue pendente de reauditoria antes do corte |

## 4. Auditoria do conjunto controlado

- Linhas auditadas: `11`.
- Localizacoes com erro: `0`.
- Localizacoes apenas com warning: `0`.
- Total de zonas de checkout: `2`.
- Contagem de issues: `{}`.

## 5. Evidencia de logs de decisao geometrica

```text
location_match_decision latitude=1.26601 longitude=103.62112 accuracy_meters=8.0 selection_source=polygon_checkout matched_location_id=11 matched_local=Zona de CheckOut nearest_workplace_distance_meters=0.0 polygon_evaluated=[10, 11] polygon_intersections=[10, 11] skipped_invalid_locations=[]
```

## 6. Pendencias humanas para concluir a homologacao em campo

- Item 7.9: validar com usuarios de negocio, em local fisico real, se a area interpretada pelo poligono corresponde ao perimetro operacional esperado.
- Item 7.10: pedir que um usuario administrativo monte e reordene vertices no admin sem assistencia tecnica, registrando se a ordem dos vertices ficou compreensivel.
- Item 7.11 no catalogo real: repetir a auditoria no ambiente alvo antes do corte, porque este relatorio cobre apenas o conjunto controlado usado na homologacao automatizada.
