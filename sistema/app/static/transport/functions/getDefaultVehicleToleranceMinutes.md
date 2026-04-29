# getDefaultVehicleToleranceMinutes

- Nome da funcao: `getDefaultVehicleToleranceMinutes`
- Arquivo gerado: `getDefaultVehicleToleranceMinutes.md`
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
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getDefaultVehicleToleranceMinutes() {
    return vehicleDefaultToleranceMinutes;
  }
```
