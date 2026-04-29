# requestJson

- Nome da funcao: `requestJson`
- Arquivo gerado: `requestJson.md`
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
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function requestJson(url, options) {
    const requestOptions = Object.assign(
      {
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
        },
      },
      options || {}
    );

    if (requestOptions.body && !requestOptions.headers["Content-Type"]) {
      requestOptions.headers["Content-Type"] = "application/json";
    }

    return fetch(url, requestOptions).then(function (response) {
      return response.text().then(function (text) {
        let payload = null;
        if (text) {
          try {
            payload = JSON.parse(text);
          } catch (error) {
            payload = null;
          }
        }

        if (!response.ok) {
          const error = new Error(formatApiErrorMessage(payload, response.status));
          error.status = response.status;
          error.payload = payload;
          throw error;
        }

        return payload;
      });
    });
  }
```
