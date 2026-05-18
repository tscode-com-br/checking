
  function getEffectiveWorkToHomeDepartureTime(dashboard, fallbackTime) {
    const dashboardTime = String(dashboard && dashboard.work_to_home_departure_time || "").trim();
    if (isValidTransportTimeValue(dashboardTime)) {
      return dashboardTime;
    }

    return normalizeTransportTimeValue(fallbackTime, DEFAULT_WORK_TO_HOME_TIME);
  }

  function getVehicleDepartureTime(vehicle, fallbackTime, scopeOverride) {
    const departureTime = String(vehicle && vehicle.departure_time || "").trim();
    if (isValidTransportTimeValue(departureTime)) {
      return departureTime;
    }

    const resolvedScope = String(vehicle && vehicle.service_scope || scopeOverride || "").trim();
    if (resolvedScope !== "regular" && resolvedScope !== "weekend") {
      return "";
    }

    return isValidTransportTimeValue(fallbackTime) ? String(fallbackTime).trim() : "";
  }

  function formatExtraVehicleReferenceLabel(routeKind, referenceTime) {
    const normalizedReferenceTime = normalizeTransportTimeValue(referenceTime, "");
    if (!isValidTransportTimeValue(normalizedReferenceTime)) {
      return "";
    }

    if (routeKind === "home_to_work") {
      return translateTransportAiReviewText("ai.review.etaLabel", "ETA {time}h", {
        time: normalizedReferenceTime,
      });
    }
    if (routeKind === "work_to_home") {
      return translateTransportAiReviewText("ai.review.etdLabel", "ETD {time}h", {
        time: normalizedReferenceTime,
      });
    }

    return normalizedReferenceTime;
  }

  function resolveVehicleReferenceMode(scope, dashboard, arriveAtWorkTime, nowRef, fallbackWorkToHomeTime, routeKind, options) {
    const normalizedScope = String(scope || "").trim();
    if (isRoutineVehicleScope(normalizedScope)) {
      return getRoutineVehicleReferenceMode(
        dashboard,
        arriveAtWorkTime,
        nowRef,
        fallbackWorkToHomeTime,
        options
      );
    }

    if (normalizedScope === "extra") {
      if (routeKind === "home_to_work") {
        return "eta";
      }
      if (routeKind === "work_to_home") {
        return "etd";
      }
    }

    return null;
  }

  function getVehicleReferenceLabel(scope, vehicle, dashboard, arriveAtWorkTime, nowRef, fallbackWorkToHomeTime, routeKind, options) {
    const normalizedScope = String(scope || "").trim();
    const referenceMode = resolveVehicleReferenceMode(
      normalizedScope,
      dashboard,
      arriveAtWorkTime,
      nowRef,
      fallbackWorkToHomeTime,
      routeKind,
      options
    );
    if (isRoutineVehicleScope(normalizedScope)) {
      const normalizedArriveAtWorkTime = normalizeTransportTimeValue(arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME);
      const effectiveWorkToHomeTime = getEffectiveWorkToHomeDepartureTime(dashboard, fallbackWorkToHomeTime);
      return formatRoutineVehicleReferenceLabel(referenceMode, normalizedArriveAtWorkTime, effectiveWorkToHomeTime);
    }

    const effectiveDepartureTime = getEffectiveWorkToHomeDepartureTime(dashboard, fallbackWorkToHomeTime);
    const departureTime = getVehicleDepartureTime(vehicle, effectiveDepartureTime, normalizedScope);
    if (normalizedScope === "extra" && (referenceMode === "eta" || referenceMode === "etd")) {
      return formatExtraVehicleReferenceLabel(routeKind, departureTime);
    }

    return departureTime;
  }

  function resolveVehiclePassengerOperationalTime(
    scope,
    vehicle,
    requestRow,
    dashboard,
    arriveAtWorkTime,
    nowRef,
    fallbackWorkToHomeTime,
    routeKind,
    options
  ) {
    const normalizedScope = String(scope || "").trim();
    const referenceMode = resolveVehicleReferenceMode(
      normalizedScope,
      dashboard,
      arriveAtWorkTime,
      nowRef,
      fallbackWorkToHomeTime,
      routeKind,
      options
    );

    if (referenceMode === "etd") {
      const effectiveDepartureTime = getEffectiveWorkToHomeDepartureTime(dashboard, fallbackWorkToHomeTime);
      return {
        mode: "etd",
        time: getVehicleDepartureTime(vehicle, effectiveDepartureTime, normalizedScope),
        timeField: null,
      };
    }

    if (referenceMode === "eta") {
      // requested_time captures only the passenger's ask and can diverge from the operational pickup.
      const boardingTime = normalizeTransportTimeValue(requestRow && requestRow.boarding_time, "");
      return {
        mode: "eta",
        time: isValidTransportTimeValue(boardingTime) ? boardingTime : "",
        timeField: "boarding_time",
      };
    }

    return {
      mode: null,
      time: "",
      timeField: null,
    };
  }

  function getExtraVehicleDepartureFieldKey(routeKind) {
    if (routeKind === "home_to_work") {
      return "modal.fields.etaTime";
    }
    if (routeKind === "work_to_home") {
      return "modal.fields.etdTime";
    }
    return "modal.fields.departureTime";
  }

  function getExtraVehicleScopeNoteKey(routeKind) {
    if (routeKind === "home_to_work") {
      return "modal.notes.extraHomeToWork";
    }
    if (routeKind === "work_to_home") {
      return "modal.notes.extraWorkToHome";
    }
    return "modal.notes.extra";
  }

  function shouldHighlightRequestName(assignmentStatus) {
    return assignmentStatus === "pending" || assignmentStatus === "rejected" || assignmentStatus === "cancelled";
  }

  function getPassengerAwarenessState(requestRow) {
    return requestRow && requestRow.awareness_status === "aware" ? "aware" : "pending";
  }

  function isRequestAssignedToVehicle(requestRow, vehicle) {
    return Boolean(
      requestRow
      && requestRow.assigned_vehicle
      && vehicle
      && Number(requestRow.assigned_vehicle.id) === Number(vehicle.id)
    );
  }

  function groupAssignedRequestsByVehicleForDate(requestRows, selectedDate) {
    const normalizedSelectedDate = String(selectedDate || "");
    return (Array.isArray(requestRows) ? requestRows : []).reduce(function (grouped, requestRow) {
      if (
        !requestRow
        || requestRow.assignment_status !== "confirmed"
        || !requestRow.assigned_vehicle
        || requestRow.assigned_vehicle.id === undefined
      ) {
        return grouped;
      }

      if (normalizedSelectedDate && String(requestRow.service_date || "") !== normalizedSelectedDate) {
        return grouped;
      }

      const vehicleId = String(requestRow.assigned_vehicle.id);
      if (!grouped[vehicleId]) {
        grouped[vehicleId] = [];
      }
      grouped[vehicleId].push(requestRow);
      return grouped;
    }, {});
  }

  function canRequestBeDroppedOnVehicle(requestRow, scope, vehicle, routeKind) {
    if (!requestRow || !vehicle || requestRow.request_kind !== scope) {
      return false;
    }

    if (!isVehicleReadyForAllocation(vehicle)) {
      return false;
    }

    if (isRequestAssignedToVehicle(requestRow, vehicle)) {
      return false;
    }

    return scope !== "extra" || Boolean(vehicle.route_kind || routeKind);
  }

  function buildVehiclePassengerPreviewRows(assignedRows, previewRequestRow, maxRows) {
    const rows = Array.isArray(assignedRows)
      ? assignedRows.filter(function (requestRow) {
          return !previewRequestRow || Number(requestRow.id) !== Number(previewRequestRow.id);
        })
      : [];

    const previewRows = previewRequestRow ? [previewRequestRow].concat(rows) : rows;
    const normalizedMaxRows = Number.isFinite(Number(maxRows)) && Number(maxRows) > 0
      ? Math.max(1, Number(maxRows))
      : null;

    if (normalizedMaxRows === null) {
      return previewRows;
    }

    return previewRows.slice(0, normalizedMaxRows);
  }

  function buildVehiclePassengerAwarenessRows(assignedRows, maxRows) {
    const normalizedMaxRows = Number.isFinite(Number(maxRows)) && Number(maxRows) > 0
      ? Math.max(1, Number(maxRows))
      : null;
    const rows = Array.isArray(assignedRows)
      ? assignedRows.map(function (requestRow) {
          return {
            name: String((requestRow && requestRow.nome) || ""),
            awarenessState: getPassengerAwarenessState(requestRow),
          };
        })
      : [];

    if (normalizedMaxRows === null) {
      return rows;
    }

    return rows.slice(0, normalizedMaxRows);
  }

  function mapScopeTitle(scope) {
    return t(`modal.scope.${scope === "regular" || scope === "weekend" ? scope : "extra"}`);
  }

  function getRouteKindLabel(routeKind) {
    const routeKey = ROUTE_KIND_KEYS[routeKind];
    return routeKey ? t(routeKey) : routeKind;
  }

  function getModalScopeNote(scope, routeKind) {
    if (scope === "extra") {
      return t(getExtraVehicleScopeNoteKey(routeKind));
    }
    const noteKey = MODAL_SCOPE_NOTE_KEYS[scope] || MODAL_SCOPE_NOTE_KEYS.regular;
    return t(noteKey);
  }

  function getRequestTitle(kind) {
    return t(REQUEST_TITLE_KEYS[kind] || REQUEST_TITLE_KEYS.regular);
  }

  function getRequestLabel(kind) {
    return t(REQUEST_LABEL_KEYS[kind] || REQUEST_LABEL_KEYS.regular);
  }

  function createEmptyState(message) {
    const wrapper = createNode("div", "transport-empty-state");
    wrapper.appendChild(createNode("strong", "transport-empty-title", message));
    return wrapper;
  }

