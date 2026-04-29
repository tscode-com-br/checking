# buildVehicleCreatePayload

- Nome da funcao: `buildVehicleCreatePayload`
- Arquivo gerado: `buildVehicleCreatePayload.md`
- Origem: `sistema/app/static/transport/app.js:881`
- Escopo original: topo do modulo
- Tema funcional: veiculo create payload
- Categoria: date/time
- Responsabilidade: Factory/builder do dashboard de transporte que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `formData`, `serviceDate`, `selectedRouteKind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `normalizeVehicleScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function buildVehicleCreatePayload(formData, serviceDate, selectedRouteKind) {
    const serviceScope = normalizeVehicleScope(formData.get("service_scope") || "regular");
    const payload = {
      service_scope: serviceScope,
      service_date: String(serviceDate || ""),
      tipo: String(formData.get("tipo") || "carro"),
      placa: String(formData.get("placa") || ""),
      color: String(formData.get("color") || ""),
      lugares: Number(formData.get("lugares") || 0),
      tolerance: Number(formData.get("tolerance") || 0),
    };

    if (serviceScope === "extra") {
      payload.service_date = String(formData.get("service_date") || "").trim();
      payload.route_kind = String(formData.get("route_kind") || selectedRouteKind || "home_to_work");
      payload.departure_time = String(formData.get("departure_time") || "").trim();
      return payload;
    }

    if (serviceScope === "weekend") {
      payload.every_saturday = Boolean(formData.get("every_saturday"));
      payload.every_sunday = Boolean(formData.get("every_sunday"));
      return payload;
    }

    payload.every_monday = Boolean(formData.get("every_monday"));
    payload.every_tuesday = Boolean(formData.get("every_tuesday"));
    payload.every_wednesday = Boolean(formData.get("every_wednesday"));
    payload.every_thursday = Boolean(formData.get("every_thursday"));
    payload.every_friday = Boolean(formData.get("every_friday"));

    return payload;
  }
```
