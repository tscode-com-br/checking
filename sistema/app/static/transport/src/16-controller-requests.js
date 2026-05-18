          });
      }

      input.addEventListener("input", function () {
        if (isSaving) {
          return;
        }
        syncEditorState();
      });

      input.addEventListener("blur", function () {
        void persistBoardingTime();
      });

      input.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault();
          void persistBoardingTime();
          return;
        }
        if (event.key === "Escape") {
          event.preventDefault();
          restoreCommittedValue();
        }
      });

      editor.appendChild(input);
      syncEditorState();
      return editor;
    }

    function createVehiclePassengerTimeContent(rowViewModel) {
      if (rowViewModel && rowViewModel.canEditBoardingTime) {
        return createVehiclePassengerTimeEditor(rowViewModel);
      }

      return createVehiclePassengerTimeValue(rowViewModel && rowViewModel.timeState);
    }

    function createVehicleDetailsPanel(vehicle, assignedRows, options) {
      const detailOptions = options || {};
      const previewRequestRow = detailOptions.previewRequestRow || null;
      const detailsPanel = createNode("div", "transport-vehicle-details");
      const passengerTableShell = createNode("div", "transport-vehicle-passenger-table-shell");
      const passengerTable = createNode("table", "transport-vehicle-passenger-table");
      const tableBody = createNode("tbody");
      const rowViewModels = buildVehicleDetailsRowViewModels(vehicle, assignedRows, detailOptions);
      const columns = buildVehicleDetailsColumnDefinitions(vehicle, rowViewModels, detailOptions);

      if (rowViewModels.length) {
        passengerTable.appendChild(createVehicleDetailsTableHead(columns));
        rowViewModels.forEach(function (rowViewModel) {
          tableBody.appendChild(createVehicleDetailsTableRow(columns, rowViewModel));
        });

        passengerTable.appendChild(tableBody);
        passengerTableShell.appendChild(passengerTable);
      } else {
        passengerTableShell.appendChild(
          createNode("p", "transport-vehicle-passenger-empty", t("empty.noPassengersAssigned"))
        );
      }

      detailsPanel.appendChild(passengerTableShell);

      if (previewRequestRow) {
        const previewActions = createNode("div", "transport-vehicle-preview-actions");
        const cancelButton = createNode("button", "transport-secondary-button", t("modal.actions.cancel"));
        const confirmButton = createNode("button", "transport-primary-button", t("misc.confirm"));
        const pendingAllocationMessage = getVehiclePendingAllocationMessage(vehicle);

        cancelButton.type = "button";
        confirmButton.type = "button";
        confirmButton.disabled = Boolean(pendingAllocationMessage);
        if (pendingAllocationMessage) {
          confirmButton.title = pendingAllocationMessage;
          confirmButton.setAttribute("aria-label", pendingAllocationMessage);
        }

        cancelButton.addEventListener("click", function (event) {
          event.preventDefault();
          event.stopPropagation();
          state.pendingAssignmentPreview = null;
          renderRequestTables();
          renderVehiclePanels();
        });

        confirmButton.addEventListener("click", function (event) {
          event.preventDefault();
          event.stopPropagation();
          if (pendingAllocationMessage) {
            setStatus(pendingAllocationMessage, "warning");
            return;
          }
          if (!state.dashboard) {
            return;
          }

          submitAssignment({
            request_id: previewRequestRow.id,
            service_date: state.dashboard.selected_date,
            route_kind: detailOptions.routeKind || getRouteKindForVehicle(vehicle.service_scope, vehicle),
            status: "confirmed",
            vehicle_id: vehicle.id,
          })
            .then(function (result) {
              if (result === null) {
                return;
              }
              state.pendingAssignmentPreview = null;
              renderRequestTables();
              renderVehiclePanels();
            })
            .catch(function () {});
        });

        previewActions.appendChild(cancelButton);
        previewActions.appendChild(confirmButton);
        detailsPanel.appendChild(previewActions);
        return detailsPanel;
      }

      const deleteButton = createNode("button", "transport-vehicle-delete-button", t("misc.delete"));
      deleteButton.type = "button";
      deleteButton.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        removeVehicleFromRoute(vehicle);
      });

      const actionRow = createNode("div", "transport-vehicle-details-actions");
      const editButton = createNode("button", "transport-secondary-button transport-vehicle-edit-button", t("misc.edit"));

      editButton.type = "button";
      editButton.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        openVehicleEditModal(vehicle);
      });

      actionRow.appendChild(editButton);
      actionRow.appendChild(deleteButton);
      detailsPanel.insertBefore(actionRow, passengerTableShell);
      return detailsPanel;
    }

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

    function createRequestMetaLine(requestRow) {
      const metaParts = [];
      if (requestRow.service_date) {
        const parsedServiceDate = parseStoredTransportDate(requestRow.service_date);
        metaParts.push(parsedServiceDate ? formatTransportDate(parsedServiceDate) : String(requestRow.service_date));
      }
      if (requestRow.requested_time) {
        metaParts.push(String(requestRow.requested_time));
      }
      if (requestRow.assigned_vehicle) {
        metaParts.push(t("misc.assignedTo", { plate: formatPendingVehicleField(requestRow.assigned_vehicle.placa) }));
      }
      if (requestRow.response_message) {
        metaParts.push(requestRow.response_message);
      }
      return metaParts.join(" | ");
    }

    function clearRequestRowStateClass(className) {
      Object.values(requestContainers).forEach(function (container) {
        if (!container) {
          return;
        }

        container.querySelectorAll(`.transport-request-row.${className}`).forEach(function (rowElement) {
          rowElement.classList.remove(className);
        });
      });
    }

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

    function groupAssignedRequestsByVehicle(scope) {
      return groupAssignedRequestsByVehicleForDate(
        getRequestsForKind(scope),
        state.dashboard ? state.dashboard.selected_date : ""
      );
    }

