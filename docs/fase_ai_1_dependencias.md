# Fase AI 1.1 - Dependencias de IA, mapas e otimizacao

## Objetivo

Registrar as dependencias escolhidas para a primeira etapa de preparacao do agente de IA do modulo `transport`, com versoes fixadas a partir de validacao local no ambiente atual do projeto.

## Dependencias adicionadas em runtime

As seguintes dependencias passaram a fazer parte de `requirements.txt`:

1. `httpx==0.28.1`
2. `langchain==1.2.15`
3. `langchain-openai==1.2.1`
4. `ortools==9.15.6755`

## Motivo das escolhas

1. `httpx==0.28.1`: cliente HTTP assíncrono/síncrono para integrar o provider de mapas com controle explícito de timeout, retry e transporte fake em testes.
2. `langchain==1.2.15`: camada de orquestracao do agente, tools, structured output e fluxo controlado de execucao no backend Python.
3. `langchain-openai==1.2.1`: integracao oficial do LangChain com os modelos OpenAI que serao usados nas fases futuras do agente.
4. `ortools==9.15.6755`: base para o solver deterministico de roteirizacao e otimizacao de frota/capacidade/janela de horario.

## Ajustes complementares

1. `httpx` foi removido de `requirements-dev.txt`, porque agora faz parte das dependencias de runtime e ja entra automaticamente no ambiente de desenvolvimento via `-r requirements.txt`.
2. O `Dockerfile` ja instala a imagem a partir de `requirements.txt`, entao a imagem local/produtiva passa a herdar os mesmos pins sem outro ajuste nesta fase.
3. O OR-Tools instalou corretamente no `venv` local, entao nao foi necessario ativar nesta etapa uma flag temporaria para desabilitar o solver. Se o custo/tamanho da imagem Docker se mostrar problematico numa fase posterior, a estrategia de fallback heuristico continua prevista no plano.

## Validacoes executadas

1. `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pip install --disable-pip-version-check -r requirements.txt`
2. `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -c "import langchain; import langchain_openai; import httpx; import ortools"`
3. `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k transport`

## Resultado da validacao

1. O ambiente resolveu e manteve todas as dependencias com os pins definidos em `requirements.txt`.
2. Os imports de `langchain`, `langchain_openai`, `httpx` e `ortools` executaram com sucesso.
3. A suite focada em transporte passou com `81 passed, 176 deselected`, confirmando que a inclusao das novas dependencias nao quebrou os imports nem o recorte atual do backend `transport`.
4. Durante o import em Python `3.14.3`, o `langchain_core` emitiu um aviso nao bloqueante sobre compatibilidade de caminhos legados de Pydantic V1 em Python `3.14+`. A validacao seguiu verde, e o runtime de container do projeto permanece em `python:3.12-slim`, que continua sendo o alvo principal desta etapa.