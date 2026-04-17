(function () {
  const form = document.getElementById('checkForm');
  const submitEndpoint = form.dataset.submitEndpoint || '/api/web/check';
  const stateEndpoint = form.dataset.stateEndpoint || '/api/web/check/state';
  const locationsEndpoint = form.dataset.locationsEndpoint || '/api/web/check/locations';
  const locationEndpoint = form.dataset.locationEndpoint || '/api/web/check/location';
  const automaticActivities = window.CheckingWebAutomaticActivities;
  const clientState = window.CheckingWebClientState;
  const chaveInput = document.getElementById('chaveInput');
  const projectField = document.getElementById('projectField');
  const projectSelect = document.getElementById('projectSelect');
  const locationSelectField = document.getElementById('locationSelectField');
  const informeField = document.getElementById('informeField');
  const manualLocationSelect = document.getElementById('manualLocationSelect');
  const automaticActivitiesToggle = document.getElementById('automaticActivitiesToggle');
  const submitButton = document.getElementById('submitButton');
  const refreshLocationButton = document.getElementById('refreshLocationButton');
  const refreshLocationButtonLabel = refreshLocationButton.querySelector('.visually-hidden');
  const notificationLinePrimary = document.getElementById('notificationLinePrimary');
  const notificationLineSecondary = document.getElementById('notificationLineSecondary');
  const lastCheckinValue = document.getElementById('lastCheckinValue');
  const lastCheckoutValue = document.getElementById('lastCheckoutValue');
  const locationValue = document.getElementById('locationValue');
  const locationAccuracy = document.getElementById('locationAccuracy');

  const actionInputs = Array.from(document.querySelectorAll('input[name="action"]'));
  const formControls = Array.from(form.querySelectorAll('input, select, button:not(.choice-card-static)'));
  const storageKey = 'checking.web.user.chave';
  const userSettingsStorageKey = 'checking.web.user.settings.by-chave';
  const locationPromptAttemptedKey = 'checking.web.user.location.prompt-attempted';
  const locationPermissionGrantedKey = 'checking.web.user.location.permission-granted';
  const defaultManualLocationLabel = 'Escritório Principal';
  const allowedProjectValues = Array.from(projectSelect.options).map((option) => option.value);
  const defaultProjectValue = projectSelect.value;
  const lifecycleTriggerCooldownMs = 1200;
  const automaticCheckoutLocation = automaticActivities.AUTOMATIC_CHECKOUT_LOCATION;
  const geolocationOptions = {
    enableHighAccuracy: true,
    maximumAge: 0,
    timeout: 20000,
  };
  const weekdayFormatter = new Intl.DateTimeFormat('pt-BR', {
    weekday: 'long',
  });
  const dateFormatter = new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
  const timeFormatter = new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });

  let historyRequestToken = 0;
  let historyAbortController = null;
  let lastLifecycleTriggerAt = 0;
  let locationRequestPromise = null;
  let currentLocationMatch = null;
  let latestHistoryState = null;
  let availableLocations = [];
  let gpsLocationPermissionGranted = false;
  let lifecycleRefreshInProgress = false;
  let locationRefreshLoading = false;
  let submitInProgress = false;
  let userInteractionLockCount = 0;
  const notificationState = {
    message: '',
    tone: null,
  };

  function isStandaloneShortcutMode() {
    return Boolean(
      (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches)
        || window.navigator.standalone === true
    );
  }

  function getLocationPermissionContainerLabel() {
    return isStandaloneShortcutMode() ? 'neste atalho/app' : 'neste navegador';
  }

  function getLocationPromptSourceLabel() {
    return isStandaloneShortcutMode() ? 'pelo atalho/app' : 'pelo navegador';
  }

  function isUserInteractionLocked() {
    return userInteractionLockCount > 0;
  }

  function syncFormControlStates() {
    const lockActive = isUserInteractionLocked();

    formControls.forEach((control) => {
      if (control === manualLocationSelect) {
        control.disabled = lockActive || gpsLocationPermissionGranted || availableLocations.length === 0;
        return;
      }

      if (control === refreshLocationButton) {
        control.disabled = lockActive || locationRefreshLoading;
        return;
      }

      if (control === submitButton) {
        control.disabled = lockActive || submitInProgress;
        return;
      }

      control.disabled = lockActive;
    });

    const isBusy = lockActive || locationRefreshLoading || submitInProgress;
    form.classList.toggle('is-busy', isBusy);
    form.setAttribute('aria-busy', String(isBusy));
  }

  function lockUserInteraction() {
    userInteractionLockCount += 1;
    syncFormControlStates();
  }

  function unlockUserInteraction() {
    userInteractionLockCount = Math.max(0, userInteractionLockCount - 1);
    syncFormControlStates();
  }

  async function runWithLockedUserInteraction(callback) {
    lockUserInteraction();
    try {
      return await callback();
    } finally {
      unlockUserInteraction();
    }
  }

  function setLocationRefreshLoading(isLoading) {
    locationRefreshLoading = Boolean(isLoading);
    refreshLocationButton.classList.toggle('is-loading', locationRefreshLoading);
    refreshLocationButton.setAttribute('aria-busy', String(locationRefreshLoading));
    refreshLocationButton.setAttribute('aria-label', locationRefreshLoading ? 'Atualizando localização' : 'Atualizar localização');
    refreshLocationButton.setAttribute('title', locationRefreshLoading ? 'Atualizando localização' : 'Atualizar localização');
    if (refreshLocationButtonLabel) {
      refreshLocationButtonLabel.textContent = locationRefreshLoading ? 'Atualizando localização' : 'Atualizar localização';
    }
    syncFormControlStates();
  }

  function applyNotificationLine(element, message, tone) {
    element.textContent = message || '';
    element.classList.remove('is-success', 'is-error', 'is-warning', 'is-info');

    if (tone) {
      element.classList.add(`is-${tone}`);
    }
  }

  function getNotificationSplitLimit() {
    const viewportWidth = Math.max(window.innerWidth || 0, document.documentElement.clientWidth || 0);
    if (viewportWidth && viewportWidth <= 360) {
      return 34;
    }
    if (viewportWidth && viewportWidth <= 420) {
      return 40;
    }
    return 52;
  }

  function renderNotifications() {
    const splitMessage = clientState.splitNotificationMessage(
      notificationState.message,
      getNotificationSplitLimit()
    );
    applyNotificationLine(notificationLinePrimary, splitMessage.primary, notificationState.tone);
    applyNotificationLine(notificationLineSecondary, splitMessage.secondary, notificationState.tone);
  }

  function setNotificationMessage(_channel, message, tone) {
    if (!message) {
      return;
    }

    notificationState.message = message;
    notificationState.tone = tone || 'info';
    renderNotifications();
  }

  function clearNotification() {
    notificationState.message = '';
    notificationState.tone = null;
    renderNotifications();
  }

  function setSequenceStatus(message) {
    setNotificationMessage('form', message || '', 'info');
  }

  function describeAutomaticActivity(action) {
    return action === 'checkout' ? 'check-out' : 'check-in';
  }

  function buildLocationCompletionMessage(payload) {
    const detailMessage = payload && typeof payload.message === 'string'
      ? payload.message.trim()
      : '';

    if (!detailMessage) {
      return 'Atualização da localização concluída.';
    }

    return `Atualização da localização concluída. ${detailMessage}`;
  }

  function resolveLocationCompletionTone(payload) {
    const toneByStatus = {
      matched: 'success',
      accuracy_too_low: 'warning',
      not_in_known_location: 'info',
      outside_workplace: 'warning',
      no_known_locations: 'error',
    };

    return toneByStatus[payload && payload.status] || 'success';
  }

  function sanitizeChave(value) {
    return String(value || '')
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, '')
      .slice(0, 4);
  }

  function getSelectedValue(name) {
    const selected = document.querySelector(`input[name="${name}"]:checked`);
    return selected ? selected.value : '';
  }

  function setSelectedValue(name, value) {
    const selectedInput = document.querySelector(`input[name="${name}"][value="${value}"]`);
    if (!selectedInput) {
      return;
    }

    selectedInput.checked = true;
  }

  function getSelectedInformeValue() {
    return isAutomaticActivitiesEnabled() ? 'normal' : getSelectedValue('informe');
  }

  function parseErrorMessage(payload) {
    if (!payload) return 'Não foi possível concluir a operação.';
    if (typeof payload.detail === 'string') return payload.detail;
    if (Array.isArray(payload.detail)) {
      return payload.detail
        .map((entry) => entry.msg || entry.message || 'Erro de validação.')
        .join(' ');
    }
    if (typeof payload.message === 'string') return payload.message;
    return 'Não foi possível concluir a operação.';
  }

  function buildClientEventId() {
    const randomPart = Math.random().toString(36).slice(2, 10);
    return `web-check-${Date.now()}-${randomPart}`;
  }

  function formatMeters(value) {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      return '--';
    }
    return `${Math.round(value)} m`;
  }

  function readStorageFlag(key) {
    try {
      return window.localStorage.getItem(key) === '1';
    } catch {
      return false;
    }
  }

  function writeStorageFlag(key, value) {
    try {
      if (value) {
        window.localStorage.setItem(key, '1');
      } else {
        window.localStorage.removeItem(key);
      }
    } catch {
      // Ignore browsers with unavailable storage.
    }
  }

  function readPersistedUserSettingsMap() {
    try {
      const rawValue = window.localStorage.getItem(userSettingsStorageKey);
      if (!rawValue) {
        return {};
      }

      const parsedValue = JSON.parse(rawValue);
      return parsedValue && typeof parsedValue === 'object' ? parsedValue : {};
    } catch {
      return {};
    }
  }

  function writePersistedUserSettingsMap(settingsMap) {
    try {
      window.localStorage.setItem(userSettingsStorageKey, JSON.stringify(settingsMap));
    } catch {
      // Ignore browsers with unavailable storage.
    }
  }

  function resolveCurrentUserSettingsDefaults() {
    return {
      project: defaultProjectValue,
      automaticActivitiesEnabled: false,
      allowedProjects: allowedProjectValues,
    };
  }

  function applyPersistedUserSettings(chave) {
    const resolvedSettings = clientState.resolvePersistedUserSettings(
      readPersistedUserSettingsMap(),
      chave,
      resolveCurrentUserSettingsDefaults()
    );

    projectSelect.value = resolvedSettings.project;
    if (automaticActivitiesToggle) {
      automaticActivitiesToggle.checked = resolvedSettings.automaticActivitiesEnabled;
    }
  }

  function restorePersistedUserSettingsForChave(chave) {
    applyPersistedUserSettings(chave);
    syncProjectVisibility();
  }

  function persistCurrentUserSettings() {
    const normalizedChave = sanitizeChave(chaveInput.value);
    if (normalizedChave.length !== 4) {
      return;
    }

    const nextSettingsMap = clientState.withPersistedUserSettings(
      readPersistedUserSettingsMap(),
      normalizedChave,
      {
        project: projectSelect.value,
        automaticActivitiesEnabled: Boolean(
          automaticActivitiesToggle && automaticActivitiesToggle.checked
        ),
      },
      resolveCurrentUserSettingsDefaults()
    );
    writePersistedUserSettingsMap(nextSettingsMap);
  }

  function setLocationPresentation(label, message, tone, accuracyText, options) {
    const settings = options || {};

    locationValue.textContent = label || '--';
    locationAccuracy.textContent = accuracyText || '--';
    locationValue.classList.remove('is-error', 'is-success', 'is-warning', 'is-info', 'is-muted');

    if (tone) {
      locationValue.classList.add(`is-${tone}`);
    }

    if (!settings.suppressNotification) {
      setNotificationMessage('location', message || '', tone || 'info');
    }

    syncManualLocationControl();
  }

  function setResolvedLocation(matchPayload) {
    currentLocationMatch = matchPayload && matchPayload.matched ? matchPayload : null;
  }

  function setLocationWithoutPermission() {
    writeStorageFlag(locationPermissionGrantedKey, false);
    setResolvedLocation(null);
    setGpsLocationPermissionGranted(false);
    setLocationPresentation('Sem Permissão', '', null, '--', { suppressNotification: true });
  }

  function isAutomaticActivitiesEnabled() {
    return Boolean(automaticActivitiesToggle && automaticActivitiesToggle.checked);
  }

  function isCheckoutZoneLocationName(value) {
    return automaticActivities.isCheckoutZoneLocationName(value);
  }

  function resolveLastRecordedAction(state) {
    return automaticActivities.resolveLastRecordedAction(state);
  }

  function resolveRecordedCheckInLocation(state) {
    return automaticActivities.resolveRecordedCheckInLocation(state);
  }

  function fetchWebState(chave) {
    return fetch(`${stateEndpoint}?chave=${encodeURIComponent(chave)}`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
    }).then(async (response) => {
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(parseErrorMessage(payload));
      }
      return payload;
    });
  }

  function shouldAttemptAutomaticLocationEvent(locationPayload, remoteState) {
    return automaticActivities.shouldAttemptAutomaticLocationEvent(locationPayload, remoteState);
  }

  function shouldAttemptAutomaticOutOfRangeCheckout(locationPayload, remoteState) {
    return automaticActivities.shouldAttemptAutomaticOutOfRangeCheckout(locationPayload, remoteState);
  }

  async function submitAutomaticActivity({ action, local, suppressStatus }) {
    const chave = sanitizeChave(chaveInput.value);
    const response = await fetch(submitEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chave,
        projeto: projectSelect.value,
        action,
        local,
        informe: getSelectedInformeValue(),
        event_time: new Date().toISOString(),
        client_event_id: buildClientEventId(),
      }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(parseErrorMessage(payload));
    }

    if (payload && payload.state) {
      latestHistoryState = payload.state;
      applyHistoryState(payload.state);
    }

    if (!suppressStatus) {
      setStatus(
        action === 'checkin'
          ? 'Check-In automático concluído.'
          : (
              isCheckoutZoneLocationName(local)
                ? 'Check-Out automático concluído.'
                : 'Check-Out automático concluído.'
            ),
        'success'
      );
    }

    return payload;
  }

  async function runAutomaticActivitiesIfNeeded(locationPayload, options) {
    const settings = options || {};
    const noActivityResult = {
      performed: false,
      action: null,
      local: null,
    };

    if (!isAutomaticActivitiesEnabled() || !gpsLocationPermissionGranted) {
      return noActivityResult;
    }

    const chave = sanitizeChave(chaveInput.value);
    if (chave.length !== 4) {
      return noActivityResult;
    }

    const remoteState = await fetchWebState(chave);
    latestHistoryState = remoteState;
    applyHistoryState(remoteState);

    if (locationPayload && locationPayload.matched && shouldAttemptAutomaticLocationEvent(locationPayload, remoteState)) {
      const automaticAction = isCheckoutZoneLocationName(locationPayload.resolved_local) ? 'checkout' : 'checkin';
      await submitAutomaticActivity({
        action: automaticAction,
        local: locationPayload.resolved_local,
        suppressStatus: settings.suppressStatus,
      });
      return {
        performed: true,
        action: automaticAction,
        local: locationPayload.resolved_local,
      };
    }

    if (
      locationPayload
      && !locationPayload.matched
      && shouldAttemptAutomaticOutOfRangeCheckout(locationPayload, remoteState)
    ) {
      await submitAutomaticActivity({
        action: 'checkout',
        local: automaticCheckoutLocation,
        suppressStatus: settings.suppressStatus,
      });
      return {
        performed: true,
        action: 'checkout',
        local: automaticCheckoutLocation,
      };
    }

    return noActivityResult;
  }

  function buildAccuracyText(accuracyMeters, thresholdMeters) {
    if (typeof accuracyMeters !== 'number' || !Number.isFinite(accuracyMeters)) {
      return thresholdMeters ? `Limite ${Math.round(thresholdMeters)} m` : '--';
    }
    if (typeof thresholdMeters !== 'number' || !Number.isFinite(thresholdMeters)) {
      return `Precisão ${formatMeters(accuracyMeters)}`;
    }
    return `Precisão ${formatMeters(accuracyMeters)} / Limite ${Math.round(thresholdMeters)} m`;
  }

  function setGpsLocationPermissionGranted(value) {
    gpsLocationPermissionGranted = Boolean(value);
    syncManualLocationControl();
  }

  function getDefaultManualLocation() {
    if (availableLocations.includes(defaultManualLocationLabel)) {
      return defaultManualLocationLabel;
    }

    return availableLocations[0] || '';
  }

  function setLocationSelectOptions(values, selectedValue, options) {
    const settings = options || {};
    const nextValues = Array.from(values || []);
    if (settings.allowTemporaryValue && selectedValue && !nextValues.includes(selectedValue)) {
      nextValues.unshift(selectedValue);
    }

    const placeholder = settings.placeholder || '';
    manualLocationSelect.replaceChildren();

    if (!nextValues.length) {
      const emptyOption = document.createElement('option');
      emptyOption.value = '';
      emptyOption.textContent = placeholder || 'Sem localizações cadastradas';
      manualLocationSelect.append(emptyOption);
      manualLocationSelect.value = '';
      return;
    }

    nextValues.forEach((value) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = value;
      manualLocationSelect.append(option);
    });

    if (selectedValue && nextValues.includes(selectedValue)) {
      manualLocationSelect.value = selectedValue;
      return;
    }

    manualLocationSelect.value = nextValues[0];
  }

  function syncManualLocationControl() {
    const displayedLocation = (locationValue.textContent || '').trim();

    if (gpsLocationPermissionGranted) {
      setLocationSelectOptions(availableLocations, displayedLocation || getDefaultManualLocation(), {
        allowTemporaryValue: true,
        placeholder: displayedLocation || 'Aguardando localização.',
      });
      syncFormControlStates();
      return;
    }

    const nextManualValue = availableLocations.includes(manualLocationSelect.value)
      ? manualLocationSelect.value
      : getDefaultManualLocation();
    setLocationSelectOptions(availableLocations, nextManualValue, {
      placeholder: 'Sem localizações cadastradas',
    });
    syncFormControlStates();
  }

  async function loadManualLocations() {
    try {
      const response = await fetch(locationsEndpoint, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(parseErrorMessage(payload));
      }

      availableLocations = Array.from(
        new Set(
          Array.isArray(payload.items)
            ? payload.items.filter((item) => typeof item === 'string' && item.trim())
            : []
        )
      );
    } catch {
      availableLocations = [];
    }

    syncManualLocationControl();
  }

  async function queryLocationPermissionState() {
    if (!navigator.permissions || typeof navigator.permissions.query !== 'function') {
      return null;
    }

    try {
      const permissionStatus = await navigator.permissions.query({ name: 'geolocation' });
      return permissionStatus && typeof permissionStatus.state === 'string'
        ? permissionStatus.state
        : null;
    } catch {
      return null;
    }
  }

  function requestCurrentPosition() {
    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, geolocationOptions);
    });
  }

  async function matchCurrentPosition(position) {
    const response = await fetch(locationEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy_meters:
          typeof position.coords.accuracy === 'number' && Number.isFinite(position.coords.accuracy)
            ? position.coords.accuracy
            : null,
      }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(parseErrorMessage(payload));
    }

    return payload;
  }

  function applyLocationMatch(payload, options) {
    const toneByStatus = {
      matched: 'success',
      accuracy_too_low: 'warning',
      not_in_known_location: 'muted',
      outside_workplace: 'warning',
      no_known_locations: 'error',
    };
    const accuracyText = buildAccuracyText(payload.accuracy_meters, payload.accuracy_threshold_meters);
    const locationMessage = payload.status === 'matched' ? '' : payload.message;
    setResolvedLocation(payload);
    setLocationPresentation(
      payload.label,
      locationMessage,
      toneByStatus[payload.status] || null,
      accuracyText,
      options
    );
  }

  function applyLocationBrowserError(error, options) {
    setResolvedLocation(null);

    if (!error || typeof error.code !== 'number') {
      setLocationPresentation(
        'Localização indisponível',
        'Não foi possível consultar a localização neste momento.',
        'error',
        '--',
        options
      );
      return;
    }

    if (error.code === 1) {
      setLocationWithoutPermission();
      return;
    }

    if (error.code === 2) {
      setLocationPresentation(
        'Localização indisponível',
        'Não foi possível obter uma posição válida do aparelho.',
        'error',
        '--',
        options
      );
      return;
    }

    if (error.code === 3) {
      setLocationPresentation(
        'Tempo esgotado',
        'A busca pela localização demorou mais do que o esperado.',
        'warning',
        '--',
        options
      );
      return;
    }

    setLocationPresentation(
      'Localização indisponível',
      'Não foi possível consultar a localização neste momento.',
      'error',
      '--',
      options
    );
  }

  async function resolveCurrentLocation(options) {
    const settings = options || {};
    const suppressNotification = Boolean(settings.suppressNotification);
    if (!window.isSecureContext || !navigator.geolocation) {
      setResolvedLocation(null);
      setLocationPresentation(
        'Indisponível',
        suppressNotification
          ? ''
          : 'A captura de localização requer HTTPS e suporte do navegador.',
        'error',
        '--',
        { suppressNotification }
      );
      return null;
    }

    if (locationRequestPromise && !settings.forceRefresh) {
      return locationRequestPromise;
    }

    if (settings.interactive) {
      writeStorageFlag(locationPromptAttemptedKey, true);
    }

    const pendingRequest = (async () => {
      setLocationRefreshLoading(true);

      if (settings.showDetectingState) {
        setLocationPresentation(
          'Detectando...',
          settings.interactive
            ? `Aguardando a confirmação da localização exata ${getLocationPromptSourceLabel()}.`
            : 'Atualizando a localização atual do aparelho.',
          null,
          '--',
          { suppressNotification }
        );
      }

      const permissionState = await queryLocationPermissionState();
      const shouldAttemptLookup = clientState.shouldAttemptSilentLocationLookup(
        permissionState,
        readStorageFlag(locationPermissionGrantedKey)
      );

      if (!shouldAttemptLookup) {
        setLocationWithoutPermission();
        return null;
      }

      try {
        const position = await requestCurrentPosition();
        writeStorageFlag(locationPermissionGrantedKey, true);
        setGpsLocationPermissionGranted(true);
        const matchPayload = await matchCurrentPosition(position);
        applyLocationMatch(matchPayload, { suppressNotification });
        if (settings.showCompletionStatus) {
          setStatus(
            buildLocationCompletionMessage(matchPayload),
            resolveLocationCompletionTone(matchPayload)
          );
        }
        return matchPayload;
      } catch (error) {
        applyLocationBrowserError(error, { suppressNotification });
        return null;
      }
    })();

    locationRequestPromise = pendingRequest;
    try {
      return await pendingRequest;
    } finally {
      if (locationRequestPromise === pendingRequest) {
        locationRequestPromise = null;
      }
      setLocationRefreshLoading(false);
    }
  }

  async function captureAndResolveLocation(options) {
    const settings = options || {};
    return resolveCurrentLocation({
      interactive: Boolean(settings.interactive),
      forceRefresh: Boolean(settings.forceRefresh),
      showCompletionStatus: Boolean(settings.showCompletionStatus),
      suppressNotification: Boolean(settings.suppressNotification),
      showDetectingState: settings.showDetectingState !== false,
    });
  }

  async function updateLocationForLifecycleSequence(options) {
    const settings = options || {};
    return resolveCurrentLocation({
      interactive: false,
      forceRefresh: Boolean(settings.forceRefresh),
      suppressNotification: settings.suppressNotification !== false,
      showDetectingState: Boolean(settings.showDetectingState),
    });
  }

  async function ensureLocationReadyForSubmit() {
    if (locationRequestPromise) {
      await locationRequestPromise;
      return;
    }

    const permissionState = await queryLocationPermissionState();
    if (
      clientState.shouldAttemptSilentLocationLookup(
        permissionState,
        readStorageFlag(locationPermissionGrantedKey)
      )
    ) {
      await captureAndResolveLocation({ interactive: false, forceRefresh: true });
    }
  }

  function readPersistedChave() {
    try {
      return sanitizeChave(window.localStorage.getItem(storageKey) || '');
    } catch {
      return '';
    }
  }

  function writePersistedChave(chave) {
    const sanitized = sanitizeChave(chave);
    try {
      if (sanitized) {
        window.localStorage.setItem(storageKey, sanitized);
      } else {
        window.localStorage.removeItem(storageKey);
      }
    } catch {
      // Ignore browsers with unavailable storage.
    }
  }

  function setStatus(message, tone) {
    setNotificationMessage('form', message || '', tone || 'info');
  }

  function setSubmitting(isSubmitting) {
    submitInProgress = Boolean(isSubmitting);
    submitButton.textContent = submitInProgress ? 'Enviando...' : 'Registrar';
    syncFormControlStates();
  }

  function setHistoryMessage(message, tone) {
    setNotificationMessage('history', message || '', tone || 'info');
  }

  function formatHistoryValue(value) {
    const parsed = parseHistoryTimestamp(value);
    if (!parsed) {
      return null;
    }

    return {
      weekday: weekdayFormatter.format(parsed),
      date: dateFormatter.format(parsed),
      time: timeFormatter.format(parsed),
    };
  }

  function parseHistoryTimestamp(value) {
    if (!value) {
      return null;
    }

    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function setSelectedAction(action) {
    const selectedInput = actionInputs.find((input) => input.value === action);
    if (!selectedInput) {
      return;
    }

    selectedInput.checked = true;
    syncProjectVisibility();
  }

  function applySuggestedActionFromHistory(state) {
    const lastCheckinAt = parseHistoryTimestamp(state && state.last_checkin_at);
    const lastCheckoutAt = parseHistoryTimestamp(state && state.last_checkout_at);

    if (lastCheckinAt && lastCheckoutAt) {
      setSelectedAction(lastCheckinAt >= lastCheckoutAt ? 'checkout' : 'checkin');
      return;
    }

    if (lastCheckinAt) {
      setSelectedAction('checkout');
      return;
    }

    if (lastCheckoutAt) {
      setSelectedAction('checkin');
      return;
    }

    setSelectedAction('checkin');
  }

  function renderHistoryValue(element, value) {
    const formatted = formatHistoryValue(value);
    element.replaceChildren();

    if (!formatted) {
      element.textContent = '--';
      return;
    }

    [
      ['history-weekday', formatted.weekday],
      ['history-date', formatted.date],
      ['history-time', formatted.time],
    ].forEach(([className, text]) => {
      const span = document.createElement('span');
      span.className = className;
      span.textContent = text;
      element.append(span);
    });
  }

  function applyHistoryState(state) {
    latestHistoryState = state;
    renderHistoryValue(lastCheckinValue, state && state.last_checkin_at);
    renderHistoryValue(lastCheckoutValue, state && state.last_checkout_at);
    applySuggestedActionFromHistory(state);
  }

  function resetHistory(message) {
    applyHistoryState(null);
    setHistoryMessage(message || 'Digite sua chave Petrobras para visualizar seu histórico.');
  }

  async function refreshHistory(chave, options) {
    const settings = options || {};
    const normalized = sanitizeChave(chave);

    if (historyAbortController) {
      historyAbortController.abort();
      historyAbortController = null;
    }

    if (normalized.length !== 4) {
      resetHistory('Digite sua chave Petrobras para visualizar seu histórico.');
      return;
    }

    const requestToken = ++historyRequestToken;
    const controller = new AbortController();
    historyAbortController = controller;
    if (settings.showLoadingMessage !== false && !settings.suppressMessages) {
      setHistoryMessage('Consultando histórico...', 'info');
    }

    try {
      const response = await fetch(`${stateEndpoint}?chave=${encodeURIComponent(normalized)}`, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
        signal: controller.signal,
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(parseErrorMessage(payload));
      }

      if (requestToken !== historyRequestToken) {
        return;
      }

      applyHistoryState(payload);
      if (!payload.found) {
        if (!settings.suppressMessages) {
          setHistoryMessage('Nenhum registro encontrado para esta chave.');
        } else {
          setHistoryMessage('');
        }
        return payload;
      }

      if (!payload.last_checkin_at && !payload.last_checkout_at) {
        if (!settings.suppressMessages) {
          setHistoryMessage('Nenhum check-in ou check-out registrado para esta chave.');
        } else {
          setHistoryMessage('');
        }
        return payload;
      }

      if (!settings.silentSuccessMessage && !settings.suppressMessages) {
        setHistoryMessage('Histórico atualizado para a chave informada.', 'success');
      } else {
        setHistoryMessage('');
      }
      return payload;
    } catch (error) {
      if (controller.signal.aborted) {
        return null;
      }

      applyHistoryState(null);
      if (!settings.suppressMessages) {
        setHistoryMessage('Não foi possível consultar o histórico desta chave.', 'error');
      } else {
        setHistoryMessage('');
      }

      if (settings.rethrowErrors) {
        throw error;
      }

      return null;
    } finally {
      if (historyAbortController === controller) {
        historyAbortController = null;
      }
    }
  }

  async function runLifecycleUpdateSequence(options) {
    const settings = options || {};
    if (isUserInteractionLocked() && !settings.allowWhileLocked) {
      return false;
    }

    const normalized = sanitizeChave(chaveInput.value);
    if (normalized.length !== 4) {
      return false;
    }

    const now = Date.now();
    if (!settings.ignoreCooldown && now - lastLifecycleTriggerAt < lifecycleTriggerCooldownMs) {
      return false;
    }

    if (lifecycleRefreshInProgress) {
      return false;
    }

    lastLifecycleTriggerAt = now;
    lifecycleRefreshInProgress = true;

    try {
      setSequenceStatus('Atualizando as atividades.....');
      await refreshHistory(normalized, {
        showLoadingMessage: false,
        silentSuccessMessage: true,
        suppressMessages: true,
        rethrowErrors: true,
      });

      setSequenceStatus('Atualizando a localização.....');
      const locationPayload = await updateLocationForLifecycleSequence();

      if (isAutomaticActivitiesEnabled()) {
        setSequenceStatus('Realizando check-in ou check-out, se aplicável.....');
        await runAutomaticActivitiesIfNeeded(locationPayload, { suppressStatus: true });
      }

      restorePersistedUserSettingsForChave(normalized);
      setNotificationMessage('history', '', null);
      setNotificationMessage('location', '', null);
      setStatus('Aplicação atualizada com sucesso.', 'success');
      return true;
    } catch (error) {
      const message = error instanceof Error
        ? error.message
        : 'Não foi possível atualizar a aplicação neste momento.';
      setNotificationMessage('history', '', null);
      setNotificationMessage('location', '', null);
      setStatus(message, 'error');
      return false;
    } finally {
      lifecycleRefreshInProgress = false;
    }
  }

  async function runManualLocationRefreshSequence() {
    if (isUserInteractionLocked()) {
      return;
    }

    await runWithLockedUserInteraction(async () => {
      await resolveCurrentLocation({
        interactive: true,
        forceRefresh: true,
        showDetectingState: true,
        showCompletionStatus: true,
        suppressNotification: false,
      });
    });
  }

  async function runAutomaticActivitiesEnableSequence() {
    const normalizedChave = sanitizeChave(chaveInput.value);
    if (normalizedChave.length !== 4) {
      setStatus('Informe uma chave com 4 caracteres alfanuméricos.', 'error');
      return;
    }

    await runWithLockedUserInteraction(async () => {
      try {
        setStatus('Atualização em andamento.', 'info');

        const locationPayload = await resolveCurrentLocation({
          interactive: true,
          forceRefresh: true,
          showDetectingState: true,
          showCompletionStatus: false,
          suppressNotification: true,
        });
        const automaticActivityResult = await runAutomaticActivitiesIfNeeded(locationPayload, {
          suppressStatus: true,
        });

        if (automaticActivityResult.performed) {
          setStatus(
            `Atualizações concluídas com ${describeAutomaticActivity(automaticActivityResult.action)} realizado.`,
            'success'
          );
          return;
        }

        setStatus('Atualizações concluídas sem atividades realizadas.', 'success');
      } catch (error) {
        const message = error instanceof Error
          ? error.message
          : 'Não foi possível concluir as atualizações automáticas neste momento.';
        setStatus(message, 'error');
      }
    });
  }

  function syncProjectVisibility() {
    const isCheckIn = getSelectedValue('action') === 'checkin';
    projectField.classList.toggle('is-hidden', !isCheckIn);
    projectField.setAttribute('aria-hidden', String(!isCheckIn));
    locationSelectField.classList.toggle('is-hidden', !isCheckIn);
    locationSelectField.setAttribute('aria-hidden', String(!isCheckIn));

    if (informeField) {
      const hideInforme = isAutomaticActivitiesEnabled();
      informeField.classList.toggle('is-hidden', hideInforme);
      informeField.setAttribute('aria-hidden', String(hideInforme));
      if (hideInforme) {
        setSelectedValue('informe', 'normal');
      }
    }
  }

  function syncAutomaticActivitiesToggle() {
    restorePersistedUserSettingsForChave(chaveInput.value);
  }

  chaveInput.addEventListener('input', () => {
    const sanitized = sanitizeChave(chaveInput.value);
    if (sanitized !== chaveInput.value) {
      chaveInput.value = sanitized;
    }
    writePersistedChave(sanitized);

    if (sanitized.length === 4) {
      restorePersistedUserSettingsForChave(sanitized);
      void runLifecycleUpdateSequence({ ignoreCooldown: true });
      return;
    }

    setNotificationMessage('form', '', null);
    setNotificationMessage('location', '', null);
    resetHistory('Digite sua chave Petrobras para visualizar seu histórico.');
  });

  actionInputs.forEach((input) => {
    input.addEventListener('change', syncProjectVisibility);
  });

  projectSelect.addEventListener('change', () => {
    persistCurrentUserSettings();
    setStatus('Atualização do projeto concluída.', 'success');
  });

  if (automaticActivitiesToggle) {
    automaticActivitiesToggle.addEventListener('change', () => {
      persistCurrentUserSettings();
      syncProjectVisibility();
      if (automaticActivitiesToggle.checked) {
        void runAutomaticActivitiesEnableSequence();
        return;
      }

      setStatus('Atividades automáticas desabilitadas.', 'success');
    });
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      void runLifecycleUpdateSequence();
    }
  });

  window.addEventListener('focus', () => {
    void runLifecycleUpdateSequence();
  });
  window.addEventListener('pageshow', () => {
    void runLifecycleUpdateSequence();
  });

  refreshLocationButton.addEventListener('click', () => {
    void runManualLocationRefreshSequence();
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const chave = sanitizeChave(chaveInput.value);
    const selectedAction = getSelectedValue('action');
    chaveInput.value = chave;

    if (chave.length !== 4) {
      setStatus('Informe uma chave com 4 caracteres alfanuméricos.', 'error');
      chaveInput.focus();
      return;
    }

    if (!gpsLocationPermissionGranted && !manualLocationSelect.value) {
      setStatus('Selecione uma localização antes de registrar.', 'error');
      manualLocationSelect.focus();
      return;
    }

    setSubmitting(true);
    setStatus('');

    try {
      await ensureLocationReadyForSubmit();

      const response = await fetch(submitEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chave,
          projeto: projectSelect.value,
          action: selectedAction,
          local: gpsLocationPermissionGranted
            ? (currentLocationMatch ? currentLocationMatch.resolved_local : null)
            : manualLocationSelect.value,
          informe: getSelectedInformeValue(),
          event_time: new Date().toISOString(),
          client_event_id: buildClientEventId(),
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(parseErrorMessage(payload));
      }

      writePersistedChave(chave);
      if (payload && payload.state) {
        applyHistoryState(payload.state);
      }
      setStatus(
        selectedAction === 'checkout' ? 'Check-Out concluído.' : 'Check-In concluído.',
        'success'
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Falha de comunicação com a API.';
      setStatus(message, 'error');
    } finally {
      setSubmitting(false);
    }
  });

  syncProjectVisibility();
  syncAutomaticActivitiesToggle();
  syncManualLocationControl();
  syncFormControlStates();
  void loadManualLocations();

  const persistedChave = readPersistedChave();
  if (persistedChave) {
    chaveInput.value = persistedChave;
    restorePersistedUserSettingsForChave(persistedChave);
    void runLifecycleUpdateSequence({ ignoreCooldown: true });
  } else {
    resetHistory('Digite sua chave Petrobras para visualizar seu histórico.');
  }
})();