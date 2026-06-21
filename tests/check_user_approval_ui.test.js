// TP6 (plan003) — Check Web approval UI. Mirrors the app: a new user enters "awaiting approval"
// (orange fields + red bar, not authenticated); queue-full shows a red message; approval flips to the
// normal found-user flow; rejection silently returns to the unknown-key state; an unknown key auto-opens
// the registration dialog and the Back control closes it.
//
// Style follows the existing check_*.test.js harnesses: extract the relevant functions from app.js by
// name and run them in a node:vm sandbox with mocked DOM/fetch dependencies.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const checkScript = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/app.js'),
  'utf8'
);

// ── source-extraction utilities (same technique as check_user_location_ui.test.js) ────────────────
function findMatchingDelimiter(sourceText, openIndex, openChar, closeChar) {
  let index = openIndex + 1;
  let depth = 1;
  let quote = null;
  let inLineComment = false;
  let inBlockComment = false;
  let escapeNext = false;

  for (; index < sourceText.length; index += 1) {
    const char = sourceText[index];
    const nextChar = sourceText[index + 1];

    if (inLineComment) {
      if (char === '\n') inLineComment = false;
      continue;
    }
    if (inBlockComment) {
      if (char === '*' && nextChar === '/') {
        inBlockComment = false;
        index += 1;
      }
      continue;
    }
    if (quote) {
      if (escapeNext) {
        escapeNext = false;
        continue;
      }
      if (char === '\\') {
        escapeNext = true;
        continue;
      }
      if (char === quote) quote = null;
      continue;
    }
    if (char === '/' && nextChar === '/') {
      inLineComment = true;
      index += 1;
      continue;
    }
    if (char === '/' && nextChar === '*') {
      inBlockComment = true;
      index += 1;
      continue;
    }
    if (char === '\'' || char === '"' || char === '`') {
      quote = char;
      continue;
    }
    if (char === openChar) {
      depth += 1;
      continue;
    }
    if (char === closeChar) {
      depth -= 1;
      if (depth === 0) return index;
    }
  }
  throw new Error(`Could not find the matching closing delimiter ${closeChar} in app.js`);
}

function findMatchingBrace(sourceText, openBraceIndex) {
  return findMatchingDelimiter(sourceText, openBraceIndex, '{', '}');
}
function findMatchingParenthesis(sourceText, openParenthesisIndex) {
  return findMatchingDelimiter(sourceText, openParenthesisIndex, '(', ')');
}

function extractFunctionSource(sourceText, functionName) {
  const functionToken = `function ${functionName}(`;
  const startIndex = sourceText.indexOf(functionToken);
  assert.notEqual(startIndex, -1, `Expected ${functionName} to be declared in app.js`);

  const openParenthesisIndex = sourceText.indexOf('(', startIndex);
  const closeParenthesisIndex = findMatchingParenthesis(sourceText, openParenthesisIndex);
  const openBraceIndex = sourceText.indexOf('{', closeParenthesisIndex);
  const closeBraceIndex = findMatchingBrace(sourceText, openBraceIndex);
  return sourceText.slice(startIndex, closeBraceIndex + 1);
}

function freshAuthState(overrides = {}) {
  return {
    chave: '',
    found: false,
    hasPassword: false,
    authenticated: false,
    passwordVerified: false,
    pendingApproval: false,
    statusResolved: false,
    statusErrored: false,
    ...overrides,
  };
}

// ── Harness 1: applyAuthenticationStatusPayload (auth/status → awaiting / found / rejection) ───────
function createAuthStatusPayloadHarness() {
  const context = {
    Boolean,
    String,
    __authState: freshAuthState(),
    __calls: {
      setStatus: [],
      setAuthenticationPrompt: [],
      syncAuthenticationAssistanceAutoOpenState: [],
      maybeAutoOpen: 0,
      schedulePendingApprovalPolling: 0,
      clearPendingApprovalPolling: 0,
    },
    chaveInput: { value: '' },
    passwordInput: { value: '' },
    sanitizeChave: (value) => String(value || '').trim().toUpperCase(),
    t: (key) => key,
    clientState: { isPasswordVerificationInputValid: () => false },
    clearProtectedClientState: () => {},
    setAuthenticationPrompt: (message) => {
      context.__calls.setAuthenticationPrompt.push(message);
    },
    setStatus: (message, tone) => {
      context.__calls.setStatus.push({ message, tone });
    },
    syncAuthenticationAssistanceAutoOpenState: (options) => {
      context.__calls.syncAuthenticationAssistanceAutoOpenState.push(options);
    },
    syncFormControlStates: () => {},
    maybeAutoOpenAuthenticationAssistanceDialog: () => {
      context.__calls.maybeAutoOpen += 1;
    },
    schedulePendingApprovalPolling: () => {
      context.__calls.schedulePendingApprovalPolling += 1;
    },
    clearPendingApprovalPolling: () => {
      context.__calls.clearPendingApprovalPolling += 1;
    },
  };

  const moduleSource = [
    'let lastVerifiedPassword = "";',
    'const authState = globalThis.__authState;',
    'const chaveInput = globalThis.__chaveInput;',
    'const passwordInput = globalThis.__passwordInput;',
    extractFunctionSource(checkScript, 'applyAuthenticationStatusPayload'),
    `globalThis.__authStatusPayloadTestExports = {
      apply(payload) { return applyAuthenticationStatusPayload(payload); },
      getSnapshot() {
        return {
          authState: { ...authState },
          calls: {
            setStatus: globalThis.__calls.setStatus.slice(),
            setAuthenticationPrompt: globalThis.__calls.setAuthenticationPrompt.slice(),
            syncAuthenticationAssistanceAutoOpenState:
              globalThis.__calls.syncAuthenticationAssistanceAutoOpenState.slice(),
            maybeAutoOpen: globalThis.__calls.maybeAutoOpen,
            schedulePendingApprovalPolling: globalThis.__calls.schedulePendingApprovalPolling,
            clearPendingApprovalPolling: globalThis.__calls.clearPendingApprovalPolling,
          },
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-auth-status-payload.vm.js' });
  return context.__authStatusPayloadTestExports;
}

// ── Harness 2: syncAuthenticationFieldHighlights (orange auth-field-pending) ───────────────────────
function createFieldHighlightHarness() {
  function makeField() {
    const classes = new Set();
    return {
      classList: {
        toggle(name, force) {
          const shouldAdd = force === undefined ? !classes.has(name) : Boolean(force);
          if (shouldAdd) classes.add(name);
          else classes.delete(name);
        },
        contains(name) {
          return classes.has(name);
        },
      },
    };
  }

  const context = {
    Boolean,
    __authState: freshAuthState(),
    __fields: [makeField(), makeField()],
    __unlocked: false,
    __assistanceActive: false,
    isApplicationUnlocked: () => context.__unlocked,
    isPasswordActionAssistanceModeActive: () => context.__assistanceActive,
  };

  const moduleSource = [
    'const authState = globalThis.__authState;',
    'const highlightedAuthFields = globalThis.__fields;',
    extractFunctionSource(checkScript, 'syncAuthenticationFieldHighlights'),
    `globalThis.__fieldHighlightTestExports = {
      sync() { return syncAuthenticationFieldHighlights(); },
      setPendingApproval(value) { authState.pendingApproval = Boolean(value); },
      setUnlocked(value) { globalThis.__unlocked = Boolean(value); },
      setAssistanceActive(value) { globalThis.__assistanceActive = Boolean(value); },
      getClasses() {
        return globalThis.__fields.map((field) => ({
          pending: field.classList.contains('auth-field-pending'),
          authenticated: field.classList.contains('auth-field-authenticated'),
        }));
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-field-highlight.vm.js' });
  return context.__fieldHighlightTestExports;
}

// ── Harness 3: auto-open state machine (unknown → open; pending → never reopen; Back dismisses) ────
function createAutoOpenHarness() {
  const context = {
    Boolean,
    String,
    __calls: [],
    __authState: freshAuthState(),
    __chaveInput: { value: '' },
    sanitizeChave: (value) => String(value || '').trim().toUpperCase(),
    isRegistrationDialogOpen: () => false,
    isPasswordDialogOpen: () => false,
    isSettingsDialogOpen: () => false,
    isTransportScreenOpen: () => false,
    openRegistrationDialog: () => {
      context.__calls.push('registration');
    },
    openPasswordDialog: () => {
      context.__calls.push('password');
    },
  };

  const moduleSource = [
    'let currentAuthenticationAssistanceStateKey = "";',
    'let lastAutoOpenedAuthenticationAssistanceStateKey = "";',
    'let lastDismissedAuthenticationAssistanceStateKey = "";',
    'const authState = globalThis.__authState;',
    'const chaveInput = globalThis.__chaveInput;',
    extractFunctionSource(checkScript, 'resolveAuthenticationAssistanceStateKey'),
    extractFunctionSource(checkScript, 'resetAuthenticationAssistanceAutoOpenState'),
    extractFunctionSource(checkScript, 'syncAuthenticationAssistanceAutoOpenState'),
    extractFunctionSource(checkScript, 'markCurrentAuthenticationAssistanceDialogAsManuallyDismissed'),
    extractFunctionSource(checkScript, 'maybeAutoOpenAuthenticationAssistanceDialog'),
    `globalThis.__autoOpenTestExports = {
      resolveStateKey(options) { return resolveAuthenticationAssistanceStateKey(options); },
      syncState(options) { return syncAuthenticationAssistanceAutoOpenState(options); },
      maybeAutoOpen() { return maybeAutoOpenAuthenticationAssistanceDialog(); },
      dismissCurrent() { return markCurrentAuthenticationAssistanceDialogAsManuallyDismissed(); },
      reset() {
        resetAuthenticationAssistanceAutoOpenState();
        globalThis.__calls.length = 0; // truncate in place: keep the outer-realm array (deepEqual prototype check)
      },
      getCalls() { return globalThis.__calls.slice(); },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-auto-open.vm.js' });
  return context.__autoOpenTestExports;
}

// ── Harness 4: submitUserSelfRegistration (queue_full / pending register branches) ────────────────
function createRegisterSubmitHarness() {
  const context = {
    Array,
    Boolean,
    Promise,
    Error,
    JSON,
    __selectedProjects: ['P80', 'P83'],
    __fetchPayload: { ok: true, authenticated: true, has_password: true, projects: ['P80'], active_project: 'P80' },
    __authState: freshAuthState({ statusErrored: true }),
    __calls: {
      fetches: [],
      statuses: [],
      schedulePendingApprovalPolling: 0,
      syncAuthenticationFieldHighlights: 0,
      persistPasswordForChave: [],
      writePersistedChave: [],
      closeRegistrationDialog: 0,
      loadAuthenticatedApplication: 0,
      syncAuthenticationAssistanceAutoOpenState: [],
    },
    __createInput: (value = '') => ({ value, focus() {} }),
    t: (key) => key,
    loadProjectCatalog: async () => {},
    readSelectedRegistrationProjectValues: () => context.__selectedProjects.slice(),
    focusRegistrationProjectOptions: () => {},
    sanitizeChave: (value) => String(value || '').trim().toUpperCase(),
    clientState: {
      isPasswordLengthValid(password) {
        const raw = String(password ?? '');
        return raw.length >= 3 && raw.length <= 10 && raw.trim().length > 0;
      },
    },
    setStatus: (message, tone) => {
      context.__calls.statuses.push({ message, tone });
    },
    createRequestError: () => new Error('request failed'),
    fetch: async (url, options) => {
      context.__calls.fetches.push({ url, body: JSON.parse(options.body) });
      return { ok: true, json: async () => context.__fetchPayload };
    },
    normalizeKnownProjectValues: (values, fallback) => {
      const raw = Array.isArray(values) ? values : [values];
      const normalized = Array.from(new Set(raw.map((value) => String(value || '')).filter(Boolean)));
      return normalized.length ? normalized : (Array.isArray(fallback) ? Array.from(fallback) : []);
    },
    normalizeKnownProjectValue: (value, fallback) => String(value || fallback || ''),
    resolveProjectCatalogFallbackValues: () => ['P80'],
    syncProjectMembershipControls: () => {},
    persistCurrentUserSettings: () => {},
    writePersistedChave: (chave) => {
      context.__calls.writePersistedChave.push(chave);
    },
    persistPasswordForChave: (chave, password) => {
      context.__calls.persistPasswordForChave.push({ chave, password });
    },
    resetAuthenticationAssistanceAutoOpenState: () => {},
    syncAuthenticationAssistanceAutoOpenState: (options) => {
      context.__calls.syncAuthenticationAssistanceAutoOpenState.push(options);
    },
    syncAuthenticationFieldHighlights: () => {
      context.__calls.syncAuthenticationFieldHighlights += 1;
    },
    schedulePendingApprovalPolling: () => {
      context.__calls.schedulePendingApprovalPolling += 1;
    },
    closeRegistrationDialog: () => {
      context.__calls.closeRegistrationDialog += 1;
    },
    dismissActiveKeyboard: () => {},
    loadAuthenticatedApplication: async () => {
      context.__calls.loadAuthenticatedApplication += 1;
      return true;
    },
    runFirstRegistrationAutomaticActivitySequence: async () => ({ performed: false, requiresManualAction: false }),
    syncFormControlStates: () => {},
  };

  const moduleSource = [
    'let userSelfRegistrationInProgress = false;',
    'let currentUserProjectValues = [];',
    'let lastCommittedProjectValue = "";',
    'let lastCommittedUserProjectValues = [];',
    'let latestHistoryState = null;',
    'let lastVerifiedPassword = "";',
    'let lastObservedPasswordFieldValue = "";',
    'const defaultProjectValue = "P80";',
    'const allowedProjectValues = ["P80", "P83"];',
    'const authUserRegisterEndpoint = "/api/web/auth/register-user";',
    'const authState = globalThis.__authState;',
    'const registrationChaveInput = globalThis.__createInput("WU13");',
    'const registrationNameInput = globalThis.__createInput("Ana Multi Projeto");',
    'const registrationEmailInput = globalThis.__createInput("ana.multi@petrobras.com.br");',
    'const registrationPasswordInput = globalThis.__createInput("cad456");',
    'const registrationConfirmPasswordInput = globalThis.__createInput("cad456");',
    'const chaveInput = globalThis.__createInput("");',
    'const passwordInput = globalThis.__createInput("");',
    extractFunctionSource(checkScript, 'applyCurrentUserProjectMemberships'),
    `async ${extractFunctionSource(checkScript, 'submitUserSelfRegistration')}`,
    `globalThis.__registerSubmitTestExports = {
      async submit() {
        return submitUserSelfRegistration({ preventDefault() {} });
      },
      setFetchPayload(value) { globalThis.__fetchPayload = value; },
      getSnapshot() {
        return {
          authState: { ...authState },
          statuses: globalThis.__calls.statuses.slice(),
          schedulePendingApprovalPolling: globalThis.__calls.schedulePendingApprovalPolling,
          syncAuthenticationFieldHighlights: globalThis.__calls.syncAuthenticationFieldHighlights,
          persistPasswordForChave: globalThis.__calls.persistPasswordForChave.slice(),
          writePersistedChave: globalThis.__calls.writePersistedChave.slice(),
          closeRegistrationDialog: globalThis.__calls.closeRegistrationDialog,
          loadAuthenticatedApplication: globalThis.__calls.loadAuthenticatedApplication,
          syncAuthenticationAssistanceAutoOpenState:
            globalThis.__calls.syncAuthenticationAssistanceAutoOpenState.slice(),
          fetches: globalThis.__calls.fetches.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-register-submit.vm.js' });
  return context.__registerSubmitTestExports;
}

// ── 1 — auth/status pending_approval → orange fields + red awaiting bar, not authenticated ─────────
test('TP6.1 — pending auth/status enters the awaiting state (red bar, polling, not authenticated)', () => {
  const harness = createAuthStatusPayloadHarness();
  harness.apply({ chave: 'NEW1', found: false, has_password: false, authenticated: false, pending_approval: true });
  const { authState, calls } = harness.getSnapshot();

  assert.equal(authState.pendingApproval, true);
  assert.equal(authState.found, false);
  assert.equal(authState.authenticated, false);
  // red bar with the awaiting message + error tone.
  assert.deepEqual(calls.setStatus, [{ message: 'auth.awaitingApproval', tone: 'error' }]);
  // server-derived polling started; the auto-open state carries pendingApproval so the form does NOT reopen.
  assert.equal(calls.schedulePendingApprovalPolling, 1);
  assert.equal(calls.clearPendingApprovalPolling, 0);
  assert.equal(calls.syncAuthenticationAssistanceAutoOpenState.at(-1).pendingApproval, true);
});

test('TP6.1 — awaiting toggles the orange auth-field-pending highlight (not authenticated)', () => {
  const harness = createFieldHighlightHarness();
  harness.setUnlocked(false);
  harness.setAssistanceActive(false);
  harness.setPendingApproval(true);
  harness.sync();
  for (const field of harness.getClasses()) {
    assert.equal(field.pending, true, 'pending users get the orange highlight');
    assert.equal(field.authenticated, false);
  }

  // Clearing pending (and not in assistance mode) removes the orange highlight.
  harness.setPendingApproval(false);
  harness.sync();
  for (const field of harness.getClasses()) {
    assert.equal(field.pending, false);
  }
});

// ── 2 — register-user → queue_full → red registrationQueueFull, not authenticated ─────────────────
test('TP6.2 — register-user queue_full shows the red queue-full message, no authentication', async () => {
  const harness = createRegisterSubmitHarness();
  harness.setFetchPayload({ ok: true, status: 'queue_full', queue_full: true, authenticated: false });
  await harness.submit();
  const snap = harness.getSnapshot();

  // submitUserSelfRegistration emits a "submitting" status first; the final status is the red queue-full bar.
  assert.deepEqual(snap.statuses.at(-1), { message: 'auth.registrationQueueFull', tone: 'error' });
  assert.equal(snap.authState.authenticated, false);
  assert.equal(snap.authState.pendingApproval, false);
  assert.equal(snap.loadAuthenticatedApplication, 0, 'must NOT load the authenticated app');
  assert.equal(snap.closeRegistrationDialog, 1);
});

test('TP6.2b — register-user pending enters awaiting (red bar, password kept, polling, not authenticated)', async () => {
  const harness = createRegisterSubmitHarness();
  harness.setFetchPayload({ ok: true, status: 'pending', pending_approval: true, authenticated: false });
  await harness.submit();
  const snap = harness.getSnapshot();

  assert.deepEqual(snap.statuses.at(-1), { message: 'auth.awaitingApproval', tone: 'error' });
  assert.equal(snap.authState.pendingApproval, true);
  assert.equal(snap.authState.authenticated, false);
  assert.equal(snap.schedulePendingApprovalPolling, 1);
  assert.equal(snap.persistPasswordForChave.length, 1, 'password kept locally for the post-approval auto-login');
  assert.equal(snap.loadAuthenticatedApplication, 0);
});

// ── 3 — approval: next auth/status found=true → leaves awaiting, normal found-user flow ────────────
test('TP6.3 — approval (found=true, not pending) clears awaiting and stops polling', () => {
  const harness = createAuthStatusPayloadHarness();
  // first pending…
  harness.apply({ chave: 'NEW1', found: false, has_password: false, authenticated: false, pending_approval: true });
  // …then approval flips found=true.
  harness.apply({ chave: 'NEW1', found: true, has_password: true, authenticated: false, pending_approval: false });
  const { authState, calls } = harness.getSnapshot();

  assert.equal(authState.found, true);
  assert.equal(authState.pendingApproval, false);
  assert.equal(calls.clearPendingApprovalPolling, 1, 'polling stops once approved');
  // no second awaiting message — the only setStatus was the first pending one.
  assert.deepEqual(calls.setStatus, [{ message: 'auth.awaitingApproval', tone: 'error' }]);
});

// ── 4 — rejection: found=false && !pending → unknown-key state, no message ────────────────────────
test('TP6.4 — rejection (found=false, not pending) is silent and stops polling', () => {
  const harness = createAuthStatusPayloadHarness();
  harness.apply({ chave: 'NEW1', found: false, has_password: false, authenticated: false, pending_approval: true });
  // poll then sees the pending row gone (rejected): found=false, pending_approval=false, empty message.
  harness.apply({ chave: 'NEW1', found: false, has_password: false, authenticated: false, pending_approval: false, message: '' });
  const { authState, calls } = harness.getSnapshot();

  assert.equal(authState.pendingApproval, false);
  assert.equal(authState.found, false);
  assert.equal(calls.clearPendingApprovalPolling, 1);
  // decision 4 — silent: no NEW status message on rejection (only the first pending one exists).
  assert.deepEqual(calls.setStatus, [{ message: 'auth.awaitingApproval', tone: 'error' }]);
  // the unknown-key auto-open state is reasserted with pendingApproval=false.
  assert.equal(calls.syncAuthenticationAssistanceAutoOpenState.at(-1).pendingApproval, false);
});

test('TP6.4 — rejection returns to the unknown-key state that auto-opens the registration form', () => {
  const harness = createAutoOpenHarness();
  // unknown key (post-rejection): found=false, not pending → :missing-user.
  assert.equal(
    harness.resolveStateKey({ chave: 'NEW1', found: false, hasPassword: false, statusResolved: true, statusErrored: false, pendingApproval: false }),
    'NEW1:missing-user'
  );
});

// ── 5 — unknown key → registrationDialog auto-opens once; the Back control closes it ───────────────
test('TP6.5 — unknown key auto-opens the registration dialog exactly once; Back dismisses it', () => {
  const harness = createAutoOpenHarness();
  harness.reset();
  harness.syncState({ chave: 'NEW1', found: false, hasPassword: false, statusResolved: true, statusErrored: false, pendingApproval: false });
  harness.maybeAutoOpen();
  assert.deepEqual(harness.getCalls(), ['registration'], 'auto-opens the registration dialog');

  // re-evaluating the same resolved state does not reopen it.
  harness.maybeAutoOpen();
  assert.deepEqual(harness.getCalls(), ['registration'], 'does not reopen on a stable state');

  // Back (manual dismissal) marks the state dismissed → no reopen afterwards.
  harness.dismissCurrent();
  harness.maybeAutoOpen();
  assert.deepEqual(harness.getCalls(), ['registration'], 'Back keeps it closed');
});

test('TP6.5 — a pending key never reopens the registration form (distinct :pending-approval state)', () => {
  const harness = createAutoOpenHarness();
  harness.reset();
  assert.equal(
    harness.resolveStateKey({ chave: 'NEW1', found: false, hasPassword: false, statusResolved: true, statusErrored: false, pendingApproval: true }),
    'NEW1:pending-approval'
  );
  harness.syncState({ chave: 'NEW1', found: false, hasPassword: false, statusResolved: true, statusErrored: false, pendingApproval: true });
  harness.maybeAutoOpen();
  assert.deepEqual(harness.getCalls(), [], 'pending state must not auto-open the registration form');
});
