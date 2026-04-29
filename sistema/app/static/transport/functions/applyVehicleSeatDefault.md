# applyVehicleSeatDefault

- Nome da funcao: `applyVehicleSeatDefault`
- Arquivo gerado: `applyVehicleSeatDefault.md`
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
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function applyVehicleSeatDefault(vehicleType, formElement) {
    const resolvedForm = resolveVehicleForm(formElement);
    if (!resolvedForm || !resolvedForm.elements.lugares) {
      return;
    }
    resolvedForm.elements.lugares.value = String(getDefaultVehicleSeatCount(vehicleType));
  }
```
