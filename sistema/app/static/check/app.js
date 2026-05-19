(function () {
  const form = document.getElementById('checkForm');
  const appHeader = document.querySelector('body > header');
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
  const submitEndpoint = form.dataset.submitEndpoint || '/api/web/check';
  const stateEndpoint = form.dataset.stateEndpoint || '/api/web/check/state';
  const projectsEndpoint = form.dataset.projectsEndpoint || '/api/web/projects';
  const userProjectsEndpoint = form.dataset.userProjectsEndpoint || '/api/web/user-projects';
  const locationsEndpoint = form.dataset.locationsEndpoint || '/api/web/check/locations';
  const locationEndpoint = form.dataset.locationEndpoint || '/api/web/check/location';
  const automaticActivities = window.CheckingWebAutomaticActivities;
  const clientState = window.CheckingWebClientState;
  const checkI18n = window.CheckingWebI18n;
  const chaveInput = document.getElementById('chaveInput');
  const passwordInput = document.getElementById('passwordInput');
  const settingsButton = document.getElementById('settingsButton');
  const chaveAuthField = chaveInput ? chaveInput.closest('.auth-field') : null;
  const passwordAuthField = passwordInput ? passwordInput.closest('.auth-field') : null;
  const projectField = document.getElementById('projectField');
  const projectMembershipButton = document.getElementById('projectMembershipButton');
  const projectMembershipSummary = document.getElementById('projectMembershipSummary');
  const projectMembershipPanel = document.getElementById('projectMembershipPanel');
  const projectMembershipOptions = document.getElementById('projectMembershipOptions');
  const projectMembershipStatus = document.getElementById('projectMembershipStatus');
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
  const registrationProjectHint = document.getElementById('registrationProjectHint');
  const registrationProjectOptions = document.getElementById('registrationProjectOptions');
  const registrationEmailInput = document.getElementById('registrationEmailInput');
  const registrationPasswordInput = document.getElementById('registrationPasswordInput');
  const registrationConfirmPasswordInput = document.getElementById('registrationConfirmPasswordInput');
  const registrationDialogBackButton = document.getElementById('registrationDialogBackButton');
  const registrationDialogSubmitButton = document.getElementById('registrationDialogSubmitButton');
  const settingsDialog = document.getElementById('settingsDialog');
  const settingsDialogBackdrop = document.getElementById('settingsDialogBackdrop');
  const settingsLanguageSelect = document.getElementById('settingsLanguageSelect');
  const settingsResetPasswordButton = document.getElementById('settingsResetPasswordButton');
  const settingsLocationPermissionButton = document.getElementById('settingsLocationPermissionButton');
  const settingsSupportButton = document.getElementById('settingsSupportButton');
  const settingsAboutButton = document.getElementById('settingsAboutButton');
  const settingsDialogBackButton = document.getElementById('settingsDialogBackButton');
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
  const authControls = [chaveInput, passwordInput, settingsButton].filter(Boolean);
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
    registrationEmailInput,
    registrationPasswordInput,
    registrationConfirmPasswordInput,
    registrationDialogBackButton,
    registrationDialogSubmitButton,
  ].filter(Boolean);
  const settingsDialogControls = [
    settingsLanguageSelect,
    settingsResetPasswordButton,
    settingsLocationPermissionButton,
    settingsSupportButton,
    settingsAboutButton,
    settingsDialogBackButton,
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
    transportScreenHeaderBackButton,
  ].filter(Boolean);
  const storageKey = 'checking.web.user.chave';
  const userSettingsStorageKey = 'checking.web.user.settings.by-chave';
  const userPasswordStorageKey = 'checking.web.user.password.by-chave';
  const userTransportLocalStateStorageKey = 'checking.web.transport.local-state.by-chave';
  const locationPromptAttemptedKey = 'checking.web.user.location.prompt-attempted';
  const locationPermissionGrantedKey = 'checking.web.user.location.permission-granted';
  const locationMeasurementStorageKey = 'checking.web.location.measurement.enabled';
  const locationMeasurementConsoleLabel = '[checking.location.measurement]';
  const locationMeasurementSessionLimit = 120;
  const checkingWebSupportWhatsAppPhone = '5521992174446';
  const checkingWebManualPath = './manual.html';
  const DEFAULT_MIXED_ZONE_INTERVAL_MINUTES = 20;
  const defaultManualLocationLabel = 'Escritório Principal';
  const accuracyFallbackManualLocationLabel = 'Precisao Insuficiente';
  const transportAutoRefreshIntervalMs = 10000;
  const transportRealtimeRefreshDebounceMs = 220;
  let allowedProjectValues = [];
  let defaultProjectValue = allowedProjectValues[0] || '';
  let currentUserProjectValues = defaultProjectValue ? [defaultProjectValue] : [];
  let lastCommittedUserProjectValues = currentUserProjectValues.slice();
  const lifecycleTriggerCooldownMs = 1200;
  const lifecycleDataReuseWindowMs = 5000;
  const passwordVerificationDebounceMs = 260;
  const unknownWebUserDetail = 'A chave do usuario nao esta cadastrada';
  const automaticCheckoutLocation = automaticActivities.AUTOMATIC_CHECKOUT_LOCATION;
  const geolocationOptions = {
    enableHighAccuracy: true,
    maximumAge: 0,
    timeout: 20000,
  };
  const lifecycleLocationCapturePlan = Object.freeze({
    strategy: 'watch_window',
    minimumWindowMs: 0,
    maxWindowMs: 5000,
  });
  const enforcedLocationCapturePlan = Object.freeze({
    strategy: 'watch_window',
    minimumWindowMs: 3000,
    maxWindowMs: 7000,
  });
  const locationCapturePlansByTrigger = Object.freeze({
    startup: lifecycleLocationCapturePlan,
    submit_guard: enforcedLocationCapturePlan,
    manual_refresh: enforcedLocationCapturePlan,
    settings_permission: enforcedLocationCapturePlan,
    automatic_activities_enable: enforcedLocationCapturePlan,
    automatic_activities_disable: enforcedLocationCapturePlan,
    visibility: lifecycleLocationCapturePlan,
    focus: lifecycleLocationCapturePlan,
    pageshow: lifecycleLocationCapturePlan,
  });
  let weekdayFormatter = new Intl.DateTimeFormat('pt-BR', {
    weekday: 'long',
  });
  let dateFormatter = new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
  let timeFormatter = new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
  const transportRequestKindLabels = {};
  const transportRequestStatusLabels = {};
  const transportRequestWeekdayLabels = {};
  const transportRequestWeekdayFullLabels = {};
  const transportRequestBuilderConfigs = {
    regular: {
      subtitle: '',
      allowedWeekdays: [0, 1, 2, 3, 4],
      defaultSelectedWeekdays: [0, 1, 2, 3, 4],
      showWeekdays: true,
      showDate: false,
      showTime: false,
    },
    weekend: {
      subtitle: '',
      allowedWeekdays: [5, 6],
      defaultSelectedWeekdays: [5],
      showWeekdays: true,
      showDate: false,
      showTime: false,
    },
    extra: {
      subtitle: '',
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
  let locationMeasurementSessionCounter = 0;
  let locationMeasurementSessions = [];
  let locationRequestPromise = null;
  let currentLocationMatch = null;
  let currentLocationResolutionStatus = null;
  let latestHistoryState = null;
  let lastHistoryStateAppliedAt = 0;
  let lastHistoryStateAppliedChave = '';
  let recentLocationResolutionPayload = null;
  let recentLocationResolutionAt = 0;
  let recentLocationResolutionChave = '';
  let availableLocations = [];
  let locationAccuracyThresholdMeters = null;
  let mixedZoneIntervalMinutes = DEFAULT_MIXED_ZONE_INTERVAL_MINUTES;
  let gpsLocationPermissionGranted = false;
  let lastKnownLocationPermissionState = null;
  let lifecycleRefreshInProgress = false;
  let lifecycleUpdateRequestTimeoutId = null;
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
  let transportAutoRefreshTimeoutId = null;
  let transportRealtimeEventSource = null;
  let transportRealtimeStreamChave = '';
  let transportRealtimeRefreshTimeoutId = null;
  let transportRealtimeRefreshPending = false;
  let projectCatalogPromise = null;
  let projectCatalogLoading = false;
  let userProjectsLoading = false;
  let authenticatedApplicationLoadPromise = null;
  let authenticatedApplicationLoadFingerprint = '';
  let authenticatedApplicationReadyFingerprint = '';
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
  let currentAuthenticationAssistanceStateKey = '';
  let lastAutoOpenedAuthenticationAssistanceStateKey = '';
  let lastDismissedAuthenticationAssistanceStateKey = '';

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
    requests: [],
  };

  const transportUiState = {
    addressEditorOpen: false,
    requestBuilderKind: null,
    selectedRequestId: null,
    detailRequestId: null,
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

  function resolveCheckLanguageCode(languageCode, fallbackCode) {
    if (checkI18n && typeof checkI18n.resolveLanguageCode === 'function') {
      return checkI18n.resolveLanguageCode(languageCode, fallbackCode);
    }
    return String(languageCode || fallbackCode || 'pt').trim().toLowerCase() || 'pt';
  }

  function getActiveCheckLanguageCode() {
    if (checkI18n && typeof checkI18n.getActiveLanguageCode === 'function') {
      return checkI18n.getActiveLanguageCode();
    }
    return 'pt';
  }

  function setActiveCheckLanguageCode(languageCode) {
    if (checkI18n && typeof checkI18n.setActiveLanguageCode === 'function') {
      return checkI18n.setActiveLanguageCode(languageCode);
    }
    return resolveCheckLanguageCode(languageCode);
  }

  function getCheckLanguage(languageCode) {
    if (checkI18n && typeof checkI18n.getLanguage === 'function') {
      return checkI18n.getLanguage(languageCode || getActiveCheckLanguageCode());
    }
    return {
      code: 'pt',
      label: 'Portuguese',
      nativeLabel: 'Português',
      locale: 'pt-BR',
    };
  }

  function getCheckDictionary(languageCode) {
    if (checkI18n && typeof checkI18n.getDictionary === 'function') {
      return checkI18n.getDictionary(languageCode || getActiveCheckLanguageCode());
    }
    return {};
  }

  function t(keyPath, values) {
    if (checkI18n && typeof checkI18n.t === 'function') {
      return checkI18n.t(keyPath, values, getActiveCheckLanguageCode());
    }
    return String(keyPath || '');
  }

  function getCheckLocale() {
    const activeLanguage = getCheckLanguage();
    return activeLanguage && typeof activeLanguage.locale === 'string' && activeLanguage.locale
      ? activeLanguage.locale
      : 'pt-BR';
  }

  function createKnownDictionaryMessageIndex(dictionaryNode, prefix, indexMap) {
    const node = dictionaryNode && typeof dictionaryNode === 'object' ? dictionaryNode : {};
    const currentPrefix = prefix ? `${prefix}.` : '';
    Object.entries(node).forEach(([key, value]) => {
      const nextKeyPath = `${currentPrefix}${key}`;
      if (typeof value === 'string') {
        indexMap.set(value, nextKeyPath);
        return;
      }
      if (value && typeof value === 'object') {
        createKnownDictionaryMessageIndex(value, nextKeyPath, indexMap);
      }
    });
  }

  const knownPtDictionaryMessageIndex = (() => {
    const indexMap = new Map();
    const defaultDictionary = getCheckDictionary('pt');
    createKnownDictionaryMessageIndex(defaultDictionary, '', indexMap);
    return indexMap;
  })();

  function localizeKnownApiMessage(message, options) {
    const rawMessage = typeof message === 'string' ? message.trim() : '';
    if (!rawMessage) {
      return '';
    }

    if (getActiveCheckLanguageCode() === 'pt') {
      return rawMessage;
    }

    const exactKeyPath = knownPtDictionaryMessageIndex.get(rawMessage);
    if (exactKeyPath) {
      const translatedMessage = t(exactKeyPath);
      return typeof translatedMessage === 'string' && translatedMessage
        ? translatedMessage
        : rawMessage;
    }

    const settings = options || {};
    const conflictPrefix = 'Ja existe uma solicitacao de transporte ativa para ';
    const ptConflictGeneric = 'Ja existe uma solicitacao de transporte ativa para essa data.';
    if (rawMessage === ptConflictGeneric) {
      return t('transport.requestBuilder.conflictGeneric');
    }
    if (rawMessage.startsWith(conflictPrefix) && rawMessage.endsWith('.')) {
      const serviceDateLabel = rawMessage.slice(conflictPrefix.length, -1).trim();
      return t('transport.requestBuilder.conflictByDate', {
        serviceDateLabel,
        ...(settings.values || {}),
      });
    }

    return rawMessage;
  }

  function localizeKnownLocationLabel(label) {
    const normalizedLabel = String(label || '').trim();
    if (!normalizedLabel) {
      return '';
    }

    if (normalizedLabel === defaultManualLocationLabel) {
      return t('location.defaultManualLocationLabel');
    }
    if (normalizedLabel === accuracyFallbackManualLocationLabel) {
      return t('location.accuracyFallbackManualLocationLabel');
    }
    if (normalizedLabel === automaticActivities.AUTOMATIC_CHECKOUT_LOCATION) {
      return t('location.outsideWorkplaceLabel');
    }
    if (normalizedLabel === automaticActivities.AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION) {
      return t('location.unregisteredLocationLabel');
    }
    if (normalizedLabel === automaticActivities.MIXED_ZONE_LOCATION) {
      return t('location.mixedZoneLabel');
    }
    if (automaticActivities.isCheckoutZoneLocationName(normalizedLabel)) {
      return t('location.checkoutZoneLabel');
    }

    return localizeKnownApiMessage(normalizedLabel) || normalizedLabel;
  }

  function formatTransportVehicleTypeLabel(value) {
    const formattedValue = clientState && typeof clientState.formatTransportVehicleType === 'function'
      ? clientState.formatTransportVehicleType(value)
      : String(value || '').trim();
    return formattedValue || '--';
  }

  function copyObjectValues(target, source) {
    Object.keys(target).forEach((key) => {
      delete target[key];
    });
    Object.entries(source || {}).forEach(([key, value]) => {
      target[key] = value;
    });
  }

  function refreshLocaleFormatters() {
    const locale = getCheckLocale();
    weekdayFormatter = new Intl.DateTimeFormat(locale, {
      weekday: 'long',
    });
    dateFormatter = new Intl.DateTimeFormat(locale, {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
    timeFormatter = new Intl.DateTimeFormat(locale, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  }

  function syncTranslatedRuntimeLabels() {
    copyObjectValues(transportRequestKindLabels, {
      regular: typeof t === 'function' ? t('transport.kinds.regular') : 'Dias Úteis',
      weekend: typeof t === 'function' ? t('transport.kinds.weekend') : 'Fim de Semana',
      extra: typeof t === 'function' ? t('transport.kinds.extra') : 'Data Específica',
    });
    copyObjectValues(transportRequestStatusLabels, {
      pending: typeof t === 'function' ? t('transport.statusLabels.pending') : 'Pendente',
      confirmed: typeof t === 'function' ? t('transport.statusLabels.confirmed') : 'Confirmado',
      realized: typeof t === 'function' ? t('transport.statusLabels.realized') : 'Realizado',
      rejected: typeof t === 'function' ? t('transport.statusLabels.rejected') : 'Rejeitado',
      cancelled: typeof t === 'function' ? t('transport.statusLabels.cancelled') : 'Cancelado',
    });
    copyObjectValues(transportRequestWeekdayLabels, getCheckDictionary().transport.weekdays.short);
    copyObjectValues(transportRequestWeekdayFullLabels, getCheckDictionary().transport.weekdays.full);
    transportRequestBuilderConfigs.regular.subtitle = t('transport.requestBuilder.regularSubtitle');
    transportRequestBuilderConfigs.weekend.subtitle = t('transport.requestBuilder.weekendSubtitle');
    transportRequestBuilderConfigs.extra.subtitle = t('transport.requestBuilder.extraSubtitle');
  }

  function isStandaloneShortcutMode() {
    return Boolean(
      (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches)
        || window.navigator.standalone === true
    );
  }

  function getLocationPermissionContainerLabel() {
    return isStandaloneShortcutMode()
      ? t('location.appContextLabel')
      : t('location.browserContextLabel');
  }

  function getLocationPromptSourceLabel() {
    return isStandaloneShortcutMode()
      ? t('location.appSourceLabel')
      : t('location.browserSourceLabel');
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
      && !transportCancelInProgress;
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
    return isPasswordDialogOpen() || isRegistrationDialogOpen() || isSettingsDialogOpen() || isTransportScreenOpen();
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

  function resolveAuthenticationAssistanceStateKey(options) {
    const settings = options || {};
    const normalizedChave = sanitizeChave(
      settings.chave !== undefined
        ? settings.chave
        : (authState.chave || chaveInput.value)
    );
    const statusResolved = settings.statusResolved !== undefined
      ? Boolean(settings.statusResolved)
      : authState.statusResolved;
    const statusErrored = settings.statusErrored !== undefined
      ? Boolean(settings.statusErrored)
      : authState.statusErrored;
    const found = settings.found !== undefined ? Boolean(settings.found) : authState.found;
    const hasPassword = settings.hasPassword !== undefined ? Boolean(settings.hasPassword) : authState.hasPassword;

    if (normalizedChave.length !== 4 || !statusResolved || statusErrored) {
      return '';
    }

    if (!found) {
      return `${normalizedChave}:missing-user`;
    }

    if (!hasPassword) {
      return `${normalizedChave}:missing-password`;
    }

    return '';
  }

  function resetAuthenticationAssistanceAutoOpenState() {
    currentAuthenticationAssistanceStateKey = '';
    lastAutoOpenedAuthenticationAssistanceStateKey = '';
    lastDismissedAuthenticationAssistanceStateKey = '';
  }

  function syncAuthenticationAssistanceAutoOpenState(options) {
    const nextStateKey = resolveAuthenticationAssistanceStateKey(options);
    if (nextStateKey !== currentAuthenticationAssistanceStateKey) {
      currentAuthenticationAssistanceStateKey = nextStateKey;
      lastAutoOpenedAuthenticationAssistanceStateKey = '';
      lastDismissedAuthenticationAssistanceStateKey = '';
    }
    return nextStateKey;
  }

  function markCurrentAuthenticationAssistanceDialogAsManuallyDismissed() {
    if (!currentAuthenticationAssistanceStateKey) {
      return;
    }
    lastDismissedAuthenticationAssistanceStateKey = currentAuthenticationAssistanceStateKey;
  }

  function maybeAutoOpenAuthenticationAssistanceDialog() {
    const stateKey = currentAuthenticationAssistanceStateKey;
    if (
      !stateKey
      || stateKey === lastAutoOpenedAuthenticationAssistanceStateKey
      || stateKey === lastDismissedAuthenticationAssistanceStateKey
      || isSettingsDialogOpen()
      || isTransportScreenOpen()
    ) {
      return false;
    }

    if (stateKey.endsWith(':missing-user')) {
      lastAutoOpenedAuthenticationAssistanceStateKey = stateKey;
      if (!isRegistrationDialogOpen()) {
        openRegistrationDialog();
      }
      return true;
    }

    if (stateKey.endsWith(':missing-password')) {
      lastAutoOpenedAuthenticationAssistanceStateKey = stateKey;
      if (!isPasswordDialogOpen()) {
        openPasswordDialog();
      }
      return true;
    }

    return false;
  }

  function canOpenPasswordChangeFromSettings() {
    return authState.statusResolved
      && !authState.statusErrored
      && authState.hasPassword
      && isApplicationUnlocked();
  }

  function resolveSupportRequestChave() {
    const authenticatedChave = authState.authenticated ? sanitizeChave(authState.chave) : '';
    if (authenticatedChave.length === 4) {
      return authenticatedChave;
    }

    const typedChave = getActiveChave();
    return typedChave.length === 4 ? typedChave : '';
  }

  function canOpenSupportFromSettings() {
    return resolveSupportRequestChave().length === 4;
  }

  function buildCheckingWebSupportMessage(chave) {
    const supportKey = sanitizeChave(chave);
    return typeof t === 'function'
      ? t('support.messageTemplate', { chave: supportKey })
      : `Preciso de ajuda com a aplicacao Web. Minha chave e ${supportKey}.`;
  }

  function buildCheckingWebSupportWhatsAppUrl(chave) {
    return `https://wa.me/${checkingWebSupportWhatsAppPhone}?text=${encodeURIComponent(buildCheckingWebSupportMessage(chave))}`;
  }

  function openSecondarySurface(url) {
    if (typeof url !== 'string' || !url) {
      return false;
    }

    if (typeof window.open === 'function') {
      const openedWindow = window.open(url, '_blank', 'noopener');
      if (openedWindow && typeof openedWindow === 'object') {
        try {
          openedWindow.opener = null;
        } catch (error) {
          // Ignore cross-origin opener assignment failures.
        }
      }
      return true;
    }

    if (window.location && typeof window.location.assign === 'function') {
      window.location.assign(url);
      return true;
    }

    return false;
  }

  function openCheckingWebSupport() {
    const supportChave = resolveSupportRequestChave();
    if (supportChave.length !== 4) {
      return false;
    }

    closeSettingsDialog({ restoreFocus: false });
    return openSecondarySurface(buildCheckingWebSupportWhatsAppUrl(supportChave));
  }

  function openCheckingWebManual() {
    closeSettingsDialog({ restoreFocus: false });
    return openSecondarySurface(checkingWebManualPath);
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
    authenticatedApplicationLoadPromise = null;
    authenticatedApplicationLoadFingerprint = '';
    authenticatedApplicationReadyFingerprint = '';
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

  function populateSettingsLanguageOptions() {
    if (!settingsLanguageSelect || !checkI18n || !Array.isArray(checkI18n.languages)) {
      return;
    }

    const activeLanguageCode = getActiveCheckLanguageCode();
    settingsLanguageSelect.replaceChildren();
    checkI18n.languages.forEach((language) => {
      const optionElement = document.createElement('option');
      optionElement.value = language.code;
      optionElement.textContent = language.label;
      optionElement.selected = language.code === activeLanguageCode;
      settingsLanguageSelect.append(optionElement);
    });
    settingsLanguageSelect.value = activeLanguageCode;
  }

  function applyTextContent(element, value) {
    if (!element) {
      return;
    }
    element.textContent = value;
  }

  function applyStaticTranslations() {
    if (document && typeof document.title === 'string') {
      document.title = t('document.title');
    }
    if (document && document.documentElement) {
      document.documentElement.lang = getCheckLocale();
    }
    populateSettingsLanguageOptions();

    if (appHeader) {
      const brandLabel = appHeader.querySelector('.header-logo-text');
      applyTextContent(brandLabel, t('auth.brand'));
    }

    if (form) {
      form.setAttribute('aria-label', t('auth.checkFormAria'));
    }

    const historyTitle = document.getElementById('historyTitle');
    const checkoutHistoryLabel = lastCheckoutItem
      ? lastCheckoutItem.querySelector('.history-label')
      : null;
    const authCredentialsRow = document.querySelector('.auth-credentials-row');
    const chaveLabelText = chaveAuthField ? chaveAuthField.querySelector('span') : null;
    const passwordLabelText = passwordAuthField ? passwordAuthField.querySelector('span') : null;
    const settingsSpacerLabel = document.querySelector('.auth-field-spacer');
    const settingsButtonHiddenLabel = settingsButton
      ? settingsButton.querySelector('.visually-hidden')
      : null;
    const registrationLegendLabel = document.querySelector('#registrationField .legend-toggle-label');
    const registrationLegendTitle = document.querySelector('#registrationField .check-group-legend-row > span:last-child');
    const checkinActionLabel = document.querySelector('label.choice-card input[name="action"][value="checkin"] + span');
    const checkoutActionLabel = document.querySelector('label.choice-card input[name="action"][value="checkout"] + span');
    const transportActionLabel = transportButton ? transportButton.querySelector('span') : null;
    const informeLegend = informeField ? informeField.querySelector('legend') : null;
    const normalInformeLabel = document.querySelector('label.choice-card input[name="informe"][value="normal"] + span');
    const retroativoInformeLabel = document.querySelector('label.choice-card input[name="informe"][value="retroativo"] + span');
    const projectFieldLabel = projectField ? projectField.querySelector('span') : null;
    const projectMembershipLink = projectMembershipButton
      ? projectMembershipButton.querySelector('.project-membership-link')
      : null;
    const locationFieldLabel = locationSelectField ? locationSelectField.querySelector('span') : null;
    const passwordOldLabel = passwordDialogOldPasswordField
      ? passwordDialogOldPasswordField.querySelector('span')
      : null;
    const passwordNewLabel = newPasswordInput
      ? newPasswordInput.closest('label') && newPasswordInput.closest('label').querySelector('span')
      : null;
    const passwordConfirmLabel = confirmPasswordInput
      ? confirmPasswordInput.closest('label') && confirmPasswordInput.closest('label').querySelector('span')
      : null;
    const registrationNote = registrationDialog
      ? registrationDialog.querySelector('.registration-dialog-note')
      : null;
    const registrationKeyLabel = registrationChaveInput
      ? registrationChaveInput.closest('label') && registrationChaveInput.closest('label').querySelector('span')
      : null;
    const registrationNameLabel = registrationNameInput
      ? registrationNameInput.closest('label') && registrationNameInput.closest('label').querySelector('span')
      : null;
    const registrationProjectsLabel = registrationDialog
      ? registrationDialog.querySelector('.registration-project-field > span')
      : null;
    const registrationEmailLabel = registrationEmailInput
      ? registrationEmailInput.closest('label') && registrationEmailInput.closest('label').querySelector('span')
      : null;
    const registrationPasswordLabel = registrationPasswordInput
      ? registrationPasswordInput.closest('label') && registrationPasswordInput.closest('label').querySelector('span')
      : null;
    const registrationConfirmPasswordLabel = registrationConfirmPasswordInput
      ? registrationConfirmPasswordInput.closest('label') && registrationConfirmPasswordInput.closest('label').querySelector('span')
      : null;
    const settingsLanguageLabel = settingsLanguageSelect
      ? settingsLanguageSelect.closest('label') && settingsLanguageSelect.closest('label').querySelector('span')
      : null;
    const settingsOptionLabels = Array.from(document.querySelectorAll('.settings-option-label'));
    const transportTitle = document.getElementById('transportScreenTitle');
    const transportOptionInstruction = document.getElementById('transportOptionInstruction');
    const transportHistoryLabel = transportRequestHistorySection
      ? transportRequestHistorySection.querySelector('.transport-request-history-label')
      : null;
    const transportAddressLabel = transportAddressInput
      ? transportAddressInput.closest('label') && transportAddressInput.closest('label').querySelector('span')
      : null;
    const transportZipLabel = transportZipInput
      ? transportZipInput.closest('label') && transportZipInput.closest('label').querySelector('span')
      : null;
    const transportWeekdayGroupLabel = transportRequestWeekdayGroup
      ? transportRequestWeekdayGroup.querySelector('.transport-request-builder-label')
      : null;
    const transportDateLabel = transportRequestDateInput
      ? transportRequestDateInput.closest('label') && transportRequestDateInput.closest('label').querySelector('span')
      : null;
    const transportTimeLabel = transportRequestTimeInput
      ? transportRequestTimeInput.closest('label') && transportRequestTimeInput.closest('label').querySelector('span')
      : null;

    applyTextContent(historyTitle, t('history.lastCheckinLabel'));
    applyTextContent(checkoutHistoryLabel, t('history.lastCheckoutLabel'));
    applyTextContent(document.getElementById('locationTitle'), t('location.title'));
    applyTextContent(chaveLabelText, t('auth.keyLabel'));
    applyTextContent(passwordLabelText, t('auth.passwordLabel'));
    applyTextContent(settingsSpacerLabel, t('auth.settingsSpacer'));
    applyTextContent(settingsButtonHiddenLabel, t('auth.openSettingsAria'));
    applyTextContent(document.getElementById('requestRegistrationButton'), t('auth.requestRegistrationButton'));
    applyTextContent(registrationLegendLabel, t('registration.automaticActivitiesLabel'));
    applyTextContent(registrationLegendTitle, t('registration.sectionTitle'));
    applyTextContent(checkinActionLabel, t('registration.checkinLabel'));
    applyTextContent(checkoutActionLabel, t('registration.checkoutLabel'));
    applyTextContent(transportActionLabel, t('registration.transportTestingLabel'));
    applyTextContent(informeLegend, t('registration.informeTitle'));
    applyTextContent(normalInformeLabel, t('registration.informeNormalLabel'));
    applyTextContent(retroativoInformeLabel, t('registration.informeRetroativoLabel'));
    applyTextContent(projectFieldLabel, t('projects.label'));
    applyTextContent(projectMembershipLink, t('projects.changeButton'));
    applyTextContent(locationFieldLabel, t('location.title'));
    applyTextContent(passwordOldLabel, t('passwordDialog.oldPasswordLabel'));
    applyTextContent(passwordNewLabel, t('passwordDialog.newPasswordLabel'));
    applyTextContent(passwordConfirmLabel, t('passwordDialog.confirmPasswordLabel'));
    applyTextContent(document.getElementById('registrationDialogTitle'), t('registrationDialog.title'));
    applyTextContent(registrationNote, t('registrationDialog.note'));
    applyTextContent(registrationKeyLabel, t('registrationDialog.keyLabel'));
    applyTextContent(registrationNameLabel, t('registrationDialog.fullNameLabel'));
    applyTextContent(registrationProjectsLabel, t('registrationDialog.projectsLabel'));
    applyTextContent(registrationEmailLabel, t('registrationDialog.emailLabel'));
    applyTextContent(registrationPasswordLabel, t('registrationDialog.passwordLabel'));
    applyTextContent(registrationConfirmPasswordLabel, t('registrationDialog.confirmPasswordLabel'));
    applyTextContent(document.getElementById('settingsDialogTitle'), t('settings.title'));
    applyTextContent(settingsLanguageLabel, t('settings.languageLabel'));
    applyTextContent(settingsOptionLabels[0], t('settings.resetPasswordLabel'));
    applyTextContent(settingsOptionLabels[1], t('settings.allowLocationLabel'));
    applyTextContent(settingsOptionLabels[2], t('settings.supportLabel'));
    applyTextContent(settingsOptionLabels[3], t('settings.aboutLabel'));
    applyTextContent(settingsResetPasswordButton, t('settings.resetPasswordLabel'));
    applyTextContent(settingsLocationPermissionButton, t('settings.allowLocationLabel'));
    applyTextContent(settingsSupportButton, t('settings.supportLabel'));
    applyTextContent(settingsAboutButton, t('settings.aboutLabel'));
    applyTextContent(settingsDialogBackButton, t('settings.backButton'));
    applyTextContent(transportTitle, t('transport.title'));
    applyTextContent(transportOptionInstruction, t('transport.optionInstruction'));
    applyTextContent(transportHistoryLabel, t('transport.historyTitle'));
    applyTextContent(transportAddressLabel, t('transport.addressLabel'));
    applyTextContent(transportZipLabel, t('transport.zipLabel'));
    applyTextContent(transportWeekdayGroupLabel, t('transport.requestBuilder.selectDaysLabel'));
    applyTextContent(transportDateLabel, t('transport.requestBuilder.dateLabel'));
    applyTextContent(transportTimeLabel, t('transport.requestBuilder.timeLabel'));

    if (authCredentialsRow) {
      authCredentialsRow.setAttribute('aria-label', t('auth.credentialsAria'));
    }
    if (chaveInput) {
      chaveInput.placeholder = t('auth.keyPlaceholder');
    }
    if (passwordInput) {
      passwordInput.placeholder = t('auth.passwordPlaceholder');
    }
    if (settingsButton) {
      settingsButton.setAttribute('aria-label', t('auth.openSettingsAria'));
      settingsButton.setAttribute('title', t('auth.openSettingsTitle'));
    }
    if (refreshLocationButton) {
      refreshLocationButton.setAttribute('aria-label', locationRefreshLoading ? t('location.refreshBusyLabel') : t('location.refreshLabel'));
      refreshLocationButton.setAttribute('title', locationRefreshLoading ? t('location.refreshBusyLabel') : t('location.refreshLabel'));
    }
    if (refreshLocationButtonLabel) {
      refreshLocationButtonLabel.textContent = locationRefreshLoading ? t('location.refreshBusyLabel') : t('location.refreshLabel');
    }
    if (registrationProjectOptions) {
      registrationProjectOptions.setAttribute('aria-label', t('projects.registrationProjectsAria'));
    }
    if (projectMembershipOptions) {
      projectMembershipOptions.setAttribute('aria-label', t('projects.userProjectsAria'));
    }
    if (registrationEmailInput) {
      registrationEmailInput.placeholder = t('registrationDialog.emailPlaceholder');
    }
    if (transportScreenHeaderBackButton) {
      transportScreenHeaderBackButton.setAttribute('aria-label', t('transport.backToMainAria'));
    }
    if (transportAddressToggleButton) {
      transportAddressToggleButton.textContent = t('transport.addressToggleLabel');
    }
    if (transportAddressInput) {
      transportAddressInput.placeholder = t('transport.addressPlaceholder');
    }
    if (transportZipInput) {
      transportZipInput.placeholder = t('transport.zipPlaceholder');
    }
    if (transportRegularButton) {
      transportRegularButton.setAttribute('aria-label', t('transport.kinds.regular'));
      const label = transportRegularButton.querySelector('.transport-option-button-label');
      if (label) {
        label.innerHTML = t('transport.kinds.regular').replace(' ', '<br />');
      }
    }
    if (transportWeekendButton) {
      transportWeekendButton.setAttribute('aria-label', t('transport.kinds.weekend'));
      const label = transportWeekendButton.querySelector('.transport-option-button-label');
      if (label) {
        label.innerHTML = t('transport.kinds.weekend').replace(' ', '<br />');
      }
    }
    if (transportExtraButton) {
      transportExtraButton.setAttribute('aria-label', t('transport.kinds.extra'));
      const label = transportExtraButton.querySelector('.transport-option-button-label');
      if (label) {
        label.innerHTML = t('transport.kinds.extra').replace(' ', '<br />');
      }
    }
    transportRequestWeekdayOptions.forEach((optionElement) => {
      const weekdayValue = String(optionElement && optionElement.getAttribute('data-weekday') || '').trim();
      const labelElement = optionElement ? optionElement.querySelector('span') : null;
      applyTextContent(labelElement, transportRequestWeekdayFullLabels[weekdayValue] || weekdayValue);
    });
  }

  function applyLanguageSelection(languageCode, options) {
    const settings = options || {};
    const resolvedLanguageCode = setActiveCheckLanguageCode(languageCode);
    if (settings.persist !== false && checkI18n && typeof checkI18n.setStoredLanguageCode === 'function') {
      checkI18n.setStoredLanguageCode(resolvedLanguageCode);
    }
    refreshLocaleFormatters();
    syncTranslatedRuntimeLabels();
    applyStaticTranslations();
    if (settings.reapplyDynamicState !== false) {
      syncPasswordDialogPresentation();
      syncProjectMembershipControls();
      syncManualLocationControl();
      if (latestHistoryState) {
        applyHistoryState(latestHistoryState);
      } else {
        renderTransportScreen();
      }
      syncFormControlStates();
      renderNotifications();
    }
    return resolvedLanguageCode;
  }

  function syncPasswordDialogPresentation() {
    const isRegisterMode = isPasswordRegistrationDialogMode();

    if (passwordDialog) {
      passwordDialog.setAttribute('data-mode', passwordDialogMode);
    }
    if (passwordDialogTitle) {
      passwordDialogTitle.textContent = isRegisterMode
        ? t('passwordDialog.titleRegister')
        : t('passwordDialog.titleChange');
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
    const manualOverrideActive = isAccuracyTooLowManualFallbackActive();
    const manualLocationOptions = resolveManualLocationOptions();
    const transportBusy = transportStateLoading
      || transportAddressSaveInProgress
      || transportRequestInProgress
      || transportCancelInProgress;

    syncAuthenticationFieldHighlights();

    const projectMembershipDisabled = dialogOpen
      || lockActive
      || !unlocked
      || submitInProgress
      || passwordRegisterInProgress
      || passwordChangeInProgress
      || userSelfRegistrationInProgress
      || projectCatalogLoading
      || userProjectsLoading
      || projectUpdateInProgress
      || allowedProjectValues.length === 0
      || (automaticActivitiesEnabled && !manualOverrideActive);

    if (projectMembershipButton) {
      projectMembershipButton.disabled = projectMembershipDisabled;
      projectMembershipButton.setAttribute('aria-disabled', String(projectMembershipDisabled));
    }

    if (projectMembershipOptions && typeof projectMembershipOptions.querySelectorAll === 'function') {
      const selectedProjectCount = readSelectedProjectMembershipValues().length || resolveCurrentUserProjectValues().length;
      Array.from(projectMembershipOptions.querySelectorAll('input[name="userProjectMembership"]')).forEach((input) => {
        input.disabled = projectMembershipDisabled || (selectedProjectCount === 1 && input.checked);
      });
    }

    if (projectMembershipDisabled) {
      closeProjectMembershipPanel();
    }

    if (projectMembershipStatus) {
      projectMembershipStatus.textContent = resolveProjectMembershipStatusText();
    }

    processControls.forEach((control) => {
      if (!control) {
        return;
      }

      if (actionInputs.includes(control)) {
        control.disabled = dialogOpen || lockActive || !unlocked || (automaticActivitiesEnabled && !manualOverrideActive);
        return;
      }

      if (control === manualLocationSelect) {
        control.disabled = dialogOpen || lockActive || !unlocked || !shouldAllowManualLocationSelection() || manualLocationOptions.length === 0;
        return;
      }

      if (control === refreshLocationButton) {
        control.disabled = dialogOpen || lockActive || !unlocked || locationRefreshLoading;
        return;
      }

      if (control === submitButton) {
        control.disabled = dialogOpen || lockActive || !unlocked || submitInProgress || (automaticActivitiesEnabled && !manualOverrideActive);
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

      if (control === settingsButton) {
        control.disabled = dialogOpen || lockActive || submitInProgress || authBusy || passwordLoginInProgress;
        control.setAttribute('aria-disabled', String(control.disabled));
        return;
      }
    });

    settingsDialogControls.forEach((control) => {
      if (!control) {
        return;
      }

      if (control === settingsDialogBackButton) {
        control.disabled = false;
        return;
      }

      if (control === settingsResetPasswordButton) {
        control.disabled = !canOpenPasswordChangeFromSettings();
        control.setAttribute('aria-disabled', String(control.disabled));
        return;
      }

      if (control === settingsLocationPermissionButton) {
        control.disabled = locationRefreshLoading || isLocationPermissionEffectivelySharedWithWebApp();
        control.setAttribute('aria-disabled', String(control.disabled));
        return;
      }

      if (control === settingsSupportButton) {
        control.disabled = !canOpenSupportFromSettings();
        control.setAttribute('aria-disabled', String(control.disabled));
        return;
      }

      if (control instanceof window.HTMLButtonElement) {
        control.disabled = false;
        control.setAttribute('aria-disabled', 'false');
        return;
      }

      control.disabled = false;
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
          ? (isRegisterMode ? `${t('passwordDialog.submitRegisterButton')}...` : `${t('passwordDialog.submitChangeButton')}...`)
          : (isRegisterMode ? t('passwordDialog.submitRegisterButton') : t('passwordDialog.submitChangeButton'));
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
        control.textContent = userSelfRegistrationInProgress
          ? `${t('registrationDialog.submitButton')}...`
          : t('registrationDialog.submitButton');
        return;
      }

      control.disabled = userSelfRegistrationInProgress;
    });

    if (registrationProjectOptions && typeof registrationProjectOptions.querySelectorAll === 'function') {
      const registrationProjectsDisabled = userSelfRegistrationInProgress || projectCatalogLoading || allowedProjectValues.length === 0;
      Array.from(registrationProjectOptions.querySelectorAll('input[name="registrationProjectMembership"]')).forEach((input) => {
        input.disabled = registrationProjectsDisabled;
      });
    }

    if (transportButton) {
      const transportButtonLocked = dialogOpen || lockActive || submitInProgress || authBusy || passwordLoginInProgress;
      transportButton.disabled = transportButtonLocked;
      transportButton.setAttribute('aria-disabled', String(transportButtonLocked));
    }

    transportScreenControls.forEach((control) => {
      if (!control) {
        return;
      }

      if (control === transportRegularButton || control === transportWeekendButton || control === transportExtraButton) {
        const transportOptionBlocked = control.dataset.transportOptionDisabled === 'true';
        control.disabled = transportBusy || transportOptionBlocked;
        control.setAttribute('aria-disabled', String(transportBusy || transportOptionBlocked));
        return;
      }

      if (control === transportAddressSubmitButton) {
        control.disabled = transportBusy;
        control.textContent = transportAddressSaveInProgress
          ? `${t('transport.addressSubmitButton')}...`
          : t('transport.addressSubmitButton');
        return;
      }

      if (control === transportRequestBuilderSubmitButton) {
        const transportSubmitBlocked = control.dataset.transportSubmitDisabled === 'true';
        control.disabled = transportBusy || transportSubmitBlocked;
        control.textContent = transportRequestInProgress
          ? (typeof t === 'function' ? `${t('transport.requestBuilder.submitButton')}...` : 'Solicitando...')
          : (typeof t === 'function' ? t('transport.requestBuilder.submitButton') : 'Solicitar');
        control.setAttribute('aria-disabled', String(transportBusy || transportSubmitBlocked));
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
    refreshLocationButton.setAttribute('aria-label', locationRefreshLoading ? t('location.refreshBusyLabel') : t('location.refreshLabel'));
    refreshLocationButton.setAttribute('title', locationRefreshLoading ? t('location.refreshBusyLabel') : t('location.refreshLabel'));
    if (refreshLocationButtonLabel) {
      refreshLocationButtonLabel.textContent = locationRefreshLoading ? t('location.refreshBusyLabel') : t('location.refreshLabel');
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
    return action === 'checkout'
      ? t('registration.checkOutLowerLabel')
      : t('registration.checkInLowerLabel');
  }

  function buildLocationCompletionMessage(payload) {
    const detailMessage = payload && typeof payload.message === 'string'
      ? localizeKnownApiMessage(payload.message).trim()
      : '';

    if (!detailMessage) {
      return t('location.completionStatus');
    }

    return t('location.completionStatusWithDetail', {
      detail: detailMessage,
    });
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

  function isLocationMeasurementEnabled() {
    if (window.__CHECKING_LOCATION_MEASUREMENT__ === true) {
      return true;
    }

    try {
      return window.localStorage.getItem(locationMeasurementStorageKey) === '1';
    } catch {
      return false;
    }
  }

  function cloneLocationMeasurementSession(session) {
    if (!session) {
      return null;
    }

    try {
      return JSON.parse(JSON.stringify(session));
    } catch {
      return null;
    }
  }

  function getLocationMeasurementSessions() {
    return locationMeasurementSessions
      .map((session) => cloneLocationMeasurementSession(session))
      .filter(Boolean);
  }

  function cloneLocationMeasurementValue(value) {
    if (value === null || typeof value !== 'object') {
      return value;
    }

    try {
      return JSON.parse(JSON.stringify(value));
    } catch {
      return null;
    }
  }

  function getLocationMeasurementTrigger(options) {
    const settings = options || {};
    const trigger = typeof settings.measurementTrigger === 'string'
      ? settings.measurementTrigger.trim()
      : '';

    if (trigger) {
      return trigger;
    }

    return settings.interactive ? 'interactive' : 'silent_lookup';
  }

  function buildLocationMeasurementBrowserLabel() {
    const navigatorRef = window.navigator || {};
    return String(navigatorRef.userAgent || '').trim() || 'unknown';
  }

  function buildLocationMeasurementConsoleSnapshot(session) {
    if (!session) {
      return null;
    }

    return {
      session_id: session.session_id,
      trigger: session.trigger,
      strategy: session.strategy,
      samples_received: session.samples_received,
      best_accuracy_meters: session.best_accuracy_meters,
      final_accuracy_sent_meters: session.final_accuracy_sent_meters,
      threshold_meters: session.threshold_meters,
      final_status: session.final_status,
      termination_reason: session.termination_reason,
      timed_out: session.timed_out,
      duplicate_post: session.duplicate_post,
      duration_ms: session.duration_ms,
    };
  }

  function shouldLogLocationMeasurementEvent(eventName) {
    return eventName === 'session_started'
      || eventName === 'geolocation_error'
      || eventName === 'session_finalized'
      || eventName === 'session_anomaly';
  }

  function recordLocationMeasurementEvent(session, eventName, details) {
    if (!session) {
      return;
    }

    const payload = details || {};
    const event = {
      event: eventName,
      at: new Date().toISOString(),
      elapsed_ms: Date.now() - session.started_at_ms,
      details: payload,
    };
    session.events.push(event);

    if (shouldLogLocationMeasurementEvent(eventName)) {
      console.info(
        locationMeasurementConsoleLabel,
        eventName,
        buildLocationMeasurementConsoleSnapshot(session),
        payload
      );
    }
  }

  function createLocationMeasurementSession(options) {
    if (!isLocationMeasurementEnabled()) {
      return null;
    }

    const startedAtMs = Date.now();
    const strategy = options && typeof options.captureStrategy === 'string' && options.captureStrategy.trim()
      ? options.captureStrategy.trim()
      : 'single_attempt';
    const targetAccuracyMeters = options && typeof options.targetAccuracyMeters === 'number' && Number.isFinite(options.targetAccuracyMeters)
      ? options.targetAccuracyMeters
      : null;
    const session = {
      session_id: `loc-${startedAtMs}-${++locationMeasurementSessionCounter}`,
      strategy,
      trigger: getLocationMeasurementTrigger(options),
      interactive: Boolean(options && options.interactive),
      force_refresh: Boolean(options && options.forceRefresh),
      browser: buildLocationMeasurementBrowserLabel(),
      browser_language: String((window.navigator && window.navigator.language) || '').trim() || 'unknown',
      secure_context: window.isSecureContext === true,
      started_at: new Date(startedAtMs).toISOString(),
      started_at_ms: startedAtMs,
      finished_at: null,
      finished_at_ms: null,
      duration_ms: null,
      time_to_first_sample_ms: null,
      samples_received: 0,
      best_accuracy_meters: null,
      time_to_best_sample_ms: null,
      final_accuracy_sent_meters: null,
      threshold_meters: targetAccuracyMeters,
      final_status: null,
      termination_reason: null,
      timed_out: false,
      cancelled: false,
      duplicate_post: false,
      match_post_count: 0,
      ui_stuck: false,
      events: [],
    };

    locationMeasurementSessions.push(session);
    if (locationMeasurementSessions.length > locationMeasurementSessionLimit) {
      locationMeasurementSessions = locationMeasurementSessions.slice(-locationMeasurementSessionLimit);
    }

    recordLocationMeasurementEvent(session, 'session_started', {
      trigger: session.trigger,
      interactive: session.interactive,
      force_refresh: session.force_refresh,
      strategy: session.strategy,
      target_accuracy_meters: targetAccuracyMeters,
    });
    return session;
  }

  function hasFiniteCoordinate(value) {
    return typeof value === 'number' && Number.isFinite(value);
  }

  function readPositionAccuracyMeters(position) {
    const accuracy = position && position.coords ? position.coords.accuracy : null;
    return typeof accuracy === 'number' && Number.isFinite(accuracy)
      ? accuracy
      : null;
  }

  function setLocationAccuracyThresholdMeters(value) {
    locationAccuracyThresholdMeters = typeof value === 'number' && Number.isFinite(value)
      ? value
      : null;
  }

  function setMixedZoneIntervalMinutes(value) {
    const normalizedValue = Number(value);
    mixedZoneIntervalMinutes = Number.isFinite(normalizedValue) && normalizedValue >= 1
      ? Math.trunc(normalizedValue)
      : DEFAULT_MIXED_ZONE_INTERVAL_MINUTES;
  }

  function readRecentHistoryState(chave, options) {
    const settings = options || {};
    const cacheWindowMs = Number(settings.cacheWindowMs);
    const normalizedChave = sanitizeChave(typeof chave === 'string' ? chave : getActiveChave());

    if (!Number.isFinite(cacheWindowMs) || cacheWindowMs < 1 || normalizedChave.length !== 4) {
      return null;
    }

    if (!latestHistoryState || lastHistoryStateAppliedChave !== normalizedChave) {
      return null;
    }

    if (Date.now() - lastHistoryStateAppliedAt > cacheWindowMs) {
      return null;
    }

    return latestHistoryState;
  }

  function readRecentLocationResolution(options) {
    const settings = options || {};
    const cacheWindowMs = Number(settings.cacheWindowMs);
    const normalizedChave = sanitizeChave(typeof settings.chave === 'string' ? settings.chave : getActiveChave());

    if (!Number.isFinite(cacheWindowMs) || cacheWindowMs < 1 || normalizedChave.length !== 4) {
      return null;
    }

    if (!recentLocationResolutionPayload || recentLocationResolutionChave !== normalizedChave) {
      return null;
    }

    if (Date.now() - recentLocationResolutionAt > cacheWindowMs) {
      return null;
    }

    return recentLocationResolutionPayload;
  }

  function isLocationSampleBetter(candidatePosition, currentBestPosition) {
    if (!candidatePosition) {
      return false;
    }

    const candidateCoords = candidatePosition.coords || null;
    const candidateAccuracy = readPositionAccuracyMeters(candidatePosition);
    if (!candidateCoords || !hasFiniteCoordinate(candidateCoords.latitude) || !hasFiniteCoordinate(candidateCoords.longitude) || candidateAccuracy === null) {
      return false;
    }

    if (!currentBestPosition) {
      return true;
    }

    const currentBestAccuracy = readPositionAccuracyMeters(currentBestPosition);

    if (currentBestAccuracy === null) {
      return true;
    }
    if (candidateAccuracy < currentBestAccuracy) {
      return true;
    }
    if (candidateAccuracy > currentBestAccuracy) {
      return false;
    }

    const candidateTimestamp = typeof candidatePosition.timestamp === 'number'
      ? candidatePosition.timestamp
      : 0;
    const currentBestTimestamp = typeof currentBestPosition.timestamp === 'number'
      ? currentBestPosition.timestamp
      : 0;
    return candidateTimestamp >= currentBestTimestamp;
  }

  function buildLocationCapturePlan(options) {
    const trigger = getLocationMeasurementTrigger(options);
    const configuredPlan = locationCapturePlansByTrigger[trigger] || null;

    if (!configuredPlan) {
      return {
        trigger,
        strategy: 'single_attempt',
        minimumWindowMs: 0,
        maxWindowMs: 0,
        targetAccuracyMeters: locationAccuracyThresholdMeters,
      };
    }

    return {
      trigger,
      strategy: configuredPlan.strategy,
      minimumWindowMs: configuredPlan.minimumWindowMs,
      maxWindowMs: configuredPlan.maxWindowMs,
      targetAccuracyMeters: locationAccuracyThresholdMeters,
    };
  }

  function shouldStopLocationWatch(bestPosition, capturePlan, startedAtMs) {
    if (!bestPosition || !capturePlan) {
      return false;
    }

    if (Date.now() - startedAtMs < capturePlan.minimumWindowMs) {
      return false;
    }

    const targetAccuracyMeters = capturePlan.targetAccuracyMeters;
    const bestAccuracyMeters = readPositionAccuracyMeters(bestPosition);
    return typeof targetAccuracyMeters === 'number'
      && Number.isFinite(targetAccuracyMeters)
      && typeof bestAccuracyMeters === 'number'
      && Number.isFinite(bestAccuracyMeters)
      && bestAccuracyMeters <= targetAccuracyMeters;
  }

  function buildWatchGeolocationOptions(capturePlan) {
    if (!capturePlan || !capturePlan.maxWindowMs) {
      return geolocationOptions;
    }

    return {
      ...geolocationOptions,
      timeout: Math.min(geolocationOptions.timeout, capturePlan.maxWindowMs),
    };
  }

  function buildLocationWatchTimeoutError() {
    const error = new Error('A busca pela localização demorou mais do que o esperado.');
    error.code = 3;
    return error;
  }

  function buildLocationCaptureProgressAccuracyText(accuracyMeters, capturePlan) {
    const accuracyText = buildAccuracyText(
      accuracyMeters,
      capturePlan && capturePlan.targetAccuracyMeters
    );
    return accuracyText.startsWith('Precisão ')
      ? accuracyText.replace('Precisão ', 'Precisão atual ')
      : accuracyText;
  }

  function updateLocationCaptureProgress(position, capturePlan, options) {
    const settings = options || {};
    if (!settings.showDetectingState || !position) {
      return;
    }

    const currentAccuracyMeters = readPositionAccuracyMeters(position);
    if (typeof currentAccuracyMeters !== 'number' || !Number.isFinite(currentAccuracyMeters)) {
      return;
    }

    setLocationPresentation(
      'Buscando precisão suficiente...',
      '',
      'info',
      buildLocationCaptureProgressAccuracyText(currentAccuracyMeters, capturePlan),
      { suppressNotification: true }
    );
  }

  function requestWatchedCurrentPosition(capturePlan, measurementSession, options) {
    const progressOptions = options || {};
    return new Promise((resolve, reject) => {
      const maxWindowMs = Math.max(
        Math.trunc(capturePlan && Number.isFinite(capturePlan.maxWindowMs) ? capturePlan.maxWindowMs : 0),
        0
      );
      if (maxWindowMs <= 0) {
        requestCurrentPosition(measurementSession)
          .then(resolve)
          .catch(reject);
        return;
      }

      const startedAtMs = Date.now();
      let bestPosition = null;
      let watchId = null;
      let finished = false;
      let lastRecoverableError = null;

      recordLocationMeasurementEvent(measurementSession, 'watch_window_started', {
        max_window_ms: maxWindowMs,
        minimum_window_ms: capturePlan.minimumWindowMs,
        target_accuracy_meters: capturePlan.targetAccuracyMeters,
      });

      function finish(position, error) {
        if (finished) {
          return;
        }
        finished = true;

        if (watchId !== null) {
          navigator.geolocation.clearWatch(watchId);
        }
        window.clearTimeout(timeoutId);

        if (error) {
          reject(error);
          return;
        }
        resolve(position);
      }

      const timeoutId = window.setTimeout(() => {
        if (bestPosition) {
          recordLocationMeasurementEvent(measurementSession, 'watch_window_completed', {
            termination_reason: 'acquisition_window_elapsed',
            best_accuracy_meters: readPositionAccuracyMeters(bestPosition),
          });
          finish(bestPosition, null);
          return;
        }

        recordLocationMeasurementEvent(measurementSession, 'watch_window_completed', {
          termination_reason: 'acquisition_window_elapsed',
          best_accuracy_meters: null,
        });
        finish(null, lastRecoverableError || buildLocationWatchTimeoutError());
      }, maxWindowMs);

      try {
        watchId = navigator.geolocation.watchPosition(
          (position) => {
            recordLocationMeasurementSample(measurementSession, position);
            updateLocationCaptureProgress(position, capturePlan, progressOptions);

            if (isLocationSampleBetter(position, bestPosition)) {
              bestPosition = position;
            }

            if (shouldStopLocationWatch(bestPosition, capturePlan, startedAtMs)) {
              recordLocationMeasurementEvent(measurementSession, 'watch_window_completed', {
                termination_reason: 'target_accuracy_reached',
                best_accuracy_meters: readPositionAccuracyMeters(bestPosition),
              });
              finish(bestPosition, null);
            }
          },
          (error) => {
            recordLocationMeasurementEvent(measurementSession, 'geolocation_error', {
              code: error && typeof error.code === 'number' ? error.code : null,
              message: error && typeof error.message === 'string' ? error.message : '',
            });

            if (error && error.code === 1) {
              finish(null, error);
              return;
            }

            lastRecoverableError = error;
          },
          buildWatchGeolocationOptions(capturePlan)
        );
      } catch (error) {
        window.clearTimeout(timeoutId);
        reject(error);
      }
    });
  }

  function requestCurrentPositionForPlan(capturePlan, measurementSession, options) {
    if (!capturePlan || capturePlan.strategy !== 'watch_window' || typeof navigator.geolocation.watchPosition !== 'function') {
      return requestCurrentPosition(measurementSession);
    }

    return requestWatchedCurrentPosition(capturePlan, measurementSession, options);
  }

  function collectLocationMeasurementNumbers(sessions, fieldName) {
    return (Array.isArray(sessions) ? sessions : [])
      .map((session) => (session ? session[fieldName] : null))
      .filter((value) => typeof value === 'number' && Number.isFinite(value));
  }

  function computeLocationMeasurementMedian(values) {
    if (!Array.isArray(values) || !values.length) {
      return null;
    }

    const sortedValues = values
      .slice()
      .sort((left, right) => left - right);
    const middleIndex = Math.floor(sortedValues.length / 2);

    if (sortedValues.length % 2 === 1) {
      return sortedValues[middleIndex];
    }

    return (sortedValues[middleIndex - 1] + sortedValues[middleIndex]) / 2;
  }

  function summarizeLocationMeasurementSessions(sessions) {
    const sourceSessions = Array.isArray(sessions)
      ? sessions.filter(Boolean)
      : [];
    const bestAccuracyValues = collectLocationMeasurementNumbers(sourceSessions, 'best_accuracy_meters');
    const finalAccuracyValues = collectLocationMeasurementNumbers(sourceSessions, 'final_accuracy_sent_meters');
    const firstSampleValues = collectLocationMeasurementNumbers(sourceSessions, 'time_to_first_sample_ms');
    const durationValues = collectLocationMeasurementNumbers(sourceSessions, 'duration_ms');
    const statusCounts = {};
    const terminationCounts = {};

    sourceSessions.forEach((session) => {
      if (typeof session.final_status === 'string' && session.final_status) {
        statusCounts[session.final_status] = (statusCounts[session.final_status] || 0) + 1;
      }
      if (typeof session.termination_reason === 'string' && session.termination_reason) {
        terminationCounts[session.termination_reason] = (terminationCounts[session.termination_reason] || 0) + 1;
      }
    });

    return {
      total_sessions: sourceSessions.length,
      completed_sessions: sourceSessions.filter((session) => session.finished_at_ms !== null).length,
      matched_sessions: statusCounts.matched || 0,
      accuracy_too_low_sessions: statusCounts.accuracy_too_low || 0,
      timeout_sessions: sourceSessions.filter((session) => session.timed_out).length,
      cancelled_sessions: sourceSessions.filter((session) => session.cancelled).length,
      duplicate_post_sessions: sourceSessions.filter((session) => session.duplicate_post).length,
      median_time_to_first_sample_ms: computeLocationMeasurementMedian(firstSampleValues),
      median_duration_ms: computeLocationMeasurementMedian(durationValues),
      median_best_accuracy_meters: computeLocationMeasurementMedian(bestAccuracyValues),
      median_final_accuracy_sent_meters: computeLocationMeasurementMedian(finalAccuracyValues),
      min_best_accuracy_meters: bestAccuracyValues.length ? Math.min(...bestAccuracyValues) : null,
      max_best_accuracy_meters: bestAccuracyValues.length ? Math.max(...bestAccuracyValues) : null,
      statuses: statusCounts,
      terminations: terminationCounts,
    };
  }

  function summarizeLocationMeasurementByTrigger(sessions) {
    const groupedSessions = {};

    (Array.isArray(sessions) ? sessions : []).forEach((session) => {
      if (!session) {
        return;
      }

      const trigger = typeof session.trigger === 'string' && session.trigger
        ? session.trigger
        : 'unknown';
      if (!groupedSessions[trigger]) {
        groupedSessions[trigger] = [];
      }
      groupedSessions[trigger].push(session);
    });

    return Object.fromEntries(
      Object.entries(groupedSessions)
        .sort(([leftTrigger], [rightTrigger]) => leftTrigger.localeCompare(rightTrigger))
        .map(([trigger, triggerSessions]) => [trigger, summarizeLocationMeasurementSessions(triggerSessions)])
    );
  }

  function buildLocationMeasurementReport(metadata) {
    const sessions = getLocationMeasurementSessions();
    const strategies = Array.from(
      new Set(
        sessions
          .map((session) => (session && typeof session.strategy === 'string' ? session.strategy : ''))
          .filter(Boolean)
      )
    ).sort();

    return {
      generated_at: new Date().toISOString(),
      metadata: cloneLocationMeasurementValue(metadata) || {},
      strategy: strategies.length <= 1 ? (strategies[0] || null) : 'mixed',
      strategies,
      overall: summarizeLocationMeasurementSessions(sessions),
      by_trigger: summarizeLocationMeasurementByTrigger(sessions),
      sessions,
    };
  }

  function recordLocationMeasurementSample(session, position) {
    if (!session) {
      return;
    }

    const coords = position && position.coords ? position.coords : null;
    if (!coords || !hasFiniteCoordinate(coords.latitude) || !hasFiniteCoordinate(coords.longitude)) {
      recordLocationMeasurementEvent(session, 'session_anomaly', {
        reason: 'invalid_position_sample',
      });
      return;
    }

    const elapsedMs = Date.now() - session.started_at_ms;
    const accuracyMeters = readPositionAccuracyMeters(position);
    session.samples_received += 1;

    if (session.time_to_first_sample_ms === null) {
      session.time_to_first_sample_ms = elapsedMs;
    }

    if (accuracyMeters !== null) {
      if (session.best_accuracy_meters === null || accuracyMeters <= session.best_accuracy_meters) {
        session.best_accuracy_meters = accuracyMeters;
        session.time_to_best_sample_ms = elapsedMs;
      }
      session.final_accuracy_sent_meters = accuracyMeters;
    }
  }

  function recordLocationMeasurementMatchRequest(session, accuracyMeters) {
    if (!session) {
      return;
    }

    session.match_post_count += 1;
    session.duplicate_post = session.match_post_count > 1;
    session.final_accuracy_sent_meters = accuracyMeters;

    if (session.duplicate_post) {
      recordLocationMeasurementEvent(session, 'session_anomaly', {
        reason: 'duplicate_match_post',
        match_post_count: session.match_post_count,
      });
    }
  }

  function finalizeLocationMeasurementSession(session, details) {
    if (!session || session.finished_at_ms !== null) {
      return;
    }

    const payload = details || {};
    const finishedAtMs = Date.now();
    session.finished_at_ms = finishedAtMs;
    session.finished_at = new Date(finishedAtMs).toISOString();
    session.duration_ms = finishedAtMs - session.started_at_ms;

    if (typeof payload.final_status === 'string' && payload.final_status.trim()) {
      session.final_status = payload.final_status.trim();
    }
    if (typeof payload.termination_reason === 'string' && payload.termination_reason.trim()) {
      session.termination_reason = payload.termination_reason.trim();
    }
    if (typeof payload.threshold_meters === 'number' && Number.isFinite(payload.threshold_meters)) {
      session.threshold_meters = payload.threshold_meters;
    }
    if (typeof payload.final_accuracy_sent_meters === 'number' && Number.isFinite(payload.final_accuracy_sent_meters)) {
      session.final_accuracy_sent_meters = payload.final_accuracy_sent_meters;
    }
    if (typeof payload.timed_out === 'boolean') {
      session.timed_out = payload.timed_out;
    }
    if (typeof payload.cancelled === 'boolean') {
      session.cancelled = payload.cancelled;
    }
    if (typeof payload.ui_stuck === 'boolean') {
      session.ui_stuck = payload.ui_stuck;
    }

    recordLocationMeasurementEvent(session, 'session_finalized', payload);
  }

  function describeLocationMeasurementFailure(error) {
    if (error && typeof error.code === 'number') {
      if (error.code === 1) {
        return {
          termination_reason: 'browser_permission_denied',
          timed_out: false,
        };
      }
      if (error.code === 2) {
        return {
          termination_reason: 'browser_position_unavailable',
          timed_out: false,
        };
      }
      if (error.code === 3) {
        return {
          termination_reason: 'browser_timeout',
          timed_out: true,
        };
      }
    }

    if (error && typeof error.status === 'number') {
      return {
        termination_reason: 'match_request_failed',
        timed_out: false,
      };
    }

    return {
      termination_reason: 'location_lookup_failed',
      timed_out: false,
    };
  }

  window.CheckingWebLocationMeasurement = Object.freeze({
    enable() {
      window.__CHECKING_LOCATION_MEASUREMENT__ = true;
      try {
        window.localStorage.setItem(locationMeasurementStorageKey, '1');
      } catch {
        // Ignore browsers with unavailable storage.
      }
      console.info(locationMeasurementConsoleLabel, 'enabled');
      return true;
    },
    disable() {
      window.__CHECKING_LOCATION_MEASUREMENT__ = false;
      try {
        window.localStorage.removeItem(locationMeasurementStorageKey);
      } catch {
        // Ignore browsers with unavailable storage.
      }
      console.info(locationMeasurementConsoleLabel, 'disabled');
      return false;
    },
    isEnabled() {
      return isLocationMeasurementEnabled();
    },
    clear() {
      locationMeasurementSessions = [];
      return [];
    },
    getSessions() {
      return getLocationMeasurementSessions();
    },
    getLatestSession() {
      const sessions = getLocationMeasurementSessions();
      return sessions.length ? sessions[sessions.length - 1] : null;
    },
    summarize() {
      return summarizeLocationMeasurementSessions(getLocationMeasurementSessions());
    },
    summarizeByTrigger() {
      return summarizeLocationMeasurementByTrigger(getLocationMeasurementSessions());
    },
    buildReport(metadata) {
      return buildLocationMeasurementReport(metadata);
    },
    printReport(metadata) {
      const report = buildLocationMeasurementReport(metadata);
      console.info(locationMeasurementConsoleLabel, 'report', report);
      return report;
    },
  });

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

    if (window.AccidentMode) window.AccidentMode.onLogout();
  }

  function clearProtectedClientState() {
    latestHistoryState = null;
    applyHistoryState(null);
    resetTransportState();
    closeTransportScreen();
    setResolvedLocation(null);
    currentLocationMatch = null;
    availableLocations = [];
    locationAccuracyThresholdMeters = null;
    mixedZoneIntervalMinutes = null;
    recentLocationResolutionPayload = null;
    recentLocationResolutionAt = 0;
    recentLocationResolutionChave = '';
    setLocationPresentation(t('auth.waitingAuthentication'), '', null, '--', { suppressNotification: true });
  }

  function resolveAuthenticationPromptMessage() {
    if (authState && authState.authenticated) {
      return '';
    }
    if (authState && authState.hasPassword) {
      return t('auth.enterPasswordPrompt');
    }
    return t('auth.createPasswordPrompt');
  }

  function setAuthenticationPrompt(message) {
    const promptMessage = localizeKnownApiMessage(message) || resolveAuthenticationPromptMessage();
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

  function routeToUnknownUserSelfRegistration(chave) {
    const normalizedChave = sanitizeChave(chave || chaveInput.value);
    applyAuthenticationLockedState({
      chave: normalizedChave,
      found: false,
      hasPassword: false,
      message: unknownWebUserDetail,
    });
    syncAuthenticationAssistanceAutoOpenState({
      chave: normalizedChave,
      found: false,
      hasPassword: false,
      statusResolved: normalizedChave.length === 4,
      statusErrored: false,
    });
    openRegistrationDialog();
  }

  function handleExpiredAuthentication(options) {
    const settings = options || {};
    closePasswordDialog();
    closeRegistrationDialog();
    closeSettingsDialog({ restoreFocus: false });
    closeTransportScreen();
    applyAuthenticationLockedState({
      chave: settings.chave || chaveInput.value,
      found: settings.found !== false,
      hasPassword: settings.hasPassword !== false,
      message: localizeKnownApiMessage(settings.message) || t('auth.enterPasswordPrompt'),
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

  function isSettingsDialogOpen() {
    return Boolean(settingsDialog && !settingsDialog.hidden);
  }

  function closeSettingsDialog(options) {
    const settings = options || {};
    if (!settingsDialog || !settingsDialogBackdrop || settingsDialog.hidden) {
      return;
    }

    dismissActiveKeyboard();
    settingsDialog.hidden = true;
    settingsDialogBackdrop.hidden = true;
    settingsDialog.classList.add('is-hidden');
    settingsDialogBackdrop.classList.add('is-hidden');
    if (settingsButton) {
      settingsButton.setAttribute('aria-expanded', 'false');
    }
    syncFormControlStates();
    realignViewport();
    if (settings.restoreFocus !== false && settingsButton && typeof settingsButton.focus === 'function') {
      settingsButton.focus();
    }
  }

  function openSettingsDialog() {
    if (!settingsDialog || !settingsDialogBackdrop) {
      return;
    }

    if (isPasswordDialogOpen() || isRegistrationDialogOpen() || isTransportScreenOpen()) {
      return;
    }

    closeProjectMembershipPanel();
    settingsDialog.hidden = false;
    settingsDialogBackdrop.hidden = false;
    settingsDialog.classList.remove('is-hidden');
    settingsDialogBackdrop.classList.remove('is-hidden');
    if (settingsButton) {
      settingsButton.setAttribute('aria-expanded', 'true');
    }
    syncFormControlStates();
    void queryLocationPermissionState();
    realignViewport();
    if (settingsLanguageSelect && typeof settingsLanguageSelect.focus === 'function') {
      settingsLanguageSelect.focus();
      return;
    }
    if (settingsDialogBackButton && typeof settingsDialogBackButton.focus === 'function') {
      settingsDialogBackButton.focus();
    }
  }

  function dismissPasswordDialogManually() {
    if (isPasswordRegistrationDialogMode()) {
      markCurrentAuthenticationAssistanceDialogAsManuallyDismissed();
    }
    closePasswordDialog();
  }

  function dismissRegistrationDialogManually() {
    markCurrentAuthenticationAssistanceDialogAsManuallyDismissed();
    closeRegistrationDialog();
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
    const persistedSettings = clientState.resolvePersistedUserSettings(
      readPersistedUserSettingsMap(),
      activeChave,
      resolveCurrentUserSettingsDefaults()
    );
    registrationChaveInput.value = activeChave;
    syncProjectMembershipControls({
      registrationProjectValues: persistedSettings.projects,
      registrationValue: persistedSettings.activeProject,
    });
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
      const authError = new Error(t('auth.enterPasswordPrompt'));
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

  const initialCheckLanguageCode = checkI18n && typeof checkI18n.resolveInitialLanguageCode === 'function'
    ? checkI18n.resolveInitialLanguageCode()
    : resolveCheckLanguageCode('pt');
  applyLanguageSelection(initialCheckLanguageCode, {
    persist: false,
    reapplyDynamicState: false,
  });

  const transportScreenConfig = {
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
    getDateFormatter: () => dateFormatter,
    formatTransportVehicleTypeLabel,
    localizeKnownApiMessage,
    t: (keyPath, values) => t(`transport.${keyPath}`, values),
    userTransportLocalStateStorageKey,
  };

  const transportScreenModule = window.CheckingWebTransportScreen.create({
    buildProtectedRequestError,
    clearTransportInlineStatus,
    clientState,
    dismissActiveKeyboard,
    dom: {
      transportScreen,
      transportScreenBackdrop,
      transportAddressSummaryValue,
      transportAddressEditor,
      transportAddressInput,
      transportZipInput,
      transportOptionButtons,
      transportRequestBuilderPanel,
      transportRequestBuilderSubtitle,
      transportRequestWeekdayGroup,
      transportRequestDateGroup,
      transportRequestTimeGroup,
      transportRequestDateInput,
      transportRequestTimeInput,
      transportRequestWeekdayInputs,
      transportRequestWeekdayOptions,
      transportRequestHistorySection,
      transportRequestHistoryList,
      transportRequestDetailWidget,
      transportRequestDetailBackdrop,
      transportRequestDetailTitle,
      transportRequestDetailContent,
      transportRequestDetailCloseButton,
    },
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
    state: {
      transportState,
      transportUiState,
      transportRequestSwipeState,
    },
    config: transportScreenConfig,
    runtime: {
      getTransportStateLoading: () => transportStateLoading,
      setTransportStateLoading: (value) => {
        transportStateLoading = value;
      },
      getTransportAddressSaveInProgress: () => transportAddressSaveInProgress,
      setTransportAddressSaveInProgress: (value) => {
        transportAddressSaveInProgress = value;
      },
      getTransportRequestInProgress: () => transportRequestInProgress,
      setTransportRequestInProgress: (value) => {
        transportRequestInProgress = value;
      },
      getTransportCancelInProgress: () => transportCancelInProgress,
      setTransportCancelInProgress: (value) => {
        transportCancelInProgress = value;
      },
    },
    syncFormControlStates,
  });

  // Preserve the original transport source in app.js for grep-based contract tests,
  // but execute the transport flow through the dedicated module at runtime.
  resetTransportState = transportScreenModule.resetTransportState;
  applyTransportStatePayload = transportScreenModule.applyTransportStatePayload;
  canMarkTransportRequestAsRealized = transportScreenModule.canMarkTransportRequestAsRealized;
  createTransportRequestCard = transportScreenModule.createTransportRequestCard;
  renderTransportScreen = transportScreenModule.renderTransportScreen;
  selectTransportRequest = transportScreenModule.selectTransportRequest;
  closeTransportAddressEditor = transportScreenModule.closeTransportAddressEditor;
  openTransportAddressEditor = transportScreenModule.openTransportAddressEditor;
  closeTransportRequestBuilder = transportScreenModule.closeTransportRequestBuilder;
  initializeTransportRequestBuilder = transportScreenModule.initializeTransportRequestBuilder;
  markTransportRequestAsRealized = transportScreenModule.markTransportRequestAsRealized;
  beginTransportRequestSwipe = transportScreenModule.beginTransportRequestSwipe;
  updateTransportRequestSwipe = transportScreenModule.updateTransportRequestSwipe;
  endTransportRequestSwipe = transportScreenModule.endTransportRequestSwipe;
  closeTransportRequestDetailWidget = transportScreenModule.closeTransportRequestDetailWidget;
  openTransportScreen = transportScreenModule.openTransportScreen;
  closeTransportScreen = transportScreenModule.closeTransportScreen;
  fetchTransportStatePayload = transportScreenModule.fetchTransportStatePayload;
  postTransportPayload = transportScreenModule.postTransportPayload;
  loadTransportState = transportScreenModule.loadTransportState;
  submitTransportAddress = transportScreenModule.submitTransportAddress;
  requestTransport = transportScreenModule.requestTransport;
  submitTransportRequestBuilder = transportScreenModule.submitTransportRequestBuilder;
  cancelTransportRequest = transportScreenModule.cancelTransportRequest;

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

    syncAuthenticationAssistanceAutoOpenState({
      chave: normalizedChave,
      found: authState.found,
      hasPassword: authState.hasPassword,
      statusResolved: authState.statusResolved,
      statusErrored: authState.statusErrored,
    });
    syncFormControlStates();
    maybeAutoOpenAuthenticationAssistanceDialog();
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
    setStatus(t('passwordDialog.validatingStatus'), 'neutral');
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
    const canAutomaticallyVerifyPassword = typeof clientState.isPasswordVerificationInputValid === 'function'
      ? clientState.isPasswordVerificationInputValid(currentPassword)
      : clientState.isPasswordLengthValid(currentPassword);

    lastObservedPasswordFieldValue = currentPassword;

    if (authState.passwordVerified && currentPassword !== lastVerifiedPassword) {
      applyAuthenticationLockedState({
        chave: normalizedChave,
        found: authState.found,
        hasPassword: authState.hasPassword,
        message: t('auth.enterPasswordPrompt'),
      });
      void logoutWebSession({ silent: true });
    }

    if (
      settings.allowAutomaticVerification === true
      && normalizedChave.length === 4
      && authState.hasPassword
      && canAutomaticallyVerifyPassword
    ) {
      schedulePasswordVerification({
        showReadyMessage: settings.showReadyMessage !== false,
        requirePersistedPasswordMatch: settings.requirePersistedPasswordMatch,
      });
    } else if (normalizedChave.length === 4 && authState.hasPassword && !currentPassword) {
      clearPasswordVerificationTimer();
      setAuthenticationPrompt(t('auth.enterPasswordPrompt'));
    } else {
      clearPasswordVerificationTimer();
    }

    syncFormControlStates();
  }

  function syncAutofilledPasswordValue() {
    if (passwordInput.value === lastObservedPasswordFieldValue) {
      return;
    }

    syncPasswordInputState({
      showReadyMessage: true,
      allowAutomaticVerification: true,
    });
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

  function buildPasswordVerificationFingerprint(chave) {
    const normalizedChave = sanitizeChave(chave || chaveInput.value);
    const normalizedPassword = String(lastVerifiedPassword || passwordInput.value || '');

    if (normalizedChave.length !== 4 || !normalizedPassword) {
      return '';
    }

    return `${normalizedChave}:${normalizedPassword}`;
  }

  function resolvePersistedPasswordForChave(chave) {
    const normalizedChave = sanitizeChave(chave);
    return clientState.resolvePersistedPassword(readPersistedUserPasswordMap(), normalizedChave);
  }

  async function loadAuthenticatedApplication(chave, options) {
    const settings = options || {};
    const normalizedChave = sanitizeChave(chave || chaveInput.value);
    const passwordVerificationFingerprint = buildPasswordVerificationFingerprint(normalizedChave);
    if (!isApplicationUnlocked(normalizedChave)) {
      return false;
    }

    if (
      authenticatedApplicationLoadPromise
      && passwordVerificationFingerprint
      && authenticatedApplicationLoadFingerprint === passwordVerificationFingerprint
    ) {
      return authenticatedApplicationLoadPromise;
    }

    if (
      passwordVerificationFingerprint
      && authenticatedApplicationReadyFingerprint === passwordVerificationFingerprint
    ) {
      return true;
    }

    const pendingLoad = (async () => {
      await loadProjectCatalog({ showError: false });
      restorePersistedUserSettingsForChave(normalizedChave);
      await loadCurrentUserProjectMemberships({ showError: false });
      await loadManualLocations();
      if (!isApplicationUnlocked(normalizedChave)) {
        return false;
      }

      if (settings.showReadyMessage) {
        setStatus(
          typeof t === 'function'
            ? t('status.authenticationCompleted')
            : 'Autenticação concluída. Atualizando a aplicação...',
          'info'
        );
      }

      await runLifecycleUpdateSequence({ ignoreCooldown: true, triggerSource: 'startup' });
      authenticatedApplicationReadyFingerprint = passwordVerificationFingerprint;
      if (window.AccidentMode) window.AccidentMode.onLogin();
      return true;
    })();

    authenticatedApplicationLoadPromise = pendingLoad;
    authenticatedApplicationLoadFingerprint = passwordVerificationFingerprint;

    try {
      return await pendingLoad;
    } finally {
      if (authenticatedApplicationLoadPromise === pendingLoad) {
        authenticatedApplicationLoadPromise = null;
        authenticatedApplicationLoadFingerprint = '';
      }
    }
  }

  async function refreshAuthenticationStatus(chave, options) {
    const settings = options || {};
    const normalizedChave = sanitizeChave(chave);

    if (authStatusAbortController) {
      authStatusAbortController.abort();
      authStatusAbortController = null;
    }

    if (normalizedChave.length !== 4) {
      resetAuthenticationAssistanceAutoOpenState();
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
      const currentPassword = passwordInput.value;
      const canAutomaticallyVerifyPassword = typeof clientState.isPasswordVerificationInputValid === 'function'
        ? clientState.isPasswordVerificationInputValid(currentPassword)
        : clientState.isPasswordLengthValid(currentPassword);
      const persistedPassword = resolvePersistedPasswordForChave(normalizedChave);
      if (
        payload.has_password
        && settings.schedulePasswordVerification !== false
        && canAutomaticallyVerifyPassword
        && currentPassword
        && currentPassword === persistedPassword
      ) {
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
        message: error instanceof Error ? localizeKnownApiMessage(error.message) : t('passwordDialog.statusLoadFailed'),
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
            ? t('auth.enterPasswordPrompt')
            : t('passwordDialog.newPasswordInvalid'),
          'error'
        );
      }
      return false;
    }

    passwordLoginInProgress = true;
    syncFormControlStates();
    if (!settings.silentValidation) {
      setStatus(t('passwordDialog.validatingStatus'), 'neutral');
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
      resetAuthenticationAssistanceAutoOpenState();
      syncFormControlStates();

      dismissActiveKeyboard();
      if (settings.showReadyMessage !== false) {
        setStatus(t('status.userAuthenticated'), 'success');
      }
      await loadAuthenticatedApplication(normalizedChave, { showReadyMessage: false });
      return true;
    } catch (error) {
      if (isStalePasswordVerificationAttempt(normalizedChave, password, verificationToken)) {
        return false;
      }

      if (isUnknownUserError(error)) {
        closePasswordDialog();
        routeToUnknownUserSelfRegistration(normalizedChave);
        return false;
      }

      applyAuthenticationLockedState({
        chave: normalizedChave,
        found: true,
        hasPassword: true,
        message: settings.allowPartialVerification
          ? t('auth.enterPasswordPrompt')
          : (error instanceof Error ? localizeKnownApiMessage(error.message) : t('passwordDialog.validationFailed')),
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
      setStatus(t('auth.invalidFourCharacterKey'), 'error');
      closePasswordDialog();
      return;
    }

    if (!registerPasswordMode && !clientState.isPasswordLengthValid(oldPassword)) {
      setStatus(t('passwordDialog.oldPasswordInvalid'), 'error');
      oldPasswordInput.focus();
      return;
    }

    if (!clientState.isPasswordLengthValid(newPassword)) {
      setStatus(t('passwordDialog.newPasswordInvalid'), 'error');
      newPasswordInput.focus();
      return;
    }

    if (newPassword !== confirmPassword) {
      setStatus(t('passwordDialog.confirmMismatch'), 'error');
      confirmPasswordInput.focus();
      return;
    }

    passwordChangeInProgress = true;
    syncFormControlStates();
    setStatus(
      registerPasswordMode ? t('passwordDialog.savingStatus') : t('passwordDialog.changingStatus'),
      'info'
    );

    try {
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
      resetAuthenticationAssistanceAutoOpenState();
      closePasswordDialog();
      dismissActiveKeyboard();
      setStatus(t('status.userAuthenticated'), 'success');
      await loadAuthenticatedApplication(normalizedChave, { showReadyMessage: false });
    } catch (error) {
      if (isUnknownUserError(error)) {
        closePasswordDialog();
        routeToUnknownUserSelfRegistration(normalizedChave);
        return;
      }
      setStatus(
        error instanceof Error ? localizeKnownApiMessage(error.message) : t('passwordDialog.changeFailed'),
        'error'
      );
    } finally {
      passwordChangeInProgress = false;
      syncFormControlStates();
    }
  }

  async function submitUserSelfRegistration(event) {
    event.preventDefault();

    await loadProjectCatalog({ showError: true });
    if (!allowedProjectValues.length) {
      setStatus(
        typeof t === 'function'
          ? t('registrationDialog.noProjectsAvailable')
          : 'Nenhum projeto está disponível no momento.',
        'error'
      );
      return;
    }

    const normalizedChave = sanitizeChave(registrationChaveInput.value);
    const nome = String(registrationNameInput.value || '').trim().replace(/\s+/g, ' ');
    const projetos = readSelectedRegistrationProjectValues();
    const email = String(registrationEmailInput.value || '').trim();
    const password = registrationPasswordInput.value;
    const confirmPassword = registrationConfirmPasswordInput.value;

    registrationChaveInput.value = normalizedChave;
    registrationNameInput.value = nome;
    registrationEmailInput.value = email;

    if (normalizedChave.length !== 4) {
      setStatus(
        typeof t === 'function' ? t('auth.invalidFourCharacterKey') : 'Informe uma chave com 4 caracteres alfanuméricos.',
        'error'
      );
      registrationChaveInput.focus();
      return;
    }

    if (nome.length < 3) {
      setStatus(
        typeof t === 'function' ? t('registrationDialog.fullNameRequired') : 'Informe o nome completo.',
        'error'
      );
      registrationNameInput.focus();
      return;
    }

    if (!projetos.length) {
      setStatus(
        typeof t === 'function' ? t('projects.selectAtLeastOne') : 'Selecione ao menos um projeto.',
        'error'
      );
      focusRegistrationProjectOptions();
      return;
    }

    if (email && email.indexOf('@') === -1) {
      setStatus(
        typeof t === 'function'
          ? t('registrationDialog.emailInvalid')
          : 'Informe um e-mail válido ou deixe o campo em branco.',
        'error'
      );
      registrationEmailInput.focus();
      return;
    }

    if (!clientState.isPasswordLengthValid(password)) {
      setStatus(
        typeof t === 'function'
          ? t('registrationDialog.passwordInvalid')
          : 'A senha deve ter entre 3 e 10 caracteres.',
        'error'
      );
      registrationPasswordInput.focus();
      return;
    }

    if (password !== confirmPassword) {
      setStatus(
        typeof t === 'function'
          ? t('registrationDialog.confirmMismatch')
          : 'A confirmação da nova senha não confere.',
        'error'
      );
      registrationConfirmPasswordInput.focus();
      return;
    }

    userSelfRegistrationInProgress = true;
    syncFormControlStates();
    setStatus(
      typeof t === 'function'
        ? t('registrationDialog.submittingStatus')
        : 'Enviando solicitação de cadastro...',
      'info'
    );

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
          projetos,
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
      if (Array.isArray(payload.projects) && payload.projects.length && payload.active_project) {
        applyCurrentUserProjectMemberships(payload);
      }
      writePersistedChave(normalizedChave);

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
      resetAuthenticationAssistanceAutoOpenState();

      closeRegistrationDialog();
      dismissActiveKeyboard();
      syncFormControlStates();
      await loadAuthenticatedApplication(normalizedChave, { showReadyMessage: false });
      setStatus(
        typeof t === 'function' ? t('registrationDialog.successStatus') : 'Cadastro concluído com sucesso.',
        'success'
      );
    } catch (error) {
      setStatus(
        error instanceof Error
          ? (typeof localizeKnownApiMessage === 'function' ? localizeKnownApiMessage(error.message) : error.message)
          : (typeof t === 'function'
              ? t('registrationDialog.submitFailed')
              : 'Não foi possível enviar a solicitação de cadastro.'),
        'error'
      );
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
    if (!payload) return t('status.operationFailed');
    if (typeof payload.detail === 'string') return localizeKnownApiMessage(payload.detail);
    if (Array.isArray(payload.detail)) {
      return payload.detail
        .map((entry) => localizeKnownApiMessage(entry.msg || entry.message) || t('status.validationError'))
        .join(' ');
    }
    if (typeof payload.message === 'string') return localizeKnownApiMessage(payload.message);
    return t('status.operationFailed');
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

  function resolveProjectCatalogFallbackValues() {
    return allowedProjectValues.length ? [allowedProjectValues[0]] : [];
  }

  function normalizeKnownProjectValue(projectValue, fallbackProject) {
    const normalizedFallback = String(fallbackProject || defaultProjectValue || allowedProjectValues[0] || '').trim().toUpperCase();
    return clientState.normalizeProjectValue(projectValue, allowedProjectValues, normalizedFallback);
  }

  function normalizeKnownProjectValues(projectValues, fallbackProjects) {
    const normalizedFallbackProjects = clientState.normalizeProjectValues(
      Array.isArray(fallbackProjects) ? fallbackProjects : [fallbackProjects],
      allowedProjectValues,
      resolveProjectCatalogFallbackValues()
    );
    return clientState.normalizeProjectValues(
      projectValues,
      allowedProjectValues,
      normalizedFallbackProjects
    );
  }

  function resolveCurrentUserProjectValues() {
    return normalizeKnownProjectValues(
      currentUserProjectValues,
      lastCommittedUserProjectValues.length ? lastCommittedUserProjectValues : resolveProjectCatalogFallbackValues()
    );
  }

  function resolveCommittedProjectValue() {
    const fallbackProject = resolveCurrentUserProjectValues()[0] || defaultProjectValue;
    return normalizeKnownProjectValue(lastCommittedProjectValue || fallbackProject, fallbackProject);
  }

  function resolveProjectMembershipSummaryText(projectValues) {
    const resolvedProjects = normalizeKnownProjectValues(projectValues, resolveCurrentUserProjectValues());
    if (resolvedProjects.length) {
      return resolvedProjects.join(', ');
    }

    return projectCatalogLoading || userProjectsLoading
      ? t('projects.loadingProjects')
      : t('projects.noneAvailableShort');
  }

  function resolveProjectMembershipStatusText() {
    if (projectUpdateInProgress) {
      return t('projects.updatingProjects');
    }
    if (projectCatalogLoading || userProjectsLoading) {
      return t('projects.loadingProjects');
    }
    if (!allowedProjectValues.length) {
      return t('projects.noneAvailableSentence');
    }
    return t('projects.selectAtLeastOne');
  }

  function setProjectMembershipPanelOpen(isOpen) {
    if (!projectMembershipPanel || !projectMembershipButton) {
      return;
    }

    const shouldOpen = Boolean(isOpen)
      && !projectMembershipButton.disabled
      && !(projectField && projectField.classList.contains('is-hidden'));
    projectMembershipPanel.hidden = !shouldOpen;
    projectMembershipPanel.classList.toggle('is-hidden', !shouldOpen);
    projectMembershipButton.setAttribute('aria-expanded', String(shouldOpen));
  }

  function closeProjectMembershipPanel() {
    setProjectMembershipPanelOpen(false);
  }

  function readSelectedProjectMembershipValues() {
    if (!projectMembershipOptions || typeof projectMembershipOptions.querySelectorAll !== 'function') {
      return resolveCurrentUserProjectValues();
    }

    return Array.from(projectMembershipOptions.querySelectorAll('input[name="userProjectMembership"]:checked'))
      .map((input) => String(input.value || '').trim().toUpperCase())
      .filter(Boolean);
  }

  function syncProjectMembershipOptions(projectValues) {
    if (projectMembershipSummary) {
      projectMembershipSummary.textContent = resolveProjectMembershipSummaryText(projectValues);
    }

    if (projectMembershipStatus) {
      projectMembershipStatus.textContent = resolveProjectMembershipStatusText();
    }

    if (!projectMembershipOptions) {
      return;
    }

    const resolvedProjects = normalizeKnownProjectValues(
      projectValues,
      lastCommittedUserProjectValues.length ? lastCommittedUserProjectValues : resolveProjectCatalogFallbackValues()
    );

    currentUserProjectValues = resolvedProjects;
    projectMembershipOptions.replaceChildren();

    if (!allowedProjectValues.length) {
      const emptyState = document.createElement('p');
      emptyState.className = 'project-membership-empty';
      emptyState.textContent = projectCatalogLoading || userProjectsLoading
        ? t('projects.loadingProjects')
        : t('projects.noneAvailableShort');
      projectMembershipOptions.append(emptyState);
      return;
    }

    const interactionDisabled = !isApplicationUnlocked()
      || projectCatalogLoading
      || userProjectsLoading
      || projectUpdateInProgress;

    allowedProjectValues.forEach((projectName) => {
      const optionLabel = document.createElement('label');
      optionLabel.className = 'project-membership-option';

      const optionInput = document.createElement('input');
      optionInput.type = 'checkbox';
      optionInput.name = 'userProjectMembership';
      optionInput.value = projectName;
      optionInput.checked = resolvedProjects.includes(projectName);
      optionInput.disabled = interactionDisabled || (resolvedProjects.length === 1 && optionInput.checked);

      const optionText = document.createElement('span');
      optionText.textContent = projectName;

      optionLabel.append(optionInput, optionText);
      projectMembershipOptions.append(optionLabel);
    });
  }

  function resolveRegistrationProjectHintText() {
    if (projectCatalogLoading) {
      return t('registrationDialog.loadingProjects');
    }
    if (!allowedProjectValues.length) {
      return t('projects.noneAvailableSentence');
    }
    return t('registrationDialog.projectsHint');
  }

  function focusRegistrationProjectOptions() {
    if (!registrationProjectOptions || typeof registrationProjectOptions.querySelector !== 'function') {
      return;
    }

    const firstInput = registrationProjectOptions.querySelector('input[name="registrationProjectMembership"]');
    if (firstInput && typeof firstInput.focus === 'function') {
      firstInput.focus();
    }
  }

  function readSelectedRegistrationProjectValues() {
    if (!registrationProjectOptions || typeof registrationProjectOptions.querySelectorAll !== 'function') {
      return [];
    }

    return Array.from(registrationProjectOptions.querySelectorAll('input[name="registrationProjectMembership"]:checked'))
      .map((input) => String(input.value || '').trim().toUpperCase())
      .filter(Boolean);
  }

  function syncRegistrationProjectOptions(projectValues) {
    if (registrationProjectHint) {
      registrationProjectHint.textContent = resolveRegistrationProjectHintText();
    }

    if (!registrationProjectOptions) {
      return;
    }

    const resolvedProjects = normalizeKnownProjectValues(
      projectValues,
      resolveProjectCatalogFallbackValues()
    );

    registrationProjectOptions.replaceChildren();

    if (!allowedProjectValues.length) {
      const emptyState = document.createElement('p');
      emptyState.className = 'project-membership-empty';
      emptyState.textContent = projectCatalogLoading
        ? t('registrationDialog.loadingProjects')
        : t('projects.noneAvailableShort');
      registrationProjectOptions.append(emptyState);
      return;
    }

    const interactionDisabled = userSelfRegistrationInProgress || projectCatalogLoading;
    allowedProjectValues.forEach((projectName) => {
      const optionLabel = document.createElement('label');
      optionLabel.className = 'project-membership-option';

      const optionInput = document.createElement('input');
      optionInput.type = 'checkbox';
      optionInput.name = 'registrationProjectMembership';
      optionInput.value = projectName;
      optionInput.checked = resolvedProjects.includes(projectName);
      optionInput.disabled = interactionDisabled;

      const optionText = document.createElement('span');
      optionText.textContent = projectName;

      optionLabel.append(optionInput, optionText);
      registrationProjectOptions.append(optionLabel);
    });
  }

  function syncProjectMembershipControls(options) {
    const settings = options || {};
    const selectedRegistrationProjects = readSelectedRegistrationProjectValues();
    const nextProjectValues = normalizeKnownProjectValues(
      settings.projectValues !== undefined ? settings.projectValues : resolveCurrentUserProjectValues(),
      lastCommittedUserProjectValues.length ? lastCommittedUserProjectValues : resolveProjectCatalogFallbackValues()
    );
    const mainValue = normalizeKnownProjectValue(
      settings.mainValue !== undefined ? settings.mainValue : (lastCommittedProjectValue || nextProjectValues[0]),
      nextProjectValues[0] || defaultProjectValue
    );
    const nextRegistrationProjectValues = normalizeKnownProjectValues(
      settings.registrationProjectValues !== undefined
        ? settings.registrationProjectValues
        : (selectedRegistrationProjects.length
            ? selectedRegistrationProjects
            : [settings.registrationValue !== undefined ? settings.registrationValue : mainValue]),
      [settings.registrationValue !== undefined ? settings.registrationValue : mainValue]
    );

    currentUserProjectValues = nextProjectValues;
    syncProjectMembershipOptions(nextProjectValues);
    syncRegistrationProjectOptions(nextRegistrationProjectValues);
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
    currentUserProjectValues = normalizeKnownProjectValues(
      currentUserProjectValues,
      resolveProjectCatalogFallbackValues()
    );
    lastCommittedUserProjectValues = normalizeKnownProjectValues(
      lastCommittedUserProjectValues.length ? lastCommittedUserProjectValues : currentUserProjectValues,
      currentUserProjectValues.length ? currentUserProjectValues : resolveProjectCatalogFallbackValues()
    );
    lastCommittedProjectValue = normalizeKnownProjectValue(lastCommittedProjectValue, defaultProjectValue);
    syncProjectMembershipControls({
      projectValues: settings.projectValues !== undefined ? settings.projectValues : currentUserProjectValues,
      mainValue: settings.mainValue !== undefined ? settings.mainValue : lastCommittedProjectValue,
      registrationProjectValues:
        settings.registrationProjectValues !== undefined
          ? settings.registrationProjectValues
          : readSelectedRegistrationProjectValues(),
      registrationValue:
        settings.registrationValue !== undefined
          ? settings.registrationValue
          : lastCommittedProjectValue,
    });
    syncFormControlStates();
  }

  async function loadProjectCatalog(options) {
    if (projectCatalogPromise) {
      return projectCatalogPromise;
    }

    const settings = options || {};
    projectCatalogLoading = true;
    syncProjectMembershipControls();
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
          setStatus(error instanceof Error ? localizeKnownApiMessage(error.message) : t('projects.loadFailed'), 'error');
        }
        syncProjectMembershipControls();
        return allowedProjectValues;
      })
      .finally(() => {
        projectCatalogLoading = false;
        syncProjectMembershipControls();
        syncFormControlStates();
        projectCatalogPromise = null;
      });

    return projectCatalogPromise;
  }

  function resolveCurrentUserSettingsDefaults() {
    const fallbackProjects = resolveCurrentUserProjectValues();
    return {
      projects: fallbackProjects,
      activeProject: normalizeKnownProjectValue(
        lastCommittedProjectValue,
        fallbackProjects[0] || defaultProjectValue
      ),
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

    currentUserProjectValues = normalizeKnownProjectValues(
      resolvedSettings.projects,
      resolveProjectCatalogFallbackValues()
    );
    lastCommittedUserProjectValues = currentUserProjectValues.slice();
    lastCommittedProjectValue = normalizeKnownProjectValue(
      resolvedSettings.activeProject,
      currentUserProjectValues[0] || defaultProjectValue
    );

    syncProjectMembershipControls({
      projectValues: currentUserProjectValues,
      mainValue: lastCommittedProjectValue,
      registrationProjectValues: currentUserProjectValues,
      registrationValue: lastCommittedProjectValue,
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
        projects: resolveCurrentUserProjectValues(),
        activeProject: resolveCommittedProjectValue(),
        automaticActivitiesEnabled: Boolean(
          automaticActivitiesToggle && automaticActivitiesToggle.checked
        ),
      },
      resolveCurrentUserSettingsDefaults()
    );
    writePersistedUserSettingsMap(nextSettingsMap);
  }

  function applyCurrentUserProjectMemberships(payload) {
    const committedProjects = normalizeKnownProjectValues(
      payload && payload.projects,
      lastCommittedUserProjectValues.length ? lastCommittedUserProjectValues : resolveProjectCatalogFallbackValues()
    );
    const committedProject = normalizeKnownProjectValue(
      payload && payload.active_project,
      committedProjects[0] || defaultProjectValue
    );

    currentUserProjectValues = committedProjects;
    lastCommittedUserProjectValues = committedProjects.slice();
    lastCommittedProjectValue = committedProject;
    syncProjectMembershipControls({
      projectValues: committedProjects,
      mainValue: committedProject,
      registrationProjectValues: committedProjects,
      registrationValue: committedProject,
    });
    if (latestHistoryState && typeof latestHistoryState === 'object') {
      latestHistoryState.projeto = committedProject;
    }
    persistCurrentUserSettings();
    return { committedProjects, committedProject };
  }

  async function loadCurrentUserProjectMemberships(options) {
    if (!isApplicationUnlocked()) {
      return null;
    }

    const settings = options || {};
    userProjectsLoading = true;
    syncProjectMembershipControls();
    syncFormControlStates();
    try {
      const response = await fetch(userProjectsEndpoint, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw buildProtectedRequestError(response, payload);
      }

      applyCurrentUserProjectMemberships(payload);
      return payload;
    } catch (error) {
      if (error && error.isAuthExpired) {
        return null;
      }

      if (settings.showError !== false) {
        setStatus(
          error instanceof Error ? localizeKnownApiMessage(error.message) : t('projects.userProjectsLoadFailed'),
          'error'
        );
      }
      syncProjectMembershipControls();
      return null;
    } finally {
      userProjectsLoading = false;
      syncProjectMembershipControls();
      syncFormControlStates();
    }
  }

  async function updateCurrentUserProjectSelection() {
    const normalizedChave = getActiveChave();
    const nextProjects = normalizeKnownProjectValues(
      readSelectedProjectMembershipValues(),
      lastCommittedUserProjectValues.length ? lastCommittedUserProjectValues : resolveProjectCatalogFallbackValues()
    );
    const manualOverrideActive = isAccuracyTooLowManualFallbackActive();
    syncProjectMembershipControls({ projectValues: nextProjects, mainValue: lastCommittedProjectValue });

    if (!nextProjects.length) {
      syncProjectMembershipControls({
        projectValues: lastCommittedUserProjectValues,
        mainValue: lastCommittedProjectValue || defaultProjectValue,
      });
      setStatus(
        typeof t === 'function' ? t('projects.selectAtLeastOne') : 'Selecione ao menos um projeto.',
        'error'
      );
      return false;
    }

    if (
      normalizedChave.length !== 4
      || !isApplicationUnlocked(normalizedChave)
      || (isAutomaticActivitiesEnabled() && !manualOverrideActive)
    ) {
      persistCurrentUserSettings();
      syncFormControlStates();
      return false;
    }

    projectUpdateInProgress = true;
    syncFormControlStates();
    try {
      const response = await fetch(userProjectsEndpoint, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          projects: nextProjects,
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw buildProtectedRequestError(response, payload);
      }

      applyCurrentUserProjectMemberships(payload);
      await loadManualLocations();
      setStatus(
        (typeof localizeKnownApiMessage === 'function' ? localizeKnownApiMessage(payload && payload.message) : (payload && payload.message))
          || (typeof t === 'function' ? t('projects.updatedSuccess') : 'Projetos atualizados com sucesso.'),
        'success'
      );
      return true;
    } catch (error) {
      if (error && error.isAuthExpired) {
        return false;
      }

      syncProjectMembershipControls({
        projectValues: lastCommittedUserProjectValues,
        mainValue: lastCommittedProjectValue || defaultProjectValue,
      });
      setStatus(
        error instanceof Error
          ? (typeof localizeKnownApiMessage === 'function' ? localizeKnownApiMessage(error.message) : error.message)
          : (typeof t === 'function' ? t('projects.updateFailed') : 'Não foi possível atualizar os projetos.'),
        'error'
      );
      return false;
    } finally {
      projectUpdateInProgress = false;
      syncProjectMembershipControls();
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

  function resolveDisplayedLocationLabel(matchPayload) {
    const locationLabel = matchPayload && typeof matchPayload.label === 'string'
      ? matchPayload.label
      : '';
    return localizeKnownLocationLabel(locationLabel);
  }

  function resolveMatchedOperationalLocation(matchPayload) {
    if (!matchPayload || !matchPayload.matched) {
      return null;
    }

    const resolvedLocal = String(matchPayload.resolved_local || '').trim();
    return resolvedLocal || null;
  }

  function setResolvedLocation(matchPayload) {
    const matchedOperationalLocation = resolveMatchedOperationalLocation(matchPayload);
    currentLocationMatch = matchedOperationalLocation
      ? { ...matchPayload, resolved_local: matchedOperationalLocation }
      : null;
    currentLocationResolutionStatus = matchPayload && typeof matchPayload.status === 'string'
      ? matchPayload.status
      : null;
    syncProjectVisibility();
  }

  function isAccuracyTooLowManualFallbackActive() {
    return gpsLocationPermissionGranted && currentLocationResolutionStatus === 'accuracy_too_low';
  }

  function shouldAllowManualLocationSelection() {
    return clientState.shouldOfferManualLocationSelection({
      automaticActivitiesEnabled: isAutomaticActivitiesEnabled(),
      gpsLocationPermissionGranted,
      accuracyTooLowFallbackActive: isAccuracyTooLowManualFallbackActive(),
    });
  }

  function setLocationWithoutPermission() {
    writeStorageFlag(locationPermissionGrantedKey, false);
    setResolvedLocation(null);
    setGpsLocationPermissionGranted(false);
    setLocationPresentation(t('location.noPermissionLabel'), '', null, '--', { suppressNotification: true });
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
      return Promise.reject(new Error(t('auth.enterPasswordPrompt')));
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

  function shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, options) {
    const settings = options || {};
    return automaticActivities.shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, {
      mixedZoneIntervalMinutes: settings.mixedZoneIntervalMinutes ?? mixedZoneIntervalMinutes,
      referenceTime: settings.referenceTime,
    });
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

  function isOperationalAutomaticCheckInLocation(locationPayload, automaticLocal) {
    return automaticActivities.isOperationalAutomaticCheckInLocation(locationPayload, automaticLocal);
  }

  function resolveAutomaticLocationAction(locationPayload, remoteState) {
    const resolvedLocal = locationPayload && locationPayload.resolved_local;

    if (automaticActivities.isMixedZoneLocationName(resolvedLocal)) {
      return automaticActivities.resolveLastRecordedAction(remoteState) === 'checkin'
        ? 'checkout'
        : 'checkin';
    }

    return isCheckoutZoneLocationName(resolvedLocal) ? 'checkout' : 'checkin';
  }

  async function submitAutomaticActivity({ action, local, suppressStatus }) {
    const chave = sanitizeChave(chaveInput.value);
    if (!isApplicationUnlocked(chave)) {
      throw new Error(t('auth.enterPasswordPrompt'));
    }

    const submittedLocal = resolveFinalSubmittableLocationValue(local);
    if (!submittedLocal) {
      return null;
    }

    const response = await fetch(submitEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chave,
        projeto: resolveCommittedProjectValue(),
        action,
        local: submittedLocal,
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
          ? t('status.automaticCheckinCompleted')
          : (
              isCheckoutZoneLocationName(submittedLocal)
                ? t('status.automaticCheckoutCompleted')
                : t('status.automaticCheckoutCompleted')
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

    const remoteState = settings.remoteState || await fetchWebState(chave);
    latestHistoryState = remoteState;
    applyHistoryState(remoteState);

    if (
      locationPayload
      && locationPayload.matched
      && shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, {
        mixedZoneIntervalMinutes,
        referenceTime: settings.referenceTime,
      })
    ) {
      const automaticAction = resolveAutomaticLocationAction(locationPayload, remoteState);
      const submittedPayload = await submitAutomaticActivity({
        action: automaticAction,
        local: locationPayload.resolved_local,
        suppressStatus: settings.suppressStatus,
      });
      if (!submittedPayload) {
        return noActivityResult;
      }
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
      const submittedPayload = await submitAutomaticActivity({
        action: 'checkout',
        local: automaticCheckoutLocation,
        suppressStatus: settings.suppressStatus,
      });
      if (!submittedPayload) {
        return noActivityResult;
      }
      return {
        performed: true,
        action: 'checkout',
        local: automaticCheckoutLocation,
      };
    }

    if (locationPayload && shouldAttemptAutomaticNearbyWorkplaceCheckIn(locationPayload, remoteState)) {
      const automaticLocal = resolveAutomaticCheckInLocation(locationPayload);
      if (!isOperationalAutomaticCheckInLocation(locationPayload, automaticLocal)) {
        return noActivityResult;
      }
      const submittedPayload = await submitAutomaticActivity({
        action: 'checkin',
        local: automaticLocal,
        suppressStatus: settings.suppressStatus,
      });
      if (!submittedPayload) {
        return noActivityResult;
      }
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
      return thresholdMeters
        ? (typeof t === 'function'
            ? t('location.accuracyLimitTemplate', { limit: Math.round(thresholdMeters) })
            : `Limite ${Math.round(thresholdMeters)} m`)
        : '--';
    }
    if (typeof thresholdMeters !== 'number' || !Number.isFinite(thresholdMeters)) {
      return typeof t === 'function'
        ? t('location.accuracyTemplate', { accuracy: formatMeters(accuracyMeters) })
        : `Precisão ${formatMeters(accuracyMeters)}`;
    }
    return typeof t === 'function'
      ? t('location.accuracyCombinedTemplate', {
        accuracy: formatMeters(accuracyMeters),
        limit: Math.round(thresholdMeters),
      })
      : `Precisão ${formatMeters(accuracyMeters)} / Limite ${Math.round(thresholdMeters)} m`;
  }

  function normalizeLocationPermissionState(value) {
    return value === 'granted' || value === 'denied' || value === 'prompt'
      ? value
      : null;
  }

  function setLastKnownLocationPermissionState(value) {
    const normalizedState = normalizeLocationPermissionState(value);
    if (lastKnownLocationPermissionState === normalizedState) {
      return;
    }

    lastKnownLocationPermissionState = normalizedState;
    syncFormControlStates();
  }

  function isLocationPermissionEffectivelySharedWithWebApp() {
    return gpsLocationPermissionGranted
      || readStorageFlag(locationPermissionGrantedKey)
      || lastKnownLocationPermissionState === 'granted';
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
    if (gpsLocationPermissionGranted) {
      setLastKnownLocationPermissionState('granted');
    }
    syncAutomaticActivitiesAvailability();
    syncProjectVisibility();
    syncManualLocationControl();
  }

  function resolveManualLocationOptions() {
    const manualLocationOptions = Array.from(new Set(availableLocations));

    if (!isAccuracyTooLowManualFallbackActive() || manualLocationOptions.includes(defaultManualLocationLabel)) {
      return manualLocationOptions;
    }

    return [accuracyFallbackManualLocationLabel, ...manualLocationOptions];
  }

  function resolveManualLocationDefaultForCurrentProject() {
    const manualLocationOptions = resolveManualLocationOptions();

    if (manualLocationOptions.includes(defaultManualLocationLabel)) {
      return defaultManualLocationLabel;
    }

    if (isAccuracyTooLowManualFallbackActive() && manualLocationOptions.includes(accuracyFallbackManualLocationLabel)) {
      return accuracyFallbackManualLocationLabel;
    }

    return manualLocationOptions[0] || '';
  }

  function getDefaultManualLocation() {
    return resolveManualLocationDefaultForCurrentProject();
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
      emptyOption.textContent = placeholder || (
        typeof t === 'function' ? t('location.noKnownLocations') : 'Sem localizações cadastradas'
      );
      manualLocationSelect.append(emptyOption);
      manualLocationSelect.value = '';
      return;
    }

    nextValues.forEach((value) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = typeof localizeKnownLocationLabel === 'function'
        ? localizeKnownLocationLabel(value)
        : value;
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
    const manualLocationOptions = resolveManualLocationOptions();

    if (!shouldAllowManualLocationSelection()) {
      setLocationSelectOptions(availableLocations, displayedLocation || getDefaultManualLocation(), {
        allowTemporaryValue: true,
        placeholder: displayedLocation || (
          typeof t === 'function' ? t('location.waitingLabel') : 'Aguardando localização.'
        ),
      });
      syncFormControlStates();
      return;
    }

    const currentSelection = manualLocationSelect.value;
    const gpsMatchedLocal = resolveMatchedOperationalLocation(currentLocationMatch);
    const nextManualValue = manualLocationOptions.includes(currentSelection)
      ? currentSelection
      : (gpsMatchedLocal && manualLocationOptions.includes(gpsMatchedLocal)
        ? gpsMatchedLocal
        : getDefaultManualLocation());
    setLocationSelectOptions(manualLocationOptions, nextManualValue, {
      placeholder: typeof t === 'function' ? t('location.noKnownLocations') : 'Sem localizações cadastradas',
    });
    syncFormControlStates();
  }

  function resolveSubmittedLocationValue() {
    if (shouldAllowManualLocationSelection()) {
      return manualLocationSelect.value || null;
    }

    return resolveMatchedOperationalLocation(currentLocationMatch);
  }

  function isSyntheticFailureLocationValue(local) {
    const normalizedLocal = String(local || '').trim();
    return normalizedLocal === automaticActivities.AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION
      || normalizedLocal === accuracyFallbackManualLocationLabel;
  }

  function resolveFinalSubmittableLocationValue(local) {
    const normalizedLocal = String(local || '').trim();
    if (!normalizedLocal || isSyntheticFailureLocationValue(normalizedLocal)) {
      return null;
    }

    return normalizedLocal;
  }

  async function loadManualLocations() {
    if (!isApplicationUnlocked()) {
      availableLocations = [];
      setLocationAccuracyThresholdMeters(null);
      mixedZoneIntervalMinutes = null;
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

      setLocationAccuracyThresholdMeters(payload.location_accuracy_threshold_meters);
      setMixedZoneIntervalMinutes(payload.mixed_zone_interval_minutes);

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
      setLastKnownLocationPermissionState(null);
      return null;
    }

    try {
      const permissionStatus = await navigator.permissions.query({ name: 'geolocation' });
      const permissionState = permissionStatus && typeof permissionStatus.state === 'string'
        ? permissionStatus.state
        : null;
      setLastKnownLocationPermissionState(permissionState);
      return permissionState;
    } catch {
      setLastKnownLocationPermissionState(null);
      return null;
    }
  }

  function requestCurrentPosition(measurementSession) {
    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          recordLocationMeasurementSample(measurementSession, position);
          resolve(position);
        },
        (error) => {
          recordLocationMeasurementEvent(measurementSession, 'geolocation_error', {
            code: error && typeof error.code === 'number' ? error.code : null,
            message: error && typeof error.message === 'string' ? error.message : '',
          });
          reject(error);
        },
        geolocationOptions
      );
    });
  }

  async function matchCurrentPosition(position, measurementSession) {
    if (!isApplicationUnlocked()) {
      throw new Error(t('auth.enterPasswordPrompt'));
    }

    const accuracyMeters = readPositionAccuracyMeters(position);
    recordLocationMeasurementMatchRequest(measurementSession, accuracyMeters);

    const response = await fetch(locationEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy_meters: accuracyMeters,
      }),
    });

    const payload = await response.json().catch(() => ({}));
    if (measurementSession) {
      if (typeof payload.accuracy_threshold_meters === 'number' && Number.isFinite(payload.accuracy_threshold_meters)) {
        measurementSession.threshold_meters = payload.accuracy_threshold_meters;
      }
      recordLocationMeasurementEvent(measurementSession, 'match_response_received', {
        http_status: response.status,
        status: typeof payload.status === 'string' ? payload.status : null,
        accuracy_threshold_meters:
          typeof payload.accuracy_threshold_meters === 'number' && Number.isFinite(payload.accuracy_threshold_meters)
            ? payload.accuracy_threshold_meters
            : null,
      });
    }
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
    setLocationAccuracyThresholdMeters(payload.accuracy_threshold_meters);
    const accuracyText = buildAccuracyText(payload.accuracy_meters, payload.accuracy_threshold_meters);
    const locationMessage = payload.status === 'matched'
      ? ''
      : localizeKnownApiMessage(payload.message);
    setResolvedLocation(payload);
    setLocationPresentation(
      resolveDisplayedLocationLabel(payload),
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
        t('location.unavailableLabel'),
        t('location.unavailableMessage'),
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
        t('location.unavailableLabel'),
        t('location.noValidPosition'),
        'error',
        '--',
        options
      );
      return;
    }

    if (error.code === 3) {
      setLocationPresentation(
        t('location.timeoutLabel'),
        t('location.timeoutMessage'),
        'warning',
        '--',
        options
      );
      return;
    }

    setLocationPresentation(
      t('location.unavailableLabel'),
      t('location.unavailableMessage'),
      'error',
      '--',
      options
    );
  }

  async function resolveCurrentLocation(options) {
    const settings = options || {};
    const suppressNotification = Boolean(settings.suppressNotification);
    const capturePlan = buildLocationCapturePlan(settings);
    const measurementSession = createLocationMeasurementSession({
      interactive: settings.interactive,
      forceRefresh: settings.forceRefresh,
      measurementTrigger: capturePlan.trigger,
      captureStrategy: capturePlan.strategy,
      targetAccuracyMeters: capturePlan.targetAccuracyMeters,
    });
    if (!window.isSecureContext || !navigator.geolocation) {
      recentLocationResolutionPayload = null;
      recentLocationResolutionAt = 0;
      recentLocationResolutionChave = '';
      setResolvedLocation(null);
      setLocationPresentation(
        t('location.unavailableShort'),
        suppressNotification
          ? ''
          : t('location.captureRequiresSupport'),
        'error',
        '--',
        { suppressNotification }
      );
      finalizeLocationMeasurementSession(measurementSession, {
        termination_reason: 'geolocation_unsupported',
      });
      return null;
    }

    if (!settings.forceRefresh) {
      const recentLocationResolution = readRecentLocationResolution({
        cacheWindowMs: settings.cacheWindowMs,
      });
      if (recentLocationResolution) {
        finalizeLocationMeasurementSession(measurementSession, {
          termination_reason: 'reused_recent_resolution',
          cancelled: true,
        });
        return recentLocationResolution;
      }
    }

    if (locationRequestPromise && !settings.forceRefresh) {
      finalizeLocationMeasurementSession(measurementSession, {
        termination_reason: 'reused_pending_request',
        cancelled: true,
      });
      return locationRequestPromise;
    }

    if (settings.interactive) {
      writeStorageFlag(locationPromptAttemptedKey, true);
    }

    const pendingRequest = (async () => {
      setLocationRefreshLoading(true);

      if (settings.showDetectingState) {
        setLocationPresentation(
          t('location.detectingLabel'),
          settings.interactive
            ? (isStandaloneShortcutMode()
                ? t('location.exactConfirmationApp')
                : t('location.exactConfirmationBrowser'))
            : t('location.updatingDeviceLocation'),
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
        recentLocationResolutionPayload = null;
        recentLocationResolutionAt = 0;
        recentLocationResolutionChave = '';
        finalizeLocationMeasurementSession(measurementSession, {
          termination_reason: 'permission_not_granted',
        });
        setLocationWithoutPermission();
        return null;
      }

      try {
        const position = await requestCurrentPositionForPlan(capturePlan, measurementSession, {
          showDetectingState: settings.showDetectingState,
        });
        writeStorageFlag(locationPermissionGrantedKey, true);
        setGpsLocationPermissionGranted(true);
        const matchPayload = await matchCurrentPosition(position, measurementSession);
        recentLocationResolutionPayload = matchPayload;
        recentLocationResolutionAt = Date.now();
        recentLocationResolutionChave = getActiveChave();
        applyLocationMatch(matchPayload, { suppressNotification });
        finalizeLocationMeasurementSession(measurementSession, {
          final_status: matchPayload && typeof matchPayload.status === 'string' ? matchPayload.status : null,
          termination_reason: 'match_response',
          threshold_meters:
            matchPayload && typeof matchPayload.accuracy_threshold_meters === 'number' && Number.isFinite(matchPayload.accuracy_threshold_meters)
              ? matchPayload.accuracy_threshold_meters
              : null,
          final_accuracy_sent_meters:
            matchPayload && typeof matchPayload.accuracy_meters === 'number' && Number.isFinite(matchPayload.accuracy_meters)
              ? matchPayload.accuracy_meters
              : null,
        });
        if (settings.showCompletionStatus) {
          setStatus(
            buildLocationCompletionMessage(matchPayload),
            resolveLocationCompletionTone(matchPayload)
          );
        }
        return matchPayload;
      } catch (error) {
        recentLocationResolutionPayload = null;
        recentLocationResolutionAt = 0;
        recentLocationResolutionChave = '';
        finalizeLocationMeasurementSession(
          measurementSession,
          describeLocationMeasurementFailure(error)
        );
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
      measurementTrigger: settings.measurementTrigger,
      showCompletionStatus: Boolean(settings.showCompletionStatus),
      suppressNotification: Boolean(settings.suppressNotification),
      showDetectingState: settings.showDetectingState !== false,
    });
  }

  async function requestPreciseLocationPermissionFromSettings() {
    if (isLocationPermissionEffectivelySharedWithWebApp()) {
      syncFormControlStates();
      return null;
    }

    if (!window.isSecureContext) {
      setStatus(
        typeof t === 'function'
          ? t('location.secureContextRequired')
          : 'A localização precisa requer uma conexão segura (HTTPS).',
        'error'
      );
      return null;
    }

    if (!navigator.geolocation) {
      setStatus(
        typeof t === 'function'
          ? t('location.browserUnsupported')
          : 'Este navegador não oferece suporte à localização precisa.',
        'error'
      );
      return null;
    }

    const permissionState = await queryLocationPermissionState();
    if (permissionState === 'denied') {
      setLocationWithoutPermission();
      setStatus(
        typeof t === 'function'
          ? t('location.permissionBlocked')
          : 'A permissão de localização está bloqueada no navegador. Libere o acesso ao site nas configurações do navegador.',
        'warning'
      );
      return null;
    }

    return runWithLockedUserInteraction(async () => resolveCurrentLocation({
      interactive: true,
      forceRefresh: true,
      measurementTrigger: 'settings_permission',
      showDetectingState: true,
      showCompletionStatus: true,
      suppressNotification: false,
    }));
  }

  async function updateLocationForLifecycleSequence(options) {
    const settings = options || {};
    return resolveCurrentLocation({
      interactive: false,
      forceRefresh: Boolean(settings.forceRefresh),
      measurementTrigger: settings.triggerSource,
      cacheWindowMs: settings.cacheWindowMs,
      suppressNotification: settings.suppressNotification !== false,
      showDetectingState: settings.showDetectingState !== false,
    });
  }

  async function ensureLocationReadyForSubmit() {
    if (!isApplicationUnlocked()) {
      throw new Error(t('auth.enterPasswordPrompt'));
    }

    if (locationRequestPromise) {
      await locationRequestPromise;
      return;
    }

    if (readRecentLocationResolution({ cacheWindowMs: lifecycleDataReuseWindowMs })) {
      return;
    }

    const permissionState = await queryLocationPermissionState();
    if (
      clientState.shouldAttemptSilentLocationLookup(
        permissionState,
        readStorageFlag(locationPermissionGrantedKey)
      )
    ) {
      await captureAndResolveLocation({
        interactive: false,
        forceRefresh: true,
        measurementTrigger: 'submit_guard',
      });
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
    submitButton.textContent = submitInProgress
      ? `${t('registration.submitButton')}...`
      : t('registration.submitButton');
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
    if (state) {
      lastHistoryStateAppliedAt = Date.now();
      lastHistoryStateAppliedChave = getActiveChave();
    } else {
      lastHistoryStateAppliedAt = 0;
      lastHistoryStateAppliedChave = '';
    }
    if (state && state.projeto) {
      const committedProject = normalizeKnownProjectValue(state.projeto, defaultProjectValue);
      lastCommittedUserProjectValues = normalizeKnownProjectValues(
        lastCommittedUserProjectValues.length ? lastCommittedUserProjectValues : [committedProject],
        [committedProject]
      );
      lastCommittedProjectValue = committedProject;
      syncProjectMembershipControls({
        projectValues: lastCommittedUserProjectValues,
        mainValue: committedProject,
      });
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

    const recentHistoryState = readRecentHistoryState(normalized, {
      cacheWindowMs: settings.cacheWindowMs,
    });
    if (recentHistoryState) {
      return recentHistoryState;
    }

    const requestToken = ++historyRequestToken;
    const controller = new AbortController();
    historyAbortController = controller;
    if (settings.showLoadingMessage !== false && !settings.suppressMessages) {
      setHistoryMessage(t('history.loadingMessage'), 'info');
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
          setHistoryMessage(t('history.notFoundMessage'));
        } else {
          setHistoryMessage('');
        }
        return payload;
      }

      if (!payload.last_checkin_at && !payload.last_checkout_at) {
        if (!settings.suppressMessages) {
          setHistoryMessage(t('history.noRecordsMessage'));
        } else {
          setHistoryMessage('');
        }
        return payload;
      }

      if (!settings.silentSuccessMessage && !settings.suppressMessages) {
        setHistoryMessage(t('history.updatedMessage'), 'success');
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
        setHistoryMessage(t('history.loadFailed'), 'error');
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
      setSequenceStatus(
        typeof t === 'function'
          ? t('status.updatingActivitiesSequence')
          : 'Atualizando as atividades.....'
      );
      const remoteState = await refreshHistory(normalized, {
        showLoadingMessage: false,
        silentSuccessMessage: true,
        suppressMessages: true,
        rethrowErrors: true,
        cacheWindowMs: lifecycleDataReuseWindowMs,
      });

      setSequenceStatus(
        typeof t === 'function'
          ? t('status.updatingLocationSequence')
          : 'Atualizando a localização.....'
      );
      const locationPayload = await updateLocationForLifecycleSequence({
        triggerSource: settings.triggerSource,
        forceRefresh: settings.forceRefresh,
        suppressNotification: settings.suppressNotification,
        showDetectingState: settings.showDetectingState,
        cacheWindowMs: settings.locationCacheWindowMs ?? lifecycleDataReuseWindowMs,
      });

      if (isAutomaticActivitiesEnabled()) {
        setSequenceStatus(
          typeof t === 'function'
            ? t('status.runningAutomaticActivitySequence')
            : 'Realizando check-in ou check-out, se aplicável.....'
        );
        await runAutomaticActivitiesIfNeeded(locationPayload, {
          suppressStatus: true,
          remoteState,
        });
      }

      restorePersistedUserSettingsForChave(normalized);
      setNotificationMessage('history', '', null);
      setNotificationMessage('location', '', null);
      setStatus(
        typeof t === 'function' ? t('status.applicationUpdated') : 'Aplicação atualizada com sucesso.',
        'success'
      );
      return true;
    } catch (error) {
      if (error && error.isAuthExpired) {
        return false;
      }

      const message = error instanceof Error
        ? (typeof localizeKnownApiMessage === 'function' ? localizeKnownApiMessage(error.message) : error.message)
        : (typeof t === 'function'
            ? t('status.applicationUpdateFailed')
            : 'Não foi possível atualizar a aplicação neste momento.');
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
      const locationPayload = await resolveCurrentLocation({
        interactive: true,
        forceRefresh: true,
        measurementTrigger: 'manual_refresh',
        showDetectingState: true,
        showCompletionStatus: true,
        suppressNotification: false,
      });

      if (locationPayload) {
        await runAutomaticActivitiesIfNeeded(locationPayload);
      }
    });
  }

  function requestLifecycleUpdateFromUi(triggerSource) {
    const nextTriggerSource = typeof triggerSource === 'string' && triggerSource
      ? triggerSource
      : 'visibility';

    if (lifecycleUpdateRequestTimeoutId !== null) {
      window.clearTimeout(lifecycleUpdateRequestTimeoutId);
    }

    lifecycleUpdateRequestTimeoutId = window.setTimeout(() => {
      lifecycleUpdateRequestTimeoutId = null;
      void runLifecycleUpdateSequence({ triggerSource: nextTriggerSource });
    }, 0);
  }

  async function runAutomaticActivitiesEnableSequence() {
    const normalizedChave = sanitizeChave(chaveInput.value);
    if (normalizedChave.length !== 4) {
      setStatus(t('auth.invalidFourCharacterKey'), 'error');
      return;
    }

    if (!isApplicationUnlocked(normalizedChave)) {
      setAuthenticationPrompt();
      return;
    }

    await runWithLockedUserInteraction(async () => {
      try {
        setStatus(t('status.automaticUpdatesRunning'), 'info');

        const locationPayload = await resolveCurrentLocation({
          interactive: true,
          forceRefresh: true,
          measurementTrigger: 'automatic_activities_enable',
          showDetectingState: true,
          showCompletionStatus: false,
          suppressNotification: true,
        });
        const automaticActivityResult = await runAutomaticActivitiesIfNeeded(locationPayload, {
          suppressStatus: true,
        });

        if (automaticActivityResult.performed) {
          setStatus(
            t('status.automaticUpdatesCompletedWithActivity', {
              activity: describeAutomaticActivity(automaticActivityResult.action),
            }),
            'success'
          );
          return;
        }

        setStatus(t('status.automaticUpdatesCompletedWithoutActivity'), 'success');
      } catch (error) {
        if (error && error.isAuthExpired) {
          return;
        }

        const message = error instanceof Error
          ? localizeKnownApiMessage(error.message)
          : t('status.automaticUpdatesFailed');
        setStatus(message, 'error');
      }
    });
  }

  function syncProjectVisibility() {
    const automaticActivitiesEnabled = isAutomaticActivitiesEnabled();
    const manualOverrideActive = isAccuracyTooLowManualFallbackActive();
    const hideProjectField = automaticActivitiesEnabled && !manualOverrideActive;
    const hideLocationField = !shouldAllowManualLocationSelection() || (automaticActivitiesEnabled && !manualOverrideActive);

    projectField.classList.toggle('is-hidden', hideProjectField);
    projectField.setAttribute('aria-hidden', String(hideProjectField));
    if (hideProjectField) {
      closeProjectMembershipPanel();
    }
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
      resetAuthenticationAssistanceAutoOpenState();
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
    resetAuthenticationAssistanceAutoOpenState();
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
    }
  });

  if (settingsButton) {
    settingsButton.addEventListener('click', openSettingsDialog);
  }

  if (settingsDialogBackButton) {
    settingsDialogBackButton.addEventListener('click', closeSettingsDialog);
  }

  if (settingsDialogBackdrop) {
    settingsDialogBackdrop.addEventListener('click', closeSettingsDialog);
  }

  if (settingsResetPasswordButton) {
    settingsResetPasswordButton.addEventListener('click', () => {
      if (!canOpenPasswordChangeFromSettings()) {
        return;
      }

      closeSettingsDialog({ restoreFocus: false });
      openPasswordDialog();
    });
  }

  if (settingsLocationPermissionButton) {
    settingsLocationPermissionButton.addEventListener('click', () => {
      void requestPreciseLocationPermissionFromSettings();
    });
  }

  if (settingsSupportButton) {
    settingsSupportButton.addEventListener('click', openCheckingWebSupport);
  }

  if (settingsAboutButton) {
    settingsAboutButton.addEventListener('click', openCheckingWebManual);
  }

  if (settingsLanguageSelect) {
    settingsLanguageSelect.addEventListener('change', () => {
      applyLanguageSelection(settingsLanguageSelect.value, {
        persist: true,
        reapplyDynamicState: true,
      });
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

  if (projectMembershipButton) {
    projectMembershipButton.addEventListener('click', (event) => {
      event.preventDefault();
      setProjectMembershipPanelOpen(projectMembershipPanel && projectMembershipPanel.hidden);
    });
  }

  if (projectMembershipOptions) {
    projectMembershipOptions.addEventListener('change', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement) || target.name !== 'userProjectMembership') {
        return;
      }

      const selectedProjects = readSelectedProjectMembershipValues();
      if (!selectedProjects.length) {
        target.checked = true;
        setStatus(t('projects.selectAtLeastOne'), 'error');
        syncFormControlStates();
        return;
      }

      void updateCurrentUserProjectSelection();
    });
  }

  if (automaticActivitiesToggle) {
    automaticActivitiesToggle.addEventListener('change', () => {
      persistCurrentUserSettings();
      syncProjectVisibility();
      syncManualLocationControl();
      if (automaticActivitiesToggle.checked) {
        void runAutomaticActivitiesEnableSequence();
        return;
      }

      if (gpsLocationPermissionGranted && isApplicationUnlocked()) {
        void runLifecycleUpdateSequence({
          ignoreCooldown: true,
          triggerSource: 'automatic_activities_disable',
        });
        return;
      }

      setStatus(t('status.automaticActivitiesDisabled'), 'success');
    });
  }

  document.addEventListener('click', (event) => {
    if (!projectField || !projectMembershipPanel || projectMembershipPanel.hidden) {
      return;
    }

    const target = resolveTransportEventTargetElement(event);
    if (target && projectField.contains(target)) {
      return;
    }

    closeProjectMembershipPanel();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeProjectMembershipPanel();
    }
  });

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      if (isSettingsDialogOpen()) {
        void queryLocationPermissionState();
      }
      scheduleViewportLayoutMetricsSync();
      schedulePasswordAutofillSync();
      requestLifecycleUpdateFromUi('visibility');
      if (isTransportScreenOpen()) {
        void loadTransportState();
      }
    }
  });

  window.addEventListener('focus', () => {
    scheduleViewportLayoutMetricsSync();
    schedulePasswordAutofillSync();
    requestLifecycleUpdateFromUi('focus');
    if (isTransportScreenOpen()) {
      void loadTransportState();
    }
  });
  window.addEventListener('pageshow', () => {
    scheduleViewportLayoutMetricsSync();
    schedulePasswordAutofillSync();
    requestLifecycleUpdateFromUi('pageshow');
    if (isTransportScreenOpen()) {
      void loadTransportState();
    }
  });
  window.addEventListener('resize', scheduleViewportLayoutMetricsSync);
  window.addEventListener('orientationchange', () => {
    scheduleViewportLayoutMetricsSync();
    realignViewport();
  });
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', scheduleViewportLayoutMetricsSync);
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

    if (isAutomaticActivitiesEnabled() && !isAccuracyTooLowManualFallbackActive()) {
      setStatus(
        typeof t === 'function'
          ? t('registration.disableAutomaticActivitiesForManualSubmit')
          : 'Desative Atividades Automáticas para registrar manualmente.',
        'error'
      );
      return;
    }

    if (chave.length !== 4) {
      setStatus(t('auth.invalidFourCharacterKey'), 'error');
      chaveInput.focus();
      return;
    }

    if (!isApplicationUnlocked(chave)) {
      setAuthenticationPrompt();
      passwordInput.focus();
      return;
    }

    if (shouldAllowManualLocationSelection() && !manualLocationSelect.value) {
      setStatus(
        typeof t === 'function'
          ? t('registration.selectLocationBeforeSubmit')
          : 'Selecione uma localização antes de registrar.',
        'error'
      );
      manualLocationSelect.focus();
      return;
    }

    setSubmitting(true);
    setStatus('');

    try {
      await ensureLocationReadyForSubmit();
      const submittedLocal = resolveFinalSubmittableLocationValue(resolveSubmittedLocationValue());
      if (!submittedLocal) {
        setStatus(
          typeof t === 'function'
            ? t('registration.selectLocationBeforeSubmit')
            : 'Selecione uma localização antes de registrar.',
          'error'
        );
        if (shouldAllowManualLocationSelection()) {
          manualLocationSelect.focus();
        }
        return;
      }

      const response = await fetch(submitEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chave,
          projeto: resolveCommittedProjectValue(),
          action: selectedAction,
          local: submittedLocal,
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
        selectedAction === 'checkout'
          ? t('status.checkoutCompleted')
          : t('status.checkinCompleted'),
        'success'
      );
    } catch (error) {
      if (error && error.isAuthExpired) {
        return;
      }

      const message = error instanceof Error
        ? localizeKnownApiMessage(error.message)
        : t('status.apiCommunicationFailure');
      setStatus(message, 'error');
    } finally {
      setSubmitting(false);
    }
  });

  if (passwordDialogBackButton) {
    passwordDialogBackButton.addEventListener('click', dismissPasswordDialogManually);
  }

  if (passwordDialogBackdrop) {
    passwordDialogBackdrop.addEventListener('click', dismissPasswordDialogManually);
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
    registrationDialogBackButton.addEventListener('click', dismissRegistrationDialogManually);
  }

  if (registrationDialogBackdrop) {
    registrationDialogBackdrop.addEventListener('click', dismissRegistrationDialogManually);
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
      dismissRegistrationDialogManually();
      return;
    }

    if (event.key === 'Escape' && isSettingsDialogOpen()) {
      closeSettingsDialog();
      return;
    }

    if (event.key === 'Escape' && isPasswordDialogOpen()) {
      dismissPasswordDialogManually();
    }
  });

  syncProjectVisibility();
  scheduleViewportLayoutMetricsSync();
  syncAutomaticActivitiesToggle();
  clearProtectedClientState();
  syncFormControlStates();
  applyLanguageSelection(getActiveCheckLanguageCode(), {
    persist: false,
    reapplyDynamicState: true,
  });
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
