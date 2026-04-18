(function () {
  const form = document.getElementById('checkForm');
  const authStatusEndpoint = form.dataset.authStatusEndpoint || '/api/web/auth/status';
  const authRegisterEndpoint = form.dataset.authRegisterEndpoint || '/api/web/auth/register-password';
  const authLoginEndpoint = form.dataset.authLoginEndpoint || '/api/web/auth/login';
  const authChangeEndpoint = form.dataset.authChangeEndpoint || '/api/web/auth/change-password';
  const submitEndpoint = form.dataset.submitEndpoint || '/api/web/check';
  const stateEndpoint = form.dataset.stateEndpoint || '/api/web/check/state';
  const locationsEndpoint = form.dataset.locationsEndpoint || '/api/web/check/locations';
  const locationEndpoint = form.dataset.locationEndpoint || '/api/web/check/location';
  const automaticActivities = window.CheckingWebAutomaticActivities;
  const clientState = window.CheckingWebClientState;
  const chaveInput = document.getElementById('chaveInput');
  const passwordInput = document.getElementById('passwordInput');
  const passwordActionButton = document.getElementById('passwordActionButton');
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
  const passwordDialog = document.getElementById('passwordDialog');
  const passwordDialogBackdrop = document.getElementById('passwordDialogBackdrop');
  const passwordChangeForm = document.getElementById('passwordChangeForm');
  const oldPasswordInput = document.getElementById('oldPasswordInput');
  const newPasswordInput = document.getElementById('newPasswordInput');
  const confirmPasswordInput = document.getElementById('confirmPasswordInput');
  const passwordDialogBackButton = document.getElementById('passwordDialogBackButton');
  const passwordDialogSubmitButton = document.getElementById('passwordDialogSubmitButton');

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
  const authControls = [chaveInput, passwordInput, passwordActionButton].filter(Boolean);
  const passwordDialogControls = [
    oldPasswordInput,
    newPasswordInput,
    confirmPasswordInput,
    passwordDialogBackButton,
    passwordDialogSubmitButton,
  ].filter(Boolean);
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
  let submitInProgress = false;
  let userInteractionLockCount = 0;
  const authState = {
    chave: '',
    hasPassword: false,
    authenticated: false,
    statusResolved: false,
    statusLoading: false,
  };
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

  function isPasswordDialogOpen() {
    return Boolean(passwordDialog && !passwordDialog.hidden);
  }

  function isPasswordActionBusy() {
    return authState.statusLoading || passwordRegisterInProgress || passwordLoginInProgress || passwordChangeInProgress;
  }

  function getActiveChave() {
    return sanitizeChave(chaveInput.value);
  }

  function isApplicationUnlocked(chave) {
    const normalizedChave = sanitizeChave(typeof chave === 'string' ? chave : chaveInput.value);
    return normalizedChave.length === 4
      && authState.authenticated
      && authState.chave === normalizedChave;
  }

  function resolvePasswordActionButtonLabel() {
    if (authState.statusLoading) {
      return 'Verificando...';
    }
    if (passwordRegisterInProgress) {
      return 'Registrando...';
    }
    return clientState.resolvePasswordActionLabel(authState.hasPassword);
  }

  function syncFormControlStates() {
    const lockActive = isUserInteractionLocked();
    const authBusy = isPasswordActionBusy();
    const dialogOpen = isPasswordDialogOpen();
    const unlocked = isApplicationUnlocked();

    projectSelect.disabled = dialogOpen || lockActive || submitInProgress || passwordRegisterInProgress || passwordLoginInProgress || passwordChangeInProgress;

    processControls.forEach((control) => {
      if (!control) {
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
        control.disabled = dialogOpen || lockActive || !unlocked || submitInProgress;
        return;
      }

      control.disabled = dialogOpen || lockActive || !unlocked;
    });

    authControls.forEach((control) => {
      if (control === chaveInput) {
        control.disabled = dialogOpen || lockActive || submitInProgress || passwordRegisterInProgress || passwordLoginInProgress || passwordChangeInProgress;
        return;
      }

      if (control === passwordInput) {
        control.disabled = dialogOpen || lockActive || submitInProgress || passwordRegisterInProgress || passwordLoginInProgress || passwordChangeInProgress;
        return;
      }

      if (control === passwordActionButton) {
        const activeChave = getActiveChave();
        const canRegisterPassword = clientState.isPasswordLengthValid(passwordInput.value);
        control.textContent = resolvePasswordActionButtonLabel();
        control.disabled = dialogOpen
          || lockActive
          || submitInProgress
          || authBusy
          || activeChave.length !== 4
          || (!authState.hasPassword && !canRegisterPassword);
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
        control.disabled = passwordChangeInProgress;
        control.textContent = passwordChangeInProgress ? 'Alterando...' : 'Alterar';
        return;
      }

      control.disabled = passwordChangeInProgress;
    });

    const isBusy = lockActive || locationRefreshLoading || submitInProgress || authBusy;
    form.classList.toggle('is-busy', isBusy);
    form.setAttribute('aria-busy', String(isBusy));
    if (passwordDialog) {
      passwordDialog.setAttribute('aria-busy', String(passwordChangeInProgress));
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

  function createRequestError(response, payload) {
    const error = new Error(parseErrorMessage(payload));
    error.status = response.status;
    error.payload = payload;
    return error;
  }

  function clearProtectedClientState() {
    latestHistoryState = null;
    applyHistoryState(null);
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
    authState.chave = normalizedChave;
    authState.hasPassword = Boolean(settings.hasPassword);
    authState.authenticated = false;
    authState.statusResolved = normalizedChave.length === 4;
    clearProtectedClientState();
    syncFormControlStates();
    setAuthenticationPrompt(settings.message);
  }

  function handleExpiredAuthentication(options) {
    const settings = options || {};
    closePasswordDialog();
    applyAuthenticationLockedState({
      chave: settings.chave || chaveInput.value,
      hasPassword: settings.hasPassword !== false,
      message: settings.message || 'Digite sua senha para iniciar.',
    });
  }

  function closePasswordDialog() {
    if (!passwordDialog || !passwordDialogBackdrop) {
      return;
    }

    passwordDialog.hidden = true;
    passwordDialogBackdrop.hidden = true;
    passwordDialog.classList.add('is-hidden');
    passwordDialogBackdrop.classList.add('is-hidden');
    if (passwordChangeForm) {
      passwordChangeForm.reset();
    }
    syncFormControlStates();
  }

  function openPasswordDialog() {
    if (!passwordDialog || !passwordDialogBackdrop || !authState.hasPassword) {
      return;
    }

    passwordDialog.hidden = false;
    passwordDialogBackdrop.hidden = false;
    passwordDialog.classList.remove('is-hidden');
    passwordDialogBackdrop.classList.remove('is-hidden');
    if (passwordChangeForm) {
      passwordChangeForm.reset();
    }
    syncFormControlStates();
    if (oldPasswordInput) {
      oldPasswordInput.focus();
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

  function applyAuthenticationStatusPayload(payload) {
    const normalizedChave = sanitizeChave((payload && payload.chave) || chaveInput.value);
    authState.chave = normalizedChave;
    authState.hasPassword = Boolean(payload && payload.has_password);
    authState.authenticated = Boolean(payload && payload.authenticated);
    authState.statusResolved = normalizedChave.length === 4;
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

  async function loadAuthenticatedApplication(chave, options) {
    const settings = options || {};
    const normalizedChave = sanitizeChave(chave || chaveInput.value);
    if (!isApplicationUnlocked(normalizedChave)) {
      return false;
    }

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
      authState.hasPassword = false;
      authState.authenticated = false;
      authState.statusResolved = false;
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
    authState.authenticated = false;
    syncFormControlStates();

    try {
      const payload = await fetchAuthenticationStatus(normalizedChave, controller.signal);
      if (requestToken !== authStatusRequestToken) {
        return null;
      }

      applyAuthenticationStatusPayload(payload);
      if (!payload.authenticated && payload.has_password && settings.allowInlineLogin !== false && clientState.isPasswordLengthValid(passwordInput.value)) {
        return attemptPasswordLogin({ showReadyMessage: true });
      }

      if (payload.authenticated && settings.startProcesses !== false) {
        await loadAuthenticatedApplication(normalizedChave, { showReadyMessage: false });
      }
      return payload;
    } catch (error) {
      if (controller.signal.aborted) {
        return null;
      }

      applyAuthenticationLockedState({
        chave: normalizedChave,
        hasPassword: false,
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
      authState.hasPassword = true;
      authState.authenticated = true;
      authState.statusResolved = true;
      syncFormControlStates();
      setStatus(payload.message || 'Senha cadastrada com sucesso.', 'success');
      await loadAuthenticatedApplication(normalizedChave, { showReadyMessage: false });
      return true;
    } catch (error) {
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

    if (normalizedChave.length !== 4 || !authState.hasPassword) {
      return false;
    }

    if (isApplicationUnlocked(normalizedChave)) {
      return true;
    }

    if (!clientState.isPasswordLengthValid(password)) {
      if (!settings.silentValidation) {
        setStatus('A senha deve ter entre 3 e 10 caracteres.', 'error');
      }
      return false;
    }

    passwordLoginInProgress = true;
    syncFormControlStates();
    setStatus('Validando senha...', 'info');

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

      authState.chave = normalizedChave;
      authState.hasPassword = true;
      authState.authenticated = true;
      authState.statusResolved = true;
      syncFormControlStates();
      if (settings.showReadyMessage !== false) {
        setStatus(payload.message || 'Autenticação concluída.', 'success');
      }
      await loadAuthenticatedApplication(normalizedChave, { showReadyMessage: false });
      return true;
    } catch (error) {
      applyAuthenticationLockedState({
        chave: normalizedChave,
        hasPassword: true,
        message: error instanceof Error ? error.message : 'Não foi possível validar a senha.',
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
    const oldPassword = oldPasswordInput.value;
    const newPassword = newPasswordInput.value;
    const confirmPassword = confirmPasswordInput.value;

    if (normalizedChave.length !== 4) {
      setStatus('Informe uma chave com 4 caracteres alfanuméricos.', 'error');
      closePasswordDialog();
      return;
    }

    if (!clientState.isPasswordLengthValid(oldPassword)) {
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
    setStatus('Alterando senha...', 'info');

    try {
      const response = await fetch(authChangeEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          chave: normalizedChave,
          senha_antiga: oldPassword,
          nova_senha: newPassword,
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw createRequestError(response, payload);
      }

      authState.chave = normalizedChave;
      authState.hasPassword = true;
      authState.authenticated = true;
      authState.statusResolved = true;
      passwordInput.value = newPassword;
      closePasswordDialog();
      setStatus(payload.message || 'Senha alterada com sucesso.', 'success');
      await loadAuthenticatedApplication(normalizedChave, { showReadyMessage: false });
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Não foi possível alterar a senha.', 'error');
    } finally {
      passwordChangeInProgress = false;
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
    const previousChave = authState.chave;
    const sanitized = sanitizeChave(chaveInput.value);
    if (sanitized !== chaveInput.value) {
      chaveInput.value = sanitized;
    }
    writePersistedChave(sanitized);

    if (sanitized !== previousChave) {
      authState.authenticated = false;
      authState.hasPassword = false;
      authState.statusResolved = false;
      passwordInput.value = '';
      closePasswordDialog();
      clearProtectedClientState();
    }

    if (sanitized.length === 4) {
      restorePersistedUserSettingsForChave(sanitized);
      void refreshAuthenticationStatus(sanitized, {
        startProcesses: true,
        allowInlineLogin: true,
      });
      return;
    }

    if (authStatusAbortController) {
      authStatusAbortController.abort();
      authStatusAbortController = null;
    }

    authState.chave = '';
    authState.hasPassword = false;
    authState.authenticated = false;
    authState.statusResolved = false;
    clearProtectedClientState();
    syncFormControlStates();
    setAuthenticationPrompt();
  });

  passwordInput.addEventListener('input', () => {
    syncFormControlStates();
  });

  passwordInput.addEventListener('change', () => {
    if (authState.hasPassword) {
      void attemptPasswordLogin({ silentValidation: true, showReadyMessage: true });
    }
  });

  passwordInput.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') {
      return;
    }

    event.preventDefault();
    if (authState.hasPassword) {
      void attemptPasswordLogin({ showReadyMessage: true });
      return;
    }

    void registerPasswordForCurrentUser();
  });

  passwordActionButton.addEventListener('click', () => {
    if (authState.hasPassword) {
      openPasswordDialog();
      return;
    }

    void registerPasswordForCurrentUser();
  });

  actionInputs.forEach((input) => {
    input.addEventListener('change', syncProjectVisibility);
  });

  projectSelect.addEventListener('change', () => {
    persistCurrentUserSettings();
    if (isApplicationUnlocked()) {
      setStatus('Atualização do projeto concluída.', 'success');
    }
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

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isPasswordDialogOpen()) {
      closePasswordDialog();
    }
  });

  syncProjectVisibility();
  syncAutomaticActivitiesToggle();
  clearProtectedClientState();
  syncFormControlStates();
  setAuthenticationPrompt();

  const persistedChave = readPersistedChave();
  if (persistedChave) {
    chaveInput.value = persistedChave;
    restorePersistedUserSettingsForChave(persistedChave);
    void refreshAuthenticationStatus(persistedChave, {
      startProcesses: true,
      allowInlineLogin: true,
    });
  }
})();