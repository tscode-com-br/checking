# Fase 1 - auditoria e saneamento das localizacoes cadastradas

## 1. Objetivo

Este documento operacionaliza a Fase 1 da migracao para localizacao poligonal no web.

Ele existe para:

- executar a auditoria tecnica das localizacoes ja cadastradas;
- mapear os resultados do script de auditoria para os itens da Fase 1;
- orientar o saneamento manual antes da ativacao da nova engine geometrica.

Importante: esta fase nao altera o layout do admin. O foco aqui e auditar os dados existentes.

## 2. Ferramenta implementada para a fase

Script operacional:

- `scripts/audit_locations.py`

Servico backend reutilizavel:

- `sistema/app/services/location_audit.py`

Testes automatizados:

- `tests/test_location_audit.py`

## 3. Como executar a auditoria

### 3.1 Saida texto

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/audit_locations.py
```

### 3.2 Saida JSON

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/audit_locations.py --format json
```

### 3.3 Salvar relatorio em arquivo

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/audit_locations.py --format json --output audit_locations_report.json
```

### 3.4 Incluir localizacoes sem problema na saida texto

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/audit_locations.py --include-valid
```

### 3.5 Tornar warnings impeditivos no pipeline

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/audit_locations.py --fail-on-warnings
```

## 4. Cobertura item por item da Fase 1

### 4.1 Item 1.1 - Levantar todas as localizacoes existentes

Cobertura implementada:

- o script audita todas as linhas da tabela `locations`;
- com `--include-valid`, ele lista inclusive localizacoes sem problema;
- com `--format json`, ele gera base estruturada para planilha ou consolidacao externa.

### 4.2 Item 1.2 - Identificar localizacoes com menos de 3 coordenadas

Cobertura implementada:

- issue code: `too_few_coordinates`.

### 4.3 Item 1.3 - Identificar coordenadas duplicadas

Cobertura implementada:

- issue code: `duplicate_coordinates`;
- issue code auxiliar: `redundant_closing_vertex` quando o ultimo ponto repete o primeiro.

### 4.4 Item 1.4 - Identificar vertices colineares ou poligonos degenerados

Cobertura implementada:

- issue code: `zero_area_polygon`.

Observacao:

- este codigo cobre tanto vertices estritamente colineares quanto outras formas degeneradas cuja area final e nula ou praticamente nula.

### 4.5 Item 1.5 - Identificar ordem de vertices potencialmente incorreta

Cobertura implementada:

- issue code: `self_intersection`;
- issue code auxiliar: `potential_vertex_order_problem`.

Observacao:

- o sistema nao tenta adivinhar a ordem correta dos vertices;
- ele apenas marca geometrias cuja ordem atual provavelmente precisa revisao manual.

### 4.6 Item 1.6 - Separar zonas especiais de checkout

Cobertura implementada:

- cada linha auditada informa `is_checkout_zone`;
- o resumo consolida `checkout_zone_locations`.

### 4.7 Item 1.7 - Identificar auto-interseccao

Cobertura implementada:

- issue code: `self_intersection`.

### 4.8 Item 1.8 - Gerar relatorio consolidado para saneamento

Cobertura implementada:

- o script gera relatorio em texto e JSON;
- a saida por linha inclui:
  - id da localizacao;
  - nome do local;
  - projetos associados;
  - quantidade total de coordenadas;
  - quantidade efetiva de vertices;
  - quantidade de vertices distintos;
  - flag de checkout;
  - area aproximada do poligono;
  - lista de issues.

## 5. Itens manuais desta fase

### 5.1 Item 1.9 - Validar com a area de negocio quais localizacoes devem ser corrigidas

Procedimento recomendado:

- exportar a saida JSON do script;
- filtrar as localizacoes com `has_errors = true` ou `needs_manual_review = true`;
- revisar cada registro com a operacao responsavel pelo cadastro;
- decidir se a localizacao deve ser corrigida, removida ou mantida temporariamente fora de uso.

### 5.2 Item 1.10 - Definir criterio de aceite para ativacao da nova engine

Criterio recomendado para esta migracao:

- nenhuma localizacao ativa deve permanecer com `has_errors = true`;
- nenhuma localizacao ativa deve permanecer com `needs_manual_review = true` sem aprovacao explicita;
- o alvo recomendado antes do corte e `100%` das localizacoes ativas aptas a formar poligonos validos.

### 5.3 Item 1.11 - Definir politica de bloqueio de localizacoes invalidas

Politica recomendada para as fases seguintes:

- durante a auditoria, apenas relatar;
- durante a implementacao da nova validacao de cadastro, bloquear novos salvamentos invalidos;
- antes do go-live da nova engine, impedir que localizacoes ativas com erro geometricamente impeditivo permaneçam no catalogo produtivo.

### 5.4 Item 1.12 - Revisao manual das localizacoes legadas de ponto unico

Cobertura implementada:

- issue code: `legacy_primary_coordinate_only`.

Procedimento recomendado:

- toda localizacao marcada com `legacy_primary_coordinate_only` deve entrar em fila de conversao para poligono real;
- a revisao deve definir ao menos 3 vertices ordenados;
- o objetivo final e zerar esse issue code antes da ativacao da nova engine poligonal.

## 6. Significado dos issue codes atuais

- `legacy_primary_coordinate_only`: a localizacao ainda depende da coordenada primaria legada e nao possui lista valida de vertices.
- `malformed_coordinates_json`: o JSON persistido das coordenadas esta corrompido ou invalido.
- `invalid_coordinate_entries`: existem entradas nao numericas, incompletas ou malformadas na lista persistida.
- `too_few_coordinates`: a localizacao nao possui vertices suficientes para formar um poligono.
- `redundant_closing_vertex`: o ultimo vertice repete o primeiro e deve ser removido da lista persistida.
- `duplicate_coordinates`: ha vertices duplicados na lista.
- `too_few_unique_coordinates`: apos remover duplicatas, restam menos de 3 vertices distintos.
- `zero_area_polygon`: a geometria tem area nula ou praticamente nula.
- `self_intersection`: as arestas do poligono se cruzam.
- `potential_vertex_order_problem`: a ordem atual dos vertices provavelmente precisa revisao manual.

## 7. Resultado esperado da Fase 1

- o time consegue listar e classificar todas as localizacoes cadastradas;
- o time consegue separar erros impeditivos de warnings;
- o time consegue montar a fila de saneamento antes da nova engine de matching;
- o layout do admin permanece inalterado nesta fase.