# shiftValue

- Nome da funcao: `shiftValue`
- Arquivo gerado: `shiftValue.md`
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
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function shiftValue(amount) {
      return setValue(shiftLocalDay(selectedDate, amount));
    }
```
