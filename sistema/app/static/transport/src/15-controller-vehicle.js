        .finally(function () {
          state.aiRouteRequestPending = false;
          syncAiAgentSettingsControls({ preserveInputs: true });
        });
    }

    function openAiAgentSettingsModal() {
      if (!aiAgentModal) {
        return;
      }
      closeAiMenu();
      closeAiChangesModal();
      closeAiSettingsModal({ force: true });
      closeExpandedVehicleDetails({ render: false });
      state.aiAgentSettingsDraft = getDefaultAiAgentSettings();
      clearAiAgentFeedback();
      applyStaticTranslations();
      syncAiAgentSettingsControls();
      aiAgentModal.hidden = false;
      if (aiAgentEarliestBoardingInput && typeof aiAgentEarliestBoardingInput.focus === "function") {
        aiAgentEarliestBoardingInput.focus();
        return;
      }
      if (aiAgentArrivalAtWorkInput && typeof aiAgentArrivalAtWorkInput.focus === "function") {
        aiAgentArrivalAtWorkInput.focus();
      }
    }

    function closeAiAgentSettingsModal(options) {
      if (!aiAgentModal) {
        return;
      }
      const closeOptions = options || {};
      const hasActiveRun = state.aiRouteRequestPending
        || state.aiRoutePollingTimer !== null
        || shouldContinuePollingAiRouteRun(state.aiRouteRunStatus);
      if (!closeOptions.force && hasActiveRun && !state.aiRouteInBackground) {
        return;
      }

      state.aiAgentSettingsDraft = getDefaultAiAgentSettings();
      clearAiAgentFeedback();
      aiAgentModal.hidden = true;
      if (
        closeOptions.restoreFocus
        && aiMenuTrigger
        && typeof aiMenuTrigger.focus === "function"
      ) {
        aiMenuTrigger.focus();
      }
    }

    function syncRouteInputs() {}

    function getSelectedRouteKind() {
      return state.selectedRouteKind || "home_to_work";
    }

    function getRouteKindForVehicle(scope, vehicle) {
      if (scope === "extra" && vehicle && vehicle.route_kind) {
        return vehicle.route_kind;
      }
      return getSelectedRouteKind();
    }

    function getRouteKindForRequestRow(requestRow, fallbackRouteKind) {
      if (
        requestRow
        && requestRow.request_kind === "extra"
        && requestRow.assigned_vehicle
        && requestRow.assigned_vehicle.route_kind
      ) {
        return requestRow.assigned_vehicle.route_kind;
      }
      return fallbackRouteKind || getSelectedRouteKind();
    }

    function getCurrentServiceDateIso() {
      return formatIsoDate(dateStore.getValue());
    }

    function canOpenVehicleModal(scope) {
      if (!state.isAuthenticated) {
        setStatus("", "warning", { key: "status.locked" });
        return false;
      }
      return true;
    }

    function syncVehicleModalFields(scope) {
      if (!vehicleForm) {
        return;
      }

      const normalizedScope = normalizeVehicleScope(scope);
      const isEditMode = isVehicleModalEditMode();
      const showExtraFields = !isEditMode && normalizedScope === "extra";
      const showWeekendPersistence = !isEditMode && normalizedScope === "weekend";
      const showRegularPersistence = !isEditMode && normalizedScope === "regular";

      syncVehicleModalCopy(normalizedScope);
      if (extraVehicleSection) {
        extraVehicleSection.hidden = !showExtraFields;
      }
      if (weekendPersistenceGroup) {
        weekendPersistenceGroup.hidden = !showWeekendPersistence;
      }
      if (regularPersistenceGroup) {
        regularPersistenceGroup.hidden = !showRegularPersistence;
      }
      if (extraServiceDateField) {
        extraServiceDateField.hidden = !showExtraFields;
      }
      if (extraDepartureField) {
        extraDepartureField.hidden = !showExtraFields;
      }
      if (extraRouteField) {
        extraRouteField.hidden = !showExtraFields;
      }
      weekendPersistenceFields.forEach(function (fieldElement) {
        fieldElement.hidden = !showWeekendPersistence;
      });
      regularPersistenceFields.forEach(function (fieldElement) {
        fieldElement.hidden = !showRegularPersistence;
      });
      if (vehicleForm.elements.route_kind) {
        if (!isEditMode && normalizedScope === "extra") {
          const currentRouteKind = String(vehicleForm.elements.route_kind.value || "").trim();
          vehicleForm.elements.route_kind.value = Object.prototype.hasOwnProperty.call(ROUTE_KIND_KEYS, currentRouteKind)
            ? currentRouteKind
            : getSelectedRouteKind();
        }
        vehicleForm.elements.route_kind.disabled = isEditMode || normalizedScope !== "extra";
      }
      syncExtraVehicleDepartureFieldCopy(normalizedScope);
      if (vehicleForm.elements.service_date) {
        vehicleForm.elements.service_date.required = !isEditMode && normalizedScope === "extra";
        vehicleForm.elements.service_date.disabled = isEditMode || normalizedScope !== "extra";
      }
      if (vehicleForm.elements.service_date && !isEditMode && normalizedScope !== "extra") {
        vehicleForm.elements.service_date.value = "";
      }
      if (vehicleForm.elements.departure_time) {
        vehicleForm.elements.departure_time.required = !isEditMode && normalizedScope === "extra";
        vehicleForm.elements.departure_time.disabled = isEditMode || normalizedScope !== "extra";
      }
      if (vehicleForm.elements.departure_time && !isEditMode && normalizedScope !== "extra") {
        vehicleForm.elements.departure_time.value = "";
      }
      if (!isEditMode) {
        if (vehicleForm.elements.every_saturday) {
          vehicleForm.elements.every_saturday.checked = false;
        }
        if (vehicleForm.elements.every_sunday) {
          vehicleForm.elements.every_sunday.checked = false;
        }
      }
    }

    function openVehicleModal(scope) {
      if (!vehicleModal || !vehicleForm) {
        return;
      }
      const normalizedScope = normalizeVehicleScope(scope);
      if (!canOpenVehicleModal(normalizedScope)) {
        return;
      }
      closeAiMenu();
      closeExpandedVehicleDetails({ render: false });
      setVehicleModalContext({ mode: "create", scope: normalizedScope, vehicleId: null });
      vehicleModal.hidden = false;
      vehicleForm.reset();
      clearVehicleModalFeedback();
      vehicleForm.elements.service_scope.value = normalizedScope;
      applyVehicleFormDefaults("carro", vehicleForm);
      const modalOpenState = resolveVehicleModalOpenState(normalizedScope, getCurrentServiceDateIso());
      if (vehicleForm.elements.service_date) {
        vehicleForm.elements.service_date.value = modalOpenState.serviceDateValue;
      }
      if (vehicleForm.elements.departure_time) {
        vehicleForm.elements.departure_time.value = modalOpenState.departureTimeValue;
      }
      syncVehicleModalFields(normalizedScope);
      if (!focusVehicleFormField(modalOpenState.initialFocusField)) {
        focusVehicleFormField(modalOpenState.fallbackFocusField);
      }
    }

    function openVehicleEditModal(vehicle) {
      if (!vehicleModal || !vehicleForm || !vehicle || vehicle.id === null || vehicle.id === undefined) {
        return;
      }

      const normalizedScope = normalizeVehicleScope(vehicle.service_scope || "regular");
      if (!canOpenVehicleModal(normalizedScope)) {
        return;
      }

      closeAiMenu();
      closeExpandedVehicleDetails({ render: false });
      setVehicleModalContext({ mode: "edit", scope: normalizedScope, vehicleId: vehicle.id });
      vehicleModal.hidden = false;
      vehicleForm.reset();
      clearVehicleModalFeedback();
      vehicleForm.elements.service_scope.value = normalizedScope;
      populateVehicleFormBaseFields(vehicle);

      if (vehicleForm.elements.service_date) {
        vehicleForm.elements.service_date.value = formatVehicleFormFieldValue(vehicle.service_date);
      }
      if (vehicleForm.elements.departure_time) {
        vehicleForm.elements.departure_time.value = formatVehicleFormFieldValue(vehicle.departure_time);
      }
      if (vehicleForm.elements.route_kind) {
        vehicleForm.elements.route_kind.value = ROUTE_KIND_KEYS[vehicle.route_kind]
          ? vehicle.route_kind
          : getSelectedRouteKind();
      }

      syncVehicleModalFields(normalizedScope);
      if (!focusVehicleFormField(resolveVehicleEditFocusField(vehicle))) {
        focusVehicleFormField("tipo");
      }
    }

    function closeVehicleModal() {
      if (!vehicleModal || !vehicleForm) {
        return;
      }
      vehicleModal.hidden = true;
      clearVehicleModalFeedback();
      vehicleForm.reset();
      setVehicleModalContext({ mode: "create", scope: "regular", vehicleId: null });
      syncVehicleModalCopy("regular");
    }

    function getRequestsForKind(kind) {
      if (!state.dashboard) {
        return [];
      }
      return Array.isArray(state.dashboard[`${kind}_requests`])
        ? state.dashboard[`${kind}_requests`]
        : [];
    }

    function getProjectRows() {
      if (!state.dashboard) {
        return [];
      }
      return Array.isArray(state.dashboard.projects) ? state.dashboard.projects : [];
    }

    function reconcileProjectVisibility() {
      const nextVisibility = {};
      getProjectRows().forEach(function (projectRow) {
        if (!projectRow || !projectRow.name) {
          return;
        }
        nextVisibility[projectRow.name] = state.projectVisibility[projectRow.name] !== false;
      });
      state.projectVisibility = nextVisibility;
    }

    function hasAnyVisibleProject() {
      const projectNames = Object.keys(state.projectVisibility);
      if (!projectNames.length) {
        return true;
      }
      return projectNames.some(function (projectName) {
        return state.projectVisibility[projectName] !== false;
      });
    }

    function isProjectVisible(projectName) {
      const normalizedProjectName = String(projectName || "").trim();
      if (!normalizedProjectName) {
        return true;
      }
      if (!(normalizedProjectName in state.projectVisibility)) {
        return true;
      }
      return state.projectVisibility[normalizedProjectName] !== false;
    }

    function getRequestRowProjects(requestRow) {
      if (!requestRow || typeof requestRow !== "object") {
        return [];
      }

      const rawProjectNames = Array.isArray(requestRow.projects) && requestRow.projects.length
        ? requestRow.projects
        : [requestRow.projeto];
      const normalizedProjectNames = [];
      const seenProjectNames = new Set();

      rawProjectNames.forEach(function (projectName) {
        const normalizedProjectName = String(projectName || "").trim();
        if (!normalizedProjectName || seenProjectNames.has(normalizedProjectName)) {
          return;
        }
        seenProjectNames.add(normalizedProjectName);
        normalizedProjectNames.push(normalizedProjectName);
      });

      return normalizedProjectNames;
    }

    function isRequestVisibleForProjects(requestRow) {
      const requestProjectNames = getRequestRowProjects(requestRow);
      if (!requestProjectNames.length) {
        return true;
      }
      return requestProjectNames.some(function (projectName) {
        return isProjectVisible(projectName);
      });
    }

    function getVisibleRequestsForKind(kind) {
      return getRequestsForKind(kind).filter(function (requestRow) {
        return isRequestVisibleForProjects(requestRow);
      });
    }

    function getVehiclesForScope(scope) {
      if (!state.dashboard) {
        return [];
      }
      return Array.isArray(state.dashboard[`${scope}_vehicles`])
        ? state.dashboard[`${scope}_vehicles`]
        : [];
    }

    function getVehicleRegistryRows(scope) {
      if (!state.dashboard) {
        return [];
      }
      return Array.isArray(state.dashboard[`${scope}_vehicle_registry`])
        ? state.dashboard[`${scope}_vehicle_registry`]
        : [];
    }

    function getAllRequests() {
      return REQUEST_SECTION_ORDER.reduce(function (rows, kind) {
        return rows.concat(getRequestsForKind(kind));
      }, []);
    }

    function getAllVisibleRequests() {
      return REQUEST_SECTION_ORDER.reduce(function (rows, kind) {
        return rows.concat(getVisibleRequestsForKind(kind));
      }, []);
    }

    function getRequestById(requestId) {
      return (
        getAllRequests().find(function (row) {
          return Number(row.id) === Number(requestId);
        }) || null
      );
    }

    function getDraggedRequest() {
      if (state.dragRequestId === null) {
        return null;
      }
      return getRequestById(state.dragRequestId);
    }

    function getVehicleByScopeAndId(scope, vehicleId) {
      return (
        getVehiclesForScope(scope).find(function (vehicle) {
          return Number(vehicle.id) === Number(vehicleId);
        }) || null
      );
    }

    function getPendingAssignmentPreview() {
      if (!state.pendingAssignmentPreview) {
        return null;
      }

      const requestRow = getRequestById(state.pendingAssignmentPreview.requestId);
      const vehicle = getVehicleByScopeAndId(
        state.pendingAssignmentPreview.scope,
        state.pendingAssignmentPreview.vehicleId
      );

      if (!requestRow || !vehicle) {
        return null;
      }

      return {
        requestRow,
        vehicle,
        scope: state.pendingAssignmentPreview.scope,
        routeKind: state.pendingAssignmentPreview.routeKind,
      };
    }

    function getVehicleDetailsKey(scope, vehicleId) {
      return `${scope}:${vehicleId}`;
    }

    function ensureExpandedVehicleStillExists() {
      if (!state.expandedVehicleKey) {
        return;
      }

      const hasVehicle = VEHICLE_SCOPE_ORDER.some(function (scope) {
        return getVehiclesForScope(scope).some(function (vehicle) {
          return getVehicleDetailsKey(scope, vehicle.id) === state.expandedVehicleKey;
        });
      });

      if (!hasVehicle) {
        state.expandedVehicleKey = null;
      }
    }

    function toggleVehicleDetails(scope, vehicleId) {
      const vehicleKey = getVehicleDetailsKey(scope, vehicleId);
      const pendingPreview = getPendingAssignmentPreview();
      if (
        pendingPreview
        && pendingPreview.scope === scope
        && Number(pendingPreview.vehicle.id) === Number(vehicleId)
      ) {
        state.expandedVehicleKey = vehicleKey;
        renderVehiclePanels();
        return;
      }
      state.expandedVehicleKey = state.expandedVehicleKey === vehicleKey ? null : vehicleKey;
      renderVehiclePanels();
    }

    function closeExpandedVehicleDetails(options) {
      const closeOptions = options || {};
      const expandedElements = closeOptions.restoreFocus ? findExpandedVehicleDetailsElements() : null;

      if (!state.expandedVehicleKey && !state.pendingAssignmentPreview) {
        clearElement(vehicleDetailsOverlayHost);
        vehicleDetailsOverlayHost.classList.remove("is-active");
        return;
      }

      state.expandedVehicleKey = null;
      state.pendingAssignmentPreview = null;
      clearElement(vehicleDetailsOverlayHost);
      vehicleDetailsOverlayHost.classList.remove("is-active");

      if (closeOptions.render !== false) {
        renderVehiclePanels();
      }

      if (
        closeOptions.restoreFocus
        && expandedElements
        && expandedElements.anchorButton
        && typeof expandedElements.anchorButton.focus === "function"
      ) {
        if (typeof globalScope.requestAnimationFrame === "function") {
          globalScope.requestAnimationFrame(function () {
            expandedElements.anchorButton.focus();
          });
        } else {
          expandedElements.anchorButton.focus();
        }
      }
    }

    function findExpandedVehicleDetailsElements() {
      if (!state.expandedVehicleKey) {
        return null;
      }

      const anchorButton = document.querySelector(
        `[data-vehicle-details-anchor-key="${state.expandedVehicleKey}"]`
      );
      const detailsPanel = vehicleDetailsOverlayHost.querySelector(
        `[data-vehicle-details-panel-key="${state.expandedVehicleKey}"]`
      );

      if (!anchorButton || !detailsPanel) {
        return null;
      }

      return {
        anchorButton,
        detailsPanel,
      };
    }

    function syncExpandedVehicleDetailsPosition() {
      const expandedElements = findExpandedVehicleDetailsElements();
      if (!expandedElements) {
        clearElement(vehicleDetailsOverlayHost);
        vehicleDetailsOverlayHost.classList.remove("is-active");
        return;
      }

      const anchorRect = expandedElements.anchorButton.getBoundingClientRect();
      const detailsStyles = typeof globalScope.getComputedStyle === "function"
        ? globalScope.getComputedStyle(expandedElements.detailsPanel)
        : null;
      const panelWidth = Math.max(
        1,
        expandedElements.detailsPanel.offsetWidth
        || parsePixelValue(detailsStyles ? detailsStyles.width : "", 264)
      );
      const panelHeight = Math.max(
        1,
        expandedElements.detailsPanel.offsetHeight
        || parsePixelValue(detailsStyles ? detailsStyles.height : "", 248)
      );
      const viewportWidth = Math.max(
        0,
        globalScope.innerWidth
        || (document.documentElement ? document.documentElement.clientWidth : 0)
      );
      const viewportHeight = Math.max(
        0,
        globalScope.innerHeight
        || (document.documentElement ? document.documentElement.clientHeight : 0)
      );
      const nextPosition = resolveVehicleDetailsPosition({
        anchorRect,
        panelWidth,
        panelHeight,
        viewportWidth,
        viewportHeight,
        offset: VEHICLE_DETAILS_PANEL_OFFSET,
        viewportMargin: VEHICLE_DETAILS_VIEWPORT_MARGIN,
      });

      expandedElements.detailsPanel.style.left = `${nextPosition.left}px`;
      expandedElements.detailsPanel.style.top = `${nextPosition.top}px`;
      expandedElements.detailsPanel.dataset.horizontalDirection = nextPosition.horizontalDirection;
      expandedElements.detailsPanel.classList.add("is-positioned");
    }

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

    function createPassengerRemoveButton(requestRow, routeKind) {
      const removeButton = createNode("button", "transport-passenger-remove-button", "×");
      const normalizedRouteKind = getRouteKindForRequestRow(requestRow, routeKind);
      const removeLabel = t("misc.removeFromVehicle", { name: String(requestRow && requestRow.nome || "") });

      removeButton.type = "button";
      removeButton.setAttribute("aria-label", removeLabel);
      removeButton.title = removeLabel;
      removeButton.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        void returnRequestRowToPending(requestRow, normalizedRouteKind);
      });
      return removeButton;
    }

    function saveRequestRowBoardingTime(requestRow, boardingTime, routeKind) {
      if (!requestRow || !requestRow.id || !requestRow.service_date) {
        setStatus("", "error", { key: "status.couldNotSaveBoardingTime" });
        return Promise.resolve(null);
      }

      return requestJson(`${TRANSPORT_API_PREFIX}/assignments/boarding-time`, {
        method: "PUT",
        body: JSON.stringify({
          request_id: requestRow.id,
          service_date: requestRow.service_date,
          route_kind: getRouteKindForRequestRow(requestRow, routeKind),
          boarding_time: boardingTime,
        }),
      }).then(function (response) {
        const structuredBoardingTimeMessage = resolveTransportApiStructuredMessage(response)
          || String(response && response.message || "").trim();
        const boardingTimeMessage = structuredBoardingTimeMessage || t("status.boardingTimeSaved");
        const boardingTimeOptions = resolveTransportApiStructuredMessageOptions(response)
          || (structuredBoardingTimeMessage ? undefined : { key: "status.boardingTimeSaved" });
        setStatus(boardingTimeMessage, "success", boardingTimeOptions);
        return loadDashboard(dateStore.getValue(), { announce: false });
      }).catch(function (error) {
        if (handleProtectedRequestError(error, t("status.couldNotSaveBoardingTime"))) {
          return null;
        }
        throw error;
      });
    }

    function resolveVehicleDetailsScope(vehicle, detailOptions) {
      const resolvedOptions = detailOptions || {};
      return String(
        resolvedOptions.scope !== undefined && resolvedOptions.scope !== null
          ? resolvedOptions.scope
          : vehicle && vehicle.service_scope
      ).trim();
    }

    function resolveVehicleDetailsRouteKind(vehicle, detailOptions) {
      const resolvedOptions = detailOptions || {};
      const scope = resolveVehicleDetailsScope(vehicle, resolvedOptions);
      return resolvedOptions.routeKind || getRouteKindForVehicle(scope, vehicle);
    }

    function resolveVehicleDetailsPassengerTime(vehicle, requestRow, detailOptions) {
      const resolvedOptions = detailOptions || {};
      const scope = resolveVehicleDetailsScope(vehicle, resolvedOptions);
      const routeKind = resolveVehicleDetailsRouteKind(vehicle, resolvedOptions);

      return resolveVehiclePassengerOperationalTime(
        scope,
        vehicle,
        requestRow,
        state.dashboard,
        state.arriveAtWorkTime,
        state.vehicleReferenceClock,
        state.workToHomeTime,
        routeKind
      );
    }

    function buildVehicleDetailsRowViewModels(vehicle, assignedRows, detailOptions) {
      const resolvedOptions = detailOptions || {};
      const previewRequestRow = resolvedOptions.previewRequestRow || null;
      const resolvedRouteKind = resolveVehicleDetailsRouteKind(vehicle, resolvedOptions);
      const scope = resolveVehicleDetailsScope(vehicle, resolvedOptions);
      const visiblePassengerRows = buildVehiclePassengerPreviewRows(
        assignedRows,
        previewRequestRow,
        VEHICLE_DETAILS_MAX_ROWS
      );

      const effectiveDepartureTime = getEffectiveWorkToHomeDepartureTime(state.dashboard, state.workToHomeTime);
      const vehicleW2hTime = normalizeTransportTimeValue(
        getVehicleDepartureTime(vehicle, effectiveDepartureTime, scope),
        ""
      );

      return visiblePassengerRows.map(function (requestRow) {
        const timeState = resolveVehicleDetailsPassengerTime(vehicle, requestRow, resolvedOptions);
        const normalizedTime = normalizeTransportTimeValue(timeState && timeState.time, "");
        const hasTime = isValidTransportTimeValue(normalizedTime);
        const isPreviewRow = Boolean(
          previewRequestRow
          && requestRow
          && Number(requestRow.id) === Number(previewRequestRow.id)
        );
        const isConfirmed = String(requestRow && requestRow.assignment_status || "").trim() === "confirmed";
        const routeKind = getRouteKindForRequestRow(requestRow, resolvedRouteKind);
        const h2wBoardingTime = normalizeTransportTimeValue(requestRow && requestRow.boarding_time, "");
        const hasH2wBoardingTime = isValidTransportTimeValue(h2wBoardingTime);

        return {
          requestRow,
          isPreviewRow,
          isConfirmed,
          routeKind,
          timeState,
          resolvedTime: hasH2wBoardingTime ? h2wBoardingTime : "",
          timeSortValue: hasTime
            ? String(parseTransportTimeToMinutes(normalizedTime)).padStart(4, "0")
            : "9999",
          h2wBoardingTime: hasH2wBoardingTime ? h2wBoardingTime : "",
          w2hTime: vehicleW2hTime,
          canEditBoardingTime: Boolean(
            requestRow
            && !isPreviewRow
            && isConfirmed
            && routeKind === "home_to_work"
          ),
        };
      }).sort(function (a, b) {
        if (a.timeSortValue < b.timeSortValue) return -1;
        if (a.timeSortValue > b.timeSortValue) return 1;
        return 0;
      });
    }

    function buildVehicleDetailsColumnDefinitions(vehicle, rowViewModels, detailOptions) {
      return [
        {
          key: "passenger",
          headerKey: "vehicleDetails.passengerHeader",
          headerClassName: "transport-vehicle-passenger-name-header",
          cellClassName: "transport-vehicle-passenger-name",
          getSortValue: function (rowViewModel) {
            return String(rowViewModel && rowViewModel.requestRow && rowViewModel.requestRow.nome || "").trim().toLowerCase();
          },
          renderCell: function (rowViewModel) {
            return createNode(
              "span",
              "transport-vehicle-passenger-name-value",
              String(rowViewModel && rowViewModel.requestRow && rowViewModel.requestRow.nome || "")
            );
          },
        },
        {
          key: "h2w-boarding",
          headerKey: "vehicleDetails.h2wBoardingHeader",
          headerClassName: "transport-vehicle-passenger-time-header",
          cellClassName: "transport-vehicle-passenger-time",
          getSortValue: function (rowViewModel) {
            return rowViewModel && rowViewModel.timeSortValue ? rowViewModel.timeSortValue : "9999";
          },
          renderCell: function (rowViewModel) {
            if (rowViewModel && rowViewModel.canEditBoardingTime) {
              return createVehiclePassengerTimeEditor(rowViewModel);
            }
            var bt = rowViewModel && rowViewModel.h2wBoardingTime || "";
            return createNode(
              "span",
              "transport-vehicle-passenger-time-value" + (bt ? "" : " is-placeholder"),
              bt || t("vehicleDetails.timeMissing")
            );
          },
        },
        {
          key: "w2h-time",
          headerKey: "vehicleDetails.w2hTimeHeader",
          headerClassName: "transport-vehicle-passenger-w2h-time-header",
          cellClassName: "transport-vehicle-passenger-w2h-time",
          renderCell: function (rowViewModel) {
            var wt = rowViewModel && rowViewModel.w2hTime || "";
            return createNode(
              "span",
              "transport-vehicle-passenger-time-value" + (wt ? "" : " is-placeholder"),
              wt || t("vehicleDetails.timeMissing")
            );
          },
        },
        {
          key: "action",
          headerKey: "vehicleDetails.actionHeader",
          headerClassName: "transport-vehicle-passenger-action-header",
          cellClassName: "transport-vehicle-passenger-status",
          renderCell: function (rowViewModel) {
            if (rowViewModel && rowViewModel.requestRow && !rowViewModel.isPreviewRow) {
              return createPassengerRemoveButton(rowViewModel.requestRow, rowViewModel.routeKind);
            }
            return null;
          },
        },
      ];
    }

    function createVehicleDetailsTableHead(columns) {
      const tableHead = createNode("thead", "transport-vehicle-passenger-table-head");
      const headerRow = createNode("tr", "transport-vehicle-passenger-header-row");

      columns.forEach(function (column) {
        const headerCell = createNode("th", column.headerClassName, t(column.headerKey));
        headerCell.setAttribute("scope", "col");
        headerCell.dataset.columnKey = column.key;
        headerRow.appendChild(headerCell);
      });

      tableHead.appendChild(headerRow);
      return tableHead;
    }

    function createVehicleDetailsTableRow(columns, rowViewModel) {
      const tableRow = createNode("tr", "transport-vehicle-passenger-row");

      tableRow.dataset.requestId = String(rowViewModel && rowViewModel.requestRow && rowViewModel.requestRow.id || "");
      tableRow.dataset.timeMode = String(rowViewModel && rowViewModel.timeState && rowViewModel.timeState.mode || "");

      columns.forEach(function (column) {
        const cell = createNode("td", column.cellClassName);
        const sortValue = typeof column.getSortValue === "function" ? column.getSortValue(rowViewModel) : "";
        const content = typeof column.renderCell === "function" ? column.renderCell(rowViewModel) : null;

        cell.dataset.columnKey = column.key;
        if (column.key === "operational-time") {
          cell.dataset.timeMode = String(rowViewModel && rowViewModel.timeState && rowViewModel.timeState.mode || "");
          cell.dataset.timeField = String(rowViewModel && rowViewModel.timeState && rowViewModel.timeState.timeField || "");
        }
        if (sortValue !== null && sortValue !== undefined && String(sortValue).trim()) {
          cell.dataset.sortValue = String(sortValue);
        }

        if (content) {
          cell.appendChild(content);
        } else {
          cell.innerHTML = "&nbsp;";
        }
        tableRow.appendChild(cell);
      });

      return tableRow;
    }

    function getVehicleDetailsTimeHeaderKey(timeState) {
      if (timeState && timeState.mode === "eta") {
        return "vehicleDetails.boardingHeader";
      }
      if (timeState && timeState.mode === "etd") {
        return "vehicleDetails.departureHeader";
      }
      return "vehicleDetails.timeHeader";
    }

    function createVehiclePassengerTimeValue(timeState) {
      const resolvedTime = normalizeTransportTimeValue(timeState && timeState.time, "");
      const hasTime = isValidTransportTimeValue(resolvedTime);
      return createNode(
        "span",
        `transport-vehicle-passenger-time-value${hasTime ? "" : " is-placeholder"}`,
        hasTime ? resolvedTime : t("vehicleDetails.timeMissing")
      );
    }

    function createVehiclePassengerTimeEditor(rowViewModel) {
      const editor = createNode("div", "transport-vehicle-passenger-time-editor");
      const input = document.createElement("input");
      const requestRow = rowViewModel && rowViewModel.requestRow;
      const routeKind = rowViewModel && rowViewModel.routeKind;
      const timeState = rowViewModel && rowViewModel.timeState;
      let committedValue = normalizeTransportTimeValue(rowViewModel && rowViewModel.resolvedTime, "");
      let isSaving = false;

      input.type = "text";
      input.value = committedValue;
      input.maxLength = 5;
      input.setAttribute("inputmode", "numeric");
      input.setAttribute("placeholder", t("vehicleDetails.boardingPlaceholder"));
      input.setAttribute("pattern", "[0-2][0-9]:[0-5][0-9]");
      input.setAttribute(
        "aria-label",
        t("vehicleDetails.boardingInputAria", { name: String(requestRow && requestRow.nome || "") })
      );
      input.className = "transport-vehicle-passenger-time-input";

      function syncEditorState() {
        const currentValue = String(input.value || "").trim();
        const resolvedValue = normalizeTransportTimeValue(currentValue, "");
        const hasValue = isValidTransportTimeValue(resolvedValue);
        editor.classList.toggle("is-placeholder", !hasValue);
        editor.classList.toggle("is-saving", isSaving);
        input.classList.toggle("is-placeholder", !hasValue);
        input.classList.toggle("is-saving", isSaving);
        input.disabled = isSaving;
        input.setAttribute("aria-busy", String(isSaving));
      }

      function restoreCommittedValue() {
        input.value = committedValue;
        syncEditorState();
      }

      function persistBoardingTime() {
        if (isSaving) {
          return Promise.resolve(null);
        }

        const rawValue = String(input.value || "").trim();
        if (rawValue && !isValidTransportTimeValue(rawValue)) {
          setStatus("", "warning", { key: "warnings.invalidBoardingTime" });
          restoreCommittedValue();
          return Promise.resolve(null);
        }

        const nextValue = rawValue || "";
        if (nextValue === committedValue) {
          syncEditorState();
          return Promise.resolve(null);
        }

        isSaving = true;
        syncEditorState();
        return saveRequestRowBoardingTime(requestRow, nextValue || null, routeKind)
          .then(function (result) {
            isSaving = false;
            if (result === null) {
              restoreCommittedValue();
              return null;
            }

            committedValue = nextValue;
            input.value = committedValue;
            syncEditorState();
            return result;
          })
          .catch(function () {
            isSaving = false;
            restoreCommittedValue();
            return null;
