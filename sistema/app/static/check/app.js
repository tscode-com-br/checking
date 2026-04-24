(function () {
  const form = document.getElementById('checkForm');
  const appBody = document.body;
  const appHeader = document.querySelector('body > header');
  const appShell = document.querySelector('main.check-shell');
  const orientationLockScreen = document.getElementById('orientationLockScreen');
  const authStatusEndpoint = form.dataset.authStatusEndpoint || '/api/web/auth/status';
  const authRegisterEndpoint = form.dataset.authRegisterEndpoint || '/api/web/auth/register-password';
  const authUserRegisterEndpoint = form.dataset.authUserRegisterEndpoint || '/api/web/auth/register-user';
  const authLoginEndpoint = form.dataset.authLoginEndpoint || '/api/web/auth/login';
  const authChangeEndpoint = form.dataset.authChangeEndpoint || '/api/web/auth/change-password';
  const authLogoutEndpoint = form.dataset.authLogoutEndpoint || '/api/web/auth/logout';
  const transportStateEndpoint = form.dataset.transportStateEndpoint || '/api/web/transport/state';
  const transportStreamEndpoint = form.dataset.transportStreamEndpoint || '/api/web/transport/stream';
  const transportAddressEndpoint = form.dataset.transportAddressEndpoint || '/api/web/transport/address';
  const transportRequestEndpoint = form.dataset.transportRequestEndpoint || '/api/web/transport/request';
  const transportCancelEndpoint = form.dataset.transportCancelEndpoint || '/api/web/transport/cancel';
  const transportAcknowledgeEndpoint = form.dataset.transportAckEndpoint || '/api/web/transport/acknowledge';
  const submitEndpoint = form.dataset.submitEndpoint || '/api/web/check';
  const stateEndpoint = form.dataset.stateEndpoint || '/api/web/check/state';
  const projectsEndpoint = form.dataset.projectsEndpoint || '/api/web/projects';
  const projectUpdateEndpoint = form.dataset.projectUpdateEndpoint || '/api/web/project';
  const locationsEndpoint = form.dataset.locationsEndpoint || '/api/web/check/locations';
  const locationEndpoint = form.dataset.locationEndpoint || '/api/web/check/location';
  const automaticActivities = window.CheckingWebAutomaticActivities;
  const clientState = window.CheckingWebClientState;
  const chaveInput = document.getElementById('chaveInput');
  const passwordInput = document.getElementById('passwordInput');
  const passwordActionButton = document.getElementById('passwordActionButton');
  const requestRegistrationButton = document.getElementById('requestRegistrationButton');
  const chaveAuthField = chaveInput ? chaveInput.closest('.auth-field') : null;
  const passwordAuthField = passwordInput ? passwordInput.closest('.auth-field') : null;
  const projectField = document.getElementById('projectField');
  const projectSelect = document.getElementById('projectSelect');
  const locationSelectField = document.getElementById('locationSelectField');
  const informeField = document.getElementById('informeField');
  const manualLocationSelect = document.getElementById('manualLocationSelect');
  const automaticActivitiesField = document.getElementById('automaticActivitiesField');
  const automaticActivitiesToggle = document.getElementById('automaticActivitiesToggle');
  const transportButton = document.getElementById('transportButton');
  const submitButton = document.getElementById('submitButton');
  const refreshLocationButton = document.getElementById('refreshLocationButton');
  const refreshLocationButtonLabel = refreshLocationButton.querySelector('.visually-hidden');
  const notificationLinePrimary = document.getElementById('notificationLinePrimary');
  const notificationLineSecondary = document.getElementById('notificationLineSecondary');
  const lastCheckinValue = document.getElementById('lastCheckinValue');
  const lastCheckoutValue = document.getElementById('lastCheckoutValue');
  const lastCheckinItem = lastCheckinValue ? lastCheckinValue.closest('.history-item') : null;
  const lastCheckoutItem = lastCheckoutValue ? lastCheckoutValue.closest('.history-item') : null;
  const locationValue = document.getElementById('locationValue');
  const locationAccuracy = document.getElementById('locationAccuracy');
  const passwordDialog = document.getElementById('passwordDialog');
  const passwordDialogBackdrop = document.getElementById('passwordDialogBackdrop');
  const passwordDialogTitle = document.getElementById('passwordDialogTitle');
  const passwordChangeForm = document.getElementById('passwordChangeForm');
  const passwordDialogOldPasswordField = document.getElementById('passwordDialogOldPasswordField');
  const oldPasswordInput = document.getElementById('oldPasswordInput');
  const newPasswordInput = document.getElementById('newPasswordInput');
  const confirmPasswordInput = document.getElementById('confirmPasswordInput');
  const passwordDialogBackButton = document.getElementById('passwordDialogBackButton');
  const passwordDialogSubmitButton = document.getElementById('passwordDialogSubmitButton');
  const registrationDialog = document.getElementById('registrationDialog');
  const registrationDialogBackdrop = document.getElementById('registrationDialogBackdrop');
  const registrationForm = document.getElementById('registrationForm');
  const registrationChaveInput = document.getElementById('registrationChaveInput');
  const registrationNameInput = document.getElementById('registrationNameInput');
  const registrationProjectSelect = document.getElementById('registrationProjectSelect');
  const registrationEmailInput = document.getElementById('registrationEmailInput');
  const registrationPasswordInput = document.getElementById('registrationPasswordInput');
  const registrationConfirmPasswordInput = document.getElementById('registrationConfirmPasswordInput');
  const registrationDialogBackButton = document.getElementById('registrationDialogBackButton');
  const registrationDialogSubmitButton = document.getElementById('registrationDialogSubmitButton');
  const transportScreen = document.getElementById('transportScreen');
  const transportScreenBackdrop = document.getElementById('transportScreenBackdrop');
  const transportScreenHeaderBackButton = document.getElementById('transportScreenHeaderBackButton');
  const transportAddressToggleButton = document.getElementById('transportAddressToggleButton');
  const transportAddressSummaryValue = document.getElementById('transportAddressSummaryValue');
  const transportAddressEditor = document.getElementById('transportAddressEditor');
  const transportAddressForm = document.getElementById('transportAddressForm');
  const transportAddressInput = document.getElementById('transportAddressInput');
  const transportZipInput = document.getElementById('transportZipInput');
  const transportAddressBackButton = document.getElementById('transportAddressBackButton');
  const transportAddressSubmitButton = document.getElementById('transportAddressSubmitButton');
  const transportOptionButtons = document.getElementById('transportOptionButtons');
  const transportRegularButton = document.getElementById('transportRegularButton');
  const transportWeekendButton = document.getElementById('transportWeekendButton');
  const transportExtraButton = document.getElementById('transportExtraButton');
  const transportRequestBuilderPanel = document.getElementById('transportRequestBuilderPanel');
  const transportRequestBuilderSubtitle = document.getElementById('transportRequestBuilderSubtitle');
  const transportRequestBuilderForm = document.getElementById('transportRequestBuilderForm');
  const transportRequestWeekdayGroup = document.getElementById('transportRequestWeekdayGroup');
  const transportRequestDateGroup = document.getElementById('transportRequestDateGroup');
  const transportRequestTimeGroup = document.getElementById('transportRequestTimeGroup');
  const transportRequestDateInput = document.getElementById('transportRequestDateInput');
  const transportRequestTimeInput = document.getElementById('transportRequestTimeInput');
  const transportRequestBuilderBackButton = document.getElementById('transportRequestBuilderBackButton');
  const transportRequestBuilderSubmitButton = document.getElementById('transportRequestBuilderSubmitButton');
  const transportRequestWeekdayInputs = Array.from(document.querySelectorAll('input[name="transport_selected_weekday"]'));
  const transportRequestWeekdayOptions = Array.from(document.querySelectorAll('[data-transport-weekday-option]'));
  const transportRequestHistorySection = document.getElementById('transportRequestHistorySection');
  const transportRequestHistoryList = document.getElementById('transportRequestHistoryList');
  const transportAcknowledgementSection = document.getElementById('transportAcknowledgementSection');
  const transportAcknowledgementCheckbox = document.getElementById('transportAcknowledgementCheckbox');
  const transportAcknowledgementButton = document.getElementById('transportAcknowledgementButton');
  const transportRequestDetailWidget = document.getElementById('transportRequestDetailWidget');
  const transportRequestDetailBackdrop = document.getElementById('transportRequestDetailBackdrop');
  const transportRequestDetailTitle = document.getElementById('transportRequestDetailWidgetTitle');
  const transportRequestDetailContent = document.getElementById('transportRequestDetailContent');
  const transportRequestDetailCloseButton = document.getElementById('transportRequestDetailCloseButton');
  const transportInlineStatus = document.getElementById('transportInlineStatus');

  const actionInputs = Array.from(document.querySelectorAll('input[name="action"]'));
  const informeInputs = Array.from(document.querySelectorAll('input[name="informe"]'));
  const processControls = [
    ...actionInputs,
    ...informeInputs,
    manualLocationSelect,
    automaticActivitiesToggle,
    submitButton,
    refreshLocationButton,
  ].filter(Boolean);
  const authControls = [chaveInput, passwordInput, passwordActionButton, requestRegistrationButton].filter(Boolean);
  const highlightedAuthFields = [chaveAuthField, passwordAuthField].filter(Boolean);
  const passwordDialogControls = [
    oldPasswordInput,
    newPasswordInput,
    confirmPasswordInput,
    passwordDialogBackButton,
    passwordDialogSubmitButton,
  ].filter(Boolean);
  const registrationDialogControls = [
    registrationChaveInput,
    registrationNameInput,
    registrationProjectSelect,
    registrationEmailInput,
    registrationPasswordInput,
    registrationConfirmPasswordInput,
    registrationDialogBackButton,
    registrationDialogSubmitButton,
  ].filter(Boolean);
  const transportScreenControls = [
    transportAddressToggleButton,
    transportAddressInput,
    transportZipInput,
    transportAddressBackButton,
    transportAddressSubmitButton,
    transportRegularButton,
    transportWeekendButton,
    transportExtraButton,
    transportRequestDateInput,
    transportRequestTimeInput,
    transportRequestBuilderBackButton,
    transportRequestBuilderSubmitButton,
    ...transportRequestWeekdayInputs,
    transportAcknowledgementCheckbox,
    transportAcknowledgementButton,
    transportScreenHeaderBackButton,
  ].filter(Boolean);
  const storageKey = 'checking.web.user.chave';
  const userSettingsStorageKey = 'checking.web.user.settings.by-chave';
  const userPasswordStorageKey = 'checking.web.user.password.by-chave';
  const userTransportLocalStateStorageKey = 'checking.web.transport.local-state.by-chave';
  const locationPromptAttemptedKey = 'checking.web.user.location.prompt-attempted';
  const locationPermissionGrantedKey = 'checking.web.user.location.permission-granted';
  const defaultManualLocationLabel = 'Escritório Principal';
  const transportAutoRefreshIntervalMs = 10000;
  const transportRealtimeRefreshDebounceMs = 220;
  let allowedProjectValues = Array.from(projectSelect.options)
    .map((option) => String(option.value || '').trim().toUpperCase())
    .filter(Boolean);
  let defaultProjectValue = allowedProjectValues[0] || '';
  const lifecycleTriggerCooldownMs = 1200;
  const passwordVerificationDebounceMs = 260;
  const unknownWebUserDetail = 'A chave do usuario nao esta cadastrada';
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
  const transportRequestKindLabels = {
    regular: 'Transporte Rotineiro',
    weekend: 'Transporte Fim de Semana',
    extra: 'Transporte Extra',
  };
  const transportRequestStatusLabels = {
    pending: 'Pendente',
    confirmed: 'Confirmado',
    realized: 'Realizado',
    rejected: 'Rejeitado',
    cancelled: 'Cancelado',
  };
  const transportRequestWeekdayLabels = {
    0: 'Seg',
    1: 'Ter',
    2: 'Qua',
    3: 'Qui',
    4: 'Sex',
    5: 'Sáb',
    6: 'Dom',
  };
  const transportRequestBuilderConfigs = {
    regular: {
      subtitle: 'Selecione os dias úteis desejados para o transporte rotineiro.',
      allowedWeekdays: [0, 1, 2, 3, 4],
      defaultSelectedWeekdays: [0, 1, 2, 3, 4],
      showWeekdays: true,
      showDate: false,
      showTime: false,
    },
    weekend: {
      subtitle: 'Selecione os dias de fim de semana desejados para o transporte.',
      allowedWeekdays: [5, 6],
      defaultSelectedWeekdays: [5],
      showWeekdays: true,
      showDate: false,
      showTime: false,
    },
    extra: {
      subtitle: 'Confira a data e o horário do transporte extra antes de solicitar.',
      allowedWeekdays: [],
      defaultSelectedWeekdays: [],
      showWeekdays: false,
      showDate: true,
      showTime: true,
      defaultTime: '18:00',
    },
  };

  let historyRequestToken = 0;
  let historyAbortController = null;
  let authStatusRequestToken = 0;
  let authStatusAbortController = null;
  let lastLifecycleTriggerAt = 0;
  let locationRequestPromise = null;
  let currentLocationMatch = null;
  let latestHistoryState = null;
  let availableLocations = [];
  let gpsLocationPermissionGranted = false;
  let lifecycleRefreshInProgress = false;
  let locationRefreshLoading = false;
  let passwordRegisterInProgress = false;
  let passwordLoginInProgress = false;
  let passwordChangeInProgress = false;
  let userSelfRegistrationInProgress = false;
  let submitInProgress = false;
  let transportStateLoading = false;
  let transportAddressSaveInProgress = false;
  let transportRequestInProgress = false;
  let transportCancelInProgress = false;
  let transportAcknowledgeInProgress = false;
  let transportAutoRefreshTimeoutId = null;
  let transportRealtimeEventSource = null;
  let transportRealtimeStreamChave = '';
  let transportRealtimeRefreshTimeoutId = null;
  let transportRealtimeRefreshPending = false;
  let projectCatalogPromise = null;
  let projectCatalogLoading = false;
  let projectUpdateInProgress = false;
  let lastCommittedProjectValue = defaultProjectValue;
  let userInteractionLockCount = 0;
  let passwordVerificationTimeoutId = null;
  let passwordAutofillSyncTimeoutId = null;
  let passwordAutofillSyncFrameId = null;
  let viewportMetricsSyncFrameId = null;
  let passwordVerificationRequestToken = 0;
  let lastVerifiedPassword = '';
  let lastObservedPasswordFieldValue = '';
  let passwordDialogMode = 'change';

  function resolveTransportEventTargetElement(event) {
    const target = event ? event.target : null;
    if (target instanceof Element) {
      return target;
    }
    if (typeof Node !== 'undefined' && target instanceof Node && target.parentElement instanceof Element) {
      return target.parentElement;
    }
    return null;
  }

  const authState = {
    chave: '',
    found: false,
    hasPassword: false,
    authenticated: false,
    passwordVerified: false,
    statusResolved: false,
    statusLoading: false,
    statusErrored: false,
  };

  const pendingAuthFieldRestoreState = {
    mode: null,
    chave: '',
    password: '',
  };

  const notificationState = {
    message: '',
    tone: null,
  };

  const transportState = {
    status: 'available',
    requestId: null,
    requestKind: null,
    routeKind: null,
    serviceDate: null,
    endRua: '',
    zip: '',
    requestedTime: '',
    boardingTime: '',
    confirmationDeadlineTime: '',
    vehicleType: '',
    vehiclePlate: '',
    vehicleColor: '',
    toleranceMinutes: null,
    awarenessRequired: false,
    awarenessConfirmed: false,
    requests: [],
  };

  const transportUiState = {
    addressEditorOpen: false,
    requestBuilderKind: null,
    selectedRequestId: null,
    detailRequestId: null,
    acknowledgementChecked: false,
    inlineMessage: '',
    inlineTone: null,
    dismissedRequestIds: new Set(),
    realizedRequestIds: new Set(),
  };

  const transportRequestSwipeState = {
    pointerId: null,
    requestId: null,
    startX: 0,
    startY: 0,
    deltaX: 0,
    deltaY: 0,
    isHorizontal: false,
    hasMoved: false,
    targetCard: null,
    holdTimeoutId: null,
    holdTriggered: false,
    suppressedClickRequestId: null,
  };

  const transportRequestDismissHoldDelayMs = 420;
  const transportRequestDismissMoveTolerancePx = 14;

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

  function dismissActiveKeyboard() {
    const activeElement = document.activeElement;
    if (activeElement && typeof activeElement.blur === 'function') {
      activeElement.blur();
    }
  }

  function isLandscapeOrientationActive() {
    if (window.matchMedia) {
      return window.matchMedia('(orientation: landscape)').matches;
    }

    const metrics = getViewportLayoutMetrics();
    return metrics.viewportWidth > metrics.viewportHeight;
  }

  async function requestPortraitOrientationLock() {
    const orientationApi = window.screen && window.screen.orientation;
    if (!orientationApi || typeof orientationApi.lock !== 'function') {
      return false;
    }

    try {
      await orientationApi.lock('portrait');
      return true;
    } catch (_error) {
      return false;
    }
  }

  function syncPortraitLockState() {
    const isLandscape = isLandscapeOrientationActive();

    if (appBody) {
      appBody.classList.toggle('portrait-lock-active', isLandscape);
    }

    if (orientationLockScreen) {
      orientationLockScreen.hidden = !isLandscape;
      orientationLockScreen.classList.toggle('is-hidden', !isLandscape);
    }

    [appHeader, appShell].filter(Boolean).forEach((element) => {
      element.setAttribute('aria-hidden', String(isLandscape));
    });

    if (isLandscape) {
      dismissActiveKeyboard();
      return;
    }

    void requestPortraitOrientationLock();
  }

  function getViewportLayoutMetrics() {
    const visualViewport = window.visualViewport;
    const viewportWidth = Math.round(
      Math.max(
        visualViewport && Number.isFinite(visualViewport.width) ? visualViewport.width : 0,
        window.innerWidth || 0,
        document.documentElement.clientWidth || 0
      )
    );
    const viewportHeight = Math.round(
      Math.max(
        visualViewport && Number.isFinite(visualViewport.height) ? visualViewport.height : 0,
        window.innerHeight || 0,
        document.documentElement.clientHeight || 0
      )
    );
    const headerHeight = appHeader ? Math.round(appHeader.getBoundingClientRect().height) : 0;

    return {
      viewportWidth,
      viewportHeight,
      headerHeight,
    };
  }

  function syncViewportLayoutMetrics() {
    const rootStyle = document.documentElement.style;
    const metrics = getViewportLayoutMetrics();

    if (metrics.viewportWidth > 0) {
      rootStyle.setProperty('--app-viewport-width', `${metrics.viewportWidth}px`);
    }
    if (metrics.viewportHeight > 0) {
      rootStyle.setProperty('--app-viewport-height', `${metrics.viewportHeight}px`);
    }
    if (metrics.headerHeight > 0) {
      rootStyle.setProperty('--app-header-height', `${metrics.headerHeight}px`);
    }
  }

  function scheduleViewportLayoutMetricsSync() {
    if (viewportMetricsSyncFrameId !== null) {
      return;
    }

    viewportMetricsSyncFrameId = window.requestAnimationFrame(() => {
      viewportMetricsSyncFrameId = null;
      syncViewportLayoutMetrics();
    });
  }

  function realignViewport() {
    scheduleViewportLayoutMetricsSync();
    window.requestAnimationFrame(() => {
      window.scrollTo(0, 0);
    });
  }

  function isPasswordDialogOpen() {
    return Boolean(passwordDialog && !passwordDialog.hidden);
  }

  function isRegistrationDialogOpen() {
    return Boolean(registrationDialog && !registrationDialog.hidden);
  }

  function isTransportScreenOpen() {
    return Boolean(transportScreen && !transportScreen.hidden);
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
    return getTransportRequests().filter(
      (requestItem) => !transportUiState.dismissedRequestIds.has(Number(requestItem.requestId))
    );
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
      && !transportStateLoading
      && !transportAddressSaveInProgress
      && !transportRequestInProgress
      && !transportCancelInProgress
      && !transportAcknowledgeInProgress
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
      && !transportStateLoading
      && !transportAddressSaveInProgress
      && !transportRequestInProgress
      && !transportCancelInProgress
      && !transportAcknowledgeInProgress;
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

  function isAnyDialogOpen() {
    return isPasswordDialogOpen() || isRegistrationDialogOpen() || isTransportScreenOpen();
  }

  function isPasswordActionBusy() {
    return authState.statusLoading || passwordRegisterInProgress || passwordChangeInProgress || userSelfRegistrationInProgress;
  }

  function getActiveChave() {
    return sanitizeChave(chaveInput.value);
  }

  function isApplicationUnlocked(chave) {
    const normalizedChave = sanitizeChave(typeof chave === 'string' ? chave : chaveInput.value);
    return normalizedChave.length === 4
      && authState.authenticated
      && authState.passwordVerified
      && authState.chave === normalizedChave;
  }

  function isMissingUserRegistrationState() {
    return authState.statusResolved && !authState.statusErrored && !authState.found;
  }

  function isMissingPasswordRegistrationState() {
    return authState.statusResolved && !authState.statusErrored && authState.found && !authState.hasPassword;
  }

  function isPasswordActionAssistanceModeActive() {
    return isMissingUserRegistrationState() || isMissingPasswordRegistrationState();
  }

  function resolvePasswordDialogMode() {
    if (isMissingPasswordRegistrationState()) {
      return 'register';
    }
    return 'change';
  }

  function isPasswordRegistrationDialogMode() {
    return passwordDialogMode === 'register';
  }

  function resolvePasswordActionButtonLabel() {
    if (authState.statusLoading) {
      return 'Verificando...';
    }
    if (passwordRegisterInProgress) {
      return 'Aguarde';
    }
    if (userSelfRegistrationInProgress) {
      return 'Aguarde';
    }
    if (isMissingUserRegistrationState()) {
      return 'Chave?';
    }
    if (isMissingPasswordRegistrationState()) {
      return 'Senha?';
    }
    return 'Alterar';
  }

  function clearPasswordVerificationTimer() {
    if (passwordVerificationTimeoutId !== null) {
      window.clearTimeout(passwordVerificationTimeoutId);
      passwordVerificationTimeoutId = null;
    }
    passwordVerificationRequestToken += 1;
  }

  function clearPasswordAutofillSync() {
    if (passwordAutofillSyncTimeoutId !== null) {
      window.clearTimeout(passwordAutofillSyncTimeoutId);
      passwordAutofillSyncTimeoutId = null;
    }

    if (passwordAutofillSyncFrameId !== null) {
      window.cancelAnimationFrame(passwordAutofillSyncFrameId);
      passwordAutofillSyncFrameId = null;
    }
  }

  function clearTypedPasswordAuthentication() {
    clearPasswordVerificationTimer();
    clearPasswordAutofillSync();
    lastVerifiedPassword = '';
    lastObservedPasswordFieldValue = passwordInput.value;
    authState.authenticated = false;
    authState.passwordVerified = false;
  }

  function syncAuthenticationFieldHighlights() {
    const authenticated = isApplicationUnlocked();
    const assistanceModeActive = isPasswordActionAssistanceModeActive();
    highlightedAuthFields.forEach((fieldElement) => {
      fieldElement.classList.toggle('auth-field-pending', !authenticated && assistanceModeActive);
      fieldElement.classList.toggle('auth-field-authenticated', authenticated);
    });
  }

  function syncPasswordDialogPresentation() {
    const isRegisterMode = isPasswordRegistrationDialogMode();

    if (passwordDialog) {
      passwordDialog.setAttribute('data-mode', passwordDialogMode);
    }
    if (passwordDialogTitle) {
      passwordDialogTitle.textContent = isRegisterMode ? 'Cadastrar Senha' : 'Alterar Senha';
    }
    if (passwordDialogOldPasswordField) {
      passwordDialogOldPasswordField.classList.toggle('is-registration-placeholder', isRegisterMode);
    }
    if (oldPasswordInput) {
      oldPasswordInput.hidden = isRegisterMode;
      oldPasswordInput.setAttribute('aria-hidden', String(isRegisterMode));
    }
  }

  function canSubmitPasswordDialog() {
    const newPassword = newPasswordInput ? newPasswordInput.value : '';
    const confirmPassword = confirmPasswordInput ? confirmPasswordInput.value : '';

    if (!clientState.isPasswordLengthValid(newPassword)) {
      return false;
    }

    if (confirmPassword !== newPassword) {
      return false;
    }

    if (isPasswordRegistrationDialogMode()) {
      return true;
    }

    return clientState.isPasswordLengthValid(oldPasswordInput ? oldPasswordInput.value : '');
  }

  function hasPendingAuthFieldRestoreState() {
    return Boolean(pendingAuthFieldRestoreState.mode);
  }

  function clearPendingAuthFieldRestoreState() {
    pendingAuthFieldRestoreState.mode = null;
    pendingAuthFieldRestoreState.chave = '';
    pendingAuthFieldRestoreState.password = '';
  }

  function rememberPendingAuthFieldRestoreState(mode) {
    const hadPendingRestore = hasPendingAuthFieldRestoreState();
    pendingAuthFieldRestoreState.mode = mode;
    pendingAuthFieldRestoreState.chave = hadPendingRestore
      ? pendingAuthFieldRestoreState.chave
      : String(chaveInput.value || '');
    pendingAuthFieldRestoreState.password = hadPendingRestore
      ? pendingAuthFieldRestoreState.password
      : String(passwordInput.value || '');
  }

  function restorePendingAuthFieldValuesIfNeeded() {
    if (!hasPendingAuthFieldRestoreState()) {
      return false;
    }

    const shouldRestore = pendingAuthFieldRestoreState.mode === 'chave'
      ? !String(chaveInput.value || '').trim() && !String(passwordInput.value || '').trim()
      : !String(passwordInput.value || '').trim();

    if (!shouldRestore) {
      return false;
    }

    chaveInput.value = pendingAuthFieldRestoreState.chave;
    passwordInput.value = pendingAuthFieldRestoreState.password;
    lastObservedPasswordFieldValue = pendingAuthFieldRestoreState.password;
    writePersistedChave(pendingAuthFieldRestoreState.chave);
    clearPendingAuthFieldRestoreState();
    syncFormControlStates();
    return true;
  }

  function isAuthInputAreaElement(element) {
    return Boolean(
      element
      && element.closest('label[for="chaveInput"], label[for="passwordInput"], #chaveInput, #passwordInput')
    );
  }

  function restorePendingAuthFieldValuesOnExternalFocus(event) {
    if (!hasPendingAuthFieldRestoreState()) {
      return;
    }

    const targetElement = resolveTransportEventTargetElement(event);
    if (isAuthInputAreaElement(targetElement)) {
      return;
    }

    restorePendingAuthFieldValuesIfNeeded();
  }

  function syncFormControlStates() {
    const lockActive = isUserInteractionLocked();
    const authBusy = isPasswordActionBusy();
    const dialogOpen = isAnyDialogOpen();
    const unlocked = isApplicationUnlocked();
    const automaticActivitiesEnabled = isAutomaticActivitiesEnabled();
    const transportBusy = transportStateLoading
      || transportAddressSaveInProgress
      || transportRequestInProgress
      || transportCancelInProgress
      || transportAcknowledgeInProgress;

    syncAuthenticationFieldHighlights();

    projectSelect.disabled = dialogOpen
      || lockActive
      || !unlocked
      || submitInProgress
      || passwordRegisterInProgress
      || passwordChangeInProgress
      || userSelfRegistrationInProgress
      || projectCatalogLoading
      || projectUpdateInProgress
      || allowedProjectValues.length === 0
      || isAutomaticActivitiesEnabled();

    processControls.forEach((control) => {
      if (!control) {
        return;
      }

      if (actionInputs.includes(control)) {
        control.disabled = dialogOpen || lockActive || !unlocked || automaticActivitiesEnabled;
        return;
      }

      if (control === manualLocationSelect) {
        control.disabled = dialogOpen || lockActive || !unlocked || gpsLocationPermissionGranted || availableLocations.length === 0;
        return;
      }

      if (control === refreshLocationButton) {
        control.disabled = dialogOpen || lockActive || !unlocked || locationRefreshLoading;
        return;
      }

      if (control === submitButton) {
        control.disabled = dialogOpen || lockActive || !unlocked || submitInProgress || automaticActivitiesEnabled;
        return;
      }

      control.disabled = dialogOpen || lockActive || !unlocked;
    });

    authControls.forEach((control) => {
      if (control === chaveInput) {
        control.disabled = dialogOpen || lockActive || submitInProgress || passwordRegisterInProgress || passwordChangeInProgress || userSelfRegistrationInProgress;
        return;
      }

      if (control === passwordInput) {
        control.disabled = dialogOpen || lockActive || submitInProgress || passwordRegisterInProgress || passwordChangeInProgress || userSelfRegistrationInProgress;
        return;
      }

      if (control === passwordActionButton) {
        const activeChave = getActiveChave();
        const canOpenRegistration = isMissingUserRegistrationState();
        const canOpenPasswordRegistration = isMissingPasswordRegistrationState();
        const canOpenPasswordChange = authState.statusResolved && !authState.statusErrored && authState.hasPassword;
        control.textContent = resolvePasswordActionButtonLabel();
        control.classList.toggle('is-attention', isPasswordActionAssistanceModeActive());
        control.classList.toggle('is-pending', passwordRegisterInProgress);
        control.disabled = dialogOpen
          || lockActive
          || submitInProgress
          || authBusy
          || activeChave.length !== 4
          || (!canOpenRegistration && !canOpenPasswordRegistration && !canOpenPasswordChange);
        return;
      }

      if (control === requestRegistrationButton) {
        control.disabled = dialogOpen || lockActive || submitInProgress || authBusy || userSelfRegistrationInProgress;
      }
    });

    passwordDialogControls.forEach((control) => {
      if (!control) {
        return;
      }

      if (control === passwordDialogBackButton) {
        control.disabled = passwordChangeInProgress;
        return;
      }

      if (control === passwordDialogSubmitButton) {
        const isRegisterMode = isPasswordRegistrationDialogMode();
        control.disabled = passwordChangeInProgress || !canSubmitPasswordDialog();
        control.textContent = passwordChangeInProgress
          ? (isRegisterMode ? 'Salvando...' : 'Alterando...')
          : (isRegisterMode ? 'Salvar' : 'Alterar');
        return;
      }

      if (control === oldPasswordInput && isPasswordRegistrationDialogMode()) {
        control.disabled = true;
        return;
      }

      control.disabled = passwordChangeInProgress;
    });

    registrationDialogControls.forEach((control) => {
      if (!control) {
        return;
      }

      if (control === registrationDialogBackButton) {
        control.disabled = userSelfRegistrationInProgress;
        return;
      }

      if (control === registrationDialogSubmitButton) {
        control.disabled = userSelfRegistrationInProgress;
        control.textContent = userSelfRegistrationInProgress ? 'Enviando...' : 'Enviar';
        return;
      }

      if (control === registrationProjectSelect) {
        control.disabled = userSelfRegistrationInProgress || projectCatalogLoading || allowedProjectValues.length === 0;
        return;
      }

      control.disabled = userSelfRegistrationInProgress;
    });

    if (transportButton) {
      const transportButtonLocked = dialogOpen || lockActive || submitInProgress || authBusy || passwordLoginInProgress;
      transportButton.disabled = transportButtonLocked;
      transportButton.setAttribute('aria-disabled', String(transportButtonLocked));
    }

    transportScreenControls.forEach((control) => {
      if (!control) {
        return;
      }

      if (control === transportAddressSubmitButton) {
        control.disabled = transportBusy;
        control.textContent = transportAddressSaveInProgress ? 'Cadastrando...' : 'Cadastrar';
        return;
      }

      if (control === transportRequestBuilderSubmitButton) {
        control.disabled = transportBusy;
        control.textContent = transportRequestInProgress ? 'Solicitando...' : 'Solicitar';
        return;
      }

      if (control === transportAcknowledgementButton) {
        control.disabled = transportBusy || !transportUiState.acknowledgementChecked;
        control.textContent = transportAcknowledgeInProgress ? 'CONFIRMANDO...' : 'CONFIRMAR CIÊNCIA';
        return;
      }

      control.disabled = transportBusy;
    });

    if (transportScreen) {
      transportScreen.setAttribute('aria-busy', String(transportBusy));
    }

    const isBusy = lockActive || locationRefreshLoading || submitInProgress || authBusy || passwordLoginInProgress;
    form.classList.toggle('is-busy', isBusy);
    form.setAttribute('aria-busy', String(isBusy));
    if (passwordDialog) {
      passwordDialog.setAttribute('aria-busy', String(passwordChangeInProgress));
    }
    if (registrationDialog) {
      registrationDialog.setAttribute('aria-busy', String(userSelfRegistrationInProgress));
    }
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
    element.classList.remove('is-success', 'is-error', 'is-warning', 'is-info', 'is-neutral');

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

  function createRequestError(response, payload) {
    const error = new Error(parseErrorMessage(payload));
    error.status = response.status;
    error.payload = payload;
    return error;
  }

  function isUnknownUserError(error) {
    return Boolean(
      error
      && error.status === 404
      && error.payload
      && error.payload.detail === unknownWebUserDetail
    );
  }

  async function logoutWebSession(options) {
    const settings = options || {};
    clearTypedPasswordAuthentication();

    try {
      await fetch(authLogoutEndpoint, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
        },
      });
    } catch {
      // Ignore logout transport failures and keep the UI locally locked.
    }

    if (!settings.silent) {
      applyAuthenticationLockedState({
        chave: settings.chave || chaveInput.value,
        hasPassword: settings.hasPassword,
        found: settings.found,
        message: settings.message,
      });
    }
  }

  function clearProtectedClientState() {
    latestHistoryState = null;
    applyHistoryState(null);
    resetTransportState();
    closeTransportScreen();
    setResolvedLocation(null);
    currentLocationMatch = null;
    availableLocations = [];
    setLocationPresentation('Aguardando autenticação.', '', null, '--', { suppressNotification: true });
  }

  function setAuthenticationPrompt(message) {
    const promptMessage = message || clientState.resolveAuthenticationPromptMessage(authState);
    if (promptMessage) {
      setStatus(promptMessage, 'error');
    }
  }

  function applyAuthenticationLockedState(options) {
    const settings = options || {};
    const normalizedChave = sanitizeChave(settings.chave || chaveInput.value);
    clearTypedPasswordAuthentication();
    authState.chave = normalizedChave;
    authState.found = Boolean(settings.found);
    authState.hasPassword = Boolean(settings.hasPassword);
    authState.statusResolved = normalizedChave.length === 4;
    authState.statusErrored = Boolean(settings.statusErrored);
    clearProtectedClientState();
    syncFormControlStates();
    setAuthenticationPrompt(settings.message);
  }

  function handleExpiredAuthentication(options) {
    const settings = options || {};
    closePasswordDialog();
    closeRegistrationDialog();
    closeTransportScreen();
    applyAuthenticationLockedState({
      chave: settings.chave || chaveInput.value,
      found: settings.found !== false,
      hasPassword: settings.hasPassword !== false,
      message: settings.message || 'Digite sua senha para iniciar.',
    });
  }

  function closePasswordDialog() {
    if (!passwordDialog || !passwordDialogBackdrop || passwordDialog.hidden) {
      return;
    }

    dismissActiveKeyboard();
    passwordDialog.hidden = true;
    passwordDialogBackdrop.hidden = true;
    passwordDialog.classList.add('is-hidden');
    passwordDialogBackdrop.classList.add('is-hidden');
    if (passwordChangeForm) {
      passwordChangeForm.reset();
    }
    passwordDialogMode = 'change';
    syncPasswordDialogPresentation();
    syncFormControlStates();
    realignViewport();
  }

  function openPasswordDialog() {
    if (!passwordDialog || !passwordDialogBackdrop) {
      return;
    }

    if (!authState.hasPassword && !isMissingPasswordRegistrationState()) {
      return;
    }

    passwordDialogMode = resolvePasswordDialogMode();
    syncPasswordDialogPresentation();
    passwordDialog.hidden = false;
    passwordDialogBackdrop.hidden = false;
    passwordDialog.classList.remove('is-hidden');
    passwordDialogBackdrop.classList.remove('is-hidden');
    if (passwordChangeForm) {
      passwordChangeForm.reset();
    }
    if (isPasswordRegistrationDialogMode()) {
      const initialPassword = clientState.isPasswordLengthValid(passwordInput.value) ? passwordInput.value : '';
      newPasswordInput.value = initialPassword;
      confirmPasswordInput.value = initialPassword;
    }
    syncFormControlStates();
    realignViewport();
    if (isPasswordRegistrationDialogMode() && newPasswordInput) {
      newPasswordInput.focus();
      return;
    }
    if (oldPasswordInput) {
      oldPasswordInput.focus();
    }
  }

  function closeRegistrationDialog() {
    if (!registrationDialog || !registrationDialogBackdrop || registrationDialog.hidden) {
      return;
    }

    dismissActiveKeyboard();
    registrationDialog.hidden = true;
    registrationDialogBackdrop.hidden = true;
    registrationDialog.classList.add('is-hidden');
    registrationDialogBackdrop.classList.add('is-hidden');
    if (registrationForm) {
      registrationForm.reset();
    }
    syncFormControlStates();
    realignViewport();
  }

  function openRegistrationDialog() {
    if (!registrationDialog || !registrationDialogBackdrop) {
      return;
    }

    if (!allowedProjectValues.length) {
      void loadProjectCatalog({ showError: false });
    }

    const activeChave = getActiveChave();
    const initialPassword = clientState.isPasswordLengthValid(passwordInput.value) ? passwordInput.value : '';
    registrationChaveInput.value = activeChave;
    syncProjectSelectOptions({ registrationValue: projectSelect.value });
    registrationPasswordInput.value = initialPassword;
    registrationConfirmPasswordInput.value = initialPassword;
    registrationDialog.hidden = false;
    registrationDialogBackdrop.hidden = false;
    registrationDialog.classList.remove('is-hidden');
    registrationDialogBackdrop.classList.remove('is-hidden');
    syncFormControlStates();
    realignViewport();
    if (registrationNameInput && activeChave.length === 4) {
      registrationNameInput.focus();
      return;
    }
    if (registrationChaveInput) {
      registrationChaveInput.focus();
    }
  }

  function buildProtectedRequestError(response, payload) {
    if (response.status === 401) {
      handleExpiredAuthentication({ chave: chaveInput.value, hasPassword: true });
      const authError = new Error('Digite sua senha para iniciar.');
      authError.status = response.status;
      authError.payload = payload;
      authError.isAuthExpired = true;
      return authError;
    }
    return createRequestError(response, payload);
  }

  function setTransportInlineStatus(message, tone) {
    transportUiState.inlineMessage = message || '';
    transportUiState.inlineTone = tone || null;
    if (!transportInlineStatus) {
      return;
    }

    transportInlineStatus.textContent = transportUiState.inlineMessage;
    transportInlineStatus.classList.remove('is-success', 'is-error', 'is-warning', 'is-info');
    if (transportUiState.inlineTone) {
      transportInlineStatus.classList.add(`is-${transportUiState.inlineTone}`);
    }
  }

  function clearTransportInlineStatus() {
    setTransportInlineStatus('', null);
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
    transportState.awarenessRequired = false;
    transportState.awarenessConfirmed = false;
    transportState.requests = [];
    transportUiState.addressEditorOpen = false;
    transportUiState.requestBuilderKind = null;
    transportUiState.selectedRequestId = null;
    transportUiState.detailRequestId = null;
    transportUiState.acknowledgementChecked = false;
    resetTransportRequestLocalState();
    resetTransportRequestSwipeState();
    clearTransportInlineStatus();
    renderTransportScreen();
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

  function initializeTransportRequestBuilder(requestKind) {
    const builderConfig = getTransportRequestBuilderConfig(requestKind);
    if (!builderConfig) {
      return;
    }

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
    const builderConfig = getTransportRequestBuilderConfig(requestKind);
    if (!builderConfig) {
      return null;
    }

    const payload = {
      request_kind: requestKind,
      requested_time: formatCurrentTransportRequestTime(),
    };

    if (builderConfig.showWeekdays) {
      const selectedWeekdays = transportRequestWeekdayInputs
        .filter((inputElement) => {
          const weekdayValue = Number(inputElement.value);
          return builderConfig.allowedWeekdays.includes(weekdayValue) && inputElement.checked;
        })
        .map((inputElement) => Number(inputElement.value));

      if (selectedWeekdays.length === 0) {
        setTransportInlineStatus('Selecione ao menos um dia para solicitar o transporte.', 'error');
        return null;
      }

      payload.selected_weekdays = selectedWeekdays;
      return payload;
    }

    const requestedDate = String(transportRequestDateInput && transportRequestDateInput.value || '').trim();
    const requestedTime = String(transportRequestTimeInput && transportRequestTimeInput.value || '').trim();
    if (!requestedDate) {
      setTransportInlineStatus('Informe a data do transporte extra.', 'error');
      return null;
    }
    if (!requestedTime) {
      setTransportInlineStatus('Informe o horário do transporte extra.', 'error');
      return null;
    }

    payload.requested_date = requestedDate;
    payload.requested_time = requestedTime;
    return payload;
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
      awarenessRequired: Boolean(payload && payload.awareness_required),
      awarenessConfirmed: Boolean(payload && payload.awareness_confirmed),
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
      awareness_required: payload && payload.awareness_required,
      awareness_confirmed: payload && payload.awareness_confirmed,
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
      awareness_required: transportState.awarenessRequired,
      awareness_confirmed: transportState.awarenessConfirmed,
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
    setTransportInlineStatus('Solicitação marcada como realizada.', 'success');
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
      } catch (error) {}
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
        } catch (error) {}
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
      } catch (error) {}
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
      } catch (error) {}
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
        transportState.awarenessRequired = false;
        transportState.awarenessConfirmed = false;
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
      transportState.awarenessRequired = Boolean(payload && payload.awareness_required);
      transportState.awarenessConfirmed = Boolean(payload && payload.awareness_confirmed);
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
    transportState.awarenessRequired = selectedRequest.awarenessRequired;
    transportState.awarenessConfirmed = selectedRequest.awarenessConfirmed;
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
    transportUiState.acknowledgementChecked = false;
    syncTransportAddressFormValues();
    renderTransportScreen();
  }

  function isTransportServiceDateToday(serviceDateValue) {
    return Boolean(serviceDateValue && serviceDateValue === formatDateInputValue(new Date()));
  }

  function canAcknowledgeSelectedTransportRequest() {
    return transportState.status === 'confirmed'
      && transportState.awarenessRequired
      && !transportState.awarenessConfirmed
      && isTransportServiceDateToday(transportState.serviceDate);
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
    return Number.isNaN(parsedDate.getTime()) ? serviceDateValue : dateFormatter.format(parsedDate);
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

  function closeTransportRequestDetailWidget() {
    if (transportUiState.detailRequestId === null) {
      return;
    }

    transportUiState.detailRequestId = null;
    renderTransportScreen();
    syncFormControlStates();
  }

  function formatTransportRequestDetailVehicleType(value) {
    const formatter = clientState && typeof clientState.formatTransportVehicleType === 'function'
      ? clientState.formatTransportVehicleType
      : null;
    const formattedValue = formatter ? formatter(value) : String(value || '').trim();
    return formattedValue || '--';
  }

  function createTransportRequestDetailField(label, value) {
    const fieldElement = document.createElement('div');
    const labelElement = document.createElement('span');
    const valueElement = document.createElement('span');

    fieldElement.className = 'transport-request-detail-field';
    labelElement.className = 'transport-request-detail-field-label';
    valueElement.className = 'transport-request-detail-field-value';

    labelElement.textContent = label;
    valueElement.textContent = value || '--';

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
      statusMessage.textContent = 'Aguardando alocação de transporte.';
      followupMessage.textContent = 'Quando você for alocado em um veículo, as informações aparecerão aqui.';
      copyStack.appendChild(followupMessage);
      fragment.appendChild(copyStack);
      return fragment;
    }

    if (requestItem.status === 'confirmed' || requestItem.status === 'realized') {
      const detailsGroup = document.createElement('div');
      const departureDate = formatTransportRequestServiceDate(requestItem.serviceDate) || '--';
      const departureTime = formatTransportRequestCardTime(requestItem.boardingTime || requestItem.requestedTime) || '--';

      detailsGroup.className = 'transport-request-detail-fields';
      statusMessage.textContent = requestItem.status === 'realized'
        ? 'Transporte realizado.'
        : 'Transporte confirmado.';

      detailsGroup.appendChild(createTransportRequestDetailField('Tipo de Veículo', formatTransportRequestDetailVehicleType(requestItem.vehicleType)));
      detailsGroup.appendChild(createTransportRequestDetailField('Placa do Veículo', requestItem.vehiclePlate || '--'));
      if (String(requestItem.vehicleColor || '').trim()) {
        detailsGroup.appendChild(createTransportRequestDetailField('Cor do Veículo', requestItem.vehicleColor));
      }
      detailsGroup.appendChild(createTransportRequestDetailField('Data de Partida', departureDate));
      detailsGroup.appendChild(createTransportRequestDetailField('Hora de Partida', departureTime));
      copyStack.appendChild(detailsGroup);
      fragment.appendChild(copyStack);
      return fragment;
    }

    statusMessage.textContent = 'Esta solicitação não está mais ativa.';
    if (String(requestItem.responseMessage || '').trim()) {
      const responseMessage = document.createElement('p');
      responseMessage.className = 'transport-request-detail-message';
      responseMessage.textContent = requestItem.responseMessage;
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
        transportRequestDetailTitle.textContent = 'Detalhes da Solicitação';
      }
      return;
    }

    if (transportRequestDetailTitle) {
      transportRequestDetailTitle.textContent = transportRequestKindLabels[detailRequest.requestKind] || 'Detalhes da Solicitação';
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
    const transportBusy = transportStateLoading
      || transportAddressSaveInProgress
      || transportRequestInProgress
      || transportCancelInProgress
      || transportAcknowledgeInProgress;
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
    cardTitle.textContent = transportRequestKindLabels[requestItem.requestKind] || 'Transporte';

    cardStatus.className = `transport-request-card-status is-${requestItem.status}`;
    cardStatus.textContent = transportRequestStatusLabels[requestItem.status] || 'Pendente';

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
      realizedButton.textContent = 'Realizado';
      cardActions.appendChild(realizedButton);
    }

    if (canCancelRequest) {
      const cancelButton = document.createElement('button');
      cancelButton.type = 'button';
      cancelButton.className = 'transport-request-card-cancel-button';
      cancelButton.dataset.transportRequestCancel = 'true';
      cancelButton.dataset.requestId = String(requestItem.requestId);
      cancelButton.disabled = transportBusy;
      cancelButton.textContent = transportCancelInProgress ? 'Cancelando...' : 'Cancelar';
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
    const hasRequests = getVisibleTransportRequests().length > 0;

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

    transportRequestWeekdayOptions.forEach((optionElement) => {
      const weekdayValue = Number(optionElement.dataset.weekday);
      const showOption = Boolean(activeBuilderConfig && activeBuilderConfig.allowedWeekdays.includes(weekdayValue));
      optionElement.hidden = !showOption;
      optionElement.classList.toggle('is-hidden', !showOption);
    });

    if (transportRequestHistorySection) {
      const showHistory = !transportUiState.addressEditorOpen && hasRequests;
      transportRequestHistorySection.hidden = !showHistory;
      transportRequestHistorySection.classList.toggle('is-hidden', !showHistory);
      if (showHistory) {
        renderTransportRequestHistory();
      }
    }

    if (transportAcknowledgementSection) {
      const showAcknowledgement = !transportUiState.addressEditorOpen && !activeBuilderConfig && canAcknowledgeSelectedTransportRequest();
      transportAcknowledgementSection.hidden = !showAcknowledgement;
      transportAcknowledgementSection.classList.toggle('is-hidden', !showAcknowledgement);
    }

    if (transportAcknowledgementCheckbox) {
      transportAcknowledgementCheckbox.checked = transportUiState.acknowledgementChecked;
    }

    renderTransportRequestDetailWidget({
      canShow: !transportUiState.addressEditorOpen && !activeBuilderConfig && hasRequests,
    });

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
    transportUiState.acknowledgementChecked = false;
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
      setStatus('Digite sua chave e valide a senha para acessar Transporte.', 'error');
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
    transportStateLoading = true;
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
      setTransportInlineStatus(error instanceof Error ? error.message : 'Não foi possível consultar o transporte.', 'error');
      return null;
    } finally {
      transportStateLoading = false;
      renderTransportScreen();
      syncFormControlStates();
    }
  }

  async function submitTransportAddress(event) {
    event.preventDefault();
    const normalizedChave = getActiveChave();
    if (normalizedChave.length !== 4) {
      setTransportInlineStatus('Informe uma chave válida antes de atualizar o endereço.', 'error');
      return;
    }

    transportAddressSaveInProgress = true;
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
      setTransportInlineStatus(payload.message || 'Endereço atualizado com sucesso.', 'success');
    } catch (error) {
      if (error && error.isAuthExpired) {
        closeTransportScreen();
        return;
      }
      setTransportInlineStatus(error instanceof Error ? error.message : 'Não foi possível atualizar o endereço.', 'error');
    } finally {
      transportAddressSaveInProgress = false;
      syncFormControlStates();
    }
  }

  async function requestTransport(requestKind, requestPayload = {}) {
    const normalizedChave = getActiveChave();
    const requestLabel = transportRequestKindLabels[requestKind] || 'Transporte';
    if (normalizedChave.length !== 4) {
      setTransportInlineStatus('Informe uma chave válida antes de solicitar o transporte.', 'error');
      return;
    }

    transportRequestInProgress = true;
    clearTransportInlineStatus();
    syncFormControlStates();
    try {
      const payload = await postTransportPayload(transportRequestEndpoint, {
        chave: normalizedChave,
        request_kind: requestKind,
        ...requestPayload,
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
      setTransportInlineStatus(error instanceof Error ? error.message : `Não foi possível solicitar ${requestLabel}.`, 'error');
    } finally {
      transportRequestInProgress = false;
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

    transportCancelInProgress = true;
    clearTransportInlineStatus();
    syncFormControlStates();
    try {
      const payload = await postTransportPayload(transportCancelEndpoint, {
        chave: normalizedChave,
        request_id: targetRequest.requestId,
      });
      applyTransportStatePayload(payload.state || {});
      transportUiState.requestBuilderKind = null;
      transportUiState.acknowledgementChecked = false;
      setTransportInlineStatus(payload.message || 'Solicitação de transporte cancelada.', 'success');
    } catch (error) {
      if (error && error.isAuthExpired) {
        closeTransportScreen();
        return;
      }
      setTransportInlineStatus(error instanceof Error ? error.message : 'Não foi possível cancelar a solicitação.', 'error');
    } finally {
      transportCancelInProgress = false;
      syncFormControlStates();
    }
  }

  async function acknowledgeTransportInformation() {
    const normalizedChave = getActiveChave();
    const selectedRequest = getTransportSelectedRequest();
    if (!selectedRequest || !selectedRequest.requestId) {
      return;
    }

    transportAcknowledgeInProgress = true;
    clearTransportInlineStatus();
    syncFormControlStates();
    try {
      const payload = await postTransportPayload(transportAcknowledgeEndpoint, {
        chave: normalizedChave,
        request_id: selectedRequest.requestId,
      });
      applyTransportStatePayload(payload.state || {});
      clearTransportInlineStatus();
    } catch (error) {
      if (error && error.isAuthExpired) {
        closeTransportScreen();
        return;
      }
      setTransportInlineStatus(error instanceof Error ? error.message : 'Não foi possível registrar a ciência.', 'error');
    } finally {
      transportAcknowledgeInProgress = false;
      syncFormControlStates();
    }
  }

  function applyAuthenticationStatusPayload(payload) {
    const normalizedChave = sanitizeChave((payload && payload.chave) || chaveInput.value);
    const sessionAuthenticated = Boolean(payload && payload.authenticated);
    const typedPasswordStillVerified = authState.passwordVerified
      && authState.chave === normalizedChave
      && passwordInput.value === lastVerifiedPassword
      && clientState.isPasswordVerificationInputValid(passwordInput.value);

    authState.chave = normalizedChave;
    authState.found = Boolean(payload && payload.found);
    authState.hasPassword = Boolean(payload && payload.has_password);
    authState.passwordVerified = sessionAuthenticated && typedPasswordStillVerified;
    authState.authenticated = sessionAuthenticated && authState.passwordVerified;
    authState.statusResolved = normalizedChave.length === 4;
    authState.statusErrored = false;

    if (!authState.passwordVerified) {
      lastVerifiedPassword = '';
    }

    if (!authState.authenticated) {
      clearProtectedClientState();
      setAuthenticationPrompt(payload && payload.message);
    }
    syncFormControlStates();
  }

  async function fetchAuthenticationStatus(chave, signal) {
    const response = await fetch(`${authStatusEndpoint}?chave=${encodeURIComponent(chave)}`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal,
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw createRequestError(response, payload);
    }

    return payload;
  }

  function isStalePasswordVerificationAttempt(chave, password, verificationToken) {
    return Boolean(
      verificationToken
      && (
        verificationToken !== passwordVerificationRequestToken
        || getActiveChave() !== chave
        || passwordInput.value !== password
      )
    );
  }

  function schedulePasswordVerification(options) {
    const settings = options || {};
    const normalizedChave = getActiveChave();
    const currentPassword = passwordInput.value;

    clearPasswordVerificationTimer();
    if (normalizedChave.length !== 4 || !authState.hasPassword) {
      return;
    }

    if (!clientState.isPasswordVerificationInputValid(currentPassword)) {
      return;
    }

    if (isApplicationUnlocked(normalizedChave) && currentPassword === lastVerifiedPassword) {
      return;
    }

    const verificationToken = passwordVerificationRequestToken;
    setStatus('Senha sendo verificada.', 'neutral');
    passwordVerificationTimeoutId = window.setTimeout(() => {
      void attemptPasswordLogin({
        silentValidation: true,
        showReadyMessage: settings.showReadyMessage !== false,
        allowPartialVerification: true,
        verificationToken,
      });
    }, passwordVerificationDebounceMs);
  }

  function syncPasswordInputState(options) {
    const settings = options || {};
    const normalizedChave = getActiveChave();
    const currentPassword = passwordInput.value;

    lastObservedPasswordFieldValue = currentPassword;

    if (authState.passwordVerified && currentPassword !== lastVerifiedPassword) {
      applyAuthenticationLockedState({
        chave: normalizedChave,
        found: authState.found,
        hasPassword: authState.hasPassword,
        message: 'Digite sua senha para iniciar.',
      });
      void logoutWebSession({ silent: true });
    }

    if (normalizedChave.length === 4 && authState.hasPassword && clientState.isPasswordVerificationInputValid(currentPassword)) {
      schedulePasswordVerification({ showReadyMessage: settings.showReadyMessage !== false });
    } else if (normalizedChave.length === 4 && authState.hasPassword && !currentPassword) {
      clearPasswordVerificationTimer();
      setAuthenticationPrompt('Digite sua senha para iniciar.');
    } else {
      clearPasswordVerificationTimer();
    }

    syncFormControlStates();
  }

  function syncAutofilledPasswordValue() {
    if (passwordInput.value === lastObservedPasswordFieldValue) {
      return;
    }

    syncPasswordInputState({ showReadyMessage: true });
  }

  function schedulePasswordAutofillSync(options) {
    const settings = options || {};
    const attempts = Number.isFinite(settings.attempts) && settings.attempts > 0
      ? Math.floor(settings.attempts)
      : 8;
    const delayMs = Number.isFinite(settings.delayMs) && settings.delayMs >= 0
      ? Math.floor(settings.delayMs)
      : 120;
    let remainingAttempts = attempts;

    clearPasswordAutofillSync();

    const runAttempt = () => {
      syncAutofilledPasswordValue();
      remainingAttempts -= 1;
      if (remainingAttempts <= 0) {
        clearPasswordAutofillSync();
        return;
      }

      passwordAutofillSyncTimeoutId = window.setTimeout(() => {
        passwordAutofillSyncFrameId = window.requestAnimationFrame(runAttempt);
      }, delayMs);
    };

    passwordAutofillSyncFrameId = window.requestAnimationFrame(runAttempt);
  }

  async function loadAuthenticatedApplication(chave, options) {
    const settings = options || {};
    const normalizedChave = sanitizeChave(chave || chaveInput.value);
    if (!isApplicationUnlocked(normalizedChave)) {
      return false;
    }

    await loadProjectCatalog({ showError: false });
    restorePersistedUserSettingsForChave(normalizedChave);
    await loadManualLocations();
    if (!isApplicationUnlocked(normalizedChave)) {
      return false;
    }

    if (settings.showReadyMessage) {
      setStatus('Autenticação concluída. Atualizando a aplicação...', 'info');
    }

    await runLifecycleUpdateSequence({ ignoreCooldown: true });
    return true;
  }

  async function refreshAuthenticationStatus(chave, options) {
    const settings = options || {};
    const normalizedChave = sanitizeChave(chave);

    if (authStatusAbortController) {
      authStatusAbortController.abort();
      authStatusAbortController = null;
    }

    if (normalizedChave.length !== 4) {
      authState.chave = '';
      authState.found = false;
      authState.hasPassword = false;
      clearTypedPasswordAuthentication();
      authState.statusResolved = false;
      authState.statusErrored = false;
      clearProtectedClientState();
      syncFormControlStates();
      setAuthenticationPrompt();
      return null;
    }

    const requestToken = ++authStatusRequestToken;
    const controller = new AbortController();
    authStatusAbortController = controller;
    authState.chave = normalizedChave;
    authState.statusResolved = false;
    authState.statusLoading = true;
    authState.found = false;
    authState.hasPassword = false;
    authState.statusErrored = false;
    clearTypedPasswordAuthentication();
    syncFormControlStates();

    try {
      const payload = await fetchAuthenticationStatus(normalizedChave, controller.signal);
      if (requestToken !== authStatusRequestToken) {
        return null;
      }

      applyAuthenticationStatusPayload(payload);
      if (!payload.found || !payload.has_password) {
        persistPasswordForChave(normalizedChave, '');
      }
      if (payload.has_password && settings.schedulePasswordVerification !== false && clientState.isPasswordVerificationInputValid(passwordInput.value)) {
        schedulePasswordVerification({ showReadyMessage: true });
      }
      if (payload.has_password) {
        schedulePasswordAutofillSync();
      }
      return payload;
    } catch (error) {
      if (controller.signal.aborted) {
        return null;
      }

      applyAuthenticationLockedState({
        chave: normalizedChave,
        found: false,
        hasPassword: false,
        statusErrored: true,
        message: error instanceof Error ? error.message : 'Não foi possível consultar o status da senha.',
      });
      return null;
    } finally {
      if (authStatusAbortController === controller) {
        authStatusAbortController = null;
      }
      authState.statusLoading = false;
      syncFormControlStates();
    }
  }

  async function registerPasswordForCurrentUser() {
    const normalizedChave = getActiveChave();
    const password = passwordInput.value;

    if (normalizedChave.length !== 4) {
      setStatus('Informe uma chave com 4 caracteres alfanuméricos.', 'error');
      chaveInput.focus();
      return false;
    }

    if (!clientState.isPasswordLengthValid(password)) {
      setStatus('A senha deve ter entre 3 e 10 caracteres.', 'error');
      passwordInput.focus();
      return false;
    }

    await loadProjectCatalog({ showError: true });
    if (!allowedProjectValues.length) {
      setStatus('Nenhum projeto está disponível no momento.', 'error');
      return false;
    }

    passwordRegisterInProgress = true;
    syncFormControlStates();
    setStatus('Cadastrando senha...', 'info');

    try {
      const response = await fetch(authRegisterEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          chave: normalizedChave,
          projeto: projectSelect.value,
          senha: password,
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw createRequestError(response, payload);
      }

      authState.chave = normalizedChave;
      authState.found = true;
      authState.hasPassword = true;
      authState.authenticated = true;
      authState.passwordVerified = true;
      authState.statusResolved = true;
      authState.statusErrored = false;
      lastVerifiedPassword = password;
      lastObservedPasswordFieldValue = password;
      persistPasswordForChave(normalizedChave, password);
      syncFormControlStates();
      dismissActiveKeyboard();
      setStatus('Usuário autenticado. Iniciando atualizações.', 'success');
      await loadAuthenticatedApplication(normalizedChave, { showReadyMessage: false });
      return true;
    } catch (error) {
      if (isUnknownUserError(error)) {
        openRegistrationDialog();
        return false;
      }
      setStatus(error instanceof Error ? error.message : 'Não foi possível cadastrar a senha.', 'error');
      return false;
    } finally {
      passwordRegisterInProgress = false;
      syncFormControlStates();
    }
  }

  async function attemptPasswordLogin(options) {
    const settings = options || {};
    const normalizedChave = getActiveChave();
    const password = passwordInput.value;
    const verificationToken = Number.isInteger(settings.verificationToken) ? settings.verificationToken : 0;

    if (normalizedChave.length !== 4 || !authState.hasPassword) {
      return false;
    }

    if (isApplicationUnlocked(normalizedChave) && password === lastVerifiedPassword) {
      return true;
    }

    const canVerifyPassword = settings.allowPartialVerification
      ? clientState.isPasswordVerificationInputValid(password)
      : clientState.isPasswordLengthValid(password);

    if (!canVerifyPassword) {
      if (!settings.silentValidation) {
        setStatus(
          settings.allowPartialVerification
            ? 'Digite sua senha para iniciar.'
            : 'A senha deve ter entre 3 e 10 caracteres.',
          'error'
        );
      }
      return false;
    }

    passwordLoginInProgress = true;
    syncFormControlStates();
    if (!settings.silentValidation) {
      setStatus('Senha sendo verificada.', 'neutral');
    }

    try {
      const response = await fetch(authLoginEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          chave: normalizedChave,
          senha: password,
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw createRequestError(response, payload);
      }

      if (isStalePasswordVerificationAttempt(normalizedChave, password, verificationToken)) {
        void logoutWebSession({ silent: true });
        return false;
      }

      authState.chave = normalizedChave;
      authState.found = true;
      authState.hasPassword = true;
      authState.authenticated = true;
      authState.passwordVerified = true;
      authState.statusResolved = true;
      authState.statusErrored = false;
      lastVerifiedPassword = password;
      lastObservedPasswordFieldValue = password;
      persistPasswordForChave(normalizedChave, password);
      syncFormControlStates();

      dismissActiveKeyboard();
      if (settings.showReadyMessage !== false) {
        setStatus('Usuário autenticado. Iniciando atualizações.', 'success');
      }
      await loadAuthenticatedApplication(normalizedChave, { showReadyMessage: false });
      return true;
    } catch (error) {
      if (isStalePasswordVerificationAttempt(normalizedChave, password, verificationToken)) {
        return false;
      }

      if (isUnknownUserError(error)) {
        closePasswordDialog();
        openRegistrationDialog();
        return false;
      }

      applyAuthenticationLockedState({
        chave: normalizedChave,
        found: true,
        hasPassword: true,
        message: settings.allowPartialVerification
          ? 'Digite sua senha para iniciar.'
          : (error instanceof Error ? error.message : 'Não foi possível validar a senha.'),
      });
      return false;
    } finally {
      passwordLoginInProgress = false;
      syncFormControlStates();
    }
  }

  async function submitPasswordChange(event) {
    event.preventDefault();

    const normalizedChave = getActiveChave();
    const registerPasswordMode = isPasswordRegistrationDialogMode();
    const oldPassword = oldPasswordInput.value;
    const newPassword = newPasswordInput.value;
    const confirmPassword = confirmPasswordInput.value;

    if (normalizedChave.length !== 4) {
      setStatus('Informe uma chave com 4 caracteres alfanuméricos.', 'error');
      closePasswordDialog();
      return;
    }

    if (!registerPasswordMode && !clientState.isPasswordLengthValid(oldPassword)) {
      setStatus('A senha antiga deve ter entre 3 e 10 caracteres.', 'error');
      oldPasswordInput.focus();
      return;
    }

    if (!clientState.isPasswordLengthValid(newPassword)) {
      setStatus('A nova senha deve ter entre 3 e 10 caracteres.', 'error');
      newPasswordInput.focus();
      return;
    }

    if (newPassword !== confirmPassword) {
      setStatus('A confirmação da nova senha não confere.', 'error');
      confirmPasswordInput.focus();
      return;
    }

    passwordChangeInProgress = true;
    syncFormControlStates();
    setStatus(registerPasswordMode ? 'Salvando senha...' : 'Alterando senha...', 'info');

    try {
      if (registerPasswordMode) {
        await loadProjectCatalog({ showError: true });
        if (!allowedProjectValues.length) {
          setStatus('Nenhum projeto está disponível no momento.', 'error');
          return;
        }
      }

      const response = await fetch(registerPasswordMode ? authRegisterEndpoint : authChangeEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(
          registerPasswordMode
            ? {
              chave: normalizedChave,
              projeto: projectSelect.value,
              senha: newPassword,
            }
            : {
              chave: normalizedChave,
              senha_antiga: oldPassword,
              nova_senha: newPassword,
            }
        ),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw createRequestError(response, payload);
      }

      authState.chave = normalizedChave;
      authState.found = true;
      authState.hasPassword = true;
      authState.authenticated = true;
      authState.passwordVerified = true;
      authState.statusResolved = true;
      authState.statusErrored = false;
      lastVerifiedPassword = newPassword;
      lastObservedPasswordFieldValue = newPassword;
      passwordInput.value = newPassword;
      persistPasswordForChave(normalizedChave, newPassword);
      closePasswordDialog();
      dismissActiveKeyboard();
      setStatus('Usuário autenticado. Iniciando atualizações.', 'success');
      await loadAuthenticatedApplication(normalizedChave, { showReadyMessage: false });
    } catch (error) {
      if (isUnknownUserError(error)) {
        closePasswordDialog();
        openRegistrationDialog();
        return;
      }
      setStatus(error instanceof Error ? error.message : 'Não foi possível alterar a senha.', 'error');
    } finally {
      passwordChangeInProgress = false;
      syncFormControlStates();
    }
  }

  async function submitUserSelfRegistration(event) {
    event.preventDefault();

    await loadProjectCatalog({ showError: true });
    if (!allowedProjectValues.length) {
      setStatus('Nenhum projeto está disponível no momento.', 'error');
      return;
    }

    const normalizedChave = sanitizeChave(registrationChaveInput.value);
    const nome = String(registrationNameInput.value || '').trim().replace(/\s+/g, ' ');
    const projeto = registrationProjectSelect.value;
    const email = String(registrationEmailInput.value || '').trim();
    const password = registrationPasswordInput.value;
    const confirmPassword = registrationConfirmPasswordInput.value;

    registrationChaveInput.value = normalizedChave;
    registrationNameInput.value = nome;
    registrationEmailInput.value = email;

    if (normalizedChave.length !== 4) {
      setStatus('Informe uma chave com 4 caracteres alfanuméricos.', 'error');
      registrationChaveInput.focus();
      return;
    }

    if (nome.length < 3) {
      setStatus('Informe o nome completo.', 'error');
      registrationNameInput.focus();
      return;
    }

    if (!String(projeto || '').trim()) {
      setStatus('Selecione um projeto.', 'error');
      registrationProjectSelect.focus();
      return;
    }

    if (email && email.indexOf('@') === -1) {
      setStatus('Informe um e-mail válido ou deixe o campo em branco.', 'error');
      registrationEmailInput.focus();
      return;
    }

    if (!clientState.isPasswordLengthValid(password)) {
      setStatus('A senha deve ter entre 3 e 10 caracteres.', 'error');
      registrationPasswordInput.focus();
      return;
    }

    if (password !== confirmPassword) {
      setStatus('A confirmação da nova senha não confere.', 'error');
      registrationConfirmPasswordInput.focus();
      return;
    }

    userSelfRegistrationInProgress = true;
    syncFormControlStates();
  setStatus('Enviando solicitação de cadastro...', 'info');

    try {
      const response = await fetch(authUserRegisterEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          chave: normalizedChave,
          nome,
          projeto,
          email: email || null,
          senha: password,
          confirmar_senha: confirmPassword,
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw createRequestError(response, payload);
      }

      chaveInput.value = normalizedChave;
      passwordInput.value = password;
      lastCommittedProjectValue = normalizeKnownProjectValue(projeto, defaultProjectValue);
      syncProjectSelectOptions({ mainValue: lastCommittedProjectValue, registrationValue: lastCommittedProjectValue });
      writePersistedChave(normalizedChave);
      persistCurrentUserSettings();

      authState.chave = normalizedChave;
      authState.found = true;
      authState.hasPassword = true;
      authState.authenticated = true;
      authState.passwordVerified = true;
      authState.statusResolved = true;
      lastVerifiedPassword = password;
      lastObservedPasswordFieldValue = password;
      persistPasswordForChave(normalizedChave, password);

      closeRegistrationDialog();
      dismissActiveKeyboard();
      syncFormControlStates();
      await loadAuthenticatedApplication(normalizedChave, { showReadyMessage: false });
      setStatus('Cadastro concluído com sucesso.', 'success');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Não foi possível enviar a solicitação de cadastro.', 'error');
    } finally {
      userSelfRegistrationInProgress = false;
      syncFormControlStates();
    }
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

  function readPersistedUserPasswordMap() {
    try {
      const rawValue = window.localStorage.getItem(userPasswordStorageKey);
      if (!rawValue) {
        return {};
      }

      const parsedValue = JSON.parse(rawValue);
      return parsedValue && typeof parsedValue === 'object' ? parsedValue : {};
    } catch {
      return {};
    }
  }

  function writePersistedUserPasswordMap(passwordMap) {
    try {
      window.localStorage.setItem(userPasswordStorageKey, JSON.stringify(passwordMap));
    } catch {
      // Ignore browsers with unavailable storage.
    }
  }

  function normalizeKnownProjectValue(projectValue, fallbackProject) {
    const normalizedFallback = String(fallbackProject || defaultProjectValue || allowedProjectValues[0] || '').trim().toUpperCase();
    return clientState.normalizeProjectValue(projectValue, allowedProjectValues, normalizedFallback);
  }

  function syncProjectSelectOptions(options) {
    const settings = options || {};
    const mainValue = normalizeKnownProjectValue(
      settings.mainValue !== undefined ? settings.mainValue : projectSelect.value,
      defaultProjectValue
    );
    const registrationValue = normalizeKnownProjectValue(
      settings.registrationValue !== undefined ? settings.registrationValue : (registrationProjectSelect.value || mainValue),
      mainValue || defaultProjectValue
    );

    [
      [projectSelect, mainValue],
      [registrationProjectSelect, registrationValue],
    ].forEach(([selectElement, selectedValue]) => {
      if (!selectElement) {
        return;
      }

      selectElement.textContent = '';
      if (!allowedProjectValues.length) {
        const placeholderOption = document.createElement('option');
        placeholderOption.value = '';
        placeholderOption.textContent = projectCatalogLoading ? 'Carregando projetos...' : 'Nenhum projeto disponível';
        selectElement.appendChild(placeholderOption);
        selectElement.value = '';
        return;
      }

      allowedProjectValues.forEach((projectName) => {
        const option = document.createElement('option');
        option.value = projectName;
        option.textContent = projectName;
        selectElement.appendChild(option);
      });
      selectElement.value = selectedValue;
    });
  }

  function setProjectCatalog(projectRows, options) {
    const settings = options || {};
    const nextProjects = Array.from(new Set(
      (Array.isArray(projectRows) ? projectRows : [])
        .map((projectRow) => String(projectRow && projectRow.name || '').trim().toUpperCase())
        .filter(Boolean)
    ));

    allowedProjectValues = nextProjects;
    defaultProjectValue = nextProjects[0] || '';
    lastCommittedProjectValue = normalizeKnownProjectValue(lastCommittedProjectValue, defaultProjectValue);
    syncProjectSelectOptions({
      mainValue: settings.mainValue !== undefined ? settings.mainValue : projectSelect.value,
      registrationValue:
        settings.registrationValue !== undefined
          ? settings.registrationValue
          : (registrationProjectSelect.value || projectSelect.value),
    });
    syncFormControlStates();
  }

  async function loadProjectCatalog(options) {
    if (projectCatalogPromise) {
      return projectCatalogPromise;
    }

    const settings = options || {};
    projectCatalogLoading = true;
    syncProjectSelectOptions();
    syncFormControlStates();
    projectCatalogPromise = fetch(projectsEndpoint, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
    })
      .then(async (response) => {
        const payload = await response.json().catch(() => ([]));
        if (!response.ok) {
          throw createRequestError(response, payload);
        }

        setProjectCatalog(payload, settings);
        return allowedProjectValues;
      })
      .catch((error) => {
        if (settings.showError !== false) {
          setStatus(error instanceof Error ? error.message : 'Não foi possível carregar os projetos.', 'error');
        }
        syncProjectSelectOptions();
        return allowedProjectValues;
      })
      .finally(() => {
        projectCatalogLoading = false;
        syncProjectSelectOptions();
        syncFormControlStates();
        projectCatalogPromise = null;
      });

    return projectCatalogPromise;
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

    syncProjectSelectOptions({
      mainValue: resolvedSettings.project,
      registrationValue: resolvedSettings.project,
    });
    if (automaticActivitiesToggle) {
      automaticActivitiesToggle.checked = resolvedSettings.automaticActivitiesEnabled;
    }
  }

  function restorePersistedPasswordForChave(chave) {
    const resolvedPassword = clientState.resolvePersistedPassword(
      readPersistedUserPasswordMap(),
      chave
    );
    passwordInput.value = resolvedPassword;
    lastObservedPasswordFieldValue = resolvedPassword;
  }

  function restorePersistedUserSettingsForChave(chave) {
    applyPersistedUserSettings(chave);
    syncAutomaticActivitiesAvailability();
    syncProjectVisibility();
  }

  function persistPasswordForChave(chave, password) {
    const normalizedChave = sanitizeChave(chave);
    if (normalizedChave.length !== 4) {
      return;
    }

    const nextPasswordMap = clientState.withPersistedPassword(
      readPersistedUserPasswordMap(),
      normalizedChave,
      password
    );
    writePersistedUserPasswordMap(nextPasswordMap);
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
        project: normalizeKnownProjectValue(projectSelect.value, defaultProjectValue),
        automaticActivitiesEnabled: Boolean(
          automaticActivitiesToggle && automaticActivitiesToggle.checked
        ),
      },
      resolveCurrentUserSettingsDefaults()
    );
    writePersistedUserSettingsMap(nextSettingsMap);
  }

  async function updateCurrentUserProjectSelection() {
    const normalizedChave = getActiveChave();
    const nextProject = normalizeKnownProjectValue(projectSelect.value, lastCommittedProjectValue || defaultProjectValue);
    syncProjectSelectOptions({ mainValue: nextProject });

    if (normalizedChave.length !== 4 || !isApplicationUnlocked(normalizedChave) || isAutomaticActivitiesEnabled()) {
      persistCurrentUserSettings();
      syncFormControlStates();
      return false;
    }

    projectUpdateInProgress = true;
    syncFormControlStates();
    try {
      const response = await fetch(projectUpdateEndpoint, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          chave: normalizedChave,
          projeto: nextProject,
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw buildProtectedRequestError(response, payload);
      }

      const committedProject = normalizeKnownProjectValue(payload && payload.project, nextProject);
      lastCommittedProjectValue = committedProject;
      syncProjectSelectOptions({ mainValue: committedProject });
      if (latestHistoryState && typeof latestHistoryState === 'object') {
        latestHistoryState.projeto = committedProject;
      }
      persistCurrentUserSettings();
      await loadManualLocations();
      setStatus(payload && payload.message ? payload.message : 'Projeto atualizado com sucesso.', 'success');
      return true;
    } catch (error) {
      if (error && error.isAuthExpired) {
        return false;
      }

      syncProjectSelectOptions({ mainValue: lastCommittedProjectValue || defaultProjectValue });
      setStatus(error instanceof Error ? error.message : 'Não foi possível atualizar o projeto.', 'error');
      return false;
    } finally {
      projectUpdateInProgress = false;
      syncFormControlStates();
    }
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
    if (!isApplicationUnlocked(chave)) {
      return Promise.reject(new Error('Digite sua senha para iniciar.'));
    }

    return fetch(`${stateEndpoint}?chave=${encodeURIComponent(chave)}`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
    }).then(async (response) => {
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw buildProtectedRequestError(response, payload);
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

  function shouldAttemptAutomaticNearbyWorkplaceCheckIn(locationPayload, remoteState) {
    return automaticActivities.shouldAttemptAutomaticNearbyWorkplaceCheckIn(locationPayload, remoteState);
  }

  function resolveAutomaticCheckInLocation(locationPayload) {
    return automaticActivities.resolveAutomaticCheckInLocation(locationPayload);
  }

  async function submitAutomaticActivity({ action, local, suppressStatus }) {
    const chave = sanitizeChave(chaveInput.value);
    if (!isApplicationUnlocked(chave)) {
      throw new Error('Digite sua senha para iniciar.');
    }

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
      throw buildProtectedRequestError(response, payload);
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

    if (!isAutomaticActivitiesEnabled() || !gpsLocationPermissionGranted || !isApplicationUnlocked()) {
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

    if (locationPayload && shouldAttemptAutomaticNearbyWorkplaceCheckIn(locationPayload, remoteState)) {
      const automaticLocal = resolveAutomaticCheckInLocation(locationPayload);
      await submitAutomaticActivity({
        action: 'checkin',
        local: automaticLocal,
        suppressStatus: settings.suppressStatus,
      });
      return {
        performed: true,
        action: 'checkin',
        local: automaticLocal,
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

  function canShowAutomaticActivitiesField() {
    return gpsLocationPermissionGranted || readStorageFlag(locationPermissionGrantedKey);
  }

  function syncAutomaticActivitiesAvailability() {
    const showAutomaticActivitiesField = canShowAutomaticActivitiesField();

    if (automaticActivitiesField) {
      automaticActivitiesField.classList.toggle('is-hidden', !showAutomaticActivitiesField);
      automaticActivitiesField.setAttribute('aria-hidden', String(!showAutomaticActivitiesField));
    }

    if (!showAutomaticActivitiesField && automaticActivitiesToggle) {
      automaticActivitiesToggle.checked = false;
    }
  }

  function setGpsLocationPermissionGranted(value) {
    gpsLocationPermissionGranted = Boolean(value);
    syncAutomaticActivitiesAvailability();
    syncProjectVisibility();
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
    if (!isApplicationUnlocked()) {
      availableLocations = [];
      syncManualLocationControl();
      return;
    }

    try {
      const response = await fetch(locationsEndpoint, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw buildProtectedRequestError(response, payload);
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
    if (!isApplicationUnlocked()) {
      throw new Error('Digite sua senha para iniciar.');
    }

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
      throw buildProtectedRequestError(response, payload);
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
    if (!isApplicationUnlocked()) {
      throw new Error('Digite sua senha para iniciar.');
    }

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

  function resolveLatestHistoryAction(state) {
    const lastCheckinAt = parseHistoryTimestamp(state && state.last_checkin_at);
    const lastCheckoutAt = parseHistoryTimestamp(state && state.last_checkout_at);

    if (lastCheckinAt && lastCheckoutAt) {
      return lastCheckinAt >= lastCheckoutAt ? 'checkin' : 'checkout';
    }

    if (lastCheckinAt) {
      return 'checkin';
    }

    if (lastCheckoutAt) {
      return 'checkout';
    }

    return null;
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
    const latestAction = resolveLatestHistoryAction(state);

    if (latestAction === 'checkin') {
      setSelectedAction('checkout');
      return;
    }

    if (latestAction === 'checkout') {
      setSelectedAction('checkin');
      return;
    }

    setSelectedAction('checkin');
  }

  function syncLatestHistoryHighlight(state) {
    const latestAction = resolveLatestHistoryAction(state);

    if (lastCheckinItem) {
      lastCheckinItem.classList.toggle('is-latest-activity', latestAction === 'checkin');
    }
    if (lastCheckoutItem) {
      lastCheckoutItem.classList.toggle('is-latest-activity', latestAction === 'checkout');
    }
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
    if (state && state.projeto) {
      const committedProject = normalizeKnownProjectValue(state.projeto, defaultProjectValue);
      lastCommittedProjectValue = committedProject;
      syncProjectSelectOptions({ mainValue: committedProject });
      persistCurrentUserSettings();
    }
    renderHistoryValue(lastCheckinValue, state && state.last_checkin_at);
    renderHistoryValue(lastCheckoutValue, state && state.last_checkout_at);
    syncLatestHistoryHighlight(state);
    applySuggestedActionFromHistory(state);
    renderTransportScreen();
    syncFormControlStates();
  }

  function resetHistory(message) {
    applyHistoryState(null);
    if (message) {
      setHistoryMessage(message);
    }
  }

  async function refreshHistory(chave, options) {
    const settings = options || {};
    const normalized = sanitizeChave(chave);

    if (historyAbortController) {
      historyAbortController.abort();
      historyAbortController = null;
    }

    if (normalized.length !== 4) {
      resetHistory();
      return;
    }

    if (!isApplicationUnlocked(normalized)) {
      resetHistory();
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
        throw buildProtectedRequestError(response, payload);
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

      if (error && error.isAuthExpired) {
        if (settings.rethrowErrors) {
          throw error;
        }
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
    if (normalized.length !== 4 || !isApplicationUnlocked(normalized)) {
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
      if (error && error.isAuthExpired) {
        return false;
      }

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
    if (isUserInteractionLocked() || !isApplicationUnlocked()) {
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

    if (!isApplicationUnlocked(normalizedChave)) {
      setAuthenticationPrompt();
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
        if (error && error.isAuthExpired) {
          return;
        }

        const message = error instanceof Error
          ? error.message
          : 'Não foi possível concluir as atualizações automáticas neste momento.';
        setStatus(message, 'error');
      }
    });
  }

  function syncProjectVisibility() {
    const hideProjectField = isAutomaticActivitiesEnabled();
    const hideLocationField = isAutomaticActivitiesEnabled() || gpsLocationPermissionGranted;

    projectField.classList.toggle('is-hidden', hideProjectField);
    projectField.setAttribute('aria-hidden', String(hideProjectField));
    locationSelectField.classList.toggle('is-hidden', hideLocationField);
    locationSelectField.setAttribute('aria-hidden', String(hideLocationField));

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

  function prepareChaveInputForNewEntry() {
    const hasVisibleValue = hasPendingAuthFieldRestoreState()
      ? Boolean(pendingAuthFieldRestoreState.chave || pendingAuthFieldRestoreState.password)
      : Boolean(chaveInput.value || passwordInput.value);
    if (!hasVisibleValue) {
      return;
    }

    rememberPendingAuthFieldRestoreState('chave');

    chaveInput.value = '';
    passwordInput.value = '';
    lastObservedPasswordFieldValue = '';
  }

  function preparePasswordInputForNewEntry() {
    const hasVisiblePassword = hasPendingAuthFieldRestoreState()
      ? Boolean(pendingAuthFieldRestoreState.password)
      : Boolean(passwordInput.value);
    if (!hasVisiblePassword) {
      return;
    }

    rememberPendingAuthFieldRestoreState('password');

    passwordInput.value = '';
    lastObservedPasswordFieldValue = '';
  }

  chaveInput.addEventListener('pointerdown', () => {
    prepareChaveInputForNewEntry();
  });

  passwordInput.addEventListener('pointerdown', () => {
    preparePasswordInputForNewEntry();
  });

  chaveInput.addEventListener('input', () => {
    clearPendingAuthFieldRestoreState();
    const previousChave = authState.chave;
    const sanitized = sanitizeChave(chaveInput.value);
    if (sanitized !== chaveInput.value) {
      chaveInput.value = sanitized;
    }
    writePersistedChave(sanitized);

    const shouldResetResolvedKeyState = sanitized !== previousChave && (
      previousChave.length === 4
      || Boolean(passwordInput.value)
      || authState.hasPassword
      || authState.authenticated
      || authState.passwordVerified
      || authState.statusResolved
    );

    if (shouldResetResolvedKeyState) {
      clearTypedPasswordAuthentication();
      authState.found = false;
      authState.hasPassword = false;
      authState.statusResolved = false;
      authState.statusErrored = false;
      passwordInput.value = '';
      closePasswordDialog();
      closeRegistrationDialog();
      clearProtectedClientState();
      void logoutWebSession({ silent: true });
    }

    if (sanitized.length === 4) {
      restorePersistedUserSettingsForChave(sanitized);
      restorePersistedPasswordForChave(sanitized);
      void refreshAuthenticationStatus(sanitized, {
        schedulePasswordVerification: true,
      });

      if (document.activeElement === chaveInput) {
        dismissActiveKeyboard();
      }
      return;
    }

    if (authStatusAbortController) {
      authStatusAbortController.abort();
      authStatusAbortController = null;
    }

    authState.chave = '';
    authState.found = false;
    authState.hasPassword = false;
    clearTypedPasswordAuthentication();
    authState.statusResolved = false;
    authState.statusErrored = false;
    clearProtectedClientState();
    syncFormControlStates();
    setAuthenticationPrompt();
  });

  passwordInput.addEventListener('input', () => {
    clearPendingAuthFieldRestoreState();
    syncPasswordInputState({ showReadyMessage: true });
  });

  passwordInput.addEventListener('change', () => {
    syncPasswordInputState({ showReadyMessage: true });
    if (authState.hasPassword && clientState.isPasswordVerificationInputValid(passwordInput.value)) {
      void attemptPasswordLogin({
        silentValidation: true,
        showReadyMessage: true,
        allowPartialVerification: true,
      });
    }
  });

  passwordInput.addEventListener('focus', () => {
    lastObservedPasswordFieldValue = passwordInput.value;
    schedulePasswordAutofillSync();
  });

  passwordInput.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') {
      return;
    }

    event.preventDefault();
    if (authState.hasPassword) {
      void attemptPasswordLogin({ showReadyMessage: true, allowPartialVerification: true });
      return;
    }

    if (authState.statusResolved && !authState.found) {
      openRegistrationDialog();
      return;
    }

    if (authState.statusResolved && authState.found && !authState.hasPassword) {
      openPasswordDialog();
    }
  });

  passwordActionButton.addEventListener('click', () => {
    if (authState.statusResolved && !authState.found) {
      openRegistrationDialog();
      return;
    }

    if (authState.statusResolved && authState.found && !authState.hasPassword) {
      openPasswordDialog();
      return;
    }

    if (authState.hasPassword) {
      openPasswordDialog();
    }
  });

  if (requestRegistrationButton) {
    requestRegistrationButton.addEventListener('click', () => {
      openRegistrationDialog();
    });
  }

  document.addEventListener('pointerdown', restorePendingAuthFieldValuesOnExternalFocus, true);
  document.addEventListener('focusin', restorePendingAuthFieldValuesOnExternalFocus, true);

  if (transportButton) {
    transportButton.addEventListener('click', openTransportScreen);
  }

  if (transportAddressToggleButton) {
    transportAddressToggleButton.addEventListener('click', () => {
      if (transportUiState.addressEditorOpen) {
        closeTransportAddressEditor();
        return;
      }
      openTransportAddressEditor();
    });
  }

  if (transportAddressBackButton) {
    transportAddressBackButton.addEventListener('click', closeTransportAddressEditor);
  }

  if (transportAddressForm) {
    transportAddressForm.addEventListener('submit', submitTransportAddress);
  }

  if (transportZipInput) {
    transportZipInput.addEventListener('input', () => {
      const digitsOnly = String(transportZipInput.value || '').replace(/\D/g, '').slice(0, 6);
      if (digitsOnly !== transportZipInput.value) {
        transportZipInput.value = digitsOnly;
      }
    });
  }

  if (transportRegularButton) {
    transportRegularButton.addEventListener('click', () => {
      initializeTransportRequestBuilder('regular');
    });
  }

  if (transportWeekendButton) {
    transportWeekendButton.addEventListener('click', () => {
      initializeTransportRequestBuilder('weekend');
    });
  }

  if (transportExtraButton) {
    transportExtraButton.addEventListener('click', () => {
      initializeTransportRequestBuilder('extra');
    });
  }

  if (transportRequestBuilderBackButton) {
    transportRequestBuilderBackButton.addEventListener('click', closeTransportRequestBuilder);
  }

  if (transportRequestBuilderForm) {
    transportRequestBuilderForm.addEventListener('submit', submitTransportRequestBuilder);
  }

  if (transportAcknowledgementCheckbox) {
    transportAcknowledgementCheckbox.addEventListener('change', () => {
      transportUiState.acknowledgementChecked = transportAcknowledgementCheckbox.checked;
      syncFormControlStates();
    });
  }

  if (transportAcknowledgementButton) {
    transportAcknowledgementButton.addEventListener('click', () => {
      void acknowledgeTransportInformation();
    });
  }

  if (transportRequestDetailCloseButton) {
    transportRequestDetailCloseButton.addEventListener('click', closeTransportRequestDetailWidget);
  }

  if (transportRequestDetailBackdrop) {
    transportRequestDetailBackdrop.addEventListener('click', closeTransportRequestDetailWidget);
  }

  if (transportRequestHistoryList) {
    transportRequestHistoryList.addEventListener('pointerdown', (event) => {
      beginTransportRequestSwipe(event);
    });

    transportRequestHistoryList.addEventListener('pointermove', (event) => {
      updateTransportRequestSwipe(event);
    });

    transportRequestHistoryList.addEventListener('pointerup', (event) => {
      endTransportRequestSwipe(event);
    });

    transportRequestHistoryList.addEventListener('pointercancel', (event) => {
      endTransportRequestSwipe(event);
    });

    transportRequestHistoryList.addEventListener('click', (event) => {
      const targetElement = resolveTransportEventTargetElement(event);
      const realizedButton = targetElement
        ? targetElement.closest('[data-transport-request-realized="true"][data-request-id]')
        : null;
      if (realizedButton) {
        const requestId = Number(realizedButton.getAttribute('data-request-id'));
        if (Number.isFinite(requestId)) {
          markTransportRequestAsRealized(requestId);
        }
        return;
      }

      const cancelButton = targetElement
        ? targetElement.closest('[data-transport-request-cancel="true"][data-request-id]')
        : null;
      if (cancelButton) {
        const requestId = Number(cancelButton.getAttribute('data-request-id'));
        if (Number.isFinite(requestId)) {
          void cancelTransportRequest(requestId);
        }
        return;
      }

      const requestButton = targetElement
        ? targetElement.closest('.transport-request-card[data-request-id]')
        : null;
      if (!requestButton) {
        return;
      }
      const requestId = Number(requestButton.getAttribute('data-request-id'));
      if (
        Number.isFinite(requestId)
        && Number(transportRequestSwipeState.suppressedClickRequestId) === requestId
      ) {
        transportRequestSwipeState.suppressedClickRequestId = null;
        return;
      }
      if (requestButton.getAttribute('aria-disabled') === 'true') {
        return;
      }

      if (!Number.isFinite(requestId)) {
        return;
      }

      selectTransportRequest(requestId, { openDetails: true });
    });

    transportRequestHistoryList.addEventListener('keydown', (event) => {
      const targetElement = resolveTransportEventTargetElement(event);
      const realizedButton = targetElement
        ? targetElement.closest('[data-transport-request-realized="true"][data-request-id]')
        : null;
      if (realizedButton) {
        return;
      }

      const cancelButton = targetElement
        ? targetElement.closest('[data-transport-request-cancel="true"][data-request-id]')
        : null;
      if (cancelButton) {
        return;
      }

      const requestCard = targetElement
        ? targetElement.closest('.transport-request-card[data-request-id]')
        : null;
      if (!requestCard || (event.key !== 'Enter' && event.key !== ' ')) {
        return;
      }
      if (requestCard.getAttribute('aria-disabled') === 'true') {
        return;
      }

      event.preventDefault();
      const requestId = Number(requestCard.getAttribute('data-request-id'));
      if (Number.isFinite(requestId)) {
        selectTransportRequest(requestId, { openDetails: true });
      }
    });
  }

  if (transportScreenHeaderBackButton) {
    transportScreenHeaderBackButton.addEventListener('click', closeTransportScreen);
  }

  if (transportScreenBackdrop) {
    transportScreenBackdrop.addEventListener('click', closeTransportScreen);
  }

  actionInputs.forEach((input) => {
    input.addEventListener('change', syncProjectVisibility);
  });

  projectSelect.addEventListener('change', () => {
    void updateCurrentUserProjectSelection();
  });

  if (automaticActivitiesToggle) {
    automaticActivitiesToggle.addEventListener('change', () => {
      persistCurrentUserSettings();
      syncProjectVisibility();
      if (automaticActivitiesToggle.checked) {
        void runAutomaticActivitiesEnableSequence();
        return;
      }

      if (gpsLocationPermissionGranted && isApplicationUnlocked()) {
        void runLifecycleUpdateSequence({ ignoreCooldown: true });
        return;
      }

      setStatus('Atividades automáticas desabilitadas.', 'success');
    });
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      scheduleViewportLayoutMetricsSync();
      syncPortraitLockState();
      schedulePasswordAutofillSync();
      void runLifecycleUpdateSequence();
      if (isTransportScreenOpen()) {
        void loadTransportState();
      }
    }
  });

  window.addEventListener('focus', () => {
    scheduleViewportLayoutMetricsSync();
    syncPortraitLockState();
    schedulePasswordAutofillSync();
    void runLifecycleUpdateSequence();
    if (isTransportScreenOpen()) {
      void loadTransportState();
    }
  });
  window.addEventListener('pageshow', () => {
    scheduleViewportLayoutMetricsSync();
    syncPortraitLockState();
    schedulePasswordAutofillSync();
    void runLifecycleUpdateSequence();
    if (isTransportScreenOpen()) {
      void loadTransportState();
    }
  });
  window.addEventListener('resize', scheduleViewportLayoutMetricsSync);
  window.addEventListener('resize', syncPortraitLockState);
  window.addEventListener('orientationchange', () => {
    scheduleViewportLayoutMetricsSync();
    syncPortraitLockState();
    realignViewport();
  });
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', scheduleViewportLayoutMetricsSync);
    window.visualViewport.addEventListener('resize', syncPortraitLockState);
    window.visualViewport.addEventListener('scroll', scheduleViewportLayoutMetricsSync);
  }

  refreshLocationButton.addEventListener('click', () => {
    void runManualLocationRefreshSequence();
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const chave = sanitizeChave(chaveInput.value);
    const selectedAction = getSelectedValue('action');
    chaveInput.value = chave;

    if (isAutomaticActivitiesEnabled()) {
      setStatus('Desative Atividades Automáticas para registrar manualmente.', 'error');
      return;
    }

    if (chave.length !== 4) {
      setStatus('Informe uma chave com 4 caracteres alfanuméricos.', 'error');
      chaveInput.focus();
      return;
    }

    if (!isApplicationUnlocked(chave)) {
      setAuthenticationPrompt();
      passwordInput.focus();
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
        throw buildProtectedRequestError(response, payload);
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
      if (error && error.isAuthExpired) {
        return;
      }

      const message = error instanceof Error ? error.message : 'Falha de comunicação com a API.';
      setStatus(message, 'error');
    } finally {
      setSubmitting(false);
    }
  });

  if (passwordDialogBackButton) {
    passwordDialogBackButton.addEventListener('click', closePasswordDialog);
  }

  if (passwordDialogBackdrop) {
    passwordDialogBackdrop.addEventListener('click', closePasswordDialog);
  }

  if (passwordChangeForm) {
    passwordChangeForm.addEventListener('submit', submitPasswordChange);
  }

  [oldPasswordInput, newPasswordInput, confirmPasswordInput].filter(Boolean).forEach((input) => {
    input.addEventListener('input', () => {
      syncFormControlStates();
    });
  });

  if (registrationDialogBackButton) {
    registrationDialogBackButton.addEventListener('click', closeRegistrationDialog);
  }

  if (registrationDialogBackdrop) {
    registrationDialogBackdrop.addEventListener('click', closeRegistrationDialog);
  }

  if (registrationForm) {
    registrationForm.addEventListener('submit', submitUserSelfRegistration);
  }

  if (registrationChaveInput) {
    registrationChaveInput.addEventListener('input', () => {
      const sanitized = sanitizeChave(registrationChaveInput.value);
      if (sanitized !== registrationChaveInput.value) {
        registrationChaveInput.value = sanitized;
      }
    });
  }

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && transportUiState.detailRequestId !== null) {
      closeTransportRequestDetailWidget();
      return;
    }

    if (event.key === 'Escape' && isTransportScreenOpen()) {
      closeTransportScreen();
      return;
    }

    if (event.key === 'Escape' && isRegistrationDialogOpen()) {
      closeRegistrationDialog();
      return;
    }

    if (event.key === 'Escape' && isPasswordDialogOpen()) {
      closePasswordDialog();
    }
  });

  syncProjectVisibility();
  scheduleViewportLayoutMetricsSync();
  syncPortraitLockState();
  syncAutomaticActivitiesToggle();
  clearProtectedClientState();
  syncFormControlStates();
  setAuthenticationPrompt();

  const persistedChave = readPersistedChave();
  void loadProjectCatalog({ showError: false }).finally(() => {
    if (!persistedChave) {
      return;
    }

    chaveInput.value = persistedChave;
    restorePersistedUserSettingsForChave(persistedChave);
    restorePersistedPasswordForChave(persistedChave);
    void logoutWebSession({ silent: true }).finally(() => {
      void refreshAuthenticationStatus(persistedChave, {
        schedulePasswordVerification: true,
      });
    });
  });
})();