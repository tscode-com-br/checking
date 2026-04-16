(function () {
  const form = document.getElementById('checkForm');
  const submitEndpoint = form.dataset.submitEndpoint || '/api/web/check';
  const stateEndpoint = form.dataset.stateEndpoint || '/api/web/check/state';
  const locationEndpoint = form.dataset.locationEndpoint || '/api/web/check/location';
  const chaveInput = document.getElementById('chaveInput');
  const projectField = document.getElementById('projectField');
  const projectSelect = document.getElementById('projectSelect');
  const submitButton = document.getElementById('submitButton');
  const refreshLocationButton = document.getElementById('refreshLocationButton');
  const refreshLocationButtonLabel = refreshLocationButton.querySelector('.visually-hidden');
  const formStatus = document.getElementById('formStatus');
  const historyStatus = document.getElementById('historyState');
  const lastCheckinValue = document.getElementById('lastCheckinValue');
  const lastCheckoutValue = document.getElementById('lastCheckoutValue');
  const locationValue = document.getElementById('locationValue');
  const locationState = document.getElementById('locationState');
  const locationAccuracy = document.getElementById('locationAccuracy');

  const actionInputs = Array.from(document.querySelectorAll('input[name="action"]'));
  const storageKey = 'checking.web.user.chave';
  const locationPromptAttemptedKey = 'checking.web.user.location.prompt-attempted';
  const locationPermissionGrantedKey = 'checking.web.user.location.permission-granted';
  const geolocationOptions = {
    enableHighAccuracy: true,
    maximumAge: 0,
    timeout: 20000,
  };
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
  let locationRequestPromise = null;
  let currentLocationMatch = null;

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

  function setLocationRefreshLoading(isLoading) {
    refreshLocationButton.disabled = isLoading;
    refreshLocationButton.classList.toggle('is-loading', isLoading);
    refreshLocationButton.setAttribute('aria-busy', String(isLoading));
    refreshLocationButton.setAttribute('aria-label', isLoading ? 'Atualizando local' : 'Atualizar local');
    refreshLocationButton.setAttribute('title', isLoading ? 'Atualizando local' : 'Atualizar local');
    if (refreshLocationButtonLabel) {
      refreshLocationButtonLabel.textContent = isLoading ? 'Atualizando local' : 'Atualizar local';
    }
  }

  function preventViewportScroll(event) {
    if (!event.cancelable) {
      return;
    }

    event.preventDefault();
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

  function setLocationPresentation(label, message, tone, accuracyText) {
    locationValue.textContent = label || '--';
    locationState.textContent = message || '';
    locationAccuracy.textContent = accuracyText || '--';
    locationValue.classList.remove('is-error', 'is-success', 'is-warning');
    locationState.classList.remove('is-error', 'is-success', 'is-warning');

    if (tone) {
      locationValue.classList.add(`is-${tone}`);
      locationState.classList.add(`is-${tone}`);
    }
  }

  function setResolvedLocation(matchPayload) {
    currentLocationMatch = matchPayload && matchPayload.matched ? matchPayload : null;
  }

  function buildAccuracyText(accuracyMeters, thresholdMeters) {
    if (typeof accuracyMeters !== 'number' || !Number.isFinite(accuracyMeters)) {
      return thresholdMeters ? `Max. ${Math.round(thresholdMeters)} m` : '--';
    }
    if (typeof thresholdMeters !== 'number' || !Number.isFinite(thresholdMeters)) {
      return `Precisao ${formatMeters(accuracyMeters)}`;
    }
    return `Precisao ${formatMeters(accuracyMeters)} / Max. ${Math.round(thresholdMeters)} m`;
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

  function applyLocationMatch(payload) {
    const toneByStatus = {
      matched: 'success',
      accuracy_too_low: 'warning',
      not_in_known_location: 'warning',
      outside_workplace: 'warning',
      no_known_locations: 'error',
    };
    const accuracyText = buildAccuracyText(payload.accuracy_meters, payload.accuracy_threshold_meters);
    const locationMessage = payload.status === 'matched' ? '' : payload.message;
    setResolvedLocation(payload);
    setLocationPresentation(payload.label, locationMessage, toneByStatus[payload.status] || null, accuracyText);
  }

  function applyLocationBrowserError(error) {
    setResolvedLocation(null);

    if (!error || typeof error.code !== 'number') {
      setLocationPresentation(
        'Localizacao indisponivel',
        'Nao foi possivel consultar a localizacao neste momento.',
        'error',
        '--'
      );
      return;
    }

    if (error.code === 1) {
      writeStorageFlag(locationPermissionGrantedKey, false);
      setLocationPresentation(
        'Permissao negada',
        `A localizacao automatica so sera reutilizada se voce liberar novamente a permissao ${getLocationPermissionContainerLabel()}.`,
        'error',
        '--'
      );
      return;
    }

    if (error.code === 2) {
      setLocationPresentation(
        'Localizacao indisponivel',
        'Nao foi possivel obter uma posicao valida do aparelho.',
        'error',
        '--'
      );
      return;
    }

    if (error.code === 3) {
      setLocationPresentation(
        'Tempo esgotado',
        'A busca pela localizacao demorou mais do que o esperado.',
        'warning',
        '--'
      );
      return;
    }

    setLocationPresentation(
      'Localizacao indisponivel',
      'Nao foi possivel consultar a localizacao neste momento.',
      'error',
      '--'
    );
  }

  async function captureAndResolveLocation(options) {
    const settings = options || {};
    if (!window.isSecureContext || !navigator.geolocation) {
      setResolvedLocation(null);
      setLocationPresentation(
        'Indisponivel',
        'A captura de localizacao requer HTTPS e suporte do navegador.',
        'error',
        '--'
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
      setLocationPresentation(
        'Detectando...',
        settings.interactive
          ? `Aguardando a confirmacao da localizacao exata ${getLocationPromptSourceLabel()}.`
          : 'Atualizando a localizacao atual do aparelho.',
        null,
        '--'
      );

      try {
        const position = await requestCurrentPosition();
        writeStorageFlag(locationPermissionGrantedKey, true);
        const matchPayload = await matchCurrentPosition(position);
        applyLocationMatch(matchPayload);
        return matchPayload;
      } catch (error) {
        applyLocationBrowserError(error);
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

  async function initializeLocationCapture() {
    if (!window.isSecureContext || !navigator.geolocation) {
      setLocationPresentation(
        'Indisponivel',
        'A captura de localizacao requer HTTPS e suporte do navegador.',
        'error',
        '--'
      );
      return;
    }

    const permissionState = await queryLocationPermissionState();
    if (permissionState === 'granted') {
      await captureAndResolveLocation({ interactive: false });
      return;
    }

    if (permissionState === 'denied') {
      writeStorageFlag(locationPermissionGrantedKey, false);
      setLocationPresentation(
        'Permissao negada',
        `A localizacao automatica foi bloqueada ${getLocationPermissionContainerLabel()}.`,
        'error',
        '--'
      );
      return;
    }

    if (!readStorageFlag(locationPromptAttemptedKey)) {
      await captureAndResolveLocation({ interactive: true });
      return;
    }

    if (readStorageFlag(locationPermissionGrantedKey)) {
      await captureAndResolveLocation({ interactive: false });
      return;
    }

    setResolvedLocation(null);
    setLocationPresentation(
      'Nao confirmado',
      'O pedido automatico de localizacao acontece somente na primeira abertura deste link.',
      'warning',
      '--'
    );
  }

  async function ensureLocationReadyForSubmit() {
    if (locationRequestPromise) {
      await locationRequestPromise;
      return;
    }

    const permissionState = await queryLocationPermissionState();
    if (permissionState === 'granted' || (permissionState === null && readStorageFlag(locationPermissionGrantedKey))) {
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
    formStatus.textContent = message || '';
    formStatus.classList.remove('is-error', 'is-success');
    if (tone === 'error') {
      formStatus.classList.add('is-error');
    }
    if (tone === 'success') {
      formStatus.classList.add('is-success');
    }
  }

  function setSubmitting(isSubmitting) {
    submitButton.disabled = isSubmitting;
    submitButton.textContent = isSubmitting ? 'Enviando...' : 'Registrar';
  }

  function setHistoryMessage(message, tone) {
    historyStatus.textContent = message || '';
    historyStatus.classList.remove('is-error', 'is-success');
    if (tone === 'error') {
      historyStatus.classList.add('is-error');
    }
    if (tone === 'success') {
      historyStatus.classList.add('is-success');
    }
  }

  function formatHistoryValue(value) {
    if (!value) {
      return '--';
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return '--';
    }

    return `${dateFormatter.format(parsed)}\n${timeFormatter.format(parsed)}`;
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

  function applyHistoryState(state) {
    lastCheckinValue.textContent = formatHistoryValue(state && state.last_checkin_at);
    lastCheckoutValue.textContent = formatHistoryValue(state && state.last_checkout_at);
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
    setHistoryMessage('Consultando histórico...');

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
        setHistoryMessage('Nenhum registro encontrado para esta chave.');
        return;
      }

      if (!payload.last_checkin_at && !payload.last_checkout_at) {
        setHistoryMessage('Nenhum check-in ou check-out registrado para esta chave.');
        return;
      }

      if (!settings.silentSuccessMessage) {
        setHistoryMessage('Histórico atualizado para a chave informada.', 'success');
      } else {
        setHistoryMessage('');
      }
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }

      applyHistoryState(null);
      setHistoryMessage('Não foi possível consultar o histórico desta chave.', 'error');
    } finally {
      if (historyAbortController === controller) {
        historyAbortController = null;
      }
    }
  }

  function syncProjectVisibility() {
    const isCheckIn = getSelectedValue('action') === 'checkin';
    projectField.classList.toggle('is-hidden', !isCheckIn);
    projectField.setAttribute('aria-hidden', String(!isCheckIn));
  }

  chaveInput.addEventListener('input', () => {
    const sanitized = sanitizeChave(chaveInput.value);
    if (sanitized !== chaveInput.value) {
      chaveInput.value = sanitized;
    }
    writePersistedChave(sanitized);

    if (sanitized.length === 4) {
      void refreshHistory(sanitized, { silentSuccessMessage: true });
      return;
    }

    resetHistory('Digite sua chave Petrobras para visualizar seu histórico.');
  });

  actionInputs.forEach((input) => {
    input.addEventListener('change', syncProjectVisibility);
  });

  refreshLocationButton.addEventListener('click', () => {
    void captureAndResolveLocation({ interactive: true, forceRefresh: true });
  });

  document.addEventListener('touchmove', preventViewportScroll, { passive: false });
  document.addEventListener('wheel', preventViewportScroll, { passive: false });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const chave = sanitizeChave(chaveInput.value);
    chaveInput.value = chave;

    if (chave.length !== 4) {
      setStatus('Informe uma chave com 4 caracteres alfanuméricos.', 'error');
      chaveInput.focus();
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
          action: getSelectedValue('action'),
          local: currentLocationMatch ? currentLocationMatch.resolved_local : null,
          informe: getSelectedValue('informe'),
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
        if (payload.state.last_checkin_at || payload.state.last_checkout_at) {
          setHistoryMessage('Histórico atualizado com base no último envio.', 'success');
        }
      }
      setStatus(payload.message || 'Operação registrada com sucesso.', 'success');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Falha de comunicação com a API.';
      setStatus(message, 'error');
    } finally {
      setSubmitting(false);
    }
  });

  syncProjectVisibility();
  void initializeLocationCapture();

  const persistedChave = readPersistedChave();
  if (persistedChave) {
    chaveInput.value = persistedChave;
    void refreshHistory(persistedChave, { silentSuccessMessage: true });
  } else {
    resetHistory('Digite sua chave Petrobras para visualizar seu histórico.');
  }
})();