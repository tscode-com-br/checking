(function () {
  const form = document.getElementById('checkForm');
  const submitEndpoint = form.dataset.submitEndpoint || '/api/web/check';
  const stateEndpoint = form.dataset.stateEndpoint || '/api/web/check/state';
  const chaveInput = document.getElementById('chaveInput');
  const projectField = document.getElementById('projectField');
  const projectSelect = document.getElementById('projectSelect');
  const submitButton = document.getElementById('submitButton');
  const formStatus = document.getElementById('formStatus');
  const historyStatus = document.getElementById('historyState');
  const lastCheckinValue = document.getElementById('lastCheckinValue');
  const lastCheckoutValue = document.getElementById('lastCheckoutValue');

  const actionInputs = Array.from(document.querySelectorAll('input[name="action"]'));
  const storageKey = 'checking.web.user.chave';
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

  function applyHistoryState(state) {
    lastCheckinValue.textContent = formatHistoryValue(state && state.last_checkin_at);
    lastCheckoutValue.textContent = formatHistoryValue(state && state.last_checkout_at);
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
      const response = await fetch(submitEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chave,
          projeto: projectSelect.value,
          action: getSelectedValue('action'),
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

  const persistedChave = readPersistedChave();
  if (persistedChave) {
    chaveInput.value = persistedChave;
    void refreshHistory(persistedChave, { silentSuccessMessage: true });
  } else {
    resetHistory('Digite sua chave Petrobras para visualizar seu histórico.');
  }
})();