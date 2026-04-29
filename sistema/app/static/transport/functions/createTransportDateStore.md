# createTransportDateStore

- Nome da funcao: `createTransportDateStore`
- Arquivo gerado: `createTransportDateStore.md`
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
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function createTransportDateStore(initialValue) {
    const subscribers = new Set();
    let selectedDate = startOfLocalDay(initialValue || new Date());

    function getValue() {
      return new Date(selectedDate);
    }

    function notify() {
      const nextValue = getValue();
      subscribers.forEach(function (subscriber) {
        subscriber(nextValue);
      });
    }

    function setValue(value, options) {
      selectedDate = startOfLocalDay(value);
      if (!options || options.notify !== false) {
        notify();
      }
      return getValue();
    }

    function shiftValue(amount) {
      return setValue(shiftLocalDay(selectedDate, amount));
    }

    function subscribe(subscriber) {
      if (typeof subscriber !== "function") {
        return function () {};
      }

      subscribers.add(subscriber);
      subscriber(getValue());

      return function unsubscribe() {
        subscribers.delete(subscriber);
      };
    }

    return {
      getValue,
      setValue,
      shiftValue,
      subscribe,
    };
  }
```
