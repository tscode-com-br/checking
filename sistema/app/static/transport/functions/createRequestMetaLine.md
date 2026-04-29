# createRequestMetaLine

- Nome da funcao: `createRequestMetaLine`
- Arquivo gerado: `createRequestMetaLine.md`
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
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function createRequestMetaLine(requestRow) {
      const metaParts = [];
      if (requestRow.service_date) {
        const parsedServiceDate = parseStoredTransportDate(requestRow.service_date);
        metaParts.push(parsedServiceDate ? formatTransportDate(parsedServiceDate) : String(requestRow.service_date));
      }
      if (requestRow.requested_time) {
        metaParts.push(String(requestRow.requested_time));
      }
      if (requestRow.assigned_vehicle) {
        metaParts.push(t("misc.assignedTo", { plate: requestRow.assigned_vehicle.placa }));
      }
      if (requestRow.response_message) {
        metaParts.push(requestRow.response_message);
      }
      return metaParts.join(" | ");
    }
```
