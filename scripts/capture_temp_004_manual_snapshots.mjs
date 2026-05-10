#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import fs from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, '..');
const checkStaticRoot = path.join(workspaceRoot, 'sistema', 'app', 'static', 'check');
const checkIndexPath = path.join(checkStaticRoot, 'index.html');
const outputRoot = path.join(checkStaticRoot, 'manual-assets');
const chromePath = findChrome();

const defaultViewport = { width: 1280, height: 720 };

const scenarios = [
  { id: 'auth-shell', outputFile: 'auth-shell.png', viewport: defaultViewport },
  { id: 'user-registration', outputFile: 'user-registration.png', viewport: defaultViewport },
  { id: 'password-registration', outputFile: 'password-registration.png', viewport: defaultViewport },
  { id: 'settings-modal', outputFile: 'settings-modal.png', viewport: defaultViewport },
  { id: 'password-change', outputFile: 'password-change.png', viewport: defaultViewport },
  { id: 'location-denied', outputFile: 'location-denied.png', viewport: defaultViewport },
  { id: 'location-granted', outputFile: 'location-granted.png', viewport: defaultViewport },
  { id: 'project-selection', outputFile: 'project-selection.png', viewport: defaultViewport },
  { id: 'transport-screen', outputFile: 'transport-screen.png', viewport: defaultViewport },
  { id: 'check-success', outputFile: 'check-success.png', viewport: defaultViewport },
];

function findChrome() {
  const configuredPath = process.env.CHECKING_CHROME_PATH;
  const candidates = [
    configuredPath,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  ].filter(Boolean);

  const resolvedPath = candidates.find((candidate) => existsSync(candidate));
  if (!resolvedPath) {
    throw new Error('Chrome or Edge was not found. Set CHECKING_CHROME_PATH to a Chromium executable.');
  }
  return resolvedPath;
}

function contentTypeFor(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  if (extension === '.html') return 'text/html; charset=utf-8';
  if (extension === '.css') return 'text/css; charset=utf-8';
  if (extension === '.js') return 'text/javascript; charset=utf-8';
  if (extension === '.png') return 'image/png';
  if (extension === '.svg') return 'image/svg+xml';
  if (extension === '.webp') return 'image/webp';
  if (extension === '.ico') return 'image/x-icon';
  if (extension === '.json') return 'application/json; charset=utf-8';
  return 'application/octet-stream';
}

async function serveStatic(requestPath, response) {
  const decodedPath = decodeURIComponent(requestPath.split('?')[0]);
  const relativePath = decodedPath.replace(/^\/+/, '');
  const candidatePath = path.normalize(path.join(workspaceRoot, relativePath));
  if (!candidatePath.startsWith(workspaceRoot) || !existsSync(candidatePath)) {
    response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Not found');
    return;
  }

  const data = await fs.readFile(candidatePath);
  response.writeHead(200, {
    'Content-Type': contentTypeFor(candidatePath),
    'Cache-Control': 'no-store',
  });
  response.end(data);
}

async function buildScenarioHtml(scenarioId) {
  const sourceHtml = await fs.readFile(checkIndexPath, 'utf8');
  const htmlWithStaticBase = sourceHtml.replace(
    '<base href="./user/" />',
    '<base href="/sistema/app/static/check/" />',
  );
  const preloadScript = `<script>${buildPreloadScript(scenarioId)}</script>`;
  const scenarioScript = `<script>${buildScenarioScript(scenarioId)}</script>`;

  return htmlWithStaticBase
    .replace(
      '<script src="automatic-activities.js"></script>',
      `${preloadScript}\n    <script src="automatic-activities.js"></script>`,
    )
    .replace('</body>', `    ${scenarioScript}\n  </body>`);
}

function buildPreloadScript(scenarioId) {
  return `
(() => {
  const scenarioId = ${JSON.stringify(scenarioId)};
  const originalFetch = window.fetch.bind(window);
  const fakeProjectRows = [
    {
      id: 101,
      name: 'BRAVO',
      country_code: 'SG',
      country_name: 'Singapore',
      timezone_name: 'Asia/Singapore',
      timezone_label: 'Singapore (Asia/Singapore)',
      address: 'Base Petrobras',
      zip_code: '088445',
    },
    {
      id: 102,
      name: 'ALFA',
      country_code: 'SG',
      country_name: 'Singapore',
      timezone_name: 'Asia/Singapore',
      timezone_label: 'Singapore (Asia/Singapore)',
      address: 'Oficina Central',
      zip_code: '118509',
    },
    {
      id: 103,
      name: 'CHARLIE',
      country_code: 'SG',
      country_name: 'Singapore',
      timezone_name: 'Asia/Singapore',
      timezone_label: 'Singapore (Asia/Singapore)',
      address: 'Zona de CheckOut',
      zip_code: '609607',
    },
  ];
  let fakeUserProjects = {
    projects: ['BRAVO', 'ALFA'],
    active_project: 'BRAVO',
  };
  const fakeLocationOptions = {
    items: ['Base Petrobras', 'Oficina Central', 'Zona de CheckOut'],
    location_accuracy_threshold_meters: 50,
    mixed_zone_interval_minutes: 20,
  };
  const fakeHistoryState = {
    found: true,
    chave: 'HR70',
    projeto: 'BRAVO',
    current_action: 'checkin',
    current_local: 'Base Petrobras',
    has_current_day_checkin: true,
    last_checkin_at: '2026-05-08T08:12:00+08:00',
    last_checkout_at: '2026-05-07T18:02:00+08:00',
  };
  const fakeSubmitState = {
    ...fakeHistoryState,
    current_action: 'checkin',
    current_local: 'Base Petrobras',
    has_current_day_checkin: true,
    last_checkin_at: '2026-05-08T08:12:00+08:00',
    last_checkout_at: '2026-05-07T18:02:00+08:00',
  };
  const fakeTransportState = {
    chave: 'HR70',
    end_rua: 'Blk 10 Tanjong Pagar Road, #05-01',
    zip: '088445',
    status: 'confirmed',
    request_id: 902,
    request_kind: 'regular',
    route_kind: 'work_to_home',
    service_date: '2026-05-08',
    requested_time: '18:00',
    boarding_time: '18:20',
    confirmation_deadline_time: '17:40',
    vehicle_type: 'van',
    vehicle_plate: 'SGX-2048',
    vehicle_color: 'Prata',
    tolerance_minutes: 10,
    awareness_required: false,
    awareness_confirmed: false,
    requests: [
      {
        request_id: 902,
        request_kind: 'regular',
        status: 'confirmed',
        is_active: true,
        service_date: '2026-05-08',
        requested_time: '18:00',
        selected_weekdays: [0, 1, 2, 3, 4],
        route_kind: 'work_to_home',
        boarding_time: '18:20',
        confirmation_deadline_time: '17:40',
        vehicle_type: 'van',
        vehicle_plate: 'SGX-2048',
        vehicle_color: 'Prata',
        tolerance_minutes: 10,
        awareness_required: false,
        awareness_confirmed: false,
        response_message: '',
        created_at: '2026-05-08T07:50:00+08:00',
      },
    ],
  };
  const authStatusByKey = {
    NEW1: {
      chave: 'NEW1',
      found: false,
      has_password: false,
      authenticated: false,
      message: 'Chave não encontrada. Solicite cadastro.',
    },
    PW00: {
      chave: 'PW00',
      found: true,
      has_password: false,
      authenticated: false,
      message: 'Digite sua chave e crie uma senha.',
    },
    HR70: {
      chave: 'HR70',
      found: true,
      has_password: true,
      authenticated: false,
      message: 'Digite sua senha para iniciar.',
    },
  };

  function json(payload, status = 200) {
    return new Response(JSON.stringify(payload), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  async function readRequestBody(request, init) {
    const explicitBody = init && init.body !== undefined ? init.body : (request && request.body ? request.body : undefined);
    if (typeof explicitBody === 'string' && explicitBody) {
      try {
        return JSON.parse(explicitBody);
      } catch {
        return {};
      }
    }
    return {};
  }

  try {
    window.localStorage.clear();
    window.localStorage.setItem('checking.web.language', 'pt');
  } catch (_error) {
    // Ignore browsers with unavailable storage.
  }

  window.__CHECKING_MANUAL_ERROR__ = null;
  window.addEventListener('error', (event) => {
    window.__CHECKING_MANUAL_ERROR__ = String(
      (event && event.error && event.error.stack)
        || (event && event.message)
        || 'Unknown runtime error during manual capture.'
    );
  });
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event && 'reason' in event ? event.reason : null;
    window.__CHECKING_MANUAL_ERROR__ = String(
      (reason && reason.stack)
        || reason
        || 'Unhandled promise rejection during manual capture.'
    );
  });

  window.fetch = async (input, init = undefined) => {
    const request = input instanceof Request ? input : null;
    const requestUrl = new URL(request ? request.url : String(input), window.location.href);
    const method = String((init && init.method) || (request && request.method) || 'GET').toUpperCase();
    const requestBody = await readRequestBody(request, init);

    if (!requestUrl.pathname.startsWith('/api/web/')) {
      return originalFetch(input, init);
    }

    if (requestUrl.pathname === '/api/web/projects') {
      return json(fakeProjectRows);
    }

    if (requestUrl.pathname === '/api/web/user-projects' && method === 'GET') {
      return json(fakeUserProjects);
    }

    if (requestUrl.pathname === '/api/web/user-projects' && method === 'PUT') {
      const nextProjects = Array.isArray(requestBody.projects)
        ? requestBody.projects.map((value) => String(value || '').trim().toUpperCase()).filter(Boolean)
        : fakeUserProjects.projects;
      fakeUserProjects = {
        projects: nextProjects.length ? nextProjects : fakeUserProjects.projects,
        active_project: nextProjects[0] || fakeUserProjects.active_project,
      };
      return json({
        ok: true,
        message: 'Projetos atualizados com sucesso.',
        ...fakeUserProjects,
      });
    }

    if (requestUrl.pathname === '/api/web/check/state') {
      return json(fakeHistoryState);
    }

    if (requestUrl.pathname === '/api/web/check/locations') {
      return json(fakeLocationOptions);
    }

    if (requestUrl.pathname === '/api/web/check/location') {
      if (scenarioId === 'location-denied') {
        return json({
          matched: false,
          resolved_local: null,
          label: 'Permissão de localização ausente',
          status: 'permission_denied',
          message: 'Ative a localização precisa no navegador para usar o GPS.',
          accuracy_meters: null,
          accuracy_threshold_meters: 50,
          minimum_checkout_distance_meters: 500,
          nearest_workplace_distance_meters: null,
        });
      }

      return json({
        matched: true,
        resolved_local: 'Base Petrobras',
        label: 'Base Petrobras',
        status: 'matched',
        message: 'Localização identificada em Base Petrobras.',
        accuracy_meters: 8,
        accuracy_threshold_meters: 50,
        minimum_checkout_distance_meters: 500,
        nearest_workplace_distance_meters: 0,
      });
    }

    if (requestUrl.pathname === '/api/web/check') {
      return json({
        ok: true,
        message: 'Check-In concluído com sucesso.',
        state: fakeSubmitState,
      });
    }

    if (requestUrl.pathname === '/api/web/auth/status') {
      const chave = String(requestUrl.searchParams.get('chave') || '').trim().toUpperCase();
      return json(authStatusByKey[chave] || {
        chave,
        found: true,
        has_password: true,
        authenticated: false,
        message: 'Digite sua senha para iniciar.',
      });
    }

    if (requestUrl.pathname === '/api/web/auth/login') {
      return json({ ok: true, authenticated: true, has_password: true, message: 'Autenticação concluída.' });
    }

    if (requestUrl.pathname === '/api/web/auth/register-password') {
      return json({ ok: true, authenticated: true, has_password: true, message: 'Senha cadastrada com sucesso.' });
    }

    if (requestUrl.pathname === '/api/web/auth/register-user') {
      return json({
        ok: true,
        authenticated: true,
        has_password: true,
        message: 'Cadastro concluído com sucesso.',
        projects: fakeUserProjects.projects,
        active_project: fakeUserProjects.active_project,
      }, 201);
    }

    if (requestUrl.pathname === '/api/web/auth/change-password') {
      return json({ ok: true, authenticated: true, has_password: true, message: 'Senha alterada com sucesso.' });
    }

    if (requestUrl.pathname === '/api/web/auth/logout') {
      return json({ ok: true, authenticated: false, has_password: false, message: 'Sessão encerrada.' });
    }

    if (requestUrl.pathname === '/api/web/transport/state') {
      return json(fakeTransportState);
    }

    if (requestUrl.pathname === '/api/web/transport/address') {
      return json({ ok: true, message: 'Endereço atualizado com sucesso.', state: fakeTransportState });
    }

    if (requestUrl.pathname === '/api/web/transport/vehicle-request' || requestUrl.pathname === '/api/web/transport/request') {
      return json({ ok: true, message: 'Solicitação registrada.', state: fakeTransportState });
    }

    if (requestUrl.pathname === '/api/web/transport/cancel') {
      return json({ ok: true, message: 'Solicitação de transporte cancelada.', state: fakeTransportState });
    }

    if (requestUrl.pathname === '/api/web/transport/acknowledge') {
      return json({ ok: true, message: 'Ciência registrada com sucesso.', state: fakeTransportState });
    }

    return json({});
  };

  window.EventSource = class {
    constructor() {
      this.onmessage = null;
      this.onerror = null;
    }

    close() {}
  };

  const deniedLocation = scenarioId === 'location-denied';
  const permissionsStub = {
    query: async () => ({
      state: deniedLocation ? 'denied' : 'granted',
      onchange: null,
    }),
  };
  const geolocationStub = {
    getCurrentPosition(success, error) {
      window.setTimeout(() => {
        if (deniedLocation) {
          if (typeof error === 'function') {
            error({ code: 1, message: 'User denied geolocation' });
          }
          return;
        }

        success({
          coords: {
            latitude: 1.2762,
            longitude: 103.8501,
            accuracy: 8,
          },
          timestamp: Date.now(),
        });
      }, 20);
    },
    watchPosition(success, error) {
      const watchId = Date.now();
      this.getCurrentPosition(success, error);
      return watchId;
    },
    clearWatch() {},
  };

  Object.defineProperty(navigator, 'permissions', {
    configurable: true,
    value: permissionsStub,
  });

  Object.defineProperty(navigator, 'geolocation', {
    configurable: true,
    value: geolocationStub,
  });

  window.open = () => null;
})();
`;
}

function buildScenarioScript(scenarioId) {
  return `
(() => {
  const scenarioId = ${JSON.stringify(scenarioId)};
  const projectValues = ['BRAVO', 'ALFA', 'CHARLIE'];
  const manualLocations = ['Base Petrobras', 'Oficina Central', 'Zona de CheckOut'];

  function byId(id) {
    return document.getElementById(id);
  }

  function wait(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function show(element) {
    if (!element) {
      return;
    }
    element.hidden = false;
    element.classList.remove('is-hidden');
    element.setAttribute('aria-hidden', 'false');
  }

  function hide(element) {
    if (!element) {
      return;
    }
    element.hidden = true;
    element.classList.add('is-hidden');
    element.setAttribute('aria-hidden', 'true');
  }

  function setInputValue(id, value, dispatchEvents = false) {
    const element = byId(id);
    if (!element) {
      return;
    }
    element.value = value;
    if (!dispatchEvents) {
      return;
    }
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function setButtonState(id, enabled) {
    const element = byId(id);
    if (!element) {
      return;
    }
    element.disabled = !enabled;
    element.setAttribute('aria-disabled', String(!enabled));
  }

  function setNotification(primary, secondary, tone) {
    [
      ['notificationLinePrimary', primary],
      ['notificationLineSecondary', secondary],
    ].forEach(([id, text]) => {
      const line = byId(id);
      if (!line) {
        return;
      }
      line.textContent = text || '';
      line.classList.remove('is-success', 'is-error', 'is-warning', 'is-info', 'is-neutral');
      if (tone) {
        line.classList.add('is-' + tone);
      }
    });
  }

  function setLocation(label, accuracy, tone) {
    const locationValue = byId('locationValue');
    const locationAccuracy = byId('locationAccuracy');
    if (locationValue) {
      locationValue.textContent = label || '--';
      locationValue.classList.remove('is-success', 'is-error', 'is-warning', 'is-info', 'is-muted');
      if (tone) {
        locationValue.classList.add('is-' + tone);
      }
    }
    if (locationAccuracy) {
      locationAccuracy.textContent = accuracy || '--';
    }
  }

  function setHistoryValue(id, parts) {
    const element = byId(id);
    if (!element) {
      return;
    }
    element.replaceChildren();
    if (!Array.isArray(parts) || parts.length !== 3) {
      element.textContent = '--';
      return;
    }

    [
      ['history-weekday', parts[0]],
      ['history-date', parts[1]],
      ['history-time', parts[2]],
    ].forEach(([className, text]) => {
      const span = document.createElement('span');
      span.className = className;
      span.textContent = text;
      element.appendChild(span);
    });
  }

  function setHistory(checkinParts, checkoutParts, latestActivity) {
    setHistoryValue('lastCheckinValue', checkinParts);
    setHistoryValue('lastCheckoutValue', checkoutParts);
    const checkinItem = byId('lastCheckinValue') && byId('lastCheckinValue').closest('.history-item');
    const checkoutItem = byId('lastCheckoutValue') && byId('lastCheckoutValue').closest('.history-item');
    if (checkinItem) {
      checkinItem.classList.toggle('is-latest-activity', latestActivity === 'checkin');
    }
    if (checkoutItem) {
      checkoutItem.classList.toggle('is-latest-activity', latestActivity === 'checkout');
    }
  }

  function fillSelect(id, values, selectedValue, keepDisabled) {
    const element = byId(id);
    if (!element) {
      return;
    }
    element.replaceChildren();
    values.forEach((value) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = value;
      if (value === selectedValue) {
        option.selected = true;
      }
      element.appendChild(option);
    });
    if (selectedValue) {
      element.value = selectedValue;
    }
    if (keepDisabled !== undefined) {
      element.disabled = Boolean(keepDisabled);
    }
  }

  function buildProjectOptions(containerId, inputName, selectedValues) {
    const container = byId(containerId);
    if (!container) {
      return;
    }
    container.replaceChildren();
    container.style.display = 'grid';
    container.style.gap = '10px';
    container.style.maxHeight = 'none';
    container.style.overflow = 'visible';
    projectValues.forEach((projectName) => {
      const optionLabel = document.createElement('label');
      optionLabel.className = 'project-membership-option';
      optionLabel.style.display = 'grid';
      optionLabel.style.gridTemplateColumns = '22px minmax(0, 1fr)';
      optionLabel.style.alignItems = 'center';
      optionLabel.style.columnGap = '12px';
      optionLabel.style.minWidth = '0';
      optionLabel.style.padding = '10px 12px';
      optionLabel.style.border = '1px solid rgba(15, 118, 110, 0.18)';
      optionLabel.style.borderRadius = '12px';
      optionLabel.style.background = '#ffffff';
      const optionInput = document.createElement('input');
      optionInput.type = 'checkbox';
      optionInput.name = inputName;
      optionInput.value = projectName;
      optionInput.checked = selectedValues.includes(projectName);
      optionInput.style.width = '20px';
      optionInput.style.height = '20px';
      optionInput.style.margin = '0';
      optionInput.style.accentColor = '#0f766e';
      const optionText = document.createElement('span');
      optionText.textContent = projectName;
      optionText.style.display = 'block';
      optionText.style.minWidth = '0';
      optionText.style.width = '100%';
      optionText.style.overflow = 'visible';
      optionText.style.textOverflow = 'clip';
      optionText.style.whiteSpace = 'normal';
      optionText.style.color = '#0f172a';
      optionText.style.fontWeight = '700';
      optionText.style.lineHeight = '1.3';
      optionLabel.append(optionInput, optionText);
      container.appendChild(optionLabel);
    });
  }

  function makeProjectMembershipPanelStatic() {
    const field = byId('projectField');
    const panel = byId('projectMembershipPanel');
    if (field) {
      field.style.overflow = 'visible';
    }
    if (!panel) {
      return;
    }
    panel.style.position = 'static';
    panel.style.top = 'auto';
    panel.style.left = 'auto';
    panel.style.width = '100%';
    panel.style.marginTop = '10px';
    panel.style.zIndex = '1';
  }

  function openProjectMembershipPanel() {
    const panel = byId('projectMembershipPanel');
    const button = byId('projectMembershipButton');
    makeProjectMembershipPanelStatic();
    show(panel);
    if (button) {
      button.setAttribute('aria-expanded', 'true');
    }
  }

  function resetProjectMembershipPanel() {
    const panel = byId('projectMembershipPanel');
    const button = byId('projectMembershipButton');
    hide(panel);
    if (button) {
      button.setAttribute('aria-expanded', 'false');
    }
  }

  function setAuthFieldState(mode) {
    document.querySelectorAll('.auth-field').forEach((field) => {
      field.classList.remove('auth-field-authenticated', 'auth-field-pending');
      if (mode === 'authenticated') {
        field.classList.add('auth-field-authenticated');
      }
      if (mode === 'pending') {
        field.classList.add('auth-field-pending');
      }
    });
  }

  function showOverlay(dialogId, backdropId) {
    show(byId(backdropId));
    show(byId(dialogId));
  }

  function closeAllOverlays() {
    [
      ['passwordDialog', 'passwordDialogBackdrop'],
      ['registrationDialog', 'registrationDialogBackdrop'],
      ['settingsDialog', 'settingsDialogBackdrop'],
      ['transportScreen', 'transportScreenBackdrop'],
    ].forEach(([dialogId, backdropId]) => {
      hide(byId(dialogId));
      hide(byId(backdropId));
    });
    resetProjectMembershipPanel();
    const settingsButton = byId('settingsButton');
    if (settingsButton) {
      settingsButton.setAttribute('aria-expanded', 'false');
    }
  }

  function applyLockedShell() {
    setAuthFieldState(null);
    setInputValue('chaveInput', 'HR70');
    setInputValue('passwordInput', '');
    fillSelect('manualLocationSelect', manualLocations, manualLocations[0], true);
    setButtonState('settingsButton', true);
    setButtonState('projectMembershipButton', false);
    const projectMembershipButton = byId('projectMembershipButton');
    if (projectMembershipButton) {
      projectMembershipButton.disabled = true;
      projectMembershipButton.setAttribute('aria-disabled', 'true');
    }
    const transportButton = byId('transportButton');
    if (transportButton) {
      transportButton.disabled = true;
      transportButton.setAttribute('aria-disabled', 'true');
    }
    const submitButton = byId('submitButton');
    if (submitButton) {
      submitButton.disabled = true;
    }
    const manualLocationSelect = byId('manualLocationSelect');
    if (manualLocationSelect) {
      manualLocationSelect.disabled = true;
    }
  }

  function applyUnlockedShell() {
    setAuthFieldState('authenticated');
    setInputValue('chaveInput', 'HR70');
    setInputValue('passwordInput', '1234');
    fillSelect('manualLocationSelect', manualLocations, 'Base Petrobras', false);
    buildProjectOptions('projectMembershipOptions', 'userProjectMembership', ['BRAVO', 'ALFA']);
    buildProjectOptions('registrationProjectOptions', 'registrationProjectMembership', ['BRAVO']);
    const projectMembershipSummary = byId('projectMembershipSummary');
    if (projectMembershipSummary) {
      projectMembershipSummary.textContent = 'BRAVO +1';
    }
    const projectMembershipStatus = byId('projectMembershipStatus');
    if (projectMembershipStatus) {
      projectMembershipStatus.textContent = '2 projetos selecionados.';
    }
    const registrationProjectHint = byId('registrationProjectHint');
    if (registrationProjectHint) {
      registrationProjectHint.textContent = 'Selecione um ou mais projetos.';
    }
    const requestRegistrationButton = byId('requestRegistrationButton');
    if (requestRegistrationButton) {
      hide(requestRegistrationButton);
    }
    [
      'settingsButton',
      'refreshLocationButton',
      'submitButton',
      'projectMembershipButton',
      'transportButton',
      'automaticActivitiesToggle',
    ].forEach((id) => {
      const element = byId(id);
      if (!element) {
        return;
      }
      element.disabled = false;
      element.setAttribute('aria-disabled', 'false');
    });
  }

  function prepareRegistrationDialog() {
    applyLockedShell();
    setAuthFieldState('pending');
    setInputValue('chaveInput', 'NEW1');
    showOverlay('registrationDialog', 'registrationDialogBackdrop');
    buildProjectOptions('registrationProjectOptions', 'registrationProjectMembership', ['BRAVO', 'ALFA']);
    setInputValue('registrationChaveInput', 'NEW1');
    setInputValue('registrationNameInput', 'Usuário Demo');
    setInputValue('registrationEmailInput', 'usuario.demo@example.com');
    setInputValue('registrationPasswordInput', '1234');
    setInputValue('registrationConfirmPasswordInput', '1234');
  }

  function preparePasswordRegistrationDialog() {
    applyLockedShell();
    setAuthFieldState('pending');
    setInputValue('chaveInput', 'PW00');
    showOverlay('passwordDialog', 'passwordDialogBackdrop');
    const title = byId('passwordDialogTitle');
    const field = byId('passwordDialogOldPasswordField');
    const oldPassword = byId('oldPasswordInput');
    const submitButton = byId('passwordDialogSubmitButton');
    if (title) {
      title.textContent = 'Cadastrar Senha';
    }
    if (field) {
      field.classList.add('is-registration-placeholder');
    }
    if (oldPassword) {
      oldPassword.hidden = true;
      oldPassword.disabled = true;
      oldPassword.value = '';
    }
    setInputValue('newPasswordInput', '1234');
    setInputValue('confirmPasswordInput', '1234');
    if (submitButton) {
      submitButton.textContent = 'Salvar';
    }
  }

  function preparePasswordChangeDialog() {
    applyUnlockedShell();
    showOverlay('passwordDialog', 'passwordDialogBackdrop');
    const title = byId('passwordDialogTitle');
    const field = byId('passwordDialogOldPasswordField');
    const oldPassword = byId('oldPasswordInput');
    const submitButton = byId('passwordDialogSubmitButton');
    if (title) {
      title.textContent = 'Alterar Senha';
    }
    if (field) {
      field.classList.remove('is-registration-placeholder');
    }
    if (oldPassword) {
      oldPassword.hidden = false;
      oldPassword.disabled = false;
      oldPassword.value = '1234';
    }
    setInputValue('newPasswordInput', '4321');
    setInputValue('confirmPasswordInput', '4321');
    if (submitButton) {
      submitButton.textContent = 'Alterar';
    }
  }

  function prepareSettingsDialog() {
    applyUnlockedShell();
    showOverlay('settingsDialog', 'settingsDialogBackdrop');
    const settingsButton = byId('settingsButton');
    if (settingsButton) {
      settingsButton.setAttribute('aria-expanded', 'true');
      settingsButton.disabled = false;
    }
    const languageSelect = byId('settingsLanguageSelect');
    if (languageSelect) {
      languageSelect.value = 'pt';
    }
    setButtonState('settingsResetPasswordButton', true);
    setButtonState('settingsLocationPermissionButton', true);
    setButtonState('settingsSupportButton', true);
    setButtonState('settingsAboutButton', true);
  }

  function createTransportRequestCard() {
    const card = document.createElement('div');
    card.className = 'transport-request-card is-confirmed is-selected';
    card.dataset.requestId = '902';

    const header = document.createElement('span');
    header.className = 'transport-request-card-header';

    const title = document.createElement('span');
    title.className = 'transport-request-card-title';
    title.textContent = 'Transporte Rotineiro';

    const status = document.createElement('span');
    status.className = 'transport-request-card-status is-confirmed';
    status.textContent = 'Confirmado';
    header.append(title, status);

    const meta = document.createElement('div');
    meta.className = 'transport-request-card-meta';

    const dateTime = document.createElement('span');
    dateTime.className = 'transport-request-card-date-time';
    dateTime.textContent = '08/05/2026 18:20';
    meta.appendChild(dateTime);

    const actionWrap = document.createElement('div');
    actionWrap.className = 'transport-request-card-actions';
    const acknowledge = document.createElement('button');
    acknowledge.type = 'button';
    acknowledge.className = 'transport-request-card-realized-button';
    acknowledge.textContent = 'Realizado';
    const cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.className = 'transport-request-card-cancel-button';
    cancel.textContent = 'Cancelar';
    actionWrap.append(acknowledge, cancel);
    meta.appendChild(actionWrap);

    card.append(header, meta);
    return card;
  }

  function prepareTransportScreen() {
    applyUnlockedShell();
    showOverlay('transportScreen', 'transportScreenBackdrop');
    const addressSummary = byId('transportAddressSummaryValue');
    if (addressSummary) {
      addressSummary.textContent = 'Blk 10 Tanjong Pagar Road, #05-01\\nZIP 088445';
    }
    hide(byId('transportAddressEditor'));
    show(byId('transportOptionButtons'));
    hide(byId('transportRequestBuilderPanel'));
    show(byId('transportRequestHistorySection'));
    const historyList = byId('transportRequestHistoryList');
    if (historyList) {
      historyList.replaceChildren(createTransportRequestCard());
    }
    const inlineStatus = byId('transportInlineStatus');
    if (inlineStatus) {
      inlineStatus.textContent = 'Solicitação confirmada para partida às 18:20.';
      inlineStatus.className = 'transport-inline-status is-success';
    }
  }

  async function applyScenario() {
    await wait(900);
    closeAllOverlays();
    buildProjectOptions('projectMembershipOptions', 'userProjectMembership', ['BRAVO', 'ALFA']);
    buildProjectOptions('registrationProjectOptions', 'registrationProjectMembership', ['BRAVO']);
    fillSelect('manualLocationSelect', manualLocations, 'Base Petrobras', true);
    setHistory(
      ['sexta-feira', '08/05/2026', '08:12:00'],
      ['quinta-feira', '07/05/2026', '18:02:00'],
      'checkin',
    );

    if (scenarioId === 'auth-shell') {
      applyLockedShell();
      setInputValue('chaveInput', 'HR70');
      setNotification(
        'Digite sua senha para iniciar.',
        'Use Ajustes para idioma, suporte, localização e manual.',
        'info',
      );
      setLocation('Aguardando localização.', '--', 'muted');
    } else if (scenarioId === 'user-registration') {
      prepareRegistrationDialog();
      setNotification(
        'Chave não encontrada.',
        'Preencha o cadastro para liberar o acesso.',
        'warning',
      );
      setLocation('Cadastro em andamento.', '--', 'info');
    } else if (scenarioId === 'password-registration') {
      preparePasswordRegistrationDialog();
      setNotification(
        'Crie sua primeira senha.',
        'Depois disso o app libera o restante do fluxo.',
        'info',
      );
      setLocation('Conta encontrada sem senha.', '--', 'info');
    } else if (scenarioId === 'settings-modal') {
      prepareSettingsDialog();
      setNotification(
        'Aplicação liberada.',
        'Ajustes concentra idioma, senha, localização, suporte e manual.',
        'success',
      );
      setLocation('Base Petrobras', 'Precisão 8 m / Limite 50 m', 'success');
    } else if (scenarioId === 'password-change') {
      preparePasswordChangeDialog();
      setNotification(
        'Aplicação liberada.',
        'A alteração de senha agora começa em Ajustes.',
        'success',
      );
      setLocation('Base Petrobras', 'Precisão 8 m / Limite 50 m', 'success');
    } else if (scenarioId === 'location-denied') {
      applyUnlockedShell();
      const manualLocationSelect = byId('manualLocationSelect');
      if (manualLocationSelect) {
        manualLocationSelect.disabled = false;
      }
      setNotification(
        'Localização não disponível.',
        'Permita o GPS preciso em Ajustes ou use o fallback manual.',
        'warning',
      );
      setLocation('Permissão de localização ausente.', '--', 'error');
      fillSelect('manualLocationSelect', manualLocations, 'Oficina Central', false);
    } else if (scenarioId === 'location-granted') {
      applyUnlockedShell();
      const manualLocationSelect = byId('manualLocationSelect');
      if (manualLocationSelect) {
        manualLocationSelect.disabled = true;
      }
      setNotification(
        'Localização compartilhada com sucesso.',
        'A precisão atual permite validar o contexto automaticamente.',
        'success',
      );
      setLocation('Base Petrobras', 'Precisão 8 m / Limite 50 m', 'success');
    } else if (scenarioId === 'project-selection') {
      applyUnlockedShell();
      openProjectMembershipPanel();
      setNotification(
        'Selecione os projetos ativos.',
        'O painel mostra os escopos vinculados à chave atual.',
        'info',
      );
      setLocation('Base Petrobras', 'Precisão 8 m / Limite 50 m', 'success');
    } else if (scenarioId === 'transport-screen') {
      prepareTransportScreen();
      setNotification(
        'Aplicação liberada.',
        'O módulo de transporte pode ser aberto sem sair do shell principal.',
        'info',
      );
      setLocation('Base Petrobras', 'Precisão 8 m / Limite 50 m', 'success');
    } else if (scenarioId === 'check-success') {
      applyUnlockedShell();
      setNotification(
        'Check-In concluído com sucesso.',
        'Evento registrado em Base Petrobras às 08:12:00.',
        'success',
      );
      setLocation('Base Petrobras', 'Precisão 6 m / Limite 50 m', 'success');
      setHistory(
        ['sexta-feira', '08/05/2026', '08:12:00'],
        ['quinta-feira', '07/05/2026', '18:02:00'],
        'checkin',
      );
    }

    window.scrollTo(0, 0);
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    window.__CHECKING_MANUAL_READY__ = true;
  }

  if (document.readyState === 'complete') {
    void applyScenario();
  } else {
    window.addEventListener('load', () => {
      void applyScenario();
    }, { once: true });
  }
})();
`;
}

async function startServer() {
  const server = http.createServer(async (request, response) => {
    try {
      const requestUrl = new URL(request.url, 'http://127.0.0.1');
      if (requestUrl.pathname.startsWith('/__temp004-manual/')) {
        const scenarioId = requestUrl.pathname.split('/').pop();
        const html = await buildScenarioHtml(scenarioId);
        response.writeHead(200, {
          'Content-Type': 'text/html; charset=utf-8',
          'Cache-Control': 'no-store',
        });
        response.end(html);
        return;
      }

      await serveStatic(requestUrl.pathname, response);
    } catch (error) {
      response.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
      response.end(error instanceof Error ? error.stack : String(error));
    }
  });

  await new Promise((resolve) => {
    server.listen(0, '127.0.0.1', resolve);
  });

  return server;
}

async function captureScenario(server, scenario) {
  const address = server.address();
  const url = `http://127.0.0.1:${address.port}/__temp004-manual/${scenario.id}`;
  const outputPath = path.join(outputRoot, scenario.outputFile);
  await captureWithChromeDevTools({
    url,
    outputPath,
    viewport: scenario.viewport,
  });
  return outputPath;
}

class CdpClient {
  constructor(webSocketUrl) {
    this.webSocket = new WebSocket(webSocketUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.eventWaiters = new Map();
    this.opened = new Promise((resolve, reject) => {
      this.webSocket.addEventListener('open', resolve, { once: true });
      this.webSocket.addEventListener('error', reject, { once: true });
    });

    this.webSocket.addEventListener('message', (event) => {
      const message = JSON.parse(event.data);
      if (message.id && this.pending.has(message.id)) {
        const { resolve, reject } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) {
          reject(new Error(message.error.message || JSON.stringify(message.error)));
        } else {
          resolve(message.result || {});
        }
        return;
      }

      if (message.method && this.eventWaiters.has(message.method)) {
        const waiters = this.eventWaiters.get(message.method);
        this.eventWaiters.delete(message.method);
        waiters.forEach((resolve) => resolve(message.params || {}));
      }
    });
  }

  async send(method, params = {}) {
    await this.opened;
    const id = this.nextId += 1;
    const payload = JSON.stringify({ id, method, params });
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.webSocket.send(payload);
    });
  }

  waitForEvent(method, timeoutMs = 5000) {
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        const waiters = this.eventWaiters.get(method) || [];
        this.eventWaiters.set(method, waiters.filter((waiter) => waiter !== resolve));
        reject(new Error(`Timed out waiting for ${method}`));
      }, timeoutMs);

      const wrappedResolve = (params) => {
        clearTimeout(timeoutId);
        resolve(params);
      };

      const waiters = this.eventWaiters.get(method) || [];
      waiters.push(wrappedResolve);
      this.eventWaiters.set(method, waiters);
    });
  }

  close() {
    this.webSocket.close();
  }
}

async function captureWithChromeDevTools({ url, outputPath, viewport }) {
  const userDataDir = path.join(os.tmpdir(), `checking-temp004-${process.pid}-${Date.now()}`);
  await removeDirectory(userDataDir);
  await fs.mkdir(userDataDir, { recursive: true });

  const chrome = spawn(chromePath, [
    '--headless=new',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-background-networking',
    '--disable-sync',
    '--disable-extensions',
    '--hide-scrollbars',
    '--remote-debugging-port=0',
    `--user-data-dir=${userDataDir}`,
    'about:blank',
  ], {
    stdio: ['ignore', 'ignore', 'pipe'],
    windowsHide: true,
  });

  let pageClient = null;
  try {
    const devToolsUrl = await waitForDevToolsUrl(chrome);
    const remotePort = new URL(devToolsUrl).port;
    const targetResponse = await fetch(
      `http://127.0.0.1:${remotePort}/json/new?${encodeURIComponent('about:blank')}`,
      { method: 'PUT' },
    );
    if (!targetResponse.ok) {
      throw new Error(`Unable to create Chrome target: HTTP ${targetResponse.status}`);
    }

    const target = await targetResponse.json();
    pageClient = new CdpClient(target.webSocketDebuggerUrl);
    await pageClient.send('Page.enable');
    await pageClient.send('Runtime.enable');
    await pageClient.send('Emulation.setDeviceMetricsOverride', {
      width: viewport.width,
      height: viewport.height,
      deviceScaleFactor: 1,
      mobile: false,
      screenWidth: viewport.width,
      screenHeight: viewport.height,
    });

    const loadEvent = pageClient.waitForEvent('Page.loadEventFired', 8000);
    await pageClient.send('Page.navigate', { url });
    await loadEvent;
    const readyResult = await pageClient.send('Runtime.evaluate', {
      awaitPromise: true,
      expression: `
        new Promise((resolve) => {
          const startedAt = Date.now();
          const check = () => {
            if (window.__CHECKING_MANUAL_READY__ === true) {
              resolve(true);
              return;
            }
            if (Date.now() - startedAt > 8000) {
              resolve(false);
              return;
            }
            setTimeout(check, 50);
          };
          check();
        })
      `,
    });
    const scenarioReady = Boolean(
      readyResult
      && readyResult.result
      && readyResult.result.value
    );
    if (!scenarioReady) {
      const scenarioError = await pageClient.send('Runtime.evaluate', {
        expression: 'window.__CHECKING_MANUAL_ERROR__ || "Scenario setup timed out before becoming ready."',
      });
      const errorMessage = scenarioError && scenarioError.result && scenarioError.result.value
        ? scenarioError.result.value
        : 'Scenario setup timed out before becoming ready.';
      throw new Error(errorMessage);
    }
    await pageClient.send('Runtime.evaluate', {
      awaitPromise: true,
      expression: 'new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))',
    });
    const screenshot = await pageClient.send('Page.captureScreenshot', {
      format: 'png',
      fromSurface: true,
      captureBeyondViewport: false,
    });
    await fs.writeFile(outputPath, Buffer.from(screenshot.data, 'base64'));
  } finally {
    if (pageClient) {
      pageClient.close();
    }
    await terminateChrome(chrome);
    await removeDirectory(userDataDir);
  }
}

async function removeDirectory(directoryPath) {
  await fs.rm(directoryPath, {
    recursive: true,
    force: true,
    maxRetries: 8,
    retryDelay: 150,
  });
}

async function terminateChrome(chrome) {
  if (chrome.exitCode !== null || chrome.signalCode !== null) {
    return;
  }

  await new Promise((resolve) => {
    chrome.once('exit', resolve);
    chrome.kill();
    setTimeout(resolve, 2000);
  });
}

function waitForDevToolsUrl(chrome) {
  return new Promise((resolve, reject) => {
    let stderr = '';
    const timeoutId = setTimeout(() => {
      reject(new Error(`Timed out waiting for Chrome DevTools URL. stderr: ${stderr}`));
    }, 10000);

    chrome.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
      const match = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) {
        clearTimeout(timeoutId);
        resolve(match[1]);
      }
    });
    chrome.on('error', (error) => {
      clearTimeout(timeoutId);
      reject(error);
    });
    chrome.on('exit', (code) => {
      if (code !== null && code !== 0) {
        clearTimeout(timeoutId);
        reject(new Error(`Chrome exited before DevTools was available. code=${code} stderr=${stderr}`));
      }
    });
  });
}

async function main() {
  await fs.mkdir(outputRoot, { recursive: true });
  const server = await startServer();

  try {
    for (const scenario of scenarios) {
      const outputPath = await captureScenario(server, scenario);
      console.log(`captured ${path.relative(workspaceRoot, outputPath).replaceAll('\\', '/')}`);
    }
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});