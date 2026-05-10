(function (root, factory) {
  root.CheckingWebTransportScreen = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function createTransportScreenModule(env) {
    const {
      buildProtectedRequestError,
      clearTransportInlineStatus,
      clientState,
      dismissActiveKeyboard,
      dom,
      getActiveChave,
      isApplicationUnlocked,
      isPasswordDialogOpen,
      isRegistrationDialogOpen,
      isTransportScreenOpen,
      realignViewport,
      resolveTransportEventTargetElement,
      sanitizeChave,
      setStatus,
      setTransportInlineStatus,
      state,
      config,
      runtime,
      syncFormControlStates,
    } = env;

    const {
      transportScreen,
      transportScreenBackdrop,
      transportAddressSummaryValue,
      transportAddressEditor,
      transportAddressInput,
      transportZipInput,
      transportOptionButtons,
      transportRegularButton,
      transportWeekendButton,
      transportExtraButton,
      transportRequestBuilderPanel,
      transportRequestBuilderSubtitle,
      transportRequestWeekdayGroup,
      transportRequestDateGroup,
      transportRequestTimeGroup,
      transportRequestDateInput,
      transportRequestTimeInput,
      transportRequestBuilderSubmitButton,
      transportRequestWeekdayInputs,
      transportRequestWeekdayOptions,
      transportRequestHistorySection,
      transportRequestHistoryList,
      transportRequestDetailWidget,
      transportRequestDetailBackdrop,
      transportRequestDetailTitle,
      transportRequestDetailContent,
      transportRequestDetailCloseButton,
    } = dom;

    const {
      transportState,
      transportUiState,
      transportRequestSwipeState,
    } = state;

    const {
      transportStateEndpoint,
      transportStreamEndpoint,
      transportAddressEndpoint,
      transportRequestEndpoint,
      transportCancelEndpoint,
      transportAutoRefreshIntervalMs,
      transportRealtimeRefreshDebounceMs,
      transportRequestDismissHoldDelayMs,
      transportRequestDismissMoveTolerancePx,
      transportRequestKindLabels,
      transportRequestStatusLabels,
      transportRequestWeekdayLabels,
      transportRequestWeekdayFullLabels,
      transportRequestBuilderConfigs,
      getDateFormatter,
      formatTransportVehicleTypeLabel,
      localizeKnownApiMessage,
      t,
      userTransportLocalStateStorageKey,
    } = config;

    const translateTransport = typeof t === 'function' ? t : function (keyPath) {
      return keyPath;
    };

    function getRuntimeDateFormatter() {
      return typeof getDateFormatter === 'function' ? getDateFormatter() : null;
    }

    let transportAutoRefreshTimeoutId = null;
    let transportRealtimeEventSource = null;
    let transportRealtimeStreamChave = '';
    let transportRealtimeRefreshTimeoutId = null;
    let transportRealtimeRefreshPending = false;
    const transportRequestProjectionKinds = ['regular', 'weekend', 'extra'];

    function getTransportStateLoading() {
      return runtime.getTransportStateLoading();
    }

    function setTransportStateLoading(value) {
      runtime.setTransportStateLoading(value);
    }

    function getTransportAddressSaveInProgress() {
      return runtime.getTransportAddressSaveInProgress();
    }

    function setTransportAddressSaveInProgress(value) {
      runtime.setTransportAddressSaveInProgress(value);
    }

    function getTransportRequestInProgress() {
      return runtime.getTransportRequestInProgress();
    }

    function setTransportRequestInProgress(value) {
      runtime.setTransportRequestInProgress(value);
    }

    function getTransportCancelInProgress() {
      return runtime.getTransportCancelInProgress();
    }

    function setTransportCancelInProgress(value) {
      runtime.setTransportCancelInProgress(value);
    }

    function getTransportBusy() {
      return getTransportStateLoading()
        || getTransportAddressSaveInProgress()
        || getTransportRequestInProgress()
        || getTransportCancelInProgress();
    }

    function clearTransportAutoRefresh() {
      if (transportAutoRefreshTimeoutId !== null) {
        window.clearTimeout(transportAutoRefreshTimeoutId);
        transportAutoRefreshTimeoutId = null;
      }
    }

    function normalizePersistedTransportRequestIds(value) {
      if (!Array.isArray(value)) {
        return [];
      }

      const uniqueIds = new Set();
      value.forEach((entry) => {
        const normalizedId = Number(entry);
        if (Number.isFinite(normalizedId)) {
          uniqueIds.add(normalizedId);
        }
      });
      return Array.from(uniqueIds);
    }

    function readPersistedTransportLocalStateMap() {
      try {
        const rawValue = window.localStorage.getItem(userTransportLocalStateStorageKey);
        if (!rawValue) {
          return {};
        }

        const parsedValue = JSON.parse(rawValue);
        return parsedValue && typeof parsedValue === 'object' ? parsedValue : {};
      } catch {
        return {};
      }
    }

    function writePersistedTransportLocalStateMap(localStateMap) {
      try {
        window.localStorage.setItem(userTransportLocalStateStorageKey, JSON.stringify(localStateMap));
      } catch {
        // Ignore browsers with unavailable storage.
      }
    }

    function resetTransportRequestLocalState() {
      transportUiState.dismissedRequestIds = new Set();
      transportUiState.realizedRequestIds = new Set();
    }

    function loadPersistedTransportRequestLocalState(chave) {
      const normalizedChave = sanitizeChave(chave);
      if (normalizedChave.length !== 4) {
        resetTransportRequestLocalState();
        return;
      }

      const localStateMap = readPersistedTransportLocalStateMap();
      const persistedState = localStateMap[normalizedChave] && typeof localStateMap[normalizedChave] === 'object'
        ? localStateMap[normalizedChave]
        : {};

      transportUiState.dismissedRequestIds = new Set(normalizePersistedTransportRequestIds(persistedState.dismissed_request_ids));
      transportUiState.realizedRequestIds = new Set(normalizePersistedTransportRequestIds(persistedState.realized_request_ids));
    }

    function persistTransportRequestLocalState(chave) {
      const normalizedChave = sanitizeChave(chave);
      if (normalizedChave.length !== 4) {
        return;
      }

      const localStateMap = readPersistedTransportLocalStateMap();
      const dismissedRequestIds = normalizePersistedTransportRequestIds(Array.from(transportUiState.dismissedRequestIds));
      const realizedRequestIds = normalizePersistedTransportRequestIds(Array.from(transportUiState.realizedRequestIds));

      if (!dismissedRequestIds.length && !realizedRequestIds.length) {
        delete localStateMap[normalizedChave];
      } else {
        localStateMap[normalizedChave] = {
          dismissed_request_ids: dismissedRequestIds,
          realized_request_ids: realizedRequestIds,
        };
      }

      writePersistedTransportLocalStateMap(localStateMap);
    }

    function normalizeTransportRequestStatusValue(value) {
      const normalizedStatus = String(value || 'pending').trim().toLowerCase();
      if (!normalizedStatus) {
        return 'pending';
      }

      // The API will own `realized` later; for now the webapp controls it locally.
      return normalizedStatus === 'realized' ? 'confirmed' : normalizedStatus;
    }

    function getTransportRequests() {
      return Array.isArray(transportState.requests) ? transportState.requests : [];
    }

    function getVisibleTransportRequests() {
      return getTransportRequests();
    }

    function findTransportRequestById(requestId) {
      const normalizedRequestId = Number(requestId);
      if (!Number.isFinite(normalizedRequestId)) {
        return null;
      }

      return getTransportRequests().find((requestItem) => Number(requestItem.requestId) === normalizedRequestId) || null;
    }

    function findVisibleTransportRequestById(requestId) {
      const normalizedRequestId = Number(requestId);
      if (!Number.isFinite(normalizedRequestId)) {
        return null;
      }

      return getVisibleTransportRequests().find((requestItem) => Number(requestItem.requestId) === normalizedRequestId) || null;
    }

    function getTransportSelectedRequest() {
      return findVisibleTransportRequestById(transportUiState.selectedRequestId);
    }

    function getTransportDetailRequest() {
      return findVisibleTransportRequestById(transportUiState.detailRequestId);
    }

    function canDismissTransportRequestItem(requestItem) {
      return Boolean(
        requestItem
        && (requestItem.status === 'realized' || requestItem.status === 'cancelled')
      );
    }

    function applyPersistedTransportRequestLocalOverrides() {
      transportState.requests = getTransportRequests().map((requestItem) => {
        if (!requestItem) {
          return requestItem;
        }

        if (
          transportUiState.realizedRequestIds.has(Number(requestItem.requestId))
          && requestItem.status === 'confirmed'
        ) {
          return {
            ...requestItem,
            status: 'realized',
          };
        }

        return requestItem;
      });
    }

    function reconcilePersistedTransportRequestLocalState() {
      const requestById = new Map(
        getTransportRequests().map((requestItem) => [Number(requestItem.requestId), requestItem])
      );
      let changed = false;

      Array.from(transportUiState.realizedRequestIds).forEach((requestId) => {
        const requestItem = requestById.get(Number(requestId));
        if (!requestItem || (requestItem.status !== 'confirmed' && requestItem.status !== 'realized')) {
          transportUiState.realizedRequestIds.delete(requestId);
          changed = true;
        }
      });

      Array.from(transportUiState.dismissedRequestIds).forEach((requestId) => {
        const requestItem = requestById.get(Number(requestId));
        if (!requestItem || !canDismissTransportRequestItem(requestItem)) {
          transportUiState.dismissedRequestIds.delete(requestId);
          changed = true;
        }
      });

      if (changed) {
        persistTransportRequestLocalState(getActiveChave());
      }
    }

    function shouldAutoRefreshTransportRequest(requestItem) {
      return Boolean(
        requestItem
        && requestItem.isActive
        && (requestItem.status === 'pending' || requestItem.status === 'confirmed')
      );
    }

    function shouldAutoRefreshTransportState() {
      return isTransportScreenOpen()
        && isApplicationUnlocked()
        && !transportUiState.requestBuilderKind
        && !getTransportStateLoading()
        && !getTransportAddressSaveInProgress()
        && !getTransportRequestInProgress()
        && !getTransportCancelInProgress()
        && getTransportRequests().some(shouldAutoRefreshTransportRequest);
    }

    function clearPendingTransportRealtimeRefresh() {
      if (transportRealtimeRefreshTimeoutId !== null) {
        window.clearTimeout(transportRealtimeRefreshTimeoutId);
        transportRealtimeRefreshTimeoutId = null;
      }
    }

    function stopTransportRealtimeUpdates() {
      clearPendingTransportRealtimeRefresh();
      transportRealtimeRefreshPending = false;
      transportRealtimeStreamChave = '';
      if (transportRealtimeEventSource) {
        transportRealtimeEventSource.close();
        transportRealtimeEventSource = null;
      }
    }

    function canProcessTransportRealtimeRefresh() {
      return isTransportScreenOpen()
        && isApplicationUnlocked()
        && !transportUiState.addressEditorOpen
        && !transportUiState.requestBuilderKind
        && !getTransportStateLoading()
        && !getTransportAddressSaveInProgress()
        && !getTransportRequestInProgress()
        && !getTransportCancelInProgress();
    }

    function requestTransportRealtimeRefresh() {
      transportRealtimeRefreshPending = true;
      if (!canProcessTransportRealtimeRefresh()) {
        return;
      }
      if (transportRealtimeRefreshTimeoutId !== null) {
        return;
      }

      transportRealtimeRefreshTimeoutId = window.setTimeout(() => {
        transportRealtimeRefreshTimeoutId = null;
        if (!transportRealtimeRefreshPending || !canProcessTransportRealtimeRefresh()) {
          return;
        }

        transportRealtimeRefreshPending = false;
        void loadTransportState();
      }, transportRealtimeRefreshDebounceMs);
    }

    function handleTransportRealtimeMessage(event) {
      const rawData = event && typeof event.data === 'string' ? event.data : '';
      if (!rawData) {
        return;
      }

      let payload = null;
      try {
        payload = JSON.parse(rawData);
      } catch {
        payload = null;
      }

      if (payload && payload.reason === 'connected') {
        return;
      }

      requestTransportRealtimeRefresh();
    }

    function startTransportRealtimeUpdates() {
      if (typeof window.EventSource !== 'function' || !isTransportScreenOpen()) {
        return;
      }

      const normalizedChave = getActiveChave();
      if (normalizedChave.length !== 4 || !isApplicationUnlocked(normalizedChave)) {
        stopTransportRealtimeUpdates();
        return;
      }

      if (transportRealtimeEventSource && transportRealtimeStreamChave === normalizedChave) {
        return;
      }

      stopTransportRealtimeUpdates();
      transportRealtimeStreamChave = normalizedChave;
      transportRealtimeEventSource = new window.EventSource(
        `${transportStreamEndpoint}?chave=${encodeURIComponent(normalizedChave)}`
      );
      transportRealtimeEventSource.onmessage = handleTransportRealtimeMessage;
      transportRealtimeEventSource.onerror = () => {
        if (!isTransportScreenOpen() || !isApplicationUnlocked(normalizedChave)) {
          stopTransportRealtimeUpdates();
        }
      };
    }

    function scheduleTransportAutoRefresh() {
      clearTransportAutoRefresh();
      if (!shouldAutoRefreshTransportState()) {
        return;
      }

      transportAutoRefreshTimeoutId = window.setTimeout(() => {
        transportAutoRefreshTimeoutId = null;
        if (shouldAutoRefreshTransportState()) {
          void loadTransportState();
        }
      }, transportAutoRefreshIntervalMs);
    }

    function syncTransportAddressFormValues() {
      if (transportAddressInput) {
        transportAddressInput.value = transportState.endRua || '';
      }
      if (transportZipInput) {
        transportZipInput.value = transportState.zip || '';
      }
    }

    function formatTransportTimeLabel(value) {
      const normalizedValue = String(value || '').trim();
      return normalizedValue ? `${normalizedValue}h` : '--';
    }

    function formatTransportAddressSummary(endRua, zipCode) {
      const normalizedAddress = String(endRua || '').trim();
      const normalizedZipCode = String(zipCode || '').trim();

      if (normalizedAddress && normalizedZipCode) {
        return `${normalizedAddress}\n${normalizedZipCode}`;
      }
      return normalizedAddress || normalizedZipCode || '';
    }

    function getTransportRequestBuilderConfig(requestKind) {
      return requestKind && transportRequestBuilderConfigs[requestKind]
        ? transportRequestBuilderConfigs[requestKind]
        : null;
    }

    function formatDateInputValue(dateValue) {
      if (!(dateValue instanceof Date) || Number.isNaN(dateValue.getTime())) {
        return '';
      }

      const year = String(dateValue.getFullYear());
      const month = String(dateValue.getMonth() + 1).padStart(2, '0');
      const day = String(dateValue.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    }

    function formatCurrentTransportRequestTime() {
      const currentDate = new Date();
      const hours = String(currentDate.getHours()).padStart(2, '0');
      const minutes = String(currentDate.getMinutes()).padStart(2, '0');
      return `${hours}:${minutes}`;
    }

    function getTransportRequestWeekdayValue(dateValue) {
      if (!(dateValue instanceof Date) || Number.isNaN(dateValue.getTime())) {
        return null;
      }

      return (dateValue.getDay() + 6) % 7;
    }

    function resolveTransportRequestTargetServiceDate(requestKind, payload) {
      if (!payload || payload.request_kind !== requestKind) {
        return '';
      }

      if (requestKind === 'extra') {
        return String(payload.requested_date || '').trim();
      }

      const selectedWeekdays = Array.isArray(payload.selected_weekdays)
        ? payload.selected_weekdays
          .map((value) => Number(value))
          .filter((value) => Number.isInteger(value) && value >= 0 && value <= 6)
        : [];
      if (selectedWeekdays.length === 0) {
        return '';
      }

      const referenceDate = new Date();
      referenceDate.setHours(0, 0, 0, 0);
      for (let dayOffset = 0; dayOffset < 7; dayOffset += 1) {
        const candidate = new Date(referenceDate);
        candidate.setDate(referenceDate.getDate() + dayOffset);
        if (selectedWeekdays.includes(getTransportRequestWeekdayValue(candidate))) {
          return formatDateInputValue(candidate);
        }
      }

      return '';
    }

    function formatTransportRequestConflictServiceDate(serviceDateValue) {
      const normalizedValue = String(serviceDateValue || '').trim();
      const matchedDate = normalizedValue.match(/^(\d{4})-(\d{2})-(\d{2})$/);
      if (!matchedDate) {
        return normalizedValue;
      }

      const formatter = getRuntimeDateFormatter();
      if (formatter && typeof formatter.format === 'function') {
        const parsedDate = new Date(`${matchedDate[1]}-${matchedDate[2]}-${matchedDate[3]}T00:00:00`);
        if (!Number.isNaN(parsedDate.getTime())) {
          return formatter.format(parsedDate);
        }
      }

      return `${matchedDate[3]}/${matchedDate[2]}/${matchedDate[1]}`;
    }

    function getTransportRequestServiceDateConflictMessage(requestKind, payload) {
      const targetServiceDate = resolveTransportRequestTargetServiceDate(requestKind, payload);
      if (!targetServiceDate) {
        return '';
      }

      const conflictingRequest = getTransportRequests().find((requestItem) => (
        requestItem
        && requestItem.isActive
        && requestItem.serviceDate === targetServiceDate
      ));
      if (!conflictingRequest) {
        return '';
      }

      const serviceDateLabel = formatTransportRequestConflictServiceDate(targetServiceDate);
      if (!serviceDateLabel) {
        return translateTransport('requestBuilder.conflictGeneric');
      }

      return translateTransport('requestBuilder.conflictByDate', { serviceDateLabel });
    }

    function getTransportAddressValidationMessage() {
      const normalizedAddress = String(transportState.endRua || '').trim();
      const normalizedZipCode = String(transportState.zip || '').replace(/\D/g, '');

      if (normalizedAddress && normalizedZipCode.length === 6) {
        return '';
      }

      return translateTransport('requestBuilder.addressRequired');
    }

    function canSubmitTransportRequest(requestKind, options) {
      const settings = options || {};
      const builderConfig = getTransportRequestBuilderConfig(requestKind);
      if (!builderConfig) {
        return {
          allowed: false,
          message: translateTransport('requestBuilder.requestUnavailable'),
          payload: null,
          shouldOpenAddressEditor: false,
        };
      }

      const addressValidationMessage = getTransportAddressValidationMessage();
      if (addressValidationMessage) {
        return {
          allowed: false,
          message: addressValidationMessage,
          payload: null,
          shouldOpenAddressEditor: true,
        };
      }

      const payload = {
        request_kind: requestKind,
        requested_time: formatCurrentTransportRequestTime(),
      };

      if (settings.skipBuilderValidation) {
        return {
          allowed: true,
          message: '',
          payload,
          shouldOpenAddressEditor: false,
        };
      }

      if (builderConfig.showWeekdays) {
        const selectedWeekdays = transportRequestWeekdayInputs
          .filter((inputElement) => {
            const weekdayValue = Number(inputElement.value);
            return builderConfig.allowedWeekdays.includes(weekdayValue) && inputElement.checked;
          })
          .map((inputElement) => Number(inputElement.value));

        if (selectedWeekdays.length === 0) {
          return {
            allowed: false,
            message: translateTransport('requestBuilder.dayRequired'),
            payload: null,
            shouldOpenAddressEditor: false,
          };
        }

        payload.selected_weekdays = selectedWeekdays;
      } else {
        const requestedDate = String(transportRequestDateInput && transportRequestDateInput.value || '').trim();
        const requestedTime = String(transportRequestTimeInput && transportRequestTimeInput.value || '').trim();
        if (!requestedDate) {
          return {
            allowed: false,
            message: translateTransport('requestBuilder.dateRequiredExtra'),
            payload: null,
            shouldOpenAddressEditor: false,
          };
        }
        if (!requestedTime) {
          return {
            allowed: false,
            message: translateTransport('requestBuilder.timeRequiredExtra'),
            payload: null,
            shouldOpenAddressEditor: false,
          };
        }

        payload.requested_date = requestedDate;
        payload.requested_time = requestedTime;
      }

      const serviceDateConflictMessage = getTransportRequestServiceDateConflictMessage(requestKind, payload);
      if (serviceDateConflictMessage) {
        return {
          allowed: false,
          message: serviceDateConflictMessage,
          payload: null,
          shouldOpenAddressEditor: false,
        };
      }

      return {
        allowed: true,
        message: '',
        payload,
        shouldOpenAddressEditor: false,
      };
    }

    function syncTransportOptionAvailability(buttonElement, requestKind) {
      if (!buttonElement) {
        return;
      }

      const availability = canSubmitTransportRequest(requestKind, { skipBuilderValidation: true });
      const blocked = !availability.allowed;
      buttonElement.dataset.transportOptionDisabled = blocked ? 'true' : 'false';
      buttonElement.setAttribute('aria-disabled', String(blocked));
      buttonElement.title = blocked ? availability.message : '';
    }

    function initializeTransportRequestBuilder(requestKind) {
      const requestAvailability = canSubmitTransportRequest(requestKind, { skipBuilderValidation: true });
      if (!requestAvailability.allowed) {
        setTransportInlineStatus(requestAvailability.message, 'error');
        if (requestAvailability.shouldOpenAddressEditor) {
          openTransportAddressEditor();
        }
        return;
      }

      const builderConfig = getTransportRequestBuilderConfig(requestKind);
      if (!builderConfig) {
        return;
      }

      clearTransportInlineStatus();
      transportUiState.requestBuilderKind = requestKind;
      transportUiState.addressEditorOpen = false;
      transportUiState.detailRequestId = null;

      transportRequestWeekdayInputs.forEach((inputElement) => {
        const weekdayValue = Number(inputElement.value);
        inputElement.checked = builderConfig.defaultSelectedWeekdays.includes(weekdayValue);
      });

      if (transportRequestDateInput) {
        transportRequestDateInput.value = formatDateInputValue(new Date());
      }
      if (transportRequestTimeInput) {
        transportRequestTimeInput.value = builderConfig.defaultTime || '';
      }

      renderTransportScreen();
      syncFormControlStates();
      realignViewport();
    }

    function closeTransportRequestBuilder() {
      if (!transportUiState.requestBuilderKind) {
        return;
      }

      transportUiState.requestBuilderKind = null;
      renderTransportScreen();
      syncFormControlStates();
      realignViewport();
    }

    function collectTransportRequestPayload(requestKind) {
      const requestAvailability = canSubmitTransportRequest(requestKind);
      if (!requestAvailability.allowed) {
        setTransportInlineStatus(requestAvailability.message, 'error');
        if (requestAvailability.shouldOpenAddressEditor) {
          openTransportAddressEditor();
        }
        return null;
      }

      return requestAvailability.payload;
    }

    function normalizeTransportRequestItem(payload) {
      const requestId = payload && payload.request_id !== null && payload.request_id !== undefined && Number.isFinite(Number(payload.request_id))
        ? Number(payload.request_id)
        : null;
      const isActive = Boolean(payload && payload.is_active);
      let normalizedStatus = normalizeTransportRequestStatusValue(payload && payload.status);

      if (!isActive && normalizedStatus !== 'realized') {
        normalizedStatus = 'cancelled';
      }

      return {
        requestId,
        requestKind: payload && payload.request_kind ? String(payload.request_kind) : null,
        status: normalizedStatus,
        isActive,
        serviceDate: payload && payload.service_date ? String(payload.service_date) : null,
        requestedTime: String(payload && payload.requested_time || ''),
        selectedWeekdays: Array.isArray(payload && payload.selected_weekdays)
          ? payload.selected_weekdays.map((value) => Number(value)).filter((value) => Number.isInteger(value) && value >= 0 && value <= 6)
          : [],
        routeKind: payload && payload.route_kind ? String(payload.route_kind) : null,
        boardingTime: String(payload && payload.boarding_time || ''),
        confirmationDeadlineTime: String(payload && payload.confirmation_deadline_time || ''),
        vehicleType: String(payload && payload.vehicle_type || ''),
        vehiclePlate: String(payload && payload.vehicle_plate || ''),
        vehicleColor: String(payload && payload.vehicle_color || ''),
        toleranceMinutes: payload && payload.tolerance_minutes !== null && payload.tolerance_minutes !== undefined && Number.isFinite(Number(payload.tolerance_minutes))
          ? Number(payload.tolerance_minutes)
          : null,
        responseMessage: String(payload && payload.response_message || ''),
        createdAt: String(payload && payload.created_at || ''),
      };
    }

    function createTransportFallbackRequest(payload) {
      const requestId = payload && payload.request_id !== null && payload.request_id !== undefined && Number.isFinite(Number(payload.request_id))
        ? Number(payload.request_id)
        : null;
      if (!requestId) {
        return [];
      }

      return [normalizeTransportRequestItem({
        request_id: requestId,
        request_kind: payload && payload.request_kind,
        status: normalizeTransportRequestStatusValue(payload && payload.status),
        is_active: payload && payload.status !== 'available',
        service_date: payload && payload.service_date,
        requested_time: payload && payload.requested_time,
        route_kind: payload && payload.route_kind,
        boarding_time: payload && payload.boarding_time,
        confirmation_deadline_time: payload && payload.confirmation_deadline_time,
        vehicle_type: payload && payload.vehicle_type,
        vehicle_plate: payload && payload.vehicle_plate,
        vehicle_color: payload && payload.vehicle_color,
        tolerance_minutes: payload && payload.tolerance_minutes,
      })];
    }

    function resolveDefaultSelectedTransportRequestId() {
      const requests = getVisibleTransportRequests();
      const preferredRequest = requests.find((requestItem) => requestItem.isActive)
        || requests[0]
        || null;
      return preferredRequest ? preferredRequest.requestId : null;
    }

    function reconcileDismissedTransportRequestIds() {
      const activeRequestIds = new Set(
        getTransportRequests()
          .map((requestItem) => Number(requestItem.requestId))
          .filter((requestId) => Number.isFinite(requestId))
      );
      let changed = false;

      Array.from(transportUiState.dismissedRequestIds).forEach((requestId) => {
        if (!activeRequestIds.has(requestId)) {
          transportUiState.dismissedRequestIds.delete(requestId);
          changed = true;
        }
      });

      if (changed) {
        persistTransportRequestLocalState(getActiveChave());
      }
    }

    function buildTransportSelectionFallbackPayload() {
      return {
        status: transportState.status,
        request_id: transportState.requestId,
        request_kind: transportState.requestKind,
        route_kind: transportState.routeKind,
        service_date: transportState.serviceDate,
        requested_time: transportState.requestedTime,
        boarding_time: transportState.boardingTime,
        confirmation_deadline_time: transportState.confirmationDeadlineTime,
        vehicle_type: transportState.vehicleType,
        vehicle_plate: transportState.vehiclePlate,
        vehicle_color: transportState.vehicleColor,
        tolerance_minutes: transportState.toleranceMinutes,
      };
    }

    function dismissTransportRequestCard(requestId) {
      const normalizedRequestId = Number(requestId);
      if (!Number.isFinite(normalizedRequestId)) {
        return;
      }

      const requestItem = findTransportRequestById(normalizedRequestId);
      if (!canDismissTransportRequestItem(requestItem)) {
        return;
      }

      transportUiState.dismissedRequestIds.add(normalizedRequestId);
      if (Number(transportUiState.detailRequestId) === normalizedRequestId) {
        transportUiState.detailRequestId = null;
      }
      persistTransportRequestLocalState(getActiveChave());
      if (!findVisibleTransportRequestById(transportUiState.selectedRequestId)) {
        transportUiState.selectedRequestId = resolveDefaultSelectedTransportRequestId();
      }
      syncSelectedTransportRequestState(buildTransportSelectionFallbackPayload());
      renderTransportScreen();
      syncFormControlStates();
    }

    function markTransportRequestAsRealized(requestId) {
      const normalizedRequestId = Number(requestId);
      if (!Number.isFinite(normalizedRequestId)) {
        return;
      }

      const requestItem = findTransportRequestById(normalizedRequestId);
      if (!canMarkTransportRequestAsRealized(requestItem)) {
        return;
      }

      transportUiState.realizedRequestIds.add(normalizedRequestId);
      transportUiState.dismissedRequestIds.delete(normalizedRequestId);
      persistTransportRequestLocalState(getActiveChave());
      applyPersistedTransportRequestLocalOverrides();
      syncSelectedTransportRequestState(buildTransportSelectionFallbackPayload());
      setTransportInlineStatus(translateTransport('messages.requestMarkedRealized'), 'success');
      renderTransportScreen();
      syncFormControlStates();
    }

    function resetTransportRequestSwipeState(options) {
      const preserveSuppressedClick = Boolean(options && options.preserveSuppressedClick);
      if (transportRequestSwipeState.holdTimeoutId !== null) {
        window.clearTimeout(transportRequestSwipeState.holdTimeoutId);
        transportRequestSwipeState.holdTimeoutId = null;
      }
      transportRequestSwipeState.pointerId = null;
      transportRequestSwipeState.requestId = null;
      transportRequestSwipeState.startX = 0;
      transportRequestSwipeState.startY = 0;
      transportRequestSwipeState.deltaX = 0;
      transportRequestSwipeState.deltaY = 0;
      transportRequestSwipeState.isHorizontal = false;
      transportRequestSwipeState.hasMoved = false;
      transportRequestSwipeState.targetCard = null;
      transportRequestSwipeState.holdTriggered = false;
      if (!preserveSuppressedClick) {
        transportRequestSwipeState.suppressedClickRequestId = null;
      }
    }

    function suppressTransportRequestCardClick(requestId) {
      transportRequestSwipeState.suppressedClickRequestId = requestId;
      window.setTimeout(() => {
        if (Number(transportRequestSwipeState.suppressedClickRequestId) === Number(requestId)) {
          transportRequestSwipeState.suppressedClickRequestId = null;
        }
      }, 250);
    }

    function snapBackTransportRequestCard(cardElement) {
      if (!cardElement) {
        return;
      }

      cardElement.classList.remove('is-swiping', 'is-pressing');
      cardElement.style.setProperty('--transport-request-swipe-offset', '0px');
      cardElement.style.setProperty('--transport-request-swipe-opacity', '1');
    }

    function animateTransportRequestCardDismissal(cardElement, requestId) {
      if (!cardElement) {
        return;
      }

      cardElement.classList.remove('is-swiping', 'is-pressing');
      cardElement.classList.add('is-dismissing');
      window.setTimeout(() => {
        dismissTransportRequestCard(requestId);
      }, 220);
    }

    function beginTransportRequestSwipe(event) {
      if (!transportRequestHistoryList || !event || event.pointerType === 'mouse') {
        return;
      }

      const targetElement = resolveTransportEventTargetElement(event);
      if (!targetElement || targetElement.closest('[data-transport-request-cancel="true"][data-request-id]')) {
        return;
      }

      const requestCard = targetElement.closest('.transport-request-card[data-request-id]');
      if (!requestCard || requestCard.getAttribute('aria-disabled') === 'true' || requestCard.classList.contains('is-dismissing')) {
        return;
      }

      const requestId = Number(requestCard.getAttribute('data-request-id'));
      if (!Number.isFinite(requestId)) {
        return;
      }

      if (!canDismissTransportRequestItem(findVisibleTransportRequestById(requestId) || findTransportRequestById(requestId))) {
        return;
      }

      const pointerId = event.pointerId;

      transportRequestSwipeState.pointerId = pointerId;
      transportRequestSwipeState.requestId = requestId;
      transportRequestSwipeState.startX = event.clientX;
      transportRequestSwipeState.startY = event.clientY;
      transportRequestSwipeState.deltaX = 0;
      transportRequestSwipeState.deltaY = 0;
      transportRequestSwipeState.isHorizontal = false;
      transportRequestSwipeState.hasMoved = false;
      transportRequestSwipeState.targetCard = requestCard;
      transportRequestSwipeState.holdTriggered = false;

      requestCard.classList.add('is-pressing');

      if (typeof requestCard.setPointerCapture === 'function') {
        try {
          requestCard.setPointerCapture(pointerId);
        } catch {}
      }

      transportRequestSwipeState.holdTimeoutId = window.setTimeout(() => {
        if (
          !transportRequestSwipeState.targetCard
          || transportRequestSwipeState.pointerId !== pointerId
          || Number(transportRequestSwipeState.requestId) !== requestId
        ) {
          return;
        }

        transportRequestSwipeState.holdTriggered = true;
        suppressTransportRequestCardClick(requestId);
        if (typeof requestCard.releasePointerCapture === 'function') {
          try {
            requestCard.releasePointerCapture(pointerId);
          } catch {}
        }
        animateTransportRequestCardDismissal(requestCard, requestId);
        resetTransportRequestSwipeState({ preserveSuppressedClick: true });
      }, transportRequestDismissHoldDelayMs);
    }

    function updateTransportRequestSwipe(event) {
      if (
        !transportRequestSwipeState.targetCard
        || transportRequestSwipeState.pointerId !== event.pointerId
      ) {
        return;
      }

      const requestCard = transportRequestSwipeState.targetCard;
      const deltaX = event.clientX - transportRequestSwipeState.startX;
      const deltaY = event.clientY - transportRequestSwipeState.startY;

      transportRequestSwipeState.deltaX = deltaX;
      transportRequestSwipeState.deltaY = deltaY;

      if (transportRequestSwipeState.holdTriggered) {
        return;
      }

      if (
        Math.abs(deltaX) <= transportRequestDismissMoveTolerancePx
        && Math.abs(deltaY) <= transportRequestDismissMoveTolerancePx
      ) {
        return;
      }

      if (typeof requestCard.releasePointerCapture === 'function') {
        try {
          requestCard.releasePointerCapture(event.pointerId);
        } catch {}
      }

      snapBackTransportRequestCard(requestCard);
      resetTransportRequestSwipeState();
    }

    function endTransportRequestSwipe(event) {
      if (
        !transportRequestSwipeState.targetCard
        || transportRequestSwipeState.pointerId !== event.pointerId
      ) {
        return;
      }

      const requestCard = transportRequestSwipeState.targetCard;

      if (typeof requestCard.releasePointerCapture === 'function') {
        try {
          requestCard.releasePointerCapture(event.pointerId);
        } catch {}
      }

      snapBackTransportRequestCard(requestCard);
      resetTransportRequestSwipeState();
    }

    function syncSelectedTransportRequestState(payload) {
      const selectedRequest = getTransportSelectedRequest();
      const fallbackStatus = payload && payload.status === 'realized'
        ? 'confirmed'
        : String(payload && payload.status || 'available');

      if (!selectedRequest) {
        if (getVisibleTransportRequests().length === 0) {
          transportState.status = 'available';
          transportState.requestId = null;
          transportState.requestKind = null;
          transportState.routeKind = null;
          transportState.serviceDate = null;
          transportState.requestedTime = '';
          transportState.boardingTime = '';
          transportState.confirmationDeadlineTime = '';
          transportState.vehicleType = '';
          transportState.vehiclePlate = '';
          transportState.vehicleColor = '';
          transportState.toleranceMinutes = null;
          return;
        }

        transportState.status = fallbackStatus;
        transportState.requestId = payload && payload.request_id !== null && payload.request_id !== undefined && Number.isFinite(Number(payload.request_id))
          ? Number(payload.request_id)
          : null;
        transportState.requestKind = payload && payload.request_kind ? String(payload.request_kind) : null;
        transportState.routeKind = payload && payload.route_kind ? String(payload.route_kind) : null;
        transportState.serviceDate = payload && payload.service_date ? String(payload.service_date) : null;
        transportState.requestedTime = String(payload && payload.requested_time || '');
        transportState.boardingTime = String(payload && payload.boarding_time || payload && payload.requested_time || '');
        transportState.confirmationDeadlineTime = String(payload && payload.confirmation_deadline_time || payload && payload.requested_time || '');
        transportState.vehicleType = String(payload && payload.vehicle_type || '');
        transportState.vehiclePlate = String(payload && payload.vehicle_plate || '');
        transportState.vehicleColor = String(payload && payload.vehicle_color || '');
        transportState.toleranceMinutes = payload && payload.tolerance_minutes !== null && payload.tolerance_minutes !== undefined && Number.isFinite(Number(payload.tolerance_minutes))
          ? Number(payload.tolerance_minutes)
          : null;
        return;
      }

      transportState.status = selectedRequest.status;
      transportState.requestId = selectedRequest.requestId;
      transportState.requestKind = selectedRequest.requestKind;
      transportState.routeKind = selectedRequest.routeKind;
      transportState.serviceDate = selectedRequest.serviceDate;
      transportState.requestedTime = selectedRequest.requestedTime;
      transportState.boardingTime = selectedRequest.boardingTime || selectedRequest.requestedTime;
      transportState.confirmationDeadlineTime = selectedRequest.confirmationDeadlineTime || selectedRequest.requestedTime;
      transportState.vehicleType = selectedRequest.vehicleType;
      transportState.vehiclePlate = selectedRequest.vehiclePlate;
      transportState.vehicleColor = selectedRequest.vehicleColor;
      transportState.toleranceMinutes = selectedRequest.toleranceMinutes;
    }

    function applyTransportStatePayload(payload) {
      transportState.endRua = String(payload && payload.end_rua || '');
      transportState.zip = String(payload && payload.zip || '');
      transportState.requests = Array.isArray(payload && payload.requests) && payload.requests.length
        ? payload.requests.map(normalizeTransportRequestItem).filter((requestItem) => Number.isFinite(requestItem.requestId))
        : createTransportFallbackRequest(payload);
      loadPersistedTransportRequestLocalState(getActiveChave());
      applyPersistedTransportRequestLocalOverrides();
      reconcileDismissedTransportRequestIds();
      reconcilePersistedTransportRequestLocalState();
      if (transportUiState.selectedRequestId === null || !findVisibleTransportRequestById(transportUiState.selectedRequestId)) {
        transportUiState.selectedRequestId = resolveDefaultSelectedTransportRequestId();
      }
      syncSelectedTransportRequestState(payload);
      if (String(payload && payload.status || 'available') !== 'available') {
        transportUiState.requestBuilderKind = null;
      }
      syncTransportAddressFormValues();
      renderTransportScreen();
    }

    function canCancelTransportRequestItem(requestItem) {
      return Boolean(
        requestItem
        && requestItem.isActive
        && (requestItem.status === 'pending' || requestItem.status === 'confirmed')
      );
    }

    function canMarkTransportRequestAsRealized(requestItem) {
      if (!requestItem || requestItem.status !== 'confirmed' || !requestItem.isActive || !requestItem.serviceDate) {
        return false;
      }

      const now = new Date();
      const todayDateValue = formatDateInputValue(now);
      if (!todayDateValue) {
        return false;
      }

      if (requestItem.serviceDate < todayDateValue) {
        return true;
      }
      if (requestItem.serviceDate > todayDateValue) {
        return false;
      }

      const departureTime = formatTransportRequestCardTime(requestItem.boardingTime || requestItem.requestedTime);
      if (!/^\d{2}:\d{2}$/.test(departureTime)) {
        return false;
      }

      const departureDateTime = new Date(`${requestItem.serviceDate}T${departureTime}:00`);
      return !Number.isNaN(departureDateTime.getTime()) && departureDateTime.getTime() <= now.getTime();
    }

    function formatTransportRequestWeekdays(selectedWeekdays) {
      if (!Array.isArray(selectedWeekdays) || selectedWeekdays.length === 0) {
        return '';
      }

      return selectedWeekdays
        .map((weekdayValue) => transportRequestWeekdayLabels[weekdayValue])
        .filter(Boolean)
        .join(', ');
    }

    function formatTransportRequestServiceDate(serviceDateValue) {
      if (!serviceDateValue) {
        return '';
      }

      const parsedDate = new Date(`${serviceDateValue}T00:00:00`);
      const formatter = getRuntimeDateFormatter();
      return Number.isNaN(parsedDate.getTime()) || !formatter || typeof formatter.format !== 'function'
        ? serviceDateValue
        : formatter.format(parsedDate);
    }

    function formatTransportRequestCardTime(value) {
      const normalizedValue = String(value || '').trim();
      if (!normalizedValue) {
        return '';
      }

      const matchedTime = normalizedValue.match(/^(\d{2}:\d{2})/);
      return matchedTime ? matchedTime[1] : normalizedValue;
    }

    function formatTransportRequestCardDateTime(requestItem) {
      const dateLabel = formatTransportRequestServiceDate(requestItem.serviceDate);
      const timeLabel = formatTransportRequestCardTime(requestItem.boardingTime || requestItem.requestedTime);

      if (dateLabel && timeLabel) {
        return `${dateLabel} ${timeLabel}`;
      }
      if (dateLabel) {
        return dateLabel;
      }
      if (timeLabel) {
        return timeLabel;
      }

      const weekdaysLabel = formatTransportRequestWeekdays(requestItem.selectedWeekdays);
      return weekdaysLabel || '--';
    }

    function getLatestTransportRequestByKind(requestKind) {
      return getTransportRequests().find((requestItem) => requestItem.requestKind === requestKind) || null;
    }

    function getTransportRequestProjection() {
      return transportRequestProjectionKinds.map((requestKind) => ({
        requestKind,
        requestItem: getLatestTransportRequestByKind(requestKind),
      }));
    }

    function formatTransportRequestSummaryStatusLabel(requestItem) {
      if (!requestItem) {
        return translateTransport('statusLabels.available');
      }

      return transportRequestStatusLabels[requestItem.status] || translateTransport('statusLabels.pending');
    }

    function formatTransportRequestSummaryVehicleLabel(requestItem) {
      if (!requestItem) {
        return '';
      }

      const formattedVehicleType = typeof formatTransportVehicleTypeLabel === 'function'
        ? formatTransportVehicleTypeLabel(requestItem.vehicleType)
        : String(requestItem.vehicleType || '').trim();
      const vehicleBits = [formattedVehicleType, String(requestItem.vehiclePlate || '').trim()].filter(Boolean);
      return vehicleBits.join(' • ');
    }

    function formatTransportRequestSummaryPrimaryText(requestItem) {
      if (!requestItem) {
        return translateTransport('summary.noRequestRecorded');
      }

      return formatTransportRequestCardDateTime(requestItem) || translateTransport('summary.scheduleUnavailable');
    }

    function formatTransportRequestSummarySecondaryText(requestItem) {
      if (!requestItem) {
        return translateTransport('summary.whenRequestExists');
      }

      if (requestItem.status === 'pending') {
        return translateTransport('summary.waitingAllocation');
      }

      if (requestItem.status === 'confirmed' || requestItem.status === 'realized') {
        return formatTransportRequestSummaryVehicleLabel(requestItem) || translateTransport('summary.vehicleAllocated');
      }

      return localizeKnownApiMessage(String(requestItem.responseMessage || '').trim()) || translateTransport('summary.requestClosed');
    }

    function formatTransportRequestSummaryTertiaryText(requestItem) {
      if (!requestItem || (requestItem.status !== 'confirmed' && requestItem.status !== 'realized')) {
        return '';
      }

      const departureTime = formatTransportRequestCardTime(requestItem.boardingTime || requestItem.requestedTime);
      const deadlineTime = formatTransportRequestCardTime(requestItem.confirmationDeadlineTime);

      if (departureTime && deadlineTime && departureTime !== deadlineTime) {
        return translateTransport('summary.departureAndLimit', {
          departureTime,
          deadlineTime,
        });
      }
      if (deadlineTime && deadlineTime !== departureTime) {
        return translateTransport('summary.limitOnly', {
          deadlineTime,
        });
      }
      return '';
    }

    function createTransportRequestSummaryCard(requestKind, requestItem) {
      const cardElement = document.createElement('section');
      const cardHeader = document.createElement('div');
      const cardTitle = document.createElement('span');
      const cardStatus = document.createElement('span');
      const copyStack = document.createElement('div');
      const primaryLine = document.createElement('p');
      const secondaryLine = document.createElement('p');
      const tertiaryLine = document.createElement('p');
      const cardActions = document.createElement('div');
      const summaryStatus = requestItem ? requestItem.status : 'available';

      cardElement.className = `transport-request-summary-card is-${summaryStatus}`;
      cardElement.dataset.requestKind = requestKind;
      if (requestItem && Number.isFinite(Number(requestItem.requestId))) {
        cardElement.dataset.requestId = String(requestItem.requestId);
      }

      cardHeader.className = 'transport-request-summary-header';
      cardTitle.className = 'transport-request-summary-title';
      cardTitle.textContent = transportRequestKindLabels[requestKind] || translateTransport('detail.genericTitle');

      cardStatus.className = `transport-request-summary-status is-${summaryStatus}`;
      cardStatus.textContent = formatTransportRequestSummaryStatusLabel(requestItem);

      cardHeader.appendChild(cardTitle);
      cardHeader.appendChild(cardStatus);

      copyStack.className = 'transport-request-summary-copy';

      primaryLine.className = 'transport-request-summary-primary';
      primaryLine.textContent = formatTransportRequestSummaryPrimaryText(requestItem);
      copyStack.appendChild(primaryLine);

      secondaryLine.className = 'transport-request-summary-secondary';
      secondaryLine.textContent = formatTransportRequestSummarySecondaryText(requestItem);
      copyStack.appendChild(secondaryLine);

      const tertiaryText = formatTransportRequestSummaryTertiaryText(requestItem);
      if (tertiaryText) {
        tertiaryLine.className = 'transport-request-summary-tertiary';
        tertiaryLine.textContent = tertiaryText;
        copyStack.appendChild(tertiaryLine);
      }

      cardElement.appendChild(cardHeader);
      cardElement.appendChild(copyStack);

      if (requestItem) {
        const canCancelRequest = canCancelTransportRequestItem(requestItem);
        const canMarkRealized = canMarkTransportRequestAsRealized(requestItem);

        if (canMarkRealized || canCancelRequest) {
          cardActions.className = 'transport-request-summary-actions';

          if (canMarkRealized) {
            const realizedButton = document.createElement('button');
            realizedButton.type = 'button';
            realizedButton.className = 'transport-request-summary-action is-realized';
            realizedButton.dataset.transportRequestRealized = 'true';
            realizedButton.dataset.requestId = String(requestItem.requestId);
            realizedButton.disabled = getTransportBusy();
            realizedButton.textContent = translateTransport('actions.markRealized');
            cardActions.appendChild(realizedButton);
          }

          if (canCancelRequest) {
            const cancelButton = document.createElement('button');
            cancelButton.type = 'button';
            cancelButton.className = 'transport-request-summary-action is-cancel';
            cancelButton.dataset.transportRequestCancel = 'true';
            cancelButton.dataset.requestId = String(requestItem.requestId);
            cancelButton.disabled = getTransportBusy();
            cancelButton.textContent = getTransportCancelInProgress()
              ? translateTransport('actions.cancelling')
              : translateTransport('actions.cancel');
            cardActions.appendChild(cancelButton);
          }

          cardElement.appendChild(cardActions);
        }
      }

      return cardElement;
    }

    function renderTransportRequestSummaries() {
      if (!transportRequestHistoryList) {
        return;
      }

      transportRequestHistoryList.replaceChildren();
      getTransportRequestProjection().forEach(({ requestKind, requestItem }) => {
        transportRequestHistoryList.appendChild(createTransportRequestSummaryCard(requestKind, requestItem));
      });
    }

    function closeTransportRequestDetailWidget() {
      if (transportUiState.detailRequestId === null) {
        return;
      }

      transportUiState.detailRequestId = null;
      renderTransportScreen();
      syncFormControlStates();
    }

    function formatTransportRequestDetailVehicleType(value) {
      const formattedValue = typeof formatTransportVehicleTypeLabel === 'function'
        ? formatTransportVehicleTypeLabel(value)
        : String(value || '').trim();
      return formattedValue || translateTransport('detail.unavailableValue');
    }

    function createTransportRequestDetailField(label, value) {
      const fieldElement = document.createElement('div');
      const labelElement = document.createElement('span');
      const valueElement = document.createElement('span');

      fieldElement.className = 'transport-request-detail-field';
      labelElement.className = 'transport-request-detail-field-label';
      valueElement.className = 'transport-request-detail-field-value';

      labelElement.textContent = label;
      valueElement.textContent = value || translateTransport('detail.unavailableValue');

      fieldElement.appendChild(labelElement);
      fieldElement.appendChild(valueElement);
      return fieldElement;
    }

    function buildTransportRequestDetailContent(requestItem) {
      const fragment = document.createDocumentFragment();
      const copyStack = document.createElement('div');
      const statusMessage = document.createElement('p');

      copyStack.className = 'transport-request-detail-copy';
      statusMessage.className = 'transport-request-detail-message';
      copyStack.appendChild(statusMessage);

      if (requestItem.status === 'pending') {
        const followupMessage = document.createElement('p');
        followupMessage.className = 'transport-request-detail-message';
        statusMessage.textContent = translateTransport('detail.waitingAllocation');
        followupMessage.textContent = translateTransport('detail.whenAllocated');
        copyStack.appendChild(followupMessage);
        fragment.appendChild(copyStack);
        return fragment;
      }

      if (requestItem.status === 'confirmed' || requestItem.status === 'realized') {
        const detailsGroup = document.createElement('div');
        const departureDate = formatTransportRequestServiceDate(requestItem.serviceDate) || translateTransport('detail.unavailableValue');
        const departureTime = formatTransportRequestCardTime(requestItem.boardingTime || requestItem.requestedTime) || translateTransport('detail.unavailableValue');

        detailsGroup.className = 'transport-request-detail-fields';
        statusMessage.textContent = requestItem.status === 'realized'
          ? translateTransport('detail.realized')
          : translateTransport('detail.confirmed');

        detailsGroup.appendChild(createTransportRequestDetailField(translateTransport('detail.vehicleTypeLabel'), formatTransportRequestDetailVehicleType(requestItem.vehicleType)));
        detailsGroup.appendChild(createTransportRequestDetailField(translateTransport('detail.vehiclePlateLabel'), requestItem.vehiclePlate || translateTransport('detail.unavailableValue')));
        if (String(requestItem.vehicleColor || '').trim()) {
          detailsGroup.appendChild(createTransportRequestDetailField(translateTransport('detail.vehicleColorLabel'), requestItem.vehicleColor));
        }
        detailsGroup.appendChild(createTransportRequestDetailField(translateTransport('detail.departureDateLabel'), departureDate));
        detailsGroup.appendChild(createTransportRequestDetailField(translateTransport('detail.departureTimeLabel'), departureTime));
        copyStack.appendChild(detailsGroup);
        fragment.appendChild(copyStack);
        return fragment;
      }

      statusMessage.textContent = translateTransport('detail.inactive');
      if (String(requestItem.responseMessage || '').trim()) {
        const responseMessage = document.createElement('p');
        responseMessage.className = 'transport-request-detail-message';
        responseMessage.textContent = localizeKnownApiMessage(requestItem.responseMessage);
        copyStack.appendChild(responseMessage);
      }
      fragment.appendChild(copyStack);
      return fragment;
    }

    function renderTransportRequestDetailWidget(options) {
      if (!transportRequestDetailWidget || !transportRequestDetailContent) {
        return;
      }

      const canShowDetails = Boolean(options && options.canShow);
      const detailRequest = canShowDetails ? getTransportDetailRequest() : null;
      if (!detailRequest) {
        transportUiState.detailRequestId = null;
      }

      const shouldShow = Boolean(canShowDetails && detailRequest);
      transportRequestDetailWidget.hidden = !shouldShow;
      transportRequestDetailWidget.classList.toggle('is-hidden', !shouldShow);

      if (!shouldShow) {
        transportRequestDetailContent.replaceChildren();
        if (transportRequestDetailTitle) {
          transportRequestDetailTitle.textContent = translateTransport('detail.title');
        }
        return;
      }

      if (transportRequestDetailTitle) {
        transportRequestDetailTitle.textContent = transportRequestKindLabels[detailRequest.requestKind] || translateTransport('detail.title');
      }
      transportRequestDetailContent.replaceChildren(buildTransportRequestDetailContent(detailRequest));
    }

    function createTransportRequestCard(requestItem) {
      const cardElement = document.createElement('div');
      const cardHeader = document.createElement('span');
      const cardTitle = document.createElement('span');
      const cardStatus = document.createElement('span');
      const cardMeta = document.createElement('div');
      const cardDateTime = document.createElement('span');
      const cardActions = document.createElement('div');
      const transportBusy = getTransportBusy();
      const canCancelRequest = canCancelTransportRequestItem(requestItem);
      const canMarkRealized = canMarkTransportRequestAsRealized(requestItem);

      cardElement.className = `transport-request-card is-${requestItem.status}`;
      cardElement.dataset.requestId = String(requestItem.requestId);
      cardElement.setAttribute('role', 'button');
      cardElement.setAttribute('aria-haspopup', 'dialog');
      cardElement.setAttribute('aria-controls', 'transportRequestDetailWidget');
      cardElement.setAttribute('aria-disabled', String(transportBusy));
      cardElement.setAttribute('aria-pressed', String(Number(transportUiState.selectedRequestId) === Number(requestItem.requestId)));
      cardElement.tabIndex = transportBusy ? -1 : 0;
      cardElement.classList.toggle('is-selected', Number(transportUiState.selectedRequestId) === Number(requestItem.requestId));

      cardHeader.className = 'transport-request-card-header';
      cardTitle.className = 'transport-request-card-title';
      cardTitle.textContent = transportRequestKindLabels[requestItem.requestKind] || translateTransport('detail.genericTitle');

      cardStatus.className = `transport-request-card-status is-${requestItem.status}`;
      cardStatus.textContent = transportRequestStatusLabels[requestItem.status] || translateTransport('statusLabels.pending');

      cardHeader.appendChild(cardTitle);
      cardHeader.appendChild(cardStatus);

      cardMeta.className = 'transport-request-card-meta';

      cardDateTime.className = 'transport-request-card-date-time';
      cardDateTime.textContent = formatTransportRequestCardDateTime(requestItem);

      cardActions.className = 'transport-request-card-actions';

      if (canMarkRealized) {
        const realizedButton = document.createElement('button');
        realizedButton.type = 'button';
        realizedButton.className = 'transport-request-card-realized-button';
        realizedButton.dataset.transportRequestRealized = 'true';
        realizedButton.dataset.requestId = String(requestItem.requestId);
        realizedButton.disabled = transportBusy;
        realizedButton.textContent = translateTransport('actions.markRealized');
        cardActions.appendChild(realizedButton);
      }

      if (canCancelRequest) {
        const cancelButton = document.createElement('button');
        cancelButton.type = 'button';
        cancelButton.className = 'transport-request-card-cancel-button';
        cancelButton.dataset.transportRequestCancel = 'true';
        cancelButton.dataset.requestId = String(requestItem.requestId);
        cancelButton.disabled = transportBusy;
        cancelButton.textContent = getTransportCancelInProgress()
          ? translateTransport('actions.cancelling')
          : translateTransport('actions.cancel');
        cardActions.appendChild(cancelButton);
      }

      cardElement.appendChild(cardHeader);
      cardMeta.appendChild(cardDateTime);
      if (cardActions.childElementCount > 0) {
        cardMeta.appendChild(cardActions);
      }
      cardElement.appendChild(cardMeta);
      return cardElement;
    }

    function renderTransportRequestHistory() {
      if (!transportRequestHistoryList) {
        return;
      }

      transportRequestHistoryList.replaceChildren();
      getVisibleTransportRequests().forEach((requestItem) => {
        transportRequestHistoryList.appendChild(createTransportRequestCard(requestItem));
      });
    }

    function renderTransportScreen() {
      const activeBuilderConfig = getTransportRequestBuilderConfig(transportUiState.requestBuilderKind);

      if (transportAddressSummaryValue) {
        transportAddressSummaryValue.textContent = formatTransportAddressSummary(transportState.endRua, transportState.zip);
      }

      if (transportAddressEditor) {
        transportAddressEditor.hidden = !transportUiState.addressEditorOpen;
        transportAddressEditor.classList.toggle('is-hidden', !transportUiState.addressEditorOpen);
      }

      if (transportOptionButtons) {
        const showOptions = !transportUiState.addressEditorOpen;
        transportOptionButtons.hidden = !showOptions;
        transportOptionButtons.classList.toggle('is-hidden', !showOptions);
      }

      syncTransportOptionAvailability(transportRegularButton, 'regular');
      syncTransportOptionAvailability(transportWeekendButton, 'weekend');
      syncTransportOptionAvailability(transportExtraButton, 'extra');

      if (transportRequestBuilderPanel) {
        const showRequestBuilder = !transportUiState.addressEditorOpen && Boolean(activeBuilderConfig);
        transportRequestBuilderPanel.hidden = !showRequestBuilder;
        transportRequestBuilderPanel.classList.toggle('is-hidden', !showRequestBuilder);
      }

      if (transportRequestBuilderSubtitle) {
        transportRequestBuilderSubtitle.textContent = activeBuilderConfig ? activeBuilderConfig.subtitle : '';
      }

      if (transportRequestWeekdayGroup) {
        const showWeekdayGroup = Boolean(activeBuilderConfig && activeBuilderConfig.showWeekdays);
        transportRequestWeekdayGroup.hidden = !showWeekdayGroup;
        transportRequestWeekdayGroup.classList.toggle('is-hidden', !showWeekdayGroup);
      }

      if (transportRequestDateGroup) {
        const showDateGroup = Boolean(activeBuilderConfig && activeBuilderConfig.showDate);
        transportRequestDateGroup.hidden = !showDateGroup;
        transportRequestDateGroup.classList.toggle('is-hidden', !showDateGroup);
      }

      if (transportRequestTimeGroup) {
        const showTimeGroup = Boolean(activeBuilderConfig && activeBuilderConfig.showTime);
        transportRequestTimeGroup.hidden = !showTimeGroup;
        transportRequestTimeGroup.classList.toggle('is-hidden', !showTimeGroup);
      }

      if (transportRequestBuilderSubmitButton) {
        const submissionAvailability = activeBuilderConfig
          ? canSubmitTransportRequest(transportUiState.requestBuilderKind)
          : { allowed: true, message: '' };
        const submitBlocked = Boolean(activeBuilderConfig) && !submissionAvailability.allowed;
        transportRequestBuilderSubmitButton.dataset.transportSubmitDisabled = submitBlocked ? 'true' : 'false';
        transportRequestBuilderSubmitButton.setAttribute('aria-disabled', String(submitBlocked));
        transportRequestBuilderSubmitButton.title = submitBlocked ? submissionAvailability.message : '';
      }

      transportRequestWeekdayOptions.forEach((optionElement) => {
        const weekdayValue = Number(optionElement.dataset.weekday);
        const showOption = Boolean(activeBuilderConfig && activeBuilderConfig.allowedWeekdays.includes(weekdayValue));
        optionElement.hidden = !showOption;
        optionElement.classList.toggle('is-hidden', !showOption);
      });

      transportUiState.detailRequestId = null;

      if (transportRequestHistorySection) {
        const showHistory = !transportUiState.addressEditorOpen;
        transportRequestHistorySection.hidden = !showHistory;
        transportRequestHistorySection.classList.toggle('is-hidden', !showHistory);
        if (showHistory) {
          renderTransportRequestSummaries();
        }
      }

      if (transportRealtimeRefreshPending) {
        requestTransportRealtimeRefresh();
      }

      scheduleTransportAutoRefresh();
    }

    function selectTransportRequest(requestId, options) {
      const selectedRequest = findTransportRequestById(requestId);
      if (!selectedRequest) {
        return;
      }

      const openDetails = Boolean(options && options.openDetails);
      transportUiState.selectedRequestId = selectedRequest.requestId;
      if (openDetails) {
        transportUiState.detailRequestId = selectedRequest.requestId;
      }
      syncSelectedTransportRequestState({ status: selectedRequest.status });
      renderTransportScreen();
      syncFormControlStates();
      if (openDetails && transportRequestDetailCloseButton) {
        window.requestAnimationFrame(() => {
          if (transportRequestDetailWidget && !transportRequestDetailWidget.hidden) {
            transportRequestDetailCloseButton.focus();
          }
        });
      }
    }

    function closeTransportAddressEditor() {
      transportUiState.addressEditorOpen = false;
      syncTransportAddressFormValues();
      renderTransportScreen();
    }

    function openTransportAddressEditor() {
      transportUiState.addressEditorOpen = true;
      transportUiState.detailRequestId = null;
      syncTransportAddressFormValues();
      renderTransportScreen();
      realignViewport();
    }

    function closeTransportScreen() {
      if (!transportScreen || !transportScreenBackdrop || transportScreen.hidden) {
        return;
      }

      stopTransportRealtimeUpdates();
      clearTransportAutoRefresh();
      dismissActiveKeyboard();
      transportScreen.hidden = true;
      transportScreenBackdrop.hidden = true;
      transportScreen.classList.add('is-hidden');
      transportScreenBackdrop.classList.add('is-hidden');
      transportUiState.addressEditorOpen = false;
      transportUiState.requestBuilderKind = null;
      transportUiState.detailRequestId = null;
      resetTransportRequestSwipeState();
      clearTransportInlineStatus();
      syncFormControlStates();
      realignViewport();
    }

    function openTransportScreen() {
      if (!transportScreen || !transportScreenBackdrop) {
        return;
      }

      if (!isApplicationUnlocked()) {
        setStatus(translateTransport('messages.accessRequiresAuthentication'), 'error');
        return;
      }

      transportUiState.addressEditorOpen = false;
      transportUiState.requestBuilderKind = null;
      transportUiState.detailRequestId = null;
      loadPersistedTransportRequestLocalState(getActiveChave());
      resetTransportRequestSwipeState();
      transportScreen.hidden = false;
      transportScreenBackdrop.hidden = false;
      transportScreen.classList.remove('is-hidden');
      transportScreenBackdrop.classList.remove('is-hidden');
      clearTransportAutoRefresh();
      clearTransportInlineStatus();
      syncTransportAddressFormValues();
      renderTransportScreen();
      syncFormControlStates();
      realignViewport();
      startTransportRealtimeUpdates();
      void loadTransportState();
    }

    async function fetchTransportStatePayload(chave) {
      const response = await fetch(`${transportStateEndpoint}?chave=${encodeURIComponent(chave)}`, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
        },
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw buildProtectedRequestError(response, payload);
      }
      return payload;
    }

    async function postTransportPayload(url, payload) {
      const response = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(payload),
      });
      const parsedPayload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw buildProtectedRequestError(response, parsedPayload);
      }
      return parsedPayload;
    }

    async function loadTransportState() {
      const normalizedChave = getActiveChave();
      if (normalizedChave.length !== 4 || !isApplicationUnlocked(normalizedChave)) {
        return null;
      }

      loadPersistedTransportRequestLocalState(normalizedChave);
      clearTransportAutoRefresh();
      setTransportStateLoading(true);
      clearTransportInlineStatus();
      syncFormControlStates();
      try {
        const payload = await fetchTransportStatePayload(normalizedChave);
        applyTransportStatePayload(payload);
        return payload;
      } catch (error) {
        if (error && error.isAuthExpired) {
          closeTransportScreen();
          return null;
        }
        setTransportInlineStatus(
          error instanceof Error ? localizeKnownApiMessage(error.message) : translateTransport('messages.loadFailed'),
          'error'
        );
        return null;
      } finally {
        setTransportStateLoading(false);
        renderTransportScreen();
        syncFormControlStates();
      }
    }

    async function submitTransportAddress(event) {
      event.preventDefault();
      const normalizedChave = getActiveChave();
      if (normalizedChave.length !== 4) {
        setTransportInlineStatus(translateTransport('messages.invalidKeyBeforeAddress'), 'error');
        return;
      }

      setTransportAddressSaveInProgress(true);
      clearTransportInlineStatus();
      syncFormControlStates();
      try {
        const payload = await postTransportPayload(transportAddressEndpoint, {
          chave: normalizedChave,
          end_rua: transportAddressInput.value,
          zip: transportZipInput.value,
        });
        applyTransportStatePayload(payload.state || {});
        closeTransportAddressEditor();
        setTransportInlineStatus(
          localizeKnownApiMessage(payload.message) || translateTransport('messages.addressUpdated'),
          'success'
        );
      } catch (error) {
        if (error && error.isAuthExpired) {
          closeTransportScreen();
          return;
        }
        setTransportInlineStatus(
          error instanceof Error ? localizeKnownApiMessage(error.message) : translateTransport('messages.addressUpdateFailed'),
          'error'
        );
      } finally {
        setTransportAddressSaveInProgress(false);
        syncFormControlStates();
      }
    }

    async function requestTransport(requestKind, requestPayload) {
      const normalizedChave = getActiveChave();
      const safeRequestPayload = requestPayload || {};
      const requestLabel = transportRequestKindLabels[requestKind] || translateTransport('detail.genericTitle');
      if (normalizedChave.length !== 4) {
        setTransportInlineStatus(translateTransport('messages.invalidKeyBeforeRequest'), 'error');
        return;
      }

      setTransportRequestInProgress(true);
      clearTransportInlineStatus();
      syncFormControlStates();
      try {
        const payload = await postTransportPayload(transportRequestEndpoint, {
          chave: normalizedChave,
          request_kind: requestKind,
          ...safeRequestPayload,
        });
        if (payload && payload.state && Array.isArray(payload.state.requests) && payload.state.requests.length > 0) {
          transportUiState.selectedRequestId = Number(payload.state.requests[0].request_id);
        } else if (payload && payload.state && payload.state.request_id !== null && payload.state.request_id !== undefined) {
          transportUiState.selectedRequestId = Number(payload.state.request_id);
        }
        applyTransportStatePayload(payload.state || {});
        clearTransportInlineStatus();
      } catch (error) {
        if (error && error.isAuthExpired) {
          closeTransportScreen();
          return;
        }
        setTransportInlineStatus(
          error instanceof Error
            ? localizeKnownApiMessage(error.message)
            : translateTransport('messages.requestFailed', { requestLabel }),
          'error'
        );
      } finally {
        setTransportRequestInProgress(false);
        syncFormControlStates();
      }
    }

    async function submitTransportRequestBuilder(event) {
      event.preventDefault();

      const requestKind = transportUiState.requestBuilderKind;
      if (!requestKind) {
        return;
      }

      const requestPayload = collectTransportRequestPayload(requestKind);
      if (!requestPayload) {
        return;
      }

      await requestTransport(requestKind, requestPayload);
    }

    async function cancelTransportRequest(requestId) {
      const normalizedChave = getActiveChave();
      const targetRequest = findTransportRequestById(requestId);
      if (!targetRequest || !targetRequest.requestId) {
        return;
      }

      setTransportCancelInProgress(true);
      clearTransportInlineStatus();
      syncFormControlStates();
      try {
        const payload = await postTransportPayload(transportCancelEndpoint, {
          chave: normalizedChave,
          request_id: targetRequest.requestId,
        });
        applyTransportStatePayload(payload.state || {});
        transportUiState.requestBuilderKind = null;
        setTransportInlineStatus(
          localizeKnownApiMessage(payload.message) || translateTransport('messages.cancelSuccess'),
          'success'
        );
      } catch (error) {
        if (error && error.isAuthExpired) {
          closeTransportScreen();
          return;
        }
        setTransportInlineStatus(
          error instanceof Error ? localizeKnownApiMessage(error.message) : translateTransport('messages.cancelFailed'),
          'error'
        );
      } finally {
        setTransportCancelInProgress(false);
        syncFormControlStates();
      }
    }

    function resetTransportState() {
      transportState.status = 'available';
      transportState.requestId = null;
      transportState.requestKind = null;
      transportState.routeKind = null;
      transportState.serviceDate = null;
      transportState.endRua = '';
      transportState.zip = '';
      transportState.requestedTime = '';
      transportState.boardingTime = '';
      transportState.confirmationDeadlineTime = '';
      transportState.vehicleType = '';
      transportState.vehiclePlate = '';
      transportState.toleranceMinutes = null;
      transportState.requests = [];
      transportUiState.addressEditorOpen = false;
      transportUiState.requestBuilderKind = null;
      transportUiState.selectedRequestId = null;
      transportUiState.detailRequestId = null;
      resetTransportRequestLocalState();
      resetTransportRequestSwipeState();
      clearTransportInlineStatus();
      renderTransportScreen();
    }

    return {
      applyPersistedTransportRequestLocalOverrides,
      applyTransportStatePayload,
      beginTransportRequestSwipe,
      canCancelTransportRequestItem,
      canDismissTransportRequestItem,
      canMarkTransportRequestAsRealized,
      closeTransportAddressEditor,
      closeTransportRequestBuilder,
      closeTransportRequestDetailWidget,
      closeTransportScreen,
      createTransportRequestCard,
      dismissTransportRequestCard,
      endTransportRequestSwipe,
      fetchTransportStatePayload,
      handleTransportRealtimeMessage,
      initializeTransportRequestBuilder,
      loadPersistedTransportRequestLocalState,
      loadTransportState,
      markTransportRequestAsRealized,
      normalizeTransportRequestStatusValue,
      openTransportAddressEditor,
      openTransportScreen,
      persistTransportRequestLocalState,
      postTransportPayload,
      renderTransportScreen,
      requestTransport,
      requestTransportRealtimeRefresh,
      resetTransportRequestSwipeState,
      resetTransportState,
      scheduleTransportAutoRefresh,
      selectTransportRequest,
      startTransportRealtimeUpdates,
      stopTransportRealtimeUpdates,
      submitTransportAddress,
      submitTransportRequestBuilder,
      updateTransportRequestSwipe,
    };
  }

  return {
    create: createTransportScreenModule,
  };
});
