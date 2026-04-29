# renderProjectList

- Nome da funcao: `renderProjectList`
- Arquivo gerado: `renderProjectList.md`
- Origem: `sistema/app/static/transport/app.js:3050`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: projeto list
- Categoria: UI + state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearElement`, `createEmptyState`, `createNode`, `getProjectRows`, `renderDashboard`, `t`, `document`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function renderProjectList() {
      if (projectListPanel) {
        projectListPanel.hidden = !state.projectListOpen;
      }
      if (projectListToggle) {
        projectListToggle.setAttribute("aria-expanded", String(state.projectListOpen));
      }
      if (!projectListContainer) {
        return;
      }

      clearElement(projectListContainer);
      const projectRows = getProjectRows();
      if (!projectRows.length) {
        projectListContainer.appendChild(createEmptyState(t("empty.noProjectsAvailable")));
        return;
      }

      projectRows.forEach(function (projectRow) {
        const label = createNode("label", "transport-project-chip");
        const checkbox = document.createElement("input");
        const text = createNode("span", "transport-project-chip-label", projectRow.name);

        checkbox.type = "checkbox";
        checkbox.checked = state.projectVisibility[projectRow.name] !== false;
        label.classList.toggle("is-selected", checkbox.checked);
        checkbox.addEventListener("change", function () {
          state.projectVisibility[projectRow.name] = checkbox.checked;
          renderDashboard();
        });

        label.appendChild(checkbox);
        label.appendChild(text);
        projectListContainer.appendChild(label);
      });
    }
```
