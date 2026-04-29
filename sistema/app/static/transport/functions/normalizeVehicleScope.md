# normalizeVehicleScope

- Nome da funcao: `normalizeVehicleScope`
- Arquivo gerado: `normalizeVehicleScope.md`
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
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function normalizeVehicleScope(scope) {
    const normalizedScope = String(scope || "").trim().toLowerCase();
    if (normalizedScope === "regular" || normalizedScope === "weekend" || normalizedScope === "extra") {
      return normalizedScope;
    }
    return "regular";
  }
```
