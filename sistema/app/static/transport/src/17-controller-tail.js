  function submitAssignment(payload) {
    return requestJson(`${TRANSPORT_API_PREFIX}/assignments`, {
      method: "POST",
      body: JSON.stringify(payload),
    }).then(function (response) {
      const structuredAllocationUpdatedMessage = resolveTransportApiStructuredMessage(response)
        || String(response && response.message || "").trim();
      const allocationUpdatedMessage = structuredAllocationUpdatedMessage || t("status.allocationUpdated");
      const allocationUpdatedOptions = resolveTransportApiStructuredMessageOptions(response)
        || (structuredAllocationUpdatedMessage ? undefined : { key: "status.allocationUpdated" });
      setStatus(allocationUpdatedMessage, "success", allocationUpdatedOptions);
      return loadDashboard(dateStore.getValue(), { announce: false });
    }).catch(function (error) {
        if (handleProtectedRequestError(error, t("status.couldNotUpdateAllocation"))) {
          return null;
        }
        throw error;
      });
    }

    function rejectRequestRow(requestRow) {
      if (!requestRow || !requestRow.id || !requestRow.service_date) {
        setStatus("", "error", { key: "status.couldNotRejectSelectedRequest" });
        return Promise.resolve();
      }

      return requestJson(`${TRANSPORT_API_PREFIX}/requests/reject`, {
        method: "POST",
        body: JSON.stringify({
          request_id: requestRow.id,
          service_date: requestRow.service_date,
          route_kind: getRouteKindForRequestRow(requestRow),
        }),
      }).then(function (response) {
        const structuredRequestRejectedMessage = resolveTransportApiStructuredMessage(response)
          || String(response && response.message || "").trim();
        const requestRejectedMessage = structuredRequestRejectedMessage || t("status.requestRejected");
        const requestRejectedOptions = resolveTransportApiStructuredMessageOptions(response)
          || (structuredRequestRejectedMessage ? undefined : { key: "status.requestRejected" });
        setStatus(requestRejectedMessage, "success", requestRejectedOptions);
        return loadDashboard(dateStore.getValue(), { announce: false });
      }).catch(function (error) {
        if (handleProtectedRequestError(error, t("status.couldNotRejectSelectedRequest"))) {
          return null;
        }
        throw error;
      });
    }

    function returnRequestRowToPending(requestRow, routeKind) {
      if (!requestRow || !requestRow.id || !requestRow.service_date) {
        setStatus("", "error", { key: "status.couldNotUpdateAllocation" });
        return Promise.resolve();
      }

      return submitAssignment({
        request_id: requestRow.id,
        service_date: requestRow.service_date,
        route_kind: routeKind || getSelectedRouteKind(),
        status: "pending",
      }).then(function (result) {
        if (result === null) {
          return null;
        }
        state.pendingAssignmentPreview = null;
        renderRequestTables();
        renderVehiclePanels();
        return result;
      }).catch(function () {});
    }

    function removeVehicleFromRoute(vehicle) {
      if (!vehicle || vehicle.schedule_id === null || vehicle.schedule_id === undefined) {
        setStatus("", "error", { key: "warnings.vehicleCannotBeRemoved" });
        return Promise.resolve();
      }

      const deleteServiceDate = vehicle.service_date || getCurrentServiceDateIso();

      return requestJson(
        `${TRANSPORT_API_PREFIX}/vehicles/${encodeURIComponent(String(vehicle.schedule_id))}?service_date=${encodeURIComponent(deleteServiceDate)}`,
        {
          method: "DELETE",
        }
      )
        .then(function (response) {
          const structuredVehicleDeletedMessage = resolveTransportApiStructuredMessage(response)
            || String(response && response.message || "").trim();
          const vehicleDeletedMessage = structuredVehicleDeletedMessage || t("status.vehicleDeleted");
          const vehicleDeletedOptions = resolveTransportApiStructuredMessageOptions(response)
            || (structuredVehicleDeletedMessage ? undefined : { key: "status.vehicleDeleted" });
          setStatus(vehicleDeletedMessage, "success", vehicleDeletedOptions);
          return loadDashboard(dateStore.getValue(), { announce: false });
        })
        .catch(function (error) {
          handleProtectedRequestError(error, t("status.couldNotDeleteVehicle"));
        });
    }

    function createVehicleIconButton(scope, vehicle, assignedRows) {
      const tileElement = createNode("div", "transport-vehicle-tile");
      const vehicleButton = createNode("button", "transport-vehicle-button");
      const assignedCount = assignedRows.length;
      const departureTime = getVehicleReferenceLabel(
        scope,
        vehicle,
        state.dashboard,
        state.arriveAtWorkTime,
        state.vehicleReferenceClock,
        state.workToHomeTime,
        vehicle && vehicle.route_kind
      );
      const vehicleDetailsKey = getVehicleDetailsKey(scope, vehicle.id);
      const draggedRequest = getDraggedRequest();
      const pendingPreview = getPendingAssignmentPreview();
      const previewRequestRow = pendingPreview
        && pendingPreview.scope === scope
        && Number(pendingPreview.vehicle.id) === Number(vehicle.id)
        ? pendingPreview.requestRow
        : null;
      const isDropTarget = canRequestBeDroppedOnVehicle(draggedRequest, scope, vehicle, getSelectedRouteKind());
      const isExpanded = state.expandedVehicleKey === vehicleDetailsKey;
      const pendingAllocationMessage = getVehiclePendingAllocationMessage(vehicle);

      vehicleButton.type = "button";
      vehicleButton.dataset.vehicleId = String(vehicle.id);
      vehicleButton.dataset.vehicleScope = scope;
      vehicleButton.dataset.vehicleDetailsAnchorKey = vehicleDetailsKey;
      vehicleButton.title = t("misc.vehicleButtonTitle", {
        type: formatPendingVehicleField(vehicle.tipo, mapVehicleTypeLabel),
        occupancy: formatVehicleOccupancyLabel(vehicle, assignedCount),
      });
      vehicleButton.classList.toggle("is-selectable", isDropTarget);
      vehicleButton.classList.toggle("is-preview-target", !!previewRequestRow);
      vehicleButton.classList.toggle("is-details-open", isExpanded);
      vehicleButton.classList.toggle("is-pending-allocation", !!pendingAllocationMessage);
      tileElement.classList.toggle("is-expanded", isExpanded);
      if (!isDropTarget && !previewRequestRow) {
        vehicleButton.classList.add("is-idle");
      }

      const iconImage = document.createElement("img");
      iconImage.className = "transport-vehicle-icon";
      iconImage.src = mapVehicleIconPath(vehicle);
      iconImage.alt = "";

      const plateLabel = createPendingVehicleFieldNode("span", "transport-vehicle-plate", vehicle.placa);
      const occupancyLabel = createNode(
        "span",
        "transport-vehicle-occupancy",
        formatVehicleOccupancyCount(vehicle, assignedCount)
      );
      if (isPendingVehicleField(vehicle.lugares)) {
        occupancyLabel.classList.add("transport-pending-value");
      }
      const departureLabel = departureTime
        ? createNode("span", "transport-vehicle-departure", departureTime)
        : null;
      const routeLabel = scope === "extra" && vehicle.route_kind
        ? createNode("span", "transport-vehicle-route", getRouteKindLabel(vehicle.route_kind))
        : null;

      if (scope === "extra" && vehicle.route_kind) {
        vehicleButton.title = `${vehicleButton.title} | ${getRouteKindLabel(vehicle.route_kind)}`;
      }
      if (departureLabel) {
        departureLabel.setAttribute("aria-label", departureTime);
        vehicleButton.title = `${vehicleButton.title} | ${departureTime}`;
      }
      if (pendingAllocationMessage) {
        vehicleButton.title = `${vehicleButton.title} | ${pendingAllocationMessage}`;
      }
      vehicleButton.setAttribute("aria-label", vehicleButton.title);
      vehicleButton.appendChild(plateLabel);
      vehicleButton.appendChild(iconImage);
      vehicleButton.appendChild(occupancyLabel);
      if (departureLabel) {
        vehicleButton.appendChild(departureLabel);
      }
      if (routeLabel) {
        vehicleButton.appendChild(routeLabel);
      }
      vehicleButton.addEventListener("click", function () {
        toggleVehicleDetails(scope, vehicle.id);
      });

      function handleVehicleDragOver(event) {
        if (!canRequestBeDroppedOnVehicle(getDraggedRequest(), scope, vehicle, getSelectedRouteKind())) {
          return;
        }
        event.preventDefault();
        if (event.dataTransfer) {
          event.dataTransfer.dropEffect = "move";
        }
      }

      function handleVehicleDrop(event) {
        const droppedRequestId = Number(
          state.dragRequestId !== null
            ? state.dragRequestId
            : event.dataTransfer
              ? event.dataTransfer.getData("text/plain")
              : ""
        );
        const droppedRequest = getRequestById(droppedRequestId);
        if (!canRequestBeDroppedOnVehicle(droppedRequest, scope, vehicle, getSelectedRouteKind())) {
          state.dragRequestId = null;
          renderRequestTables();
          renderVehiclePanels();
          return;
        }

        event.preventDefault();
        state.expandedVehicleKey = vehicleDetailsKey;
        state.pendingAssignmentPreview = {
          requestId: droppedRequest.id,
          vehicleId: vehicle.id,
          scope,
          routeKind: getRouteKindForVehicle(scope, vehicle),
        };
        state.dragRequestId = null;
        renderRequestTables();
        renderVehiclePanels();
      }

      function handleVehicleDragEnter(event) {
        if (!canRequestBeDroppedOnVehicle(getDraggedRequest(), scope, vehicle, getSelectedRouteKind())) {
          return;
        }
        event.preventDefault();
      }

      tileElement.addEventListener("dragover", handleVehicleDragOver);
      tileElement.addEventListener("drop", handleVehicleDrop);
      tileElement.addEventListener("dragenter", handleVehicleDragEnter);

      tileElement.appendChild(vehicleButton);
      if (isExpanded) {
        tileElement.expandedDetailsPanel = createVehicleDetailsPanel(vehicle, assignedRows, {
          previewRequestRow,
          scope,
          routeKind: pendingPreview ? pendingPreview.routeKind : getRouteKindForVehicle(scope, vehicle),
        });
        tileElement.expandedDetailsPanel.dataset.vehicleDetailsPanelKey = vehicleDetailsKey;
      }
      return tileElement;
    }

    function createVehicleManagementTable(scope, registryRows) {
      const table = createNode("table", "transport-vehicle-management-table");
      const tableBody = document.createElement("tbody");

      registryRows.forEach(function (rowData) {
        const row = createNode("tr", "transport-vehicle-management-row");
        const typeCell = createNode("td", "transport-vehicle-management-type");
        const plateCell = createNode("td", "transport-vehicle-management-plate-cell");
        const occupancyCell = createNode("td", "transport-vehicle-management-occupancy");
        const actionsCell = createNode("td", "transport-vehicle-management-actions");
        const vehicleType = createPendingVehicleFieldNode(
          "span",
          "transport-vehicle-management-type-value",
          rowData.tipo,
          formatVehicleTypeTableValue
        );
        const vehiclePlate = createPendingVehicleFieldNode("strong", "transport-vehicle-management-plate", rowData.placa);
        const occupancyValue = createNode(
          "span",
          "transport-vehicle-management-occupancy-value",
          formatVehicleOccupancyCount(rowData, rowData.assigned_count)
        );
        const departureTime = getVehicleReferenceLabel(
          scope,
          rowData,
          state.dashboard,
          state.arriveAtWorkTime,
          state.vehicleReferenceClock,
          state.workToHomeTime,
          rowData && rowData.route_kind
        );
        const deleteButton = createNode(
          "button",
          "transport-vehicle-delete-button transport-vehicle-management-delete",
          t("misc.delete")
        );

        occupancyCell.classList.toggle("is-occupied", Number(rowData.assigned_count) > 0);
        deleteButton.type = "button";
        deleteButton.disabled = rowData.schedule_id === null || rowData.schedule_id === undefined;
        deleteButton.addEventListener("click", function (event) {
          event.preventDefault();
          event.stopPropagation();
          removeVehicleFromRoute(rowData);
        });

        if (isPendingVehicleField(rowData.lugares)) {
          occupancyValue.classList.add("transport-pending-value");
        }

        typeCell.appendChild(vehicleType);
        plateCell.appendChild(vehiclePlate);
        occupancyCell.appendChild(occupancyValue);
        row.appendChild(typeCell);
        row.appendChild(plateCell);
        if (departureTime) {
          row.appendChild(createNode("td", "transport-vehicle-management-time", departureTime));
        }
        actionsCell.appendChild(deleteButton);
        row.appendChild(occupancyCell);

        if (scope === "extra") {
          row.appendChild(
            createNode("td", "transport-vehicle-management-date", rowData.service_date || "")
          );
          row.appendChild(
            createNode(
              "td",
              "transport-vehicle-management-route-value",
              rowData.route_kind ? formatRouteTableValue(rowData.route_kind) : ""
            )
          );
        }

        row.appendChild(actionsCell);
        tableBody.appendChild(row);
      });

      table.appendChild(tableBody);
      table.setAttribute("aria-label", t("misc.vehiclesAria", { scope: mapScopeTitle(scope) }));
      return table;
    }

    function renderVehiclePanels() {
      syncVehicleViewToggleState();
      clearElement(vehicleDetailsOverlayHost);
      vehicleDetailsOverlayHost.classList.remove("is-active");
      let hasExpandedDetailsPanel = false;

      VEHICLE_SCOPE_ORDER.forEach(function (scope) {
        const container = vehicleContainers[scope];
        const vehicles = getVehiclesForScope(scope);
        const registryRows = getVehicleRegistryRows(scope);
        const assignedRowsByVehicle = groupAssignedRequestsByVehicle(scope);
        clearElement(container);
        if (!container) {
          return;
        }

        setVehicleContainerViewMode(container, scope);

        if (getVehicleViewMode(scope) === "table") {
          if (!registryRows.length) {
            container.appendChild(createEmptyState(t("empty.noVehicles", { scope: mapScopeTitle(scope) })));
            return;
          }
          container.appendChild(createVehicleManagementTable(scope, registryRows));
          return;
        }

        if (!vehicles.length) {
          container.appendChild(createEmptyState(t("empty.noVehicles", { scope: mapScopeTitle(scope) })));
          return;
        }

        vehicles.forEach(function (vehicle) {
          const assignedRows = assignedRowsByVehicle[String(vehicle.id)] || [];
          const tileElement = createVehicleIconButton(scope, vehicle, assignedRows);
          container.appendChild(tileElement);
          if (tileElement.expandedDetailsPanel) {
            vehicleDetailsOverlayHost.appendChild(tileElement.expandedDetailsPanel);
            hasExpandedDetailsPanel = true;
          }
        });

        updateVehicleGridLayout(container);
      });

      vehicleDetailsOverlayHost.classList.toggle("is-active", hasExpandedDetailsPanel);

      scheduleExpandedVehicleDetailsPositionSync();
    }

    function renderDashboard() {
      ensureExpandedVehicleStillExists();
      renderProjectList();
      renderRequestTables();
      renderVehiclePanels();
      const vehiclePanelsRoot = document.getElementById("tela01main_dir");
      if (vehiclePanelsRoot) {
        syncVehiclePanelExplicitHeights(vehiclePanelsRoot);
        updateVehicleGridLayouts(vehiclePanelsRoot);
      }
      syncRequestSectionToggleState();
    }

    function clearDashboard() {
      clearVehicleReferenceClock();
      renderProjectList();
      REQUEST_SECTION_ORDER.forEach(function (kind) {
        const container = requestContainers[kind];
        clearElement(container);
        if (container) {
          container.appendChild(createEmptyState(t("empty.noRows", { title: getRequestTitle(kind) })));
        }
      });
      VEHICLE_SCOPE_ORDER.forEach(function (scope) {
        const container = vehicleContainers[scope];
        clearElement(container);
        if (container) {
          setVehicleContainerViewMode(container, scope);
          container.appendChild(createEmptyState(t("empty.noVehicles", { scope: mapScopeTitle(scope) })));
          container.style.removeProperty("grid-template-rows");
          container.style.removeProperty("grid-auto-columns");
        }
      });
      clearElement(vehicleDetailsOverlayHost);
      vehicleDetailsOverlayHost.classList.remove("is-active");
      state.expandedVehicleKey = null;
      state.pendingAssignmentPreview = null;
      state.dragRequestId = null;
      syncVehicleViewToggleState();
      syncRequestSectionToggleState();
      syncRouteTimeControls();
    }

    function loadDashboard(selectedDate, options) {
      const loadOptions = options || {};
      const shouldAnnounce = loadOptions.announce !== false;
      if (!state.isAuthenticated) {
        if (state.sessionBootstrapPending) {
          return Promise.resolve(null);
        }
        state.dashboard = null;
        clearDashboard();
        setStatus("", "warning", { key: "status.locked" });
        return Promise.resolve(null);
      }

      const normalizedDate = startOfLocalDay(selectedDate || dateStore.getValue());
      const serviceDate = formatIsoDate(normalizedDate);
      const routeKind = getSelectedRouteKind();

      if (isTransportPageHidden() && loadOptions.allowWhileHidden !== true) {
        queueDeferredDashboardLoad(normalizedDate, loadOptions);
        return state.dashboardLoadPromise || Promise.resolve(null);
      }

      if (state.dashboardLoadPromise) {
        queueDashboardLoad(normalizedDate, loadOptions);
        return state.dashboardLoadPromise;
      }

      state.pendingAssignmentPreview = null;
      state.dragRequestId = null;
      state.isLoading = true;
      clearVehicleReferenceModeTimer();
      syncRouteTimeControls();
      if (shouldAnnounce) {
        setStatus("", "info", { key: "status.loadingDashboard" });
      }
      state.dashboardLoadPromise = requestJson(
        `${TRANSPORT_API_PREFIX}/dashboard?service_date=${encodeURIComponent(serviceDate)}&route_kind=${encodeURIComponent(routeKind)}`
      )
        .then(function (dashboard) {
          state.dashboard = dashboard || null;
          syncTransportReferenceClock(state.dashboard);
          reconcileProjectVisibility();
          state.selectedRouteKind = (dashboard && dashboard.selected_route) || routeKind;
          syncRouteInputs();
          syncRouteTimeControls();
          if (shouldAnnounce) {
            setStatus("", "info", { key: "status.dashboardUpdated" });
          }
          renderDashboard();
          applyStaticTranslations();
          scheduleVehicleReferenceModeTimer();
        })
        .catch(function (error) {
          state.dashboard = null;
          clearDashboard();
          applyStaticTranslations();
          if (error && Number(error.status) === 401) {
            clearTransportSession(getTransportSessionExpiredMessage());
            return;
          }
          const structuredDashboardErrorMessage = resolveTransportApiStructuredMessage(error && error.payload)
            || localizeTransportApiMessage(error && error.message);
          const dashboardErrorMessage = structuredDashboardErrorMessage || t("status.couldNotLoadDashboard");
          const dashboardErrorOptions = resolveTransportApiStructuredMessageOptions(error && error.payload)
            || (structuredDashboardErrorMessage ? undefined : { key: "status.couldNotLoadDashboard" });
          setStatus(dashboardErrorMessage, "error", dashboardErrorOptions);
        })
        .finally(function () {
          const queuedLoad = state.queuedDashboardLoad;
          state.dashboardLoadPromise = null;
          if (queuedLoad && state.isAuthenticated) {
            state.queuedDashboardLoad = null;
            if (isTransportPageHidden()) {
              queueDeferredDashboardLoad(queuedLoad.selectedDate, queuedLoad.options);
              state.isLoading = false;
              syncRouteTimeControls();
              return null;
            }
            return loadDashboard(queuedLoad.selectedDate, queuedLoad.options);
          }
          state.queuedDashboardLoad = null;
          state.isLoading = false;
          syncRouteTimeControls();
        });
      return state.dashboardLoadPromise;
    }

    return {
      __testCreateVehicleDetailsPanel: createVehicleDetailsPanel,
      bootstrapTransportSession,
      closeRouteTimePopover,
      handlePageVisibilityChange,
      loadDashboard,
      refreshVehicleGridLayouts: function () {
        const vehiclePanelsRoot = document.getElementById("tela01main_dir");
        if (vehiclePanelsRoot) {
          syncVehiclePanelExplicitHeights(vehiclePanelsRoot);
          updateVehicleGridLayouts(vehiclePanelsRoot);
          syncVehiclePanelResizeHandleState(vehiclePanelsRoot);
        } else {
          updateVehicleGridLayouts(document);
          syncVehiclePanelResizeHandleState(document);
        }
        scheduleExpandedVehicleDetailsPositionSync();
        syncAiButtonPlacement();
      },
    };
  }
