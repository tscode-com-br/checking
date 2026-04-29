# extractApiMessage

- Nome da funcao: `extractApiMessage`
- Arquivo gerado: `extractApiMessage.md`
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
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function extractApiMessage(value) {
    if (typeof value === "string") {
      return value.trim();
    }

    if (Array.isArray(value)) {
      return value
        .map(function (item) {
          return extractApiMessage(item);
        })
        .filter(Boolean)
        .join(" ");
    }

    if (value && typeof value === "object") {
      if (typeof value.msg === "string" && value.msg.trim()) {
        return value.msg.trim();
      }
      if (typeof value.message === "string" && value.message.trim()) {
        return value.message.trim();
      }
      if (typeof value.detail === "string" && value.detail.trim()) {
        return value.detail.trim();
      }
    }

    return "";
  }
```
