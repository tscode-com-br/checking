# handleVehicleDragOver

- Nome da funcao: `handleVehicleDragOver`
- Arquivo gerado: `handleVehicleDragOver.md`
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
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function handleVehicleDragOver(event) {
        if (!canRequestBeDroppedOnVehicle(getDraggedRequest(), scope, vehicle, getSelectedRouteKind())) {
          return;
        }
        event.preventDefault();
        if (event.dataTransfer) {
          event.dataTransfer.dropEffect = "move";
        }
      }
```
