# renderRequestTables

- Nome da funcao: `renderRequestTables`
- Arquivo gerado: `renderRequestTables.md`
- Origem: `sistema/app/static/transport/app.js:3117`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: solicitacao tables
- Categoria: UI + state + date/time
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearElement`, `clearRequestRowStateClass`, `createEmptyState`, `createNode`, `createRequestMetaLine`, `getRequestRowCollapsedState`, `getRequestTitle`, `getVisibleRequestsForKind`, `hasAnyVisibleProject`, `rejectRequestRow`, `renderVehiclePanels`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function renderRequestTables() {
      REQUEST_SECTION_ORDER.forEach(function (kind) {
        const container = requestContainers[kind];
        const requestRows = getVisibleRequestsForKind(kind);
        clearElement(container);
        if (!container) {
          return;
        }

        if (!hasAnyVisibleProject()) {
          container.appendChild(createEmptyState(t("empty.noProjectsSelected")));
          return;
        }

        if (!requestRows.length) {
          container.appendChild(createEmptyState(t("empty.noRows", { title: getRequestTitle(kind) })));
          return;
        }

        requestRows.forEach(function (requestRow) {
          const rowShell = createNode("div", "transport-request-row-shell");
          const rowButton = createNode("div", `transport-request-row is-${requestRow.assignment_status}`);
          const rejectButton = createNode("button", "transport-request-reject-button", "X");
          const requestMatchesSelectedDate = !state.dashboard
            || String(requestRow.service_date || "") === String(state.dashboard.selected_date || "");
          const metaLine = createRequestMetaLine(requestRow);
          rowButton.draggable = requestMatchesSelectedDate;
          rowButton.dataset.requestId = String(requestRow.id);
          rowButton.classList.toggle("is-readonly", !requestMatchesSelectedDate);
          rowButton.classList.toggle("is-dragging", Number(state.dragRequestId) === Number(requestRow.id));
          rowButton.classList.toggle(
            "is-previewing",
            !!state.pendingAssignmentPreview && Number(state.pendingAssignmentPreview.requestId) === Number(requestRow.id)
          );
          rowButton.classList.toggle("is-collapsed", getRequestRowCollapsedState(requestRow));
          rowButton.tabIndex = 0;
          rowButton.setAttribute("role", "button");
          rowButton.setAttribute("aria-expanded", String(!getRequestRowCollapsedState(requestRow)));
          rowShell.classList.toggle("is-collapsed", getRequestRowCollapsedState(requestRow));

          const nameCell = createNode("span", "transport-request-primary", requestRow.nome);
          const addressCell = createNode("span", "transport-request-secondary", requestRow.end_rua || t("misc.addressPending"));
          const zipCell = createNode("span", "transport-request-secondary transport-request-zip", requestRow.zip || t("misc.zipPending"));

          if (shouldHighlightRequestName(requestRow.assignment_status)) {
            nameCell.classList.add("is-attention");
          }

          rowButton.appendChild(nameCell);
          rowButton.appendChild(addressCell);
          rowButton.appendChild(zipCell);
          if (metaLine) {
            rowButton.appendChild(createNode("span", "transport-request-meta", metaLine));
          }

          rejectButton.type = "button";
          rejectButton.setAttribute("aria-label", t("misc.reject"));
          rejectButton.title = t("misc.reject");
          rejectButton.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            void rejectRequestRow(requestRow);
          });

          rowButton.addEventListener("dragstart", function (event) {
            state.pendingAssignmentPreview = null;
            clearRequestRowStateClass("is-previewing");
            clearRequestRowStateClass("is-dragging");
            state.dragRequestId = requestRow.id;
            rowButton.classList.add("is-dragging");
            if (event.dataTransfer) {
              event.dataTransfer.effectAllowed = "move";
              event.dataTransfer.setData("text/plain", String(requestRow.id));
            }
            renderVehiclePanels();
          });

          rowButton.addEventListener("dragend", function () {
            rowButton.classList.remove("is-dragging");
            state.dragRequestId = null;
            renderRequestTables();
            renderVehiclePanels();
          });

          rowButton.addEventListener("click", function () {
            toggleRequestRowCollapsed(requestRow, rowButton);
          });

          rowButton.addEventListener("keydown", function (event) {
            if (event.key !== "Enter" && event.key !== " ") {
              return;
            }
            event.preventDefault();
            toggleRequestRowCollapsed(requestRow, rowButton);
          });

          rowShell.appendChild(rowButton);
          rowShell.appendChild(rejectButton);
          container.appendChild(rowShell);
        });
      });

      syncRequestSectionToggleState();
    }
```
