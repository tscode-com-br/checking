# scheduleExpandedVehicleDetailsPositionSync

- Nome da funcao: `scheduleExpandedVehicleDetailsPositionSync`
- Arquivo gerado: `scheduleExpandedVehicleDetailsPositionSync.md`
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
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function scheduleExpandedVehicleDetailsPositionSync() {
      if (state.expandedVehiclePositionFrame !== null && typeof globalScope.cancelAnimationFrame === "function") {
        globalScope.cancelAnimationFrame(state.expandedVehiclePositionFrame);
        state.expandedVehiclePositionFrame = null;
      }

      if (typeof globalScope.requestAnimationFrame !== "function") {
        syncExpandedVehicleDetailsPosition();
        return;
      }

      state.expandedVehiclePositionFrame = globalScope.requestAnimationFrame(function () {
        state.expandedVehiclePositionFrame = null;
        syncExpandedVehicleDetailsPosition();
      });
    }
```
