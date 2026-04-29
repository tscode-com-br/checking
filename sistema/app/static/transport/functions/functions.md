# Transport Dashboard Function Inventory

Inventario gerado automaticamente a partir de `sistema/app/static/transport/app.js` e `sistema/app/static/transport/i18n.js`.

Resumo:
- Total de funcoes nomeadas mapeadas: 192
- Arquivos individuais gerados: 192
- Indice complementar por capacidade funcional: `functions_by_capability.md`
- Callbacks anonimos permanecem dentro do codigo da funcao nomeada proprietaria, porque nao existe um nome estavel para virar nome de arquivo.
- Para consumo por agentes, um catalogo declarativo de acoes ainda seria uma superficie operacional melhor do que o espelhamento literal da UI.

## sistema/app/static/transport/app.js

### [getDictionaryForLanguage.md](getDictionaryForLanguage.md)

- Funcao no arquivo: `getDictionaryForLanguage`
- Origem: `sistema/app/static/transport/app.js:58`
- Escopo original: topo do modulo
- Tema funcional: dicionario do idioma
- Categoria: i18n
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `languageCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a dicionario do idioma, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getDictionary`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [resolveStoredLanguageCode.md](resolveStoredLanguageCode.md)

- Funcao no arquivo: `resolveStoredLanguageCode`
- Origem: `sistema/app/static/transport/app.js:70`
- Escopo original: topo do modulo
- Tema funcional: codigo de idioma persistido
- Categoria: i18n
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a codigo de idioma persistido, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `globalScope`, `localStorage`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Interage com `localStorage` para persistencia local do navegador.

### [setStoredLanguageCode.md](setStoredLanguageCode.md)

- Funcao no arquivo: `setStoredLanguageCode`
- Origem: `sistema/app/static/transport/app.js:89`
- Escopo original: topo do modulo
- Tema funcional: codigo de idioma persistido
- Categoria: i18n
- Responsabilidade: Rotina de sincronizacao do dashboard de transporte que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `languageCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `globalScope`, `localStorage`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Interage com `localStorage` para persistencia local do navegador.

### [resolveLanguageCode.md](resolveLanguageCode.md)

- Funcao no arquivo: `resolveLanguageCode`
- Origem: `sistema/app/static/transport/app.js:99`
- Escopo original: topo do modulo
- Tema funcional: codigo de idioma
- Categoria: i18n
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `languageCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a codigo de idioma, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getActiveLanguageCode.md](getActiveLanguageCode.md)

- Funcao no arquivo: `getActiveLanguageCode`
- Origem: `sistema/app/static/transport/app.js:105`
- Escopo original: topo do modulo
- Tema funcional: codigo de idioma ativo
- Categoria: i18n
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a codigo de idioma ativo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `resolveLanguageCode`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [setActiveLanguageCode.md](setActiveLanguageCode.md)

- Funcao no arquivo: `setActiveLanguageCode`
- Origem: `sistema/app/static/transport/app.js:109`
- Escopo original: topo do modulo
- Tema funcional: codigo de idioma ativo
- Categoria: i18n
- Responsabilidade: Rotina de sincronizacao do dashboard de transporte que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `languageCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `resolveLanguageCode`, `setStoredLanguageCode`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getLanguageConfig.md](getLanguageConfig.md)

- Funcao no arquivo: `getLanguageConfig`
- Origem: `sistema/app/static/transport/app.js:116`
- Escopo original: topo do modulo
- Tema funcional: configuracao de idioma
- Categoria: i18n
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `languageCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a configuracao de idioma, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `resolveLanguageCode`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [readTranslationValue.md](readTranslationValue.md)

- Funcao no arquivo: `readTranslationValue`
- Origem: `sistema/app/static/transport/app.js:124`
- Escopo original: topo do modulo
- Tema funcional: traducao valor
- Categoria: i18n
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `dictionary`, `keyPath` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a traducao valor, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [interpolateTranslation.md](interpolateTranslation.md)

- Funcao no arquivo: `interpolateTranslation`
- Origem: `sistema/app/static/transport/app.js:135`
- Escopo original: topo do modulo
- Tema funcional: traducao
- Categoria: i18n
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `template`, `values` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a traducao, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [t.md](t.md)

- Funcao no arquivo: `t`
- Origem: `sistema/app/static/transport/app.js:148`
- Escopo original: topo do modulo
- Tema funcional: t
- Categoria: utility
- Responsabilidade: Encapsula uma responsabilidade interna do dashboard de transporte, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `keyPath`, `values`, `languageCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getActiveLanguageCode`, `getDictionaryForLanguage`, `interpolateTranslation`, `readTranslationValue`, `resolveLanguageCode`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getTransportLockedMessage.md](getTransportLockedMessage.md)

- Funcao no arquivo: `getTransportLockedMessage`
- Origem: `sistema/app/static/transport/app.js:156`
- Escopo original: topo do modulo
- Tema funcional: transporte bloqueio mensagem
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a transporte bloqueio mensagem, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getTransportSessionExpiredMessage.md](getTransportSessionExpiredMessage.md)

- Funcao no arquivo: `getTransportSessionExpiredMessage`
- Origem: `sistema/app/static/transport/app.js:160`
- Escopo original: topo do modulo
- Tema funcional: transporte sessao expirada mensagem
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a transporte sessao expirada mensagem, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getDefaultStatusMessage.md](getDefaultStatusMessage.md)

- Funcao no arquivo: `getDefaultStatusMessage`
- Origem: `sistema/app/static/transport/app.js:164`
- Escopo original: topo do modulo
- Tema funcional: padrao mensagem de status
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a padrao mensagem de status, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [startOfLocalDay.md](startOfLocalDay.md)

- Funcao no arquivo: `startOfLocalDay`
- Origem: `sistema/app/static/transport/app.js:168`
- Escopo original: topo do modulo
- Tema funcional: de local dia
- Categoria: date/time
- Responsabilidade: Orquestra um fluxo operacional do dashboard de transporte, ligando validacao local, integracao externa, feedback visual e recarga de dados quando necessario.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getOrdinalSuffix.md](getOrdinalSuffix.md)

- Funcao no arquivo: `getOrdinalSuffix`
- Origem: `sistema/app/static/transport/app.js:173`
- Escopo original: topo do modulo
- Tema funcional: ordinal sufixo
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `day` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a ordinal sufixo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [formatTransportDate.md](formatTransportDate.md)

- Funcao no arquivo: `formatTransportDate`
- Origem: `sistema/app/static/transport/app.js:192`
- Escopo original: topo do modulo
- Tema funcional: transporte data
- Categoria: date/time
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a transporte data, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getActiveLanguageCode`, `getLanguageConfig`, `getOrdinalSuffix`, `startOfLocalDay`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [shiftLocalDay.md](shiftLocalDay.md)

- Funcao no arquivo: `shiftLocalDay`
- Origem: `sistema/app/static/transport/app.js:209`
- Escopo original: topo do modulo
- Tema funcional: local dia
- Categoria: date/time
- Responsabilidade: Encapsula uma responsabilidade interna do dashboard de transporte, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `value`, `amount` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `startOfLocalDay`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [formatIsoDate.md](formatIsoDate.md)

- Funcao no arquivo: `formatIsoDate`
- Origem: `sistema/app/static/transport/app.js:215`
- Escopo original: topo do modulo
- Tema funcional: ISO data
- Categoria: date/time
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a ISO data, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `startOfLocalDay`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [parseStoredTransportDate.md](parseStoredTransportDate.md)

- Funcao no arquivo: `parseStoredTransportDate`
- Origem: `sistema/app/static/transport/app.js:220`
- Escopo original: topo do modulo
- Tema funcional: persistido transporte data
- Categoria: date/time
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a persistido transporte data, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `startOfLocalDay`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [resolveStoredTransportDate.md](resolveStoredTransportDate.md)

- Funcao no arquivo: `resolveStoredTransportDate`
- Origem: `sistema/app/static/transport/app.js:243`
- Escopo original: topo do modulo
- Tema funcional: persistido transporte data
- Categoria: date/time
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `referenceValue` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a persistido transporte data, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `startOfLocalDay`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [setStoredTransportDate.md](setStoredTransportDate.md)

- Funcao no arquivo: `setStoredTransportDate`
- Origem: `sistema/app/static/transport/app.js:247`
- Escopo original: topo do modulo
- Tema funcional: persistido transporte data
- Categoria: utility
- Responsabilidade: Rotina de sincronizacao do dashboard de transporte que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `globalScope`, `localStorage`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Interage com `localStorage` para persistencia local do navegador.

### [getTransportDateState.md](getTransportDateState.md)

- Funcao no arquivo: `getTransportDateState`
- Origem: `sistema/app/static/transport/app.js:259`
- Escopo original: topo do modulo
- Tema funcional: transporte data state
- Categoria: date/time
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value`, `referenceValue` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a transporte data state, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `startOfLocalDay`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [isWeekendDate.md](isWeekendDate.md)

- Funcao no arquivo: `isWeekendDate`
- Origem: `sistema/app/static/transport/app.js:270`
- Escopo original: topo do modulo
- Tema funcional: fim de semana data
- Categoria: utility
- Responsabilidade: Predicate do dashboard de transporte que inspeciona os dados disponiveis e devolve a decisao booleana usada para permitir, negar ou destacar um comportamento.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor booleano usado para gating de UI, validacao ou destaque de estado.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `startOfLocalDay`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [createTransportDateStore.md](createTransportDateStore.md)

- Funcao no arquivo: `createTransportDateStore`
- Origem: `sistema/app/static/transport/app.js:275`
- Escopo original: topo do modulo
- Tema funcional: transporte data store
- Categoria: date/time
- Responsabilidade: Factory/builder do dashboard de transporte que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `initialValue` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: `getValue`, `notify`, `setValue`, `shiftValue`, `subscribe`
- Dependencias observadas: `shiftLocalDay`, `startOfLocalDay`, `unsubscribe`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getValue.md](getValue.md)

- Funcao no arquivo: `getValue`
- Origem: `sistema/app/static/transport/app.js:279`
- Escopo original: interna de `createTransportDateStore`
- Tema funcional: valor
- Categoria: date/time
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a valor, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [notify.md](notify.md)

- Funcao no arquivo: `notify`
- Origem: `sistema/app/static/transport/app.js:283`
- Escopo original: interna de `createTransportDateStore`
- Tema funcional: notify
- Categoria: utility
- Responsabilidade: Controla o ciclo de vida reativo do controller da pagina, registrando, disparando ou encerrando comportamento associado a mudancas de estado.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getValue`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [setValue.md](setValue.md)

- Funcao no arquivo: `setValue`
- Origem: `sistema/app/static/transport/app.js:290`
- Escopo original: interna de `createTransportDateStore`
- Tema funcional: valor
- Categoria: date/time
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `value`, `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getValue`, `notify`, `startOfLocalDay`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [shiftValue.md](shiftValue.md)

- Funcao no arquivo: `shiftValue`
- Origem: `sistema/app/static/transport/app.js:298`
- Escopo original: interna de `createTransportDateStore`
- Tema funcional: valor
- Categoria: date/time
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `amount` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `setValue`, `shiftLocalDay`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [subscribe.md](subscribe.md)

- Funcao no arquivo: `subscribe`
- Origem: `sistema/app/static/transport/app.js:302`
- Escopo original: interna de `createTransportDateStore`
- Tema funcional: subscribe
- Categoria: utility
- Responsabilidade: Controla o ciclo de vida reativo do controller da pagina, registrando, disparando ou encerrando comportamento associado a mudancas de estado.
- Entradas: Recebe `subscriber` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: `unsubscribe`
- Dependencias observadas: `getValue`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [unsubscribe.md](unsubscribe.md)

- Funcao no arquivo: `unsubscribe`
- Origem: `sistema/app/static/transport/app.js:310`
- Escopo original: interna de `subscribe`
- Tema funcional: unsubscribe
- Categoria: utility
- Responsabilidade: Controla o ciclo de vida reativo do controller da pagina, registrando, disparando ou encerrando comportamento associado a mudancas de estado.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [clampValue.md](clampValue.md)

- Funcao no arquivo: `clampValue`
- Origem: `sistema/app/static/transport/app.js:323`
- Escopo original: topo do modulo
- Tema funcional: valor
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value`, `minValue`, `maxValue` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a valor, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [parsePositiveNumber.md](parsePositiveNumber.md)

- Funcao no arquivo: `parsePositiveNumber`
- Origem: `sistema/app/static/transport/app.js:327`
- Escopo original: topo do modulo
- Tema funcional: positivo number
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value`, `fallbackValue` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a positivo number, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [parsePixelValue.md](parsePixelValue.md)

- Funcao no arquivo: `parsePixelValue`
- Origem: `sistema/app/static/transport/app.js:335`
- Escopo original: topo do modulo
- Tema funcional: pixel valor
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value`, `fallbackValue` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a pixel valor, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [resolvePanelSizes.md](resolvePanelSizes.md)

- Funcao no arquivo: `resolvePanelSizes`
- Origem: `sistema/app/static/transport/app.js:343`
- Escopo original: topo do modulo
- Tema funcional: painel sizes
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `clampValue`, `parsePositiveNumber`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [resolveResizeConfig.md](resolveResizeConfig.md)

- Funcao no arquivo: `resolveResizeConfig`
- Origem: `sistema/app/static/transport/app.js:363`
- Escopo original: topo do modulo
- Tema funcional: redimensionamento configuracao
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `orientation` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a redimensionamento configuracao, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [resolveVehicleDetailsPosition.md](resolveVehicleDetailsPosition.md)

- Funcao no arquivo: `resolveVehicleDetailsPosition`
- Origem: `sistema/app/static/transport/app.js:377`
- Escopo original: topo do modulo
- Tema funcional: detalhes do veiculo posicao
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `clampValue`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getVehicleGridItemMetrics.md](getVehicleGridItemMetrics.md)

- Funcao no arquivo: `getVehicleGridItemMetrics`
- Origem: `sistema/app/static/transport/app.js:427`
- Escopo original: topo do modulo
- Tema funcional: grade de veiculos item metricas
- Categoria: UI
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `gridElement` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [updateVehicleGridLayout.md](updateVehicleGridLayout.md)

- Funcao no arquivo: `updateVehicleGridLayout`
- Origem: `sistema/app/static/transport/app.js:443`
- Escopo original: topo do modulo
- Tema funcional: grade de veiculos layout
- Categoria: UI
- Responsabilidade: Encapsula uma responsabilidade interna do dashboard de transporte, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `gridElement` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getVehicleGridItemMetrics`, `parsePixelValue`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [updateVehicleGridLayouts.md](updateVehicleGridLayouts.md)

- Funcao no arquivo: `updateVehicleGridLayouts`
- Origem: `sistema/app/static/transport/app.js:472`
- Escopo original: topo do modulo
- Tema funcional: grade de veiculos layouts
- Categoria: UI
- Responsabilidade: Encapsula uma responsabilidade interna do dashboard de transporte, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `rootElement` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `updateVehicleGridLayout`, `document`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [resolvePanelMinimumSize.md](resolvePanelMinimumSize.md)

- Funcao no arquivo: `resolvePanelMinimumSize`
- Origem: `sistema/app/static/transport/app.js:479`
- Escopo original: topo do modulo
- Tema funcional: painel minimo tamanho
- Categoria: UI
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `panelElement`, `fallbackValue` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a painel minimo tamanho, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getVehicleGridItemMetrics`, `parsePixelValue`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [enableResizableDivider.md](enableResizableDivider.md)

- Funcao no arquivo: `enableResizableDivider`
- Origem: `sistema/app/static/transport/app.js:503`
- Escopo original: topo do modulo
- Tema funcional: resizable divisor
- Categoria: UI
- Responsabilidade: Encapsula uma responsabilidade interna do dashboard de transporte, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `dividerElement` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: `applyResize`, `stopResize`
- Dependencias observadas: `parsePositiveNumber`, `resolvePanelMinimumSize`, `resolvePanelSizes`, `resolveResizeConfig`, `updateVehicleGridLayouts`, `document`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [applyResize.md](applyResize.md)

- Funcao no arquivo: `applyResize`
- Origem: `sistema/app/static/transport/app.js:550`
- Escopo original: interna de `enableResizableDivider`
- Tema funcional: redimensionamento
- Categoria: utility
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `moveEvent` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `resolvePanelSizes`, `updateVehicleGridLayouts`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [stopResize.md](stopResize.md)

- Funcao no arquivo: `stopResize`
- Origem: `sistema/app/static/transport/app.js:573`
- Escopo original: interna de `enableResizableDivider`
- Tema funcional: redimensionamento
- Categoria: UI
- Responsabilidade: Orquestra um fluxo operacional do controller da pagina, ligando validacao local, integracao externa, feedback visual e recarga de dados quando necessario.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `document`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [createDatePanelController.md](createDatePanelController.md)

- Funcao no arquivo: `createDatePanelController`
- Origem: `sistema/app/static/transport/app.js:589`
- Escopo original: topo do modulo
- Tema funcional: data painel controller
- Categoria: UI + date/time
- Responsabilidade: Factory/builder do dashboard de transporte que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `rootElement`, `dateStore` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: `render`
- Dependencias observadas: `formatTransportDate`, `getTransportDateState`, `setValue`, `shiftValue`, `subscribe`, `dateStore`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [render.md](render.md)

- Funcao no arquivo: `render`
- Origem: `sistema/app/static/transport/app.js:595`
- Escopo original: interna de `createDatePanelController`
- Tema funcional: render
- Categoria: UI + date/time
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `selectedDate` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `formatTransportDate`, `getTransportDateState`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [clearElement.md](clearElement.md)

- Funcao no arquivo: `clearElement`
- Origem: `sistema/app/static/transport/app.js:624`
- Escopo original: topo do modulo
- Tema funcional: element
- Categoria: utility
- Responsabilidade: Rotina de sincronizacao do dashboard de transporte que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `element` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [createNode.md](createNode.md)

- Funcao no arquivo: `createNode`
- Origem: `sistema/app/static/transport/app.js:633`
- Escopo original: topo do modulo
- Tema funcional: node
- Categoria: UI
- Responsabilidade: Factory/builder do dashboard de transporte que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `tagName`, `className`, `textContent` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `document`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [requestJson.md](requestJson.md)

- Funcao no arquivo: `requestJson`
- Origem: `sistema/app/static/transport/app.js:644`
- Escopo original: topo do modulo
- Tema funcional: JSON
- Categoria: API
- Responsabilidade: Centraliza chamadas HTTP JSON do dashboard, aplica cabecalhos padrao, interpreta o payload de resposta e converte respostas nao OK em erros ricos com `status` e `payload`.
- Entradas: Recebe `url`, `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `formatApiErrorMessage`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.

### [extractApiMessage.md](extractApiMessage.md)

- Funcao no arquivo: `extractApiMessage`
- Origem: `sistema/app/static/transport/app.js:682`
- Escopo original: topo do modulo
- Tema funcional: mensagem de API
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a mensagem de API, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [formatApiErrorMessage.md](formatApiErrorMessage.md)

- Funcao no arquivo: `formatApiErrorMessage`
- Origem: `sistema/app/static/transport/app.js:711`
- Escopo original: topo do modulo
- Tema funcional: API erro mensagem
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `payload`, `statusCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a API erro mensagem, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `extractApiMessage`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [localizeTransportApiMessage.md](localizeTransportApiMessage.md)

- Funcao no arquivo: `localizeTransportApiMessage`
- Origem: `sistema/app/static/transport/app.js:716`
- Escopo original: topo do modulo
- Tema funcional: transporte mensagem de API
- Categoria: utility
- Responsabilidade: Encapsula uma responsabilidade interna do dashboard de transporte, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `message` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [normalizeVehicleSeatCountSetting.md](normalizeVehicleSeatCountSetting.md)

- Funcao no arquivo: `normalizeVehicleSeatCountSetting`
- Origem: `sistema/app/static/transport/app.js:740`
- Escopo original: topo do modulo
- Tema funcional: veiculo assento quantidade setting
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value`, `fallbackValue` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo assento quantidade setting, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [resolveTransportVehicleSeatDefaults.md](resolveTransportVehicleSeatDefaults.md)

- Funcao no arquivo: `resolveTransportVehicleSeatDefaults`
- Origem: `sistema/app/static/transport/app.js:748`
- Escopo original: topo do modulo
- Tema funcional: transporte veiculo assento defaults
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `source`, `fallbackValues` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `normalizeVehicleSeatCountSetting`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [applyTransportVehicleSeatDefaults.md](applyTransportVehicleSeatDefaults.md)

- Funcao no arquivo: `applyTransportVehicleSeatDefaults`
- Origem: `sistema/app/static/transport/app.js:770`
- Escopo original: topo do modulo
- Tema funcional: transporte veiculo assento defaults
- Categoria: utility
- Responsabilidade: Rotina de sincronizacao do dashboard de transporte que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `nextValues` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `resolveTransportVehicleSeatDefaults`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [normalizeVehicleToleranceSetting.md](normalizeVehicleToleranceSetting.md)

- Funcao no arquivo: `normalizeVehicleToleranceSetting`
- Origem: `sistema/app/static/transport/app.js:775`
- Escopo original: topo do modulo
- Tema funcional: veiculo tolerancia setting
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value`, `fallbackValue` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo tolerancia setting, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [applyTransportVehicleToleranceDefault.md](applyTransportVehicleToleranceDefault.md)

- Funcao no arquivo: `applyTransportVehicleToleranceDefault`
- Origem: `sistema/app/static/transport/app.js:783`
- Escopo original: topo do modulo
- Tema funcional: transporte veiculo tolerancia padrao
- Categoria: utility
- Responsabilidade: Rotina de sincronizacao do dashboard de transporte que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `nextValue` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `normalizeVehicleToleranceSetting`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getDefaultVehicleSeatCount.md](getDefaultVehicleSeatCount.md)

- Funcao no arquivo: `getDefaultVehicleSeatCount`
- Origem: `sistema/app/static/transport/app.js:788`
- Escopo original: topo do modulo
- Tema funcional: padrao veiculo assento quantidade
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `vehicleType` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a padrao veiculo assento quantidade, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getDefaultVehicleToleranceMinutes.md](getDefaultVehicleToleranceMinutes.md)

- Funcao no arquivo: `getDefaultVehicleToleranceMinutes`
- Origem: `sistema/app/static/transport/app.js:792`
- Escopo original: topo do modulo
- Tema funcional: padrao veiculo tolerancia minutes
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a padrao veiculo tolerancia minutes, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getDefaultVehicleFormValues.md](getDefaultVehicleFormValues.md)

- Funcao no arquivo: `getDefaultVehicleFormValues`
- Origem: `sistema/app/static/transport/app.js:796`
- Escopo original: topo do modulo
- Tema funcional: padrao veiculo formulario valores
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `vehicleType` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getDefaultVehicleSeatCount`, `getDefaultVehicleToleranceMinutes`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [normalizeVehicleScope.md](normalizeVehicleScope.md)

- Funcao no arquivo: `normalizeVehicleScope`
- Origem: `sistema/app/static/transport/app.js:808`
- Escopo original: topo do modulo
- Tema funcional: veiculo escopo
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo escopo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [resolveVehicleForm.md](resolveVehicleForm.md)

- Funcao no arquivo: `resolveVehicleForm`
- Origem: `sistema/app/static/transport/app.js:816`
- Escopo original: topo do modulo
- Tema funcional: veiculo formulario
- Categoria: UI
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `formElement` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo formulario, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `document`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [applyVehicleSeatDefault.md](applyVehicleSeatDefault.md)

- Funcao no arquivo: `applyVehicleSeatDefault`
- Origem: `sistema/app/static/transport/app.js:833`
- Escopo original: topo do modulo
- Tema funcional: veiculo assento padrao
- Categoria: utility
- Responsabilidade: Rotina de sincronizacao do dashboard de transporte que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `vehicleType`, `formElement` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getDefaultVehicleSeatCount`, `resolveVehicleForm`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [syncVehicleTypeDependentDefaults.md](syncVehicleTypeDependentDefaults.md)

- Funcao no arquivo: `syncVehicleTypeDependentDefaults`
- Origem: `sistema/app/static/transport/app.js:841`
- Escopo original: topo do modulo
- Tema funcional: veiculo type dependent defaults
- Categoria: utility
- Responsabilidade: Rotina de sincronizacao do dashboard de transporte que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `vehicleType`, `formElement` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `applyVehicleSeatDefault`, `getDefaultVehicleToleranceMinutes`, `resolveVehicleForm`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [applyVehicleFormDefaults.md](applyVehicleFormDefaults.md)

- Funcao no arquivo: `applyVehicleFormDefaults`
- Origem: `sistema/app/static/transport/app.js:862`
- Escopo original: topo do modulo
- Tema funcional: veiculo formulario defaults
- Categoria: utility
- Responsabilidade: Rotina de sincronizacao do dashboard de transporte que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `vehicleType`, `formElement` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getDefaultVehicleFormValues`, `resolveVehicleForm`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [buildVehicleCreatePayload.md](buildVehicleCreatePayload.md)

- Funcao no arquivo: `buildVehicleCreatePayload`
- Origem: `sistema/app/static/transport/app.js:881`
- Escopo original: topo do modulo
- Tema funcional: veiculo create payload
- Categoria: date/time
- Responsabilidade: Factory/builder do dashboard de transporte que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `formData`, `serviceDate`, `selectedRouteKind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `normalizeVehicleScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [resolveVehicleModalOpenState.md](resolveVehicleModalOpenState.md)

- Funcao no arquivo: `resolveVehicleModalOpenState`
- Origem: `sistema/app/static/transport/app.js:915`
- Escopo original: topo do modulo
- Tema funcional: veiculo modal open state
- Categoria: date/time
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `scope`, `currentServiceDate` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `normalizeVehicleScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [resolveVehicleCreateValidationError.md](resolveVehicleCreateValidationError.md)

- Funcao no arquivo: `resolveVehicleCreateValidationError`
- Origem: `sistema/app/static/transport/app.js:925`
- Escopo original: topo do modulo
- Tema funcional: veiculo create validacao erro
- Categoria: date/time
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `payload` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [resolveVehicleSaveReloadDate.md](resolveVehicleSaveReloadDate.md)

- Funcao no arquivo: `resolveVehicleSaveReloadDate`
- Origem: `sistema/app/static/transport/app.js:968`
- Escopo original: topo do modulo
- Tema funcional: veiculo save reload data
- Categoria: date/time
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `payload`, `fallbackDate` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo save reload data, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `parseStoredTransportDate`, `startOfLocalDay`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [mapVehicleTypeLabel.md](mapVehicleTypeLabel.md)

- Funcao no arquivo: `mapVehicleTypeLabel`
- Origem: `sistema/app/static/transport/app.js:981`
- Escopo original: topo do modulo
- Tema funcional: veiculo type rotulo
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo type rotulo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [formatVehicleTypeTableValue.md](formatVehicleTypeTableValue.md)

- Funcao no arquivo: `formatVehicleTypeTableValue`
- Origem: `sistema/app/static/transport/app.js:987`
- Escopo original: topo do modulo
- Tema funcional: veiculo type table valor
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo type table valor, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `mapVehicleTypeLabel`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [formatRouteTableValue.md](formatRouteTableValue.md)

- Funcao no arquivo: `formatRouteTableValue`
- Origem: `sistema/app/static/transport/app.js:991`
- Escopo original: topo do modulo
- Tema funcional: rota table valor
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `routeKind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a rota table valor, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getRouteKindLabel`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [mapVehicleIconPath.md](mapVehicleIconPath.md)

- Funcao no arquivo: `mapVehicleIconPath`
- Origem: `sistema/app/static/transport/app.js:995`
- Escopo original: topo do modulo
- Tema funcional: veiculo icone path
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo icone path, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [formatVehicleOccupancyLabel.md](formatVehicleOccupancyLabel.md)

- Funcao no arquivo: `formatVehicleOccupancyLabel`
- Origem: `sistema/app/static/transport/app.js:999`
- Escopo original: topo do modulo
- Tema funcional: veiculo ocupacao rotulo
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `vehicle`, `assignedCount` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo ocupacao rotulo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [formatVehicleOccupancyCount.md](formatVehicleOccupancyCount.md)

- Funcao no arquivo: `formatVehicleOccupancyCount`
- Origem: `sistema/app/static/transport/app.js:1005`
- Escopo original: topo do modulo
- Tema funcional: veiculo ocupacao quantidade
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `vehicle`, `assignedCount` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo ocupacao quantidade, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [isValidTransportTimeValue.md](isValidTransportTimeValue.md)

- Funcao no arquivo: `isValidTransportTimeValue`
- Origem: `sistema/app/static/transport/app.js:1011`
- Escopo original: topo do modulo
- Tema funcional: valid transporte horario valor
- Categoria: utility
- Responsabilidade: Predicate do dashboard de transporte que inspeciona os dados disponiveis e devolve a decisao booleana usada para permitir, negar ou destacar um comportamento.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor booleano usado para gating de UI, validacao ou destaque de estado.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [normalizeTransportTimeValue.md](normalizeTransportTimeValue.md)

- Funcao no arquivo: `normalizeTransportTimeValue`
- Origem: `sistema/app/static/transport/app.js:1015`
- Escopo original: topo do modulo
- Tema funcional: transporte horario valor
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value`, `fallbackValue` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a transporte horario valor, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `isValidTransportTimeValue`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getEffectiveWorkToHomeDepartureTime.md](getEffectiveWorkToHomeDepartureTime.md)

- Funcao no arquivo: `getEffectiveWorkToHomeDepartureTime`
- Origem: `sistema/app/static/transport/app.js:1019`
- Escopo original: topo do modulo
- Tema funcional: efetivo rota trabalho para casa saida horario
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `dashboard`, `fallbackTime` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a efetivo rota trabalho para casa saida horario, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `isValidTransportTimeValue`, `normalizeTransportTimeValue`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getVehicleDepartureTime.md](getVehicleDepartureTime.md)

- Funcao no arquivo: `getVehicleDepartureTime`
- Origem: `sistema/app/static/transport/app.js:1028`
- Escopo original: topo do modulo
- Tema funcional: veiculo saida horario
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `vehicle`, `fallbackTime`, `scopeOverride` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo saida horario, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `isValidTransportTimeValue`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [shouldHighlightRequestName.md](shouldHighlightRequestName.md)

- Funcao no arquivo: `shouldHighlightRequestName`
- Origem: `sistema/app/static/transport/app.js:1042`
- Escopo original: topo do modulo
- Tema funcional: destaque solicitacao name
- Categoria: utility
- Responsabilidade: Predicate do dashboard de transporte que inspeciona os dados disponiveis e devolve a decisao booleana usada para permitir, negar ou destacar um comportamento.
- Entradas: Recebe `assignmentStatus` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor booleano usado para gating de UI, validacao ou destaque de estado.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getPassengerAwarenessState.md](getPassengerAwarenessState.md)

- Funcao no arquivo: `getPassengerAwarenessState`
- Origem: `sistema/app/static/transport/app.js:1046`
- Escopo original: topo do modulo
- Tema funcional: passageiro ciencia state
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `requestRow` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a passageiro ciencia state, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [isRequestAssignedToVehicle.md](isRequestAssignedToVehicle.md)

- Funcao no arquivo: `isRequestAssignedToVehicle`
- Origem: `sistema/app/static/transport/app.js:1050`
- Escopo original: topo do modulo
- Tema funcional: solicitacao alocada para veiculo
- Categoria: utility
- Responsabilidade: Predicate do dashboard de transporte que inspeciona os dados disponiveis e devolve a decisao booleana usada para permitir, negar ou destacar um comportamento.
- Entradas: Recebe `requestRow`, `vehicle` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor booleano usado para gating de UI, validacao ou destaque de estado.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [groupAssignedRequestsByVehicleForDate.md](groupAssignedRequestsByVehicleForDate.md)

- Funcao no arquivo: `groupAssignedRequestsByVehicleForDate`
- Origem: `sistema/app/static/transport/app.js:1059`
- Escopo original: topo do modulo
- Tema funcional: alocada solicitacoes by veiculo para data
- Categoria: date/time
- Responsabilidade: Organiza colecoes do dashboard de transporte em uma estrutura intermediaria pronta para renderizacao, filtro ou tomada de decisao.
- Entradas: Recebe `requestRows`, `selectedDate` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [canRequestBeDroppedOnVehicle.md](canRequestBeDroppedOnVehicle.md)

- Funcao no arquivo: `canRequestBeDroppedOnVehicle`
- Origem: `sistema/app/static/transport/app.js:1084`
- Escopo original: topo do modulo
- Tema funcional: solicitacao be dropped on veiculo
- Categoria: utility
- Responsabilidade: Predicate do dashboard de transporte que inspeciona os dados disponiveis e devolve a decisao booleana usada para permitir, negar ou destacar um comportamento.
- Entradas: Recebe `requestRow`, `scope`, `vehicle`, `routeKind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor booleano usado para gating de UI, validacao ou destaque de estado.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `isRequestAssignedToVehicle`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [buildVehiclePassengerPreviewRows.md](buildVehiclePassengerPreviewRows.md)

- Funcao no arquivo: `buildVehiclePassengerPreviewRows`
- Origem: `sistema/app/static/transport/app.js:1096`
- Escopo original: topo do modulo
- Tema funcional: veiculo passageiro previsualizacao linhas
- Categoria: utility
- Responsabilidade: Factory/builder do dashboard de transporte que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `assignedRows`, `previewRequestRow`, `maxRows` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [buildVehiclePassengerAwarenessRows.md](buildVehiclePassengerAwarenessRows.md)

- Funcao no arquivo: `buildVehiclePassengerAwarenessRows`
- Origem: `sistema/app/static/transport/app.js:1115`
- Escopo original: topo do modulo
- Tema funcional: veiculo passageiro ciencia linhas
- Categoria: utility
- Responsabilidade: Factory/builder do dashboard de transporte que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `assignedRows`, `maxRows` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getPassengerAwarenessState`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [mapScopeTitle.md](mapScopeTitle.md)

- Funcao no arquivo: `mapScopeTitle`
- Origem: `sistema/app/static/transport/app.js:1136`
- Escopo original: topo do modulo
- Tema funcional: escopo titulo
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a escopo titulo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getRouteKindLabel.md](getRouteKindLabel.md)

- Funcao no arquivo: `getRouteKindLabel`
- Origem: `sistema/app/static/transport/app.js:1140`
- Escopo original: topo do modulo
- Tema funcional: tipo de rota rotulo
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `routeKind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a tipo de rota rotulo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getModalScopeNote.md](getModalScopeNote.md)

- Funcao no arquivo: `getModalScopeNote`
- Origem: `sistema/app/static/transport/app.js:1145`
- Escopo original: topo do modulo
- Tema funcional: modal escopo note
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a modal escopo note, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getRequestTitle.md](getRequestTitle.md)

- Funcao no arquivo: `getRequestTitle`
- Origem: `sistema/app/static/transport/app.js:1150`
- Escopo original: topo do modulo
- Tema funcional: solicitacao titulo
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `kind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a solicitacao titulo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getRequestLabel.md](getRequestLabel.md)

- Funcao no arquivo: `getRequestLabel`
- Origem: `sistema/app/static/transport/app.js:1154`
- Escopo original: topo do modulo
- Tema funcional: solicitacao rotulo
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `kind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a solicitacao rotulo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [createEmptyState.md](createEmptyState.md)

- Funcao no arquivo: `createEmptyState`
- Origem: `sistema/app/static/transport/app.js:1158`
- Escopo original: topo do modulo
- Tema funcional: vazio state
- Categoria: UI
- Responsabilidade: Factory/builder do dashboard de transporte que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `message` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `createNode`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [createTransportPageController.md](createTransportPageController.md)

- Funcao no arquivo: `createTransportPageController`
- Origem: `sistema/app/static/transport/app.js:1164`
- Escopo original: topo do modulo
- Tema funcional: transporte pagina controller
- Categoria: API + UI + state + date/time
- Responsabilidade: Monta o controller principal do dashboard de transporte, encapsulando estado, autenticacao, tempo real, modais, renderizacao, drag and drop e os fluxos que conversam com a API.
- Entradas: Recebe `dateStore` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: `refreshDatePanelLabels`, `setDashboardDateForSilentReload`, `focusVehicleFormField`, `applyStaticTranslations`, `clearRequestCollapseOverridesForKind`, `getRequestSectionCollapsedState`, `getRequestRowCollapsedState`, `setRequestRowCollapsedState`, `applyRequestRowCollapsedVisualState`, `preserveRequestSectionScrollPosition`, `syncRequestSectionCollapsedRowsInDom`, `toggleRequestRowCollapsed`, ... (+82 filhas nomeadas)
- Dependencias observadas: `state`, `applyTransportVehicleSeatDefaults`, `applyTransportVehicleToleranceDefault`, `applyVehicleFormDefaults`, `buildVehicleCreatePayload`, `buildVehiclePassengerAwarenessRows`, `buildVehiclePassengerPreviewRows`, `canRequestBeDroppedOnVehicle`, `clearElement`, `createEmptyState`, `createNode`, `formatIsoDate`
- Endpoints/rotas envolvidos: `GET /api/transport/auth/session`, `POST /api/transport/auth/verify`, `POST /api/transport/auth/logout`, `SSE /api/transport/stream`, `GET /api/transport/dashboard`, `GET /api/transport/settings`, `PUT /api/transport/settings`, `PUT /api/transport/date-settings`, `POST /api/transport/vehicles`, `DELETE /api/transport/vehicles/{schedule_id}?service_date=...`, `POST /api/transport/requests/reject`, `POST /api/transport/assignments`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Agenda ou cancela trabalho assincrono no navegador.

### [refreshDatePanelLabels.md](refreshDatePanelLabels.md)

- Funcao no arquivo: `refreshDatePanelLabels`
- Origem: `sistema/app/static/transport/app.js:1329`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: data painel labels
- Categoria: UI + state + date/time
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `formatTransportDate`, `getTransportDateState`, `getValue`, `dateStore`, `document`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [setDashboardDateForSilentReload.md](setDashboardDateForSilentReload.md)

- Funcao no arquivo: `setDashboardDateForSilentReload`
- Origem: `sistema/app/static/transport/app.js:1337`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: dashboard data para silent reload
- Categoria: state + date/time
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `nextDate` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `closeRouteTimePopover`, `refreshDatePanelLabels`, `setStoredTransportDate`, `setValue`, `dateStore`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [focusVehicleFormField.md](focusVehicleFormField.md)

- Funcao no arquivo: `focusVehicleFormField`
- Origem: `sistema/app/static/transport/app.js:1345`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo formulario field
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `fieldName` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `vehicleForm`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [applyStaticTranslations.md](applyStaticTranslations.md)

- Funcao no arquivo: `applyStaticTranslations`
- Origem: `sistema/app/static/transport/app.js:1359`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: estatica translations
- Categoria: i18n + UI + state + date/time
- Responsabilidade: Aplica todas as traducoes estaticas do dashboard nos titulos, labels, botoes, atributos de acessibilidade e textos auxiliares presentes na pagina.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getActiveLanguageCode`, `getRequestTitle`, `getRouteKindLabel`, `mapScopeTitle`, `mapVehicleTypeLabel`, `refreshDatePanelLabels`, `syncVehicleModalFields`, `t`, `vehicleForm`, `vehicleModal`, `document`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [clearRequestCollapseOverridesForKind.md](clearRequestCollapseOverridesForKind.md)

- Funcao no arquivo: `clearRequestCollapseOverridesForKind`
- Origem: `sistema/app/static/transport/app.js:1652`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: solicitacao colapso overrides para tipo
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `kind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getRequestsForKind`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [getRequestSectionCollapsedState.md](getRequestSectionCollapsedState.md)

- Funcao no arquivo: `getRequestSectionCollapsedState`
- Origem: `sistema/app/static/transport/app.js:1658`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: solicitacao secao collapsed state
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `kind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a solicitacao secao collapsed state, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [getRequestRowCollapsedState.md](getRequestRowCollapsedState.md)

- Funcao no arquivo: `getRequestRowCollapsedState`
- Origem: `sistema/app/static/transport/app.js:1662`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: linha de solicitacao collapsed state
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `requestRow` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a linha de solicitacao collapsed state, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getRequestSectionCollapsedState`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [setRequestRowCollapsedState.md](setRequestRowCollapsedState.md)

- Funcao no arquivo: `setRequestRowCollapsedState`
- Origem: `sistema/app/static/transport/app.js:1675`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: linha de solicitacao collapsed state
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `requestRow`, `collapsed` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getRequestSectionCollapsedState`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [applyRequestRowCollapsedVisualState.md](applyRequestRowCollapsedVisualState.md)

- Funcao no arquivo: `applyRequestRowCollapsedVisualState`
- Origem: `sistema/app/static/transport/app.js:1690`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: linha de solicitacao collapsed visual state
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `rowButton`, `collapsed` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [preserveRequestSectionScrollPosition.md](preserveRequestSectionScrollPosition.md)

- Funcao no arquivo: `preserveRequestSectionScrollPosition`
- Origem: `sistema/app/static/transport/app.js:1703`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: solicitacao secao scroll posicao
- Categoria: state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `kind`, `callback` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [syncRequestSectionCollapsedRowsInDom.md](syncRequestSectionCollapsedRowsInDom.md)

- Funcao no arquivo: `syncRequestSectionCollapsedRowsInDom`
- Origem: `sistema/app/static/transport/app.js:1714`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: solicitacao secao collapsed linhas in dom
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `kind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `applyRequestRowCollapsedVisualState`, `getRequestRowCollapsedState`, `getVisibleRequestsForKind`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [toggleRequestRowCollapsed.md](toggleRequestRowCollapsed.md)

- Funcao no arquivo: `toggleRequestRowCollapsed`
- Origem: `sistema/app/static/transport/app.js:1726`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: linha de solicitacao collapsed
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `requestRow`, `rowButton` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `applyRequestRowCollapsedVisualState`, `getRequestRowCollapsedState`, `preserveRequestSectionScrollPosition`, `setRequestRowCollapsedState`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [syncRequestSectionToggleState.md](syncRequestSectionToggleState.md)

- Funcao no arquivo: `syncRequestSectionToggleState`
- Origem: `sistema/app/static/transport/app.js:1737`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: solicitacao secao alternancia state
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getRequestSectionCollapsedState`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [toggleRequestSectionCollapsed.md](toggleRequestSectionCollapsed.md)

- Funcao no arquivo: `toggleRequestSectionCollapsed`
- Origem: `sistema/app/static/transport/app.js:1750`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: solicitacao secao collapsed
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `kind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearRequestCollapseOverridesForKind`, `getRequestSectionCollapsedState`, `preserveRequestSectionScrollPosition`, `syncRequestSectionCollapsedRowsInDom`, `syncRequestSectionToggleState`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [populateLanguageOptions.md](populateLanguageOptions.md)

- Funcao no arquivo: `populateLanguageOptions`
- Origem: `sistema/app/static/transport/app.js:1759`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: idioma options
- Categoria: i18n + UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `clearElement`, `document`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [syncSettingsControls.md](syncSettingsControls.md)

- Funcao no arquivo: `syncSettingsControls`
- Origem: `sistema/app/static/transport/app.js:1773`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: configuracoes controles
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getActiveLanguageCode`, `getDefaultVehicleSeatCount`, `getDefaultVehicleToleranceMinutes`, `normalizeTransportTimeValue`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [readTransportSettingsDraft.md](readTransportSettingsDraft.md)

- Funcao no arquivo: `readTransportSettingsDraft`
- Origem: `sistema/app/static/transport/app.js:1800`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte configuracoes rascunho
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [syncRouteTimeControls.md](syncRouteTimeControls.md)

- Funcao no arquivo: `syncRouteTimeControls`
- Origem: `sistema/app/static/transport/app.js:1812`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: rota horario controles
- Categoria: state + date/time
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `formatTransportDate`, `getEffectiveWorkToHomeDepartureTime`, `getValue`, `t`, `dateStore`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [closeRouteTimePopover.md](closeRouteTimePopover.md)

- Funcao no arquivo: `closeRouteTimePopover`
- Origem: `sistema/app/static/transport/app.js:1832`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: rota horario popover
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `syncRouteTimeControls`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [saveRouteTimeForSelectedDate.md](saveRouteTimeForSelectedDate.md)

- Funcao no arquivo: `saveRouteTimeForSelectedDate`
- Origem: `sistema/app/static/transport/app.js:1836`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: rota horario para selecionado data
- Categoria: API + state + date/time
- Responsabilidade: Grava o horario `work_to_home` da data selecionada, protege o fluxo contra usuario sem autenticacao e reabre a tela com os dados atualizados.
- Entradas: Recebe `nextWorkToHomeTime` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getCurrentServiceDateIso`, `getTransportLockedMessage`, `getValue`, `handleProtectedRequestError`, `loadDashboard`, `requestJson`, `setStatus`, `syncRouteTimeControls`, `t`, `dateStore`
- Endpoints/rotas envolvidos: `PUT /api/transport/date-settings`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [getVehicleViewMode.md](getVehicleViewMode.md)

- Funcao no arquivo: `getVehicleViewMode`
- Origem: `sistema/app/static/transport/app.js:1879`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo visualizacao modo
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo visualizacao modo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [setVehicleContainerViewMode.md](setVehicleContainerViewMode.md)

- Funcao no arquivo: `setVehicleContainerViewMode`
- Origem: `sistema/app/static/transport/app.js:1883`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo container visualizacao modo
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `container`, `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getVehicleViewMode`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [syncVehicleViewToggleState.md](syncVehicleViewToggleState.md)

- Funcao no arquivo: `syncVehicleViewToggleState`
- Origem: `sistema/app/static/transport/app.js:1893`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo visualizacao alternancia state
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getVehicleViewMode`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [toggleVehicleViewMode.md](toggleVehicleViewMode.md)

- Funcao no arquivo: `toggleVehicleViewMode`
- Origem: `sistema/app/static/transport/app.js:1906`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo visualizacao modo
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getVehicleViewMode`, `renderVehiclePanels`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [setAuthShellState.md](setAuthShellState.md)

- Funcao no arquivo: `setAuthShellState`
- Origem: `sistema/app/static/transport/app.js:1911`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: autenticacao shell state
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `shellElement`, `authenticated` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [updateAuthControls.md](updateAuthControls.md)

- Funcao no arquivo: `updateAuthControls`
- Origem: `sistema/app/static/transport/app.js:1919`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: autenticacao controles
- Categoria: state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `setAuthShellState`, `syncRouteTimeControls`, `syncSettingsControls`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [normalizeAuthKeyValue.md](normalizeAuthKeyValue.md)

- Funcao no arquivo: `normalizeAuthKeyValue`
- Origem: `sistema/app/static/transport/app.js:1929`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: autenticacao chave valor
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a autenticacao chave valor, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [clearPendingAuthVerification.md](clearPendingAuthVerification.md)

- Funcao no arquivo: `clearPendingAuthVerification`
- Origem: `sistema/app/static/transport/app.js:1943`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: pending autenticacao verificacao
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Agenda ou cancela trabalho assincrono no navegador.

### [clearPendingRealtimeRefresh.md](clearPendingRealtimeRefresh.md)

- Funcao no arquivo: `clearPendingRealtimeRefresh`
- Origem: `sistema/app/static/transport/app.js:1950`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: pending tempo real atualizacao
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Agenda ou cancela trabalho assincrono no navegador.

### [stopRealtimeUpdates.md](stopRealtimeUpdates.md)

- Funcao no arquivo: `stopRealtimeUpdates`
- Origem: `sistema/app/static/transport/app.js:1957`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: tempo real updates
- Categoria: state
- Responsabilidade: Orquestra um fluxo operacional do controller da pagina, ligando validacao local, integracao externa, feedback visual e recarga de dados quando necessario.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearPendingRealtimeRefresh`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [requestDashboardRefresh.md](requestDashboardRefresh.md)

- Funcao no arquivo: `requestDashboardRefresh`
- Origem: `sistema/app/static/transport/app.js:1966`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: dashboard atualizacao
- Categoria: state + date/time
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearPendingRealtimeRefresh`, `getValue`, `loadDashboard`, `dateStore`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Agenda ou cancela trabalho assincrono no navegador.

### [startRealtimeUpdates.md](startRealtimeUpdates.md)

- Funcao no arquivo: `startRealtimeUpdates`
- Origem: `sistema/app/static/transport/app.js:1979`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: tempo real updates
- Categoria: API + state
- Responsabilidade: Orquestra um fluxo operacional do controller da pagina, ligando validacao local, integracao externa, feedback visual e recarga de dados quando necessario.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `requestDashboardRefresh`, `stopRealtimeUpdates`, `globalScope`
- Endpoints/rotas envolvidos: `SSE /api/transport/stream`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Abre, fecha ou administra o canal SSE de atualizacoes em tempo real.

### [setAuthenticationState.md](setAuthenticationState.md)

- Funcao no arquivo: `setAuthenticationState`
- Origem: `sistema/app/static/transport/app.js:1998`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: authentication state
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `authenticated`, `user`, `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearDashboard`, `startRealtimeUpdates`, `stopRealtimeUpdates`, `syncSettingsControls`, `updateAuthControls`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [clearTransportSession.md](clearTransportSession.md)

- Funcao no arquivo: `clearTransportSession`
- Origem: `sistema/app/static/transport/app.js:2035`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte sessao
- Categoria: API + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `message` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearPendingAuthVerification`, `getTransportLockedMessage`, `requestJson`, `setAuthenticationState`, `setStatus`
- Endpoints/rotas envolvidos: `POST /api/transport/auth/logout`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [handleProtectedRequestError.md](handleProtectedRequestError.md)

- Funcao no arquivo: `handleProtectedRequestError`
- Origem: `sistema/app/static/transport/app.js:2043`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: protegida solicitacao erro
- Categoria: state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `error`, `fallbackMessage` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `clearTransportSession`, `getTransportSessionExpiredMessage`, `localizeTransportApiMessage`, `requestDashboardRefresh`, `setStatus`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [openUserCreationRequest.md](openUserCreationRequest.md)

- Funcao no arquivo: `openUserCreationRequest`
- Origem: `sistema/app/static/transport/app.js:2055`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: usuario criacao solicitacao
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `setStatus`, `t`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [loadTransportSettings.md](loadTransportSettings.md)

- Funcao no arquivo: `loadTransportSettings`
- Origem: `sistema/app/static/transport/app.js:2062`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte configuracoes
- Categoria: API + state
- Responsabilidade: Orquestra um fluxo operacional do controller da pagina, ligando validacao local, integracao externa, feedback visual e recarga de dados quando necessario.
- Entradas: Recebe `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `applyTransportVehicleSeatDefaults`, `applyTransportVehicleToleranceDefault`, `handleProtectedRequestError`, `requestJson`, `syncRouteTimeControls`, `syncSettingsControls`, `t`
- Endpoints/rotas envolvidos: `GET /api/transport/settings`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [saveTransportSettings.md](saveTransportSettings.md)

- Funcao no arquivo: `saveTransportSettings`
- Origem: `sistema/app/static/transport/app.js:2106`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte configuracoes
- Categoria: API + state + date/time
- Responsabilidade: Persiste as configuracoes do dashboard, normaliza horarios e defaults de veiculos, atualiza o estado local e recarrega a tela apos confirmacao do backend.
- Entradas: Recebe `nextValues` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `applyTransportVehicleSeatDefaults`, `applyTransportVehicleToleranceDefault`, `getTransportLockedMessage`, `getValue`, `handleProtectedRequestError`, `isValidTransportTimeValue`, `loadDashboard`, `normalizeTransportTimeValue`, `normalizeVehicleToleranceSetting`, `requestJson`, `resolveTransportVehicleSeatDefaults`
- Endpoints/rotas envolvidos: `PUT /api/transport/settings`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [switchTransportLanguage.md](switchTransportLanguage.md)

- Funcao no arquivo: `switchTransportLanguage`
- Origem: `sistema/app/static/transport/app.js:2197`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte idioma
- Categoria: i18n + state
- Responsabilidade: Orquestra um fluxo operacional do controller da pagina, ligando validacao local, integracao externa, feedback visual e recarga de dados quando necessario.
- Entradas: Recebe `nextLanguageCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `applyStaticTranslations`, `clearDashboard`, `getTransportLockedMessage`, `renderDashboard`, `resolveLanguageCode`, `setActiveLanguageCode`, `setStatus`, `syncRouteTimeControls`, `syncSettingsControls`, `t`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Agenda ou cancela trabalho assincrono no navegador.

### [verifyTransportCredentials.md](verifyTransportCredentials.md)

- Funcao no arquivo: `verifyTransportCredentials`
- Origem: `sistema/app/static/transport/app.js:2232`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte credenciais
- Categoria: API + state + date/time
- Responsabilidade: Valida as credenciais digitadas na barra superior, atualiza o estado de autenticacao e, em caso de sucesso, carrega dashboard e configuracoes.
- Entradas: Recebe `requestToken` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getTransportLockedMessage`, `getValue`, `loadDashboard`, `loadTransportSettings`, `localizeTransportApiMessage`, `normalizeAuthKeyValue`, `requestJson`, `setAuthenticationState`, `setStatus`, `t`, `dateStore`
- Endpoints/rotas envolvidos: `POST /api/transport/auth/verify`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [scheduleTransportVerification.md](scheduleTransportVerification.md)

- Funcao no arquivo: `scheduleTransportVerification`
- Origem: `sistema/app/static/transport/app.js:2270`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte verificacao
- Categoria: state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearPendingAuthVerification`, `getTransportLockedMessage`, `normalizeAuthKeyValue`, `setAuthenticationState`, `setStatus`, `verifyTransportCredentials`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Agenda ou cancela trabalho assincrono no navegador.

### [bootstrapTransportSession.md](bootstrapTransportSession.md)

- Funcao no arquivo: `bootstrapTransportSession`
- Origem: `sistema/app/static/transport/app.js:2289`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte sessao
- Categoria: API + state + date/time
- Responsabilidade: Restaura uma sessao ja autenticada a partir do backend no carregamento inicial, decidindo entre liberar ou bloquear a experiencia do dashboard.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getDefaultStatusMessage`, `getTransportLockedMessage`, `getValue`, `loadDashboard`, `loadTransportSettings`, `requestJson`, `setAuthenticationState`, `setStatus`, `dateStore`
- Endpoints/rotas envolvidos: `GET /api/transport/auth/session`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.

### [setStatus.md](setStatus.md)

- Funcao no arquivo: `setStatus`
- Origem: `sistema/app/static/transport/app.js:2460`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: status
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `message`, `tone` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getDefaultStatusMessage`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [setVehicleModalFeedback.md](setVehicleModalFeedback.md)

- Funcao no arquivo: `setVehicleModalFeedback`
- Origem: `sistema/app/static/transport/app.js:2469`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo modal feedback
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `message`, `tone` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `vehicleModal`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [clearVehicleModalFeedback.md](clearVehicleModalFeedback.md)

- Funcao no arquivo: `clearVehicleModalFeedback`
- Origem: `sistema/app/static/transport/app.js:2487`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo modal feedback
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `setVehicleModalFeedback`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [openSettingsModal.md](openSettingsModal.md)

- Funcao no arquivo: `openSettingsModal`
- Origem: `sistema/app/static/transport/app.js:2491`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: configuracoes modal
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `closeExpandedVehicleDetails`, `loadTransportSettings`, `syncSettingsControls`, `settingsModal`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [closeSettingsModal.md](closeSettingsModal.md)

- Funcao no arquivo: `closeSettingsModal`
- Origem: `sistema/app/static/transport/app.js:2506`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: configuracoes modal
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `settingsModal`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [syncRouteInputs.md](syncRouteInputs.md)

- Funcao no arquivo: `syncRouteInputs`
- Origem: `sistema/app/static/transport/app.js:2519`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: rota inputs
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getSelectedRouteKind.md](getSelectedRouteKind.md)

- Funcao no arquivo: `getSelectedRouteKind`
- Origem: `sistema/app/static/transport/app.js:2521`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: selecionado tipo de rota
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a selecionado tipo de rota, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [getRouteKindForVehicle.md](getRouteKindForVehicle.md)

- Funcao no arquivo: `getRouteKindForVehicle`
- Origem: `sistema/app/static/transport/app.js:2525`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: tipo de rota para veiculo
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `scope`, `vehicle` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a tipo de rota para veiculo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getSelectedRouteKind`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getRouteKindForRequestRow.md](getRouteKindForRequestRow.md)

- Funcao no arquivo: `getRouteKindForRequestRow`
- Origem: `sistema/app/static/transport/app.js:2532`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: tipo de rota para linha de solicitacao
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `requestRow`, `fallbackRouteKind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a tipo de rota para linha de solicitacao, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getSelectedRouteKind`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getCurrentServiceDateIso.md](getCurrentServiceDateIso.md)

- Funcao no arquivo: `getCurrentServiceDateIso`
- Origem: `sistema/app/static/transport/app.js:2544`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: atual servico data ISO
- Categoria: state + date/time
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a atual servico data ISO, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `formatIsoDate`, `getValue`, `dateStore`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [canOpenVehicleModal.md](canOpenVehicleModal.md)

- Funcao no arquivo: `canOpenVehicleModal`
- Origem: `sistema/app/static/transport/app.js:2548`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: open veiculo modal
- Categoria: state
- Responsabilidade: Predicate do controller da pagina que inspeciona os dados disponiveis e devolve a decisao booleana usada para permitir, negar ou destacar um comportamento.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor booleano usado para gating de UI, validacao ou destaque de estado.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getTransportLockedMessage`, `setStatus`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [syncVehicleModalFields.md](syncVehicleModalFields.md)

- Funcao no arquivo: `syncVehicleModalFields`
- Origem: `sistema/app/static/transport/app.js:2556`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo modal fields
- Categoria: UI + state + date/time
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getModalScopeNote`, `getSelectedRouteKind`, `mapScopeTitle`, `normalizeVehicleScope`, `vehicleForm`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [openVehicleModal.md](openVehicleModal.md)

- Funcao no arquivo: `openVehicleModal`
- Origem: `sistema/app/static/transport/app.js:2610`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo modal
- Categoria: state + date/time
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `applyVehicleFormDefaults`, `canOpenVehicleModal`, `clearVehicleModalFeedback`, `closeExpandedVehicleDetails`, `focusVehicleFormField`, `getCurrentServiceDateIso`, `normalizeVehicleScope`, `resolveVehicleModalOpenState`, `syncVehicleModalFields`, `vehicleForm`, `vehicleModal`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [closeVehicleModal.md](closeVehicleModal.md)

- Funcao no arquivo: `closeVehicleModal`
- Origem: `sistema/app/static/transport/app.js:2638`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo modal
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `clearVehicleModalFeedback`, `vehicleForm`, `vehicleModal`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getRequestsForKind.md](getRequestsForKind.md)

- Funcao no arquivo: `getRequestsForKind`
- Origem: `sistema/app/static/transport/app.js:2647`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: solicitacoes para tipo
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `kind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a solicitacoes para tipo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [getProjectRows.md](getProjectRows.md)

- Funcao no arquivo: `getProjectRows`
- Origem: `sistema/app/static/transport/app.js:2656`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: projeto linhas
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a projeto linhas, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [reconcileProjectVisibility.md](reconcileProjectVisibility.md)

- Funcao no arquivo: `reconcileProjectVisibility`
- Origem: `sistema/app/static/transport/app.js:2663`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: projeto visibility
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getProjectRows`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [hasAnyVisibleProject.md](hasAnyVisibleProject.md)

- Funcao no arquivo: `hasAnyVisibleProject`
- Origem: `sistema/app/static/transport/app.js:2674`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: algum visivel projeto
- Categoria: state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [isProjectVisible.md](isProjectVisible.md)

- Funcao no arquivo: `isProjectVisible`
- Origem: `sistema/app/static/transport/app.js:2684`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: projeto visivel
- Categoria: state
- Responsabilidade: Predicate do controller da pagina que inspeciona os dados disponiveis e devolve a decisao booleana usada para permitir, negar ou destacar um comportamento.
- Entradas: Recebe `projectName` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor booleano usado para gating de UI, validacao ou destaque de estado.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [getVisibleRequestsForKind.md](getVisibleRequestsForKind.md)

- Funcao no arquivo: `getVisibleRequestsForKind`
- Origem: `sistema/app/static/transport/app.js:2695`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: visivel solicitacoes para tipo
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `kind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a visivel solicitacoes para tipo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getRequestsForKind`, `isProjectVisible`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getVehiclesForScope.md](getVehiclesForScope.md)

- Funcao no arquivo: `getVehiclesForScope`
- Origem: `sistema/app/static/transport/app.js:2701`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: vehicles para escopo
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a vehicles para escopo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [getVehicleRegistryRows.md](getVehicleRegistryRows.md)

- Funcao no arquivo: `getVehicleRegistryRows`
- Origem: `sistema/app/static/transport/app.js:2710`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo registry linhas
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo registry linhas, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [getAllRequests.md](getAllRequests.md)

- Funcao no arquivo: `getAllRequests`
- Origem: `sistema/app/static/transport/app.js:2719`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: todas solicitacoes
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a todas solicitacoes, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getRequestsForKind`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getAllVisibleRequests.md](getAllVisibleRequests.md)

- Funcao no arquivo: `getAllVisibleRequests`
- Origem: `sistema/app/static/transport/app.js:2725`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: todas visivel solicitacoes
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a todas visivel solicitacoes, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getVisibleRequestsForKind`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getRequestById.md](getRequestById.md)

- Funcao no arquivo: `getRequestById`
- Origem: `sistema/app/static/transport/app.js:2731`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: solicitacao by id
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `requestId` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a solicitacao by id, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getAllRequests`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getDraggedRequest.md](getDraggedRequest.md)

- Funcao no arquivo: `getDraggedRequest`
- Origem: `sistema/app/static/transport/app.js:2739`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: arrastada solicitacao
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a arrastada solicitacao, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getRequestById`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [getVehicleByScopeAndId.md](getVehicleByScopeAndId.md)

- Funcao no arquivo: `getVehicleByScopeAndId`
- Origem: `sistema/app/static/transport/app.js:2746`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo by escopo and id
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `scope`, `vehicleId` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo by escopo and id, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getVehiclesForScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getPendingAssignmentPreview.md](getPendingAssignmentPreview.md)

- Funcao no arquivo: `getPendingAssignmentPreview`
- Origem: `sistema/app/static/transport/app.js:2754`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: pending assignment previsualizacao
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getRequestById`, `getVehicleByScopeAndId`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [getVehicleDetailsKey.md](getVehicleDetailsKey.md)

- Funcao no arquivo: `getVehicleDetailsKey`
- Origem: `sistema/app/static/transport/app.js:2777`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: detalhes do veiculo chave
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `scope`, `vehicleId` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a detalhes do veiculo chave, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [ensureExpandedVehicleStillExists.md](ensureExpandedVehicleStillExists.md)

- Funcao no arquivo: `ensureExpandedVehicleStillExists`
- Origem: `sistema/app/static/transport/app.js:2781`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: expandido veiculo still exists
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getVehicleDetailsKey`, `getVehiclesForScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [toggleVehicleDetails.md](toggleVehicleDetails.md)

- Funcao no arquivo: `toggleVehicleDetails`
- Origem: `sistema/app/static/transport/app.js:2797`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: detalhes do veiculo
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `scope`, `vehicleId` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getPendingAssignmentPreview`, `getVehicleDetailsKey`, `renderVehiclePanels`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [closeExpandedVehicleDetails.md](closeExpandedVehicleDetails.md)

- Funcao no arquivo: `closeExpandedVehicleDetails`
- Origem: `sistema/app/static/transport/app.js:2813`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: expandido detalhes do veiculo
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearElement`, `findExpandedVehicleDetailsElements`, `renderVehiclePanels`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Agenda ou cancela trabalho assincrono no navegador.

### [findExpandedVehicleDetailsElements.md](findExpandedVehicleDetailsElements.md)

- Funcao no arquivo: `findExpandedVehicleDetailsElements`
- Origem: `sistema/app/static/transport/app.js:2848`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: expandido detalhes do veiculo elements
- Categoria: UI + state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `document`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [syncExpandedVehicleDetailsPosition.md](syncExpandedVehicleDetailsPosition.md)

- Funcao no arquivo: `syncExpandedVehicleDetailsPosition`
- Origem: `sistema/app/static/transport/app.js:2870`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: expandido detalhes do veiculo posicao
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `clearElement`, `findExpandedVehicleDetailsElements`, `parsePixelValue`, `resolveVehicleDetailsPosition`, `document`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [scheduleExpandedVehicleDetailsPositionSync.md](scheduleExpandedVehicleDetailsPositionSync.md)

- Funcao no arquivo: `scheduleExpandedVehicleDetailsPositionSync`
- Origem: `sistema/app/static/transport/app.js:2918`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: expandido detalhes do veiculo posicao sync
- Categoria: state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `syncExpandedVehicleDetailsPosition`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Agenda ou cancela trabalho assincrono no navegador.

### [createPassengerRemoveButton.md](createPassengerRemoveButton.md)

- Funcao no arquivo: `createPassengerRemoveButton`
- Origem: `sistema/app/static/transport/app.js:2935`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: passageiro remocao button
- Categoria: UI + state
- Responsabilidade: Factory/builder do controller da pagina que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `requestRow`, `routeKind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `createNode`, `getRouteKindForRequestRow`, `returnRequestRowToPending`, `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [createVehicleDetailsPanel.md](createVehicleDetailsPanel.md)

- Funcao no arquivo: `createVehicleDetailsPanel`
- Origem: `sistema/app/static/transport/app.js:2951`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: detalhes do veiculo painel
- Categoria: UI + state + date/time
- Responsabilidade: Factory/builder do controller da pagina que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `vehicle`, `assignedRows`, `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `buildVehiclePassengerAwarenessRows`, `buildVehiclePassengerPreviewRows`, `createNode`, `createPassengerRemoveButton`, `getRouteKindForVehicle`, `removeVehicleFromRoute`, `renderRequestTables`, `renderVehiclePanels`, `submitAssignment`, `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [renderProjectList.md](renderProjectList.md)

- Funcao no arquivo: `renderProjectList`
- Origem: `sistema/app/static/transport/app.js:3050`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: projeto list
- Categoria: UI + state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearElement`, `createEmptyState`, `createNode`, `getProjectRows`, `renderDashboard`, `t`, `document`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [createRequestMetaLine.md](createRequestMetaLine.md)

- Funcao no arquivo: `createRequestMetaLine`
- Origem: `sistema/app/static/transport/app.js:3087`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: solicitacao meta line
- Categoria: state + date/time
- Responsabilidade: Factory/builder do controller da pagina que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `requestRow` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `formatTransportDate`, `parseStoredTransportDate`, `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [clearRequestRowStateClass.md](clearRequestRowStateClass.md)

- Funcao no arquivo: `clearRequestRowStateClass`
- Origem: `sistema/app/static/transport/app.js:3105`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: linha de solicitacao state class
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `className` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [renderRequestTables.md](renderRequestTables.md)

- Funcao no arquivo: `renderRequestTables`
- Origem: `sistema/app/static/transport/app.js:3117`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: solicitacao tables
- Categoria: UI + state + date/time
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearElement`, `clearRequestRowStateClass`, `createEmptyState`, `createNode`, `createRequestMetaLine`, `getRequestRowCollapsedState`, `getRequestTitle`, `getVisibleRequestsForKind`, `hasAnyVisibleProject`, `rejectRequestRow`, `renderVehiclePanels`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [groupAssignedRequestsByVehicle.md](groupAssignedRequestsByVehicle.md)

- Funcao no arquivo: `groupAssignedRequestsByVehicle`
- Origem: `sistema/app/static/transport/app.js:3222`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: alocada solicitacoes by veiculo
- Categoria: state + date/time
- Responsabilidade: Organiza colecoes do controller da pagina em uma estrutura intermediaria pronta para renderizacao, filtro ou tomada de decisao.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getRequestsForKind`, `groupAssignedRequestsByVehicleForDate`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [submitAssignment.md](submitAssignment.md)

- Funcao no arquivo: `submitAssignment`
- Origem: `sistema/app/static/transport/app.js:3229`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: assignment
- Categoria: API + state + date/time
- Responsabilidade: Envia uma alteracao de alocacao para a API, trata erros protegidos e recarrega o dashboard quando a operacao e aceita.
- Entradas: Recebe `payload` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getValue`, `handleProtectedRequestError`, `loadDashboard`, `requestJson`, `setStatus`, `t`, `dateStore`
- Endpoints/rotas envolvidos: `POST /api/transport/assignments`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.

### [rejectRequestRow.md](rejectRequestRow.md)

- Funcao no arquivo: `rejectRequestRow`
- Origem: `sistema/app/static/transport/app.js:3244`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: linha de solicitacao
- Categoria: API + state + date/time
- Responsabilidade: Rejeita uma solicitacao de transporte pela API usando o `request_id`, a `service_date` efetiva e a rota resolvida para a linha.
- Entradas: Recebe `requestRow` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getRouteKindForRequestRow`, `getValue`, `handleProtectedRequestError`, `loadDashboard`, `requestJson`, `setStatus`, `t`, `dateStore`
- Endpoints/rotas envolvidos: `POST /api/transport/requests/reject`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.

### [returnRequestRowToPending.md](returnRequestRowToPending.md)

- Funcao no arquivo: `returnRequestRowToPending`
- Origem: `sistema/app/static/transport/app.js:3268`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: linha de solicitacao para pending
- Categoria: state + date/time
- Responsabilidade: Devolve uma solicitacao ao estado pendente, limpando a previsualizacao local e sincronizando as tabelas e os paineis depois da resposta.
- Entradas: Recebe `requestRow`, `routeKind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getSelectedRouteKind`, `renderRequestTables`, `renderVehiclePanels`, `setStatus`, `submitAssignment`, `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [removeVehicleFromRoute.md](removeVehicleFromRoute.md)

- Funcao no arquivo: `removeVehicleFromRoute`
- Origem: `sistema/app/static/transport/app.js:3290`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo from rota
- Categoria: API + state + date/time
- Responsabilidade: Remove um veiculo da agenda/rota atual pela API usando o `schedule_id` e a `service_date`, com feedback visual e recarga do dashboard.
- Entradas: Recebe `vehicle` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getCurrentServiceDateIso`, `getValue`, `handleProtectedRequestError`, `loadDashboard`, `requestJson`, `setStatus`, `t`, `dateStore`
- Endpoints/rotas envolvidos: `DELETE /api/transport/vehicles/{schedule_id}?service_date=...`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.

### [createVehicleIconButton.md](createVehicleIconButton.md)

- Funcao no arquivo: `createVehicleIconButton`
- Origem: `sistema/app/static/transport/app.js:3313`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo icone button
- Categoria: UI + state
- Responsabilidade: Factory/builder do controller da pagina que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `scope`, `vehicle`, `assignedRows` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: `handleVehicleDragOver`, `handleVehicleDrop`, `handleVehicleDragEnter`
- Dependencias observadas: `state`, `canRequestBeDroppedOnVehicle`, `createNode`, `createVehicleDetailsPanel`, `formatVehicleOccupancyCount`, `formatVehicleOccupancyLabel`, `getDraggedRequest`, `getEffectiveWorkToHomeDepartureTime`, `getPendingAssignmentPreview`, `getRequestById`, `getRouteKindForVehicle`, `getRouteKindLabel`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [handleVehicleDragOver.md](handleVehicleDragOver.md)

- Funcao no arquivo: `handleVehicleDragOver`
- Origem: `sistema/app/static/transport/app.js:3385`
- Escopo original: interna de `createVehicleIconButton`
- Tema funcional: veiculo arraste over
- Categoria: utility
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `event` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `canRequestBeDroppedOnVehicle`, `getDraggedRequest`, `getSelectedRouteKind`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [handleVehicleDrop.md](handleVehicleDrop.md)

- Funcao no arquivo: `handleVehicleDrop`
- Origem: `sistema/app/static/transport/app.js:3395`
- Escopo original: interna de `createVehicleIconButton`
- Tema funcional: veiculo drop
- Categoria: state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `event` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `canRequestBeDroppedOnVehicle`, `getRequestById`, `getRouteKindForVehicle`, `getSelectedRouteKind`, `renderRequestTables`, `renderVehiclePanels`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [handleVehicleDragEnter.md](handleVehicleDragEnter.md)

- Funcao no arquivo: `handleVehicleDragEnter`
- Origem: `sistema/app/static/transport/app.js:3424`
- Escopo original: interna de `createVehicleIconButton`
- Tema funcional: veiculo arraste enter
- Categoria: utility
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `event` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `canRequestBeDroppedOnVehicle`, `getDraggedRequest`, `getSelectedRouteKind`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [createVehicleManagementTable.md](createVehicleManagementTable.md)

- Funcao no arquivo: `createVehicleManagementTable`
- Origem: `sistema/app/static/transport/app.js:3446`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo gerenciamento table
- Categoria: UI + state + date/time
- Responsabilidade: Factory/builder do controller da pagina que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `scope`, `registryRows` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `createNode`, `formatRouteTableValue`, `formatVehicleOccupancyCount`, `formatVehicleTypeTableValue`, `getEffectiveWorkToHomeDepartureTime`, `getVehicleDepartureTime`, `mapScopeTitle`, `removeVehicleFromRoute`, `t`, `document`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [renderVehiclePanels.md](renderVehiclePanels.md)

- Funcao no arquivo: `renderVehiclePanels`
- Origem: `sistema/app/static/transport/app.js:3513`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo panels
- Categoria: UI + state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `clearElement`, `createEmptyState`, `createVehicleIconButton`, `createVehicleManagementTable`, `getVehicleRegistryRows`, `getVehicleViewMode`, `getVehiclesForScope`, `groupAssignedRequestsByVehicle`, `mapScopeTitle`, `scheduleExpandedVehicleDetailsPositionSync`, `setVehicleContainerViewMode`, `syncVehicleViewToggleState`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [renderDashboard.md](renderDashboard.md)

- Funcao no arquivo: `renderDashboard`
- Origem: `sistema/app/static/transport/app.js:3563`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: dashboard
- Categoria: state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `ensureExpandedVehicleStillExists`, `renderProjectList`, `renderRequestTables`, `renderVehiclePanels`, `syncRequestSectionToggleState`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [clearDashboard.md](clearDashboard.md)

- Funcao no arquivo: `clearDashboard`
- Origem: `sistema/app/static/transport/app.js:3571`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: dashboard
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearElement`, `createEmptyState`, `getRequestTitle`, `mapScopeTitle`, `renderProjectList`, `setVehicleContainerViewMode`, `syncRequestSectionToggleState`, `syncRouteTimeControls`, `syncVehicleViewToggleState`, `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

### [loadDashboard.md](loadDashboard.md)

- Funcao no arquivo: `loadDashboard`
- Origem: `sistema/app/static/transport/app.js:3600`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: dashboard
- Categoria: API + state + date/time
- Responsabilidade: Carrega o dashboard para a data selecionada, sincroniza o estado local, recalcula visibilidade de projetos e dispara a renderizacao completa das listas e dos paineis de veiculos.
- Entradas: Recebe `selectedDate`, `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearDashboard`, `clearTransportSession`, `formatIsoDate`, `getSelectedRouteKind`, `getTransportLockedMessage`, `getTransportSessionExpiredMessage`, `localizeTransportApiMessage`, `reconcileProjectVisibility`, `renderDashboard`, `requestJson`, `setStatus`
- Endpoints/rotas envolvidos: `GET /api/transport/dashboard`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.

### [initTransportPage.md](initTransportPage.md)

- Funcao no arquivo: `initTransportPage`
- Origem: `sistema/app/static/transport/app.js:3659`
- Escopo original: topo do modulo
- Tema funcional: transporte pagina
- Categoria: UI + date/time
- Responsabilidade: Inicializa a pagina de transporte, cria o store de data, conecta paineis, divisores redimensionaveis, controller principal e listeners globais.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `bootstrapTransportSession`, `closeRouteTimePopover`, `createDatePanelController`, `createTransportDateStore`, `createTransportPageController`, `loadDashboard`, `resolveStoredTransportDate`, `setStoredTransportDate`, `subscribe`, `dateStore`, `document`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.

## sistema/app/static/transport/i18n.js

### [getDictionary.md](getDictionary.md)

- Funcao no arquivo: `getDictionary`
- Origem: `sistema/app/static/transport/i18n.js:971`
- Escopo original: topo do modulo
- Tema funcional: dicionario
- Categoria: i18n
- Responsabilidade: Helper utilitario do modulo de i18n que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `languageCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a dicionario, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.

### [getLanguage.md](getLanguage.md)

- Funcao no arquivo: `getLanguage`
- Origem: `sistema/app/static/transport/i18n.js:975`
- Escopo original: topo do modulo
- Tema funcional: idioma
- Categoria: i18n
- Responsabilidade: Helper utilitario do modulo de i18n que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `languageCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a idioma, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
