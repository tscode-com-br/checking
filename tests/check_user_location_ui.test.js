const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const checkHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/index.html'),
  'utf8'
);

const checkScript = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/app.js'),
  'utf8'
);

const checkAutomaticActivities = require('../sistema/app/static/check/automatic-activities.js');

function extractObjectFreezeConstant(sourceText, constantName) {
  const pattern = new RegExp(`const ${constantName} = Object\\.freeze\\((\\{[\\s\\S]*?\\})\\);`);
  const match = sourceText.match(pattern);
  assert.ok(match, `Expected ${constantName} to be declared in app.js`);
  return `const ${constantName} = Object.freeze(${match[1]});`;
}

function extractConstSource(sourceText, constantName) {
  const startToken = `const ${constantName} = `;
  const startIndex = sourceText.indexOf(startToken);
  assert.notEqual(startIndex, -1, `Expected ${constantName} to be declared in app.js`);

  let index = startIndex + startToken.length;
  let parenDepth = 0;
  let braceDepth = 0;
  let bracketDepth = 0;
  let quote = null;
  let inLineComment = false;
  let inBlockComment = false;
  let escapeNext = false;

  for (; index < sourceText.length; index += 1) {
    const char = sourceText[index];
    const nextChar = sourceText[index + 1];

    if (inLineComment) {
      if (char === '\n') {
        inLineComment = false;
      }
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
      if (char === quote) {
        quote = null;
      }
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

    if (char === '(') {
      parenDepth += 1;
      continue;
    }
    if (char === ')') {
      parenDepth -= 1;
      continue;
    }
    if (char === '{') {
      braceDepth += 1;
      continue;
    }
    if (char === '}') {
      braceDepth -= 1;
      continue;
    }
    if (char === '[') {
      bracketDepth += 1;
      continue;
    }
    if (char === ']') {
      bracketDepth -= 1;
      continue;
    }

    if (char === ';' && parenDepth === 0 && braceDepth === 0 && bracketDepth === 0) {
      return sourceText.slice(startIndex, index + 1);
    }
  }

  throw new Error(`Could not extract ${constantName} from app.js`);
}

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
      if (char === '\n') {
        inLineComment = false;
      }
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
      if (char === quote) {
        quote = null;
      }
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
      if (depth === 0) {
        return index;
      }
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
  assert.notEqual(openParenthesisIndex, -1, `Expected ${functionName} to declare parameters`);

  const closeParenthesisIndex = findMatchingParenthesis(sourceText, openParenthesisIndex);
  const openBraceIndex = sourceText.indexOf('{', closeParenthesisIndex);
  assert.notEqual(openBraceIndex, -1, `Expected ${functionName} to contain a block body`);

  const closeBraceIndex = findMatchingBrace(sourceText, openBraceIndex);
  return sourceText.slice(startIndex, closeBraceIndex + 1);
}

function createLocationHelperHarness(overrides = {}) {
  const context = {
    Object,
    Math,
    Number,
    Date: overrides.Date || Date,
    Promise,
    Error,
    JSON,
    navigator: overrides.navigator || { geolocation: {} },
    window: overrides.window || {
      setTimeout,
      clearTimeout,
    },
    setLocationPresentation: overrides.setLocationPresentation || (() => {}),
    recordLocationMeasurementEvent: overrides.recordLocationMeasurementEvent || (() => {}),
    recordLocationMeasurementSample: overrides.recordLocationMeasurementSample || (() => {}),
    requestCurrentPosition: overrides.requestCurrentPosition || (() => Promise.resolve(null)),
  };

  const moduleSource = [
    'let locationAccuracyThresholdMeters = null;',
    extractConstSource(checkScript, 'geolocationOptions'),
    extractObjectFreezeConstant(checkScript, 'lifecycleLocationCapturePlan'),
    extractObjectFreezeConstant(checkScript, 'enforcedLocationCapturePlan'),
    extractObjectFreezeConstant(checkScript, 'locationCapturePlansByTrigger'),
    extractFunctionSource(checkScript, 'hasFiniteCoordinate'),
    extractFunctionSource(checkScript, 'readPositionAccuracyMeters'),
    extractFunctionSource(checkScript, 'isLocationSampleBetter'),
    extractFunctionSource(checkScript, 'getLocationMeasurementTrigger'),
    extractFunctionSource(checkScript, 'buildLocationCapturePlan'),
    extractFunctionSource(checkScript, 'shouldStopLocationWatch'),
    extractFunctionSource(checkScript, 'buildWatchGeolocationOptions'),
    extractFunctionSource(checkScript, 'buildLocationWatchTimeoutError'),
    extractFunctionSource(checkScript, 'formatMeters'),
    extractFunctionSource(checkScript, 'buildAccuracyText'),
    extractFunctionSource(checkScript, 'buildLocationCaptureProgressAccuracyText'),
    extractFunctionSource(checkScript, 'updateLocationCaptureProgress'),
    extractFunctionSource(checkScript, 'requestWatchedCurrentPosition'),
    extractFunctionSource(checkScript, 'requestCurrentPositionForPlan'),
    `globalThis.__locationTestExports = {
      geolocationOptions,
      lifecycleLocationCapturePlan,
      enforcedLocationCapturePlan,
      locationCapturePlansByTrigger,
      setLocationAccuracyThresholdMeters(value) {
        locationAccuracyThresholdMeters = value;
      },
      buildLocationCapturePlan,
      shouldStopLocationWatch,
      buildWatchGeolocationOptions,
      buildAccuracyText,
      buildLocationCaptureProgressAccuracyText,
      updateLocationCaptureProgress,
      requestWatchedCurrentPosition,
      requestCurrentPositionForPlan,
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-location-helpers.vm.js' });
  return {
    helpers: context.__locationTestExports,
    context,
  };
}

function createManualLocationFallbackHarness() {
  const context = {
    Boolean,
    syncProjectVisibility: () => {},
  };

  const moduleSource = [
    'let gpsLocationPermissionGranted = false;',
    'let currentLocationMatch = null;',
    'let currentLocationResolutionStatus = null;',
    extractFunctionSource(checkScript, 'resolveMatchedOperationalLocation'),
    extractFunctionSource(checkScript, 'isAccuracyTooLowManualFallbackActive'),
    extractFunctionSource(checkScript, 'shouldAllowManualLocationSelection'),
    extractFunctionSource(checkScript, 'setResolvedLocation'),
    `globalThis.__manualLocationFallbackTestExports = {
      isAccuracyTooLowManualFallbackActive,
      shouldAllowManualLocationSelection,
      setGpsLocationPermissionGranted(value) {
        gpsLocationPermissionGranted = Boolean(value);
      },
      setResolvedLocation,
      getState() {
        return {
          gpsLocationPermissionGranted,
          currentLocationMatch,
          currentLocationResolutionStatus,
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-manual-location-fallback.vm.js' });
  return {
    helpers: context.__manualLocationFallbackTestExports,
    context,
  };
}

function createManualOverrideUiHarness() {
  function createElement() {
    const classes = new Set();
    return {
      disabled: false,
      textContent: '',
      value: '',
      attributes: {},
      classList: {
        toggle(name, force) {
          const shouldAdd = force === undefined ? !classes.has(name) : Boolean(force);
          if (shouldAdd) {
            classes.add(name);
            return;
          }
          classes.delete(name);
        },
        contains(name) {
          return classes.has(name);
        },
      },
      setAttribute(name, value) {
        this.attributes[name] = String(value);
      },
      getAttribute(name) {
        return this.attributes[name];
      },
      querySelectorAll() {
        return [];
      },
      contains() {
        return false;
      },
    };
  }

  const context = {
    Array,
    Boolean,
    Object,
    __createElement: createElement,
    __selectedValues: [],
    isUserInteractionLocked: () => false,
    syncAuthenticationFieldHighlights: () => {},
    isPasswordActionBusy: () => false,
    isAnyDialogOpen: () => false,
    isApplicationUnlocked: () => true,
    isPasswordActionAssistanceModeActive: () => false,
    getActiveChave: () => 'AB12',
    isMissingUserRegistrationState: () => false,
    isMissingPasswordRegistrationState: () => false,
    canSubmitPasswordDialog: () => false,
    isPasswordRegistrationDialogMode: () => false,
    setSelectedValue(name, value) {
      context.__selectedValues.push({ name, value });
    },
  };

  const moduleSource = [
    'let gpsLocationPermissionGranted = false;',
    'let currentLocationResolutionStatus = null;',
    'let transportStateLoading = false;',
    'let transportAddressSaveInProgress = false;',
    'let transportRequestInProgress = false;',
    'let transportCancelInProgress = false;',
    'let submitInProgress = false;',
    'let passwordRegisterInProgress = false;',
    'let passwordChangeInProgress = false;',
    'let userSelfRegistrationInProgress = false;',
    'let projectCatalogLoading = false;',
    'let userProjectsLoading = false;',
    'let projectUpdateInProgress = false;',
    'let locationRefreshLoading = false;',
    'let passwordLoginInProgress = false;',
    'let availableLocations = ["Portaria"];',
    'let allowedProjectValues = ["Projeto A"];',
    'const automaticActivitiesToggle = { checked: false };',
    'const projectMembershipButton = globalThis.__createElement();',
    'const projectMembershipOptions = globalThis.__createElement();',
    'const projectMembershipStatus = globalThis.__createElement();',
    'const registrationProjectOptions = globalThis.__createElement();',
    'const manualLocationSelect = globalThis.__createElement();',
    'const refreshLocationButton = globalThis.__createElement();',
    'const submitButton = globalThis.__createElement();',
    'const projectField = globalThis.__createElement();',
    'const locationSelectField = globalThis.__createElement();',
    'const informeField = globalThis.__createElement();',
    'const form = globalThis.__createElement();',
    'const actionInputs = [globalThis.__createElement(), globalThis.__createElement()];',
    'const processControls = [actionInputs[0], actionInputs[1], manualLocationSelect, refreshLocationButton, submitButton];',
    'const authControls = [];',
    'const passwordDialogControls = [];',
    'const registrationDialogControls = [];',
    'const settingsDialogControls = [];',
    'const transportScreenControls = [];',
    'const transportUiState = {};',
    'const transportButton = null;',
    'const transportScreen = null;',
    'const passwordDialog = null;',
    'const registrationDialog = null;',
    'function closeProjectMembershipPanel() {}',
    'function resolveProjectMembershipStatusText() { return ""; }',
    'function readSelectedProjectMembershipValues() { return ["Projeto A"]; }',
    'function resolveCurrentUserProjectValues() { return ["Projeto A"]; }',
    extractConstSource(checkScript, 'defaultManualLocationLabel'),
    extractConstSource(checkScript, 'accuracyFallbackManualLocationLabel'),
    extractFunctionSource(checkScript, 'isAccuracyTooLowManualFallbackActive'),
    extractFunctionSource(checkScript, 'shouldAllowManualLocationSelection'),
    extractFunctionSource(checkScript, 'resolveManualLocationOptions'),
    extractFunctionSource(checkScript, 'isAutomaticActivitiesEnabled'),
    extractFunctionSource(checkScript, 'syncFormControlStates'),
    extractFunctionSource(checkScript, 'syncProjectVisibility'),
    `globalThis.__manualOverrideUiTestExports = {
      syncFormControlStates,
      syncProjectVisibility,
      setAutomaticActivitiesEnabled(value) {
        automaticActivitiesToggle.checked = Boolean(value);
      },
      setGpsLocationPermissionGranted(value) {
        gpsLocationPermissionGranted = Boolean(value);
      },
      setCurrentLocationResolutionStatus(value) {
        currentLocationResolutionStatus = value;
      },
      setAvailableLocations(values) {
        availableLocations = Array.from(values || []);
      },
      getSnapshot() {
        return {
          projectHidden: projectField.classList.contains('is-hidden'),
          locationHidden: locationSelectField.classList.contains('is-hidden'),
          informeHidden: informeField.classList.contains('is-hidden'),
          projectDisabled: projectMembershipButton.disabled,
          manualLocationDisabled: manualLocationSelect.disabled,
          actionDisabled: actionInputs.map((control) => control.disabled),
          submitDisabled: submitButton.disabled,
          selectedValues: globalThis.__selectedValues.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-manual-override-ui.vm.js' });
  return {
    helpers: context.__manualOverrideUiTestExports,
    context,
  };
}

function createManualLocationSelectHarness() {
  function createSelectElement() {
    return {
      value: '',
      options: [],
      replaceChildren() {
        this.options = [];
      },
      append(option) {
        this.options.push({
          value: option.value,
          textContent: option.textContent,
        });
      },
    };
  }

  const context = {
    Array,
    Boolean,
    Object,
    __createSelectElement: createSelectElement,
    document: {
      createElement() {
        return {
          value: '',
          textContent: '',
        };
      },
    },
    syncFormControlStates: () => {},
  };

  const moduleSource = [
    'let gpsLocationPermissionGranted = false;',
    'let currentLocationResolutionStatus = null;',
    'let availableLocations = [];',
    'const manualLocationSelect = globalThis.__createSelectElement();',
    'const locationValue = { textContent: "" };',
    extractConstSource(checkScript, 'defaultManualLocationLabel'),
    extractConstSource(checkScript, 'accuracyFallbackManualLocationLabel'),
    extractFunctionSource(checkScript, 'isAccuracyTooLowManualFallbackActive'),
    extractFunctionSource(checkScript, 'shouldAllowManualLocationSelection'),
    extractFunctionSource(checkScript, 'resolveManualLocationOptions'),
    extractFunctionSource(checkScript, 'resolveManualLocationDefaultForCurrentProject'),
    extractFunctionSource(checkScript, 'getDefaultManualLocation'),
    extractFunctionSource(checkScript, 'setLocationSelectOptions'),
    extractFunctionSource(checkScript, 'syncManualLocationControl'),
    `globalThis.__manualLocationSelectTestExports = {
      syncManualLocationControl,
      resolveManualLocationOptions,
      resolveManualLocationDefaultForCurrentProject,
      setGpsLocationPermissionGranted(value) {
        gpsLocationPermissionGranted = Boolean(value);
      },
      setCurrentLocationResolutionStatus(value) {
        currentLocationResolutionStatus = value;
      },
      setAvailableLocations(values) {
        availableLocations = Array.from(values || []);
      },
      setDisplayedLocation(value) {
        locationValue.textContent = String(value || '');
      },
      setManualLocationValue(value) {
        manualLocationSelect.value = String(value || '');
      },
      getSnapshot() {
        return {
          options: manualLocationSelect.options.map((option) => option.value),
          selectedValue: manualLocationSelect.value,
          resolvedDefault: resolveManualLocationDefaultForCurrentProject(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-manual-location-select.vm.js' });
  return {
    helpers: context.__manualLocationSelectTestExports,
    context,
  };
}

function createSubmittedLocationHarness() {
  const context = {
    Boolean,
    automaticActivities: {
      AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION: 'Localização não Cadastrada',
    },
    accuracyFallbackManualLocationLabel: 'Precisao Insuficiente',
  };

  const moduleSource = [
    'let gpsLocationPermissionGranted = false;',
    'let currentLocationResolutionStatus = null;',
    'let currentLocationMatch = null;',
    'const manualLocationSelect = { value: "" };',
    extractFunctionSource(checkScript, 'resolveMatchedOperationalLocation'),
    extractFunctionSource(checkScript, 'isAccuracyTooLowManualFallbackActive'),
    extractFunctionSource(checkScript, 'shouldAllowManualLocationSelection'),
    extractFunctionSource(checkScript, 'resolveSubmittedLocationValue'),
    extractFunctionSource(checkScript, 'isSyntheticFailureLocationValue'),
    extractFunctionSource(checkScript, 'resolveFinalSubmittableLocationValue'),
    `globalThis.__submittedLocationTestExports = {
      resolveSubmittedLocationValue,
      resolveFinalSubmittableLocationValue,
      setGpsLocationPermissionGranted(value) {
        gpsLocationPermissionGranted = Boolean(value);
      },
      setCurrentLocationResolutionStatus(value) {
        currentLocationResolutionStatus = value;
      },
      setCurrentLocationMatch(value) {
        currentLocationMatch = value;
      },
      setManualLocationValue(value) {
        manualLocationSelect.value = String(value || '');
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-submitted-location.vm.js' });
  return {
    helpers: context.__submittedLocationTestExports,
    context,
  };
}

function createAutomaticSubmitHarness(overrides = {}) {
  const context = {
    Date,
    Error,
    Promise,
    JSON,
    __calls: {
      fetch: [],
      applyHistoryState: [],
      setStatus: [],
    },
    automaticActivities: {
      AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION: 'Localização não Cadastrada',
    },
    accuracyFallbackManualLocationLabel: 'Precisao Insuficiente',
    chaveInput: { value: overrides.chave || 'A123' },
    submitEndpoint: '/api/web/check',
    latestHistoryState: null,
    sanitizeChave: overrides.sanitizeChave || ((value) => String(value || '').trim().toUpperCase()),
    isApplicationUnlocked: overrides.isApplicationUnlocked || (() => true),
    t: overrides.t || ((key) => key),
    resolveCommittedProjectValue: overrides.resolveCommittedProjectValue || (() => 'P80'),
    getSelectedInformeValue: overrides.getSelectedInformeValue || (() => 'normal'),
    buildClientEventId: overrides.buildClientEventId || (() => 'cid-123'),
    buildProtectedRequestError:
      overrides.buildProtectedRequestError || ((response, payload) => new Error(payload?.message || `HTTP ${response.status || 500}`)),
    fetch: overrides.fetch || (async (url, options) => {
      context.__calls.fetch.push({ url, options });
      const body = JSON.parse(options.body);
      return {
        ok: true,
        json: async () => ({
          state: {
            current_action: body.action,
            current_local: body.local,
          },
        }),
      };
    }),
    applyHistoryState: overrides.applyHistoryState || ((state) => {
      context.__calls.applyHistoryState.push(state);
    }),
    isCheckoutZoneLocationName:
      overrides.isCheckoutZoneLocationName || ((value) => String(value || '').trim() === 'Zona de CheckOut'),
    setStatus: overrides.setStatus || ((message, tone) => {
      context.__calls.setStatus.push({ message, tone });
    }),
  };

  const moduleSource = [
    extractFunctionSource(checkScript, 'isSyntheticFailureLocationValue'),
    extractFunctionSource(checkScript, 'resolveFinalSubmittableLocationValue'),
    `async ${extractFunctionSource(checkScript, 'submitAutomaticActivity')};`,
    `globalThis.__automaticSubmitTestExports = {
      submitAutomaticActivity,
      resolveFinalSubmittableLocationValue,
      getSnapshot() {
        return {
          fetch: globalThis.__calls.fetch.slice(),
          applyHistoryState: globalThis.__calls.applyHistoryState.slice(),
          setStatus: globalThis.__calls.setStatus.slice(),
          latestHistoryState,
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-automatic-submit.vm.js' });
  return {
    helpers: context.__automaticSubmitTestExports,
    context,
  };
}

function createLocationMatchPresentationHarness(overrides = {}) {
  const presentationCalls = [];
  const context = {
    Boolean,
    Number,
    localizeKnownLocationLabel: overrides.localizeKnownLocationLabel || ((label) => `UI:${label}`),
    localizeKnownApiMessage: overrides.localizeKnownApiMessage || ((message) => `MSG:${message}`),
    setLocationAccuracyThresholdMeters: overrides.setLocationAccuracyThresholdMeters || (() => {}),
    buildAccuracyText: overrides.buildAccuracyText || ((accuracy, threshold) => `ACC:${accuracy}/${threshold}`),
    setLocationPresentation: overrides.setLocationPresentation || ((...args) => presentationCalls.push(args)),
    syncProjectVisibility: overrides.syncProjectVisibility || (() => {}),
  };

  const moduleSource = [
    'let currentLocationMatch = null;',
    'let currentLocationResolutionStatus = null;',
    extractFunctionSource(checkScript, 'resolveDisplayedLocationLabel'),
    extractFunctionSource(checkScript, 'resolveMatchedOperationalLocation'),
    extractFunctionSource(checkScript, 'setResolvedLocation'),
    extractFunctionSource(checkScript, 'applyLocationMatch'),
    `globalThis.__locationMatchPresentationTestExports = {
      applyLocationMatch,
      resolveDisplayedLocationLabel,
      resolveMatchedOperationalLocation,
      getSnapshot() {
        return {
          presentationCalls: globalThis.__presentationCalls.slice(),
          currentLocationMatch,
          currentLocationResolutionStatus,
        };
      },
    };`,
  ].join('\n\n');

  context.__presentationCalls = presentationCalls;
  vm.runInNewContext(moduleSource, context, { filename: 'check-location-match-presentation.vm.js' });
  return {
    helpers: context.__locationMatchPresentationTestExports,
    context,
  };
}

function createProjectSelectionHarness() {
  const context = {
    Array,
    Boolean,
    Promise,
    Error,
    JSON,
    __calls: {
      fetches: [],
      loadManualLocations: 0,
      persistCurrentUserSettings: 0,
      syncFormControlStates: 0,
      syncProjectMembershipControls: [],
      statuses: [],
    },
    fetch: async (url, options) => {
      context.__calls.fetches.push({
        url,
        body: JSON.parse(options.body),
      });
      return {
        ok: true,
        json: async () => ({
          projects: JSON.parse(options.body).projects.slice(),
          active_project: JSON.parse(options.body).projects[0],
          message: 'Projetos atualizados com sucesso.',
        }),
      };
    },
    getActiveChave: () => 'AB12',
    normalizeKnownProjectValue: (value, fallback) => String(value || fallback || ''),
    normalizeKnownProjectValues: (values) => Array.from(values || []),
    syncProjectMembershipControls: (settings) => {
      context.__calls.syncProjectMembershipControls.push(settings);
    },
    isApplicationUnlocked: () => true,
    persistCurrentUserSettings: () => {
      context.__calls.persistCurrentUserSettings += 1;
    },
    syncFormControlStates: () => {
      context.__calls.syncFormControlStates += 1;
    },
    buildProtectedRequestError: () => new Error('request failed'),
    loadManualLocations: async () => {
      context.__calls.loadManualLocations += 1;
    },
    setStatus: (message, tone) => {
      context.__calls.statuses.push({ message, tone });
    },
  };

  const moduleSource = [
    'let gpsLocationPermissionGranted = false;',
    'let currentLocationResolutionStatus = null;',
    'let projectUpdateInProgress = false;',
    'let currentUserProjectValues = ["Projeto A"];',
    'let lastCommittedProjectValue = "Projeto A";',
    'let lastCommittedUserProjectValues = ["Projeto A"];',
    'let latestHistoryState = { projeto: "Projeto A" };',
    'const defaultProjectValue = "Projeto A";',
    'const userProjectsEndpoint = "/api/web/user-projects";',
    'const automaticActivitiesToggle = { checked: false };',
    'let selectedProjectValues = ["Projeto B"];',
    'function resolveProjectCatalogFallbackValues() { return ["Projeto A"]; }',
    'function readSelectedProjectMembershipValues() { return selectedProjectValues.slice(); }',
    `function applyCurrentUserProjectMemberships(payload) {
      currentUserProjectValues = payload.projects.slice();
      lastCommittedUserProjectValues = payload.projects.slice();
      lastCommittedProjectValue = payload.active_project;
      if (latestHistoryState) {
        latestHistoryState.projeto = payload.active_project;
      }
      persistCurrentUserSettings();
      syncProjectMembershipControls({ projectValues: payload.projects.slice(), mainValue: payload.active_project });
      return { committedProjects: payload.projects.slice(), committedProject: payload.active_project };
    }`,
    extractFunctionSource(checkScript, 'isAccuracyTooLowManualFallbackActive'),
    extractFunctionSource(checkScript, 'isAutomaticActivitiesEnabled'),
    `async ${extractFunctionSource(checkScript, 'updateCurrentUserProjectSelection')}`,
    `globalThis.__projectSelectionTestExports = {
      async updateCurrentUserProjectSelection() {
        return updateCurrentUserProjectSelection();
      },
      setAutomaticActivitiesEnabled(value) {
        automaticActivitiesToggle.checked = Boolean(value);
      },
      setGpsLocationPermissionGranted(value) {
        gpsLocationPermissionGranted = Boolean(value);
      },
      setCurrentLocationResolutionStatus(value) {
        currentLocationResolutionStatus = value;
      },
      setProjectValue(value) {
        selectedProjectValues = [String(value || '')];
      },
      getSnapshot() {
        return {
          fetches: globalThis.__calls.fetches.slice(),
          loadManualLocations: globalThis.__calls.loadManualLocations,
          persistCurrentUserSettings: globalThis.__calls.persistCurrentUserSettings,
          syncFormControlStates: globalThis.__calls.syncFormControlStates,
          syncProjectMembershipControls: globalThis.__calls.syncProjectMembershipControls.slice(),
          statuses: globalThis.__calls.statuses.slice(),
          lastCommittedProjectValue,
          latestHistoryProject: latestHistoryState ? latestHistoryState.projeto : null,
          projectUpdateInProgress,
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-project-selection.vm.js' });
  return {
    helpers: context.__projectSelectionTestExports,
    context,
  };
}

function createRegistrationSubmissionHarness() {
  const context = {
    Array,
    Boolean,
    Promise,
    Error,
    JSON,
    __selectedProjects: ['P83', 'P80'],
    __calls: {
      preventDefault: 0,
      fetches: [],
      focused: [],
      statuses: [],
      loadProjectCatalog: [],
      syncProjectMembershipControls: [],
      persistCurrentUserSettings: 0,
      writePersistedChave: [],
      persistPasswordForChave: [],
      closeRegistrationDialog: 0,
      dismissActiveKeyboard: 0,
      loadAuthenticatedApplication: [],
      syncFormControlStates: 0,
    },
    __createInput: (name, value = '') => ({
      value,
      focus() {
        context.__calls.focused.push(name);
      },
    }),
    loadProjectCatalog: async (options) => {
      context.__calls.loadProjectCatalog.push(options);
    },
    readSelectedRegistrationProjectValues: () => context.__selectedProjects.slice(),
    focusRegistrationProjectOptions: () => {
      context.__calls.focused.push('registrationProjectOptions');
    },
    sanitizeChave: (value) => String(value || '').trim().toUpperCase(),
    clientState: {
      isPasswordLengthValid(password) {
        const rawPassword = String(password ?? '');
        return rawPassword.length >= 3 && rawPassword.length <= 10 && rawPassword.trim().length > 0;
      },
    },
    setStatus: (message, tone) => {
      context.__calls.statuses.push({ message, tone });
    },
    createRequestError: () => new Error('request failed'),
    fetch: async (url, options) => {
      const body = JSON.parse(options.body);
      context.__calls.fetches.push({ url, body });
      return {
        ok: true,
        json: async () => ({
          ok: true,
          authenticated: true,
          has_password: true,
          message: 'Cadastro concluido com sucesso.',
          projects: ['P80', 'P83'],
          active_project: 'P80',
        }),
      };
    },
    normalizeKnownProjectValues: (values, fallback) => {
      const rawValues = Array.isArray(values) ? values : [values];
      const normalizedValues = Array.from(new Set(rawValues.map((value) => String(value || '')).filter(Boolean)));
      if (normalizedValues.length) {
        return normalizedValues;
      }
      return Array.isArray(fallback) ? Array.from(fallback) : [];
    },
    normalizeKnownProjectValue: (value, fallback) => String(value || fallback || ''),
    resolveProjectCatalogFallbackValues: () => ['P80'],
    syncProjectMembershipControls: (settings) => {
      context.__calls.syncProjectMembershipControls.push(settings);
    },
    persistCurrentUserSettings: () => {
      context.__calls.persistCurrentUserSettings += 1;
    },
    writePersistedChave: (chave) => {
      context.__calls.writePersistedChave.push(chave);
    },
    persistPasswordForChave: (chave, password) => {
      context.__calls.persistPasswordForChave.push({ chave, password });
    },
    resetAuthenticationAssistanceAutoOpenState: () => {},
    closeRegistrationDialog: () => {
      context.__calls.closeRegistrationDialog += 1;
    },
    dismissActiveKeyboard: () => {
      context.__calls.dismissActiveKeyboard += 1;
    },
    loadAuthenticatedApplication: async (chave, options) => {
      context.__calls.loadAuthenticatedApplication.push({ chave, options });
      return true;
    },
    syncFormControlStates: () => {
      context.__calls.syncFormControlStates += 1;
    },
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
    'const registrationChaveInput = globalThis.__createInput("registrationChaveInput", "wu13");',
    'const registrationNameInput = globalThis.__createInput("registrationNameInput", "ana multi projeto");',
    'const registrationEmailInput = globalThis.__createInput("registrationEmailInput", "ana.multi@petrobras.com.br");',
    'const registrationPasswordInput = globalThis.__createInput("registrationPasswordInput", "cad456");',
    'const registrationConfirmPasswordInput = globalThis.__createInput("registrationConfirmPasswordInput", "cad456");',
    'const chaveInput = globalThis.__createInput("chaveInput", "");',
    'const passwordInput = globalThis.__createInput("passwordInput", "");',
    'const authState = { statusErrored: true };',
    extractFunctionSource(checkScript, 'applyCurrentUserProjectMemberships'),
    `async ${extractFunctionSource(checkScript, 'submitUserSelfRegistration')}`,
    `globalThis.__registrationSubmissionTestExports = {
      async submitRegistration() {
        return submitUserSelfRegistration({
          preventDefault() {
            globalThis.__calls.preventDefault += 1;
          },
        });
      },
      setSelectedProjects(values) {
        globalThis.__selectedProjects = Array.from(values || []);
      },
      getSnapshot() {
        return {
          preventDefault: globalThis.__calls.preventDefault,
          fetches: globalThis.__calls.fetches.slice(),
          focused: globalThis.__calls.focused.slice(),
          statuses: globalThis.__calls.statuses.slice(),
          loadProjectCatalog: globalThis.__calls.loadProjectCatalog.slice(),
          syncProjectMembershipControls: globalThis.__calls.syncProjectMembershipControls.slice(),
          persistCurrentUserSettings: globalThis.__calls.persistCurrentUserSettings,
          writePersistedChave: globalThis.__calls.writePersistedChave.slice(),
          persistPasswordForChave: globalThis.__calls.persistPasswordForChave.slice(),
          closeRegistrationDialog: globalThis.__calls.closeRegistrationDialog,
          dismissActiveKeyboard: globalThis.__calls.dismissActiveKeyboard,
          loadAuthenticatedApplication: globalThis.__calls.loadAuthenticatedApplication.slice(),
          syncFormControlStates: globalThis.__calls.syncFormControlStates,
          currentUserProjectValues,
          lastCommittedProjectValue,
          lastCommittedUserProjectValues,
          chaveInputValue: chaveInput.value,
          passwordInputValue: passwordInput.value,
          authState: { ...authState },
          lastVerifiedPassword,
          lastObservedPasswordFieldValue,
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-registration-submission.vm.js' });
  return {
    helpers: context.__registrationSubmissionTestExports,
    context,
  };
}

function createLocationCatalogSettingsHarness() {
  const context = {
    Array,
    Number,
    Math,
    Promise,
    Set,
    JSON,
    __calls: {
      fetch: [],
      syncManualLocationControl: 0,
    },
    __applicationUnlocked: true,
    __payload: {
      items: [],
      location_accuracy_threshold_meters: 30,
      mixed_zone_interval_minutes: 20,
    },
    __fetchFailure: false,
    isApplicationUnlocked: () => context.__applicationUnlocked,
    fetch: async (url, options) => {
      context.__calls.fetch.push({ url, options });
      if (context.__fetchFailure) {
        throw new Error('network failure');
      }
      return {
        ok: true,
        json: async () => context.__payload,
      };
    },
    buildProtectedRequestError: () => new Error('request failed'),
    syncManualLocationControl: () => {
      context.__calls.syncManualLocationControl += 1;
    },
  };

  const moduleSource = [
    'let availableLocations = [];',
    'let locationAccuracyThresholdMeters = null;',
    'let mixedZoneIntervalMinutes = null;',
    'const locationsEndpoint = "/api/web/check/locations";',
    extractConstSource(checkScript, 'DEFAULT_MIXED_ZONE_INTERVAL_MINUTES'),
    extractFunctionSource(checkScript, 'setLocationAccuracyThresholdMeters'),
    extractFunctionSource(checkScript, 'setMixedZoneIntervalMinutes'),
    `async ${extractFunctionSource(checkScript, 'loadManualLocations')}`,
    `globalThis.__locationCatalogSettingsTestExports = {
      async loadManualLocations() {
        return loadManualLocations();
      },
      setApplicationUnlocked(value) {
        globalThis.__applicationUnlocked = Boolean(value);
      },
      setPayload(value) {
        globalThis.__payload = value;
      },
      setFetchFailure(value) {
        globalThis.__fetchFailure = Boolean(value);
      },
      getSnapshot() {
        return {
          availableLocations: availableLocations.slice(),
          locationAccuracyThresholdMeters,
          mixedZoneIntervalMinutes,
          fetchCalls: globalThis.__calls.fetch.slice(),
          syncManualLocationControl: globalThis.__calls.syncManualLocationControl,
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-location-catalog-settings.vm.js' });
  return {
    helpers: context.__locationCatalogSettingsTestExports,
    context,
  };
}

function createAuthenticatedApplicationHarness() {
  const context = {
    Promise,
    Boolean,
    String,
    __calls: [],
    chaveInput: { value: '' },
    sanitizeChave: (value) => String(value || '').trim().toUpperCase(),
    isApplicationUnlocked: () => true,
    loadProjectCatalog: async (options) => {
      context.__calls.push({ step: 'loadProjectCatalog', options });
    },
    restorePersistedUserSettingsForChave: (chave) => {
      context.__calls.push({ step: 'restorePersistedUserSettingsForChave', chave });
    },
    loadCurrentUserProjectMemberships: async (options) => {
      context.__calls.push({ step: 'loadCurrentUserProjectMemberships', options });
    },
    loadManualLocations: async () => {
      context.__calls.push({ step: 'loadManualLocations' });
    },
    setStatus: (message, tone) => {
      context.__calls.push({ step: 'setStatus', message, tone });
    },
    runLifecycleUpdateSequence: async (options) => {
      context.__calls.push({ step: 'runLifecycleUpdateSequence', options });
      return true;
    },
  };

  const moduleSource = [
    'let authenticatedApplicationLoadPromise = null;',
    'let authenticatedApplicationLoadFingerprint = "";',
    'let authenticatedApplicationReadyFingerprint = "";',
    'let lastVerifiedPassword = "persisted-secret";',
    'const passwordInput = { value: "persisted-secret" };',
    extractFunctionSource(checkScript, 'buildPasswordVerificationFingerprint'),
    `async ${extractFunctionSource(checkScript, 'loadAuthenticatedApplication')}`,
    `globalThis.__authenticatedApplicationTestExports = {
      async loadAuthenticatedApplication(chave, options) {
        return loadAuthenticatedApplication(chave, options);
      },
      getSnapshot() {
        return globalThis.__calls.slice();
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-authenticated-application.vm.js' });
  return {
    helpers: context.__authenticatedApplicationTestExports,
    context,
  };
}

function createPasswordInputAuthenticationHarness() {
  const context = {
    Boolean,
    Promise,
    String,
    __calls: {
      applyAuthenticationLockedState: [],
      logoutWebSession: [],
      schedulePasswordVerification: [],
      clearPasswordVerificationTimer: 0,
      setAuthenticationPrompt: [],
    },
    __authState: {
      found: true,
      hasPassword: true,
      authenticated: false,
      passwordVerified: false,
      statusResolved: true,
    },
    __chaveInput: { value: 'AB12' },
    __passwordInput: { value: '' },
    getActiveChave: () => 'AB12',
    isApplicationUnlocked: () => false,
    applyAuthenticationLockedState: (options) => {
      context.__calls.applyAuthenticationLockedState.push(options);
    },
    logoutWebSession: (options) => {
      context.__calls.logoutWebSession.push(options);
      return Promise.resolve();
    },
    schedulePasswordVerification: (options) => {
      context.__calls.schedulePasswordVerification.push(options);
    },
    clearPasswordVerificationTimer: () => {
      context.__calls.clearPasswordVerificationTimer += 1;
    },
    setAuthenticationPrompt: (message) => {
      context.__calls.setAuthenticationPrompt.push(message);
    },
    syncFormControlStates: () => {},
    clientState: {
      isPasswordLengthValid(password) {
        const rawPassword = String(password ?? '');
        return rawPassword.length >= 3 && rawPassword.length <= 10 && rawPassword.trim().length > 0;
      },
    },
  };

  const moduleSource = [
    'const authState = globalThis.__authState;',
    'const chaveInput = globalThis.__chaveInput;',
    'const passwordInput = globalThis.__passwordInput;',
    'let lastObservedPasswordFieldValue = "";',
    'let lastVerifiedPassword = "";',
    extractFunctionSource(checkScript, 'syncPasswordInputState'),
    `globalThis.__passwordInputAuthenticationTestExports = {
      syncPasswordInputState(options) {
        return syncPasswordInputState(options);
      },
      setPasswordValue(value) {
        passwordInput.value = value;
      },
      resetCalls() {
        globalThis.__calls.applyAuthenticationLockedState = [];
        globalThis.__calls.logoutWebSession = [];
        globalThis.__calls.schedulePasswordVerification = [];
        globalThis.__calls.clearPasswordVerificationTimer = 0;
        globalThis.__calls.setAuthenticationPrompt = [];
      },
      getSnapshot() {
        return {
          schedulePasswordVerification: globalThis.__calls.schedulePasswordVerification.slice(),
          clearPasswordVerificationTimer: globalThis.__calls.clearPasswordVerificationTimer,
          setAuthenticationPrompt: globalThis.__calls.setAuthenticationPrompt.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-password-input-authentication.vm.js' });
  return {
    helpers: context.__passwordInputAuthenticationTestExports,
    context,
  };
}

function createAuthenticationStatusHarness() {
  const context = {
    AbortController,
    Promise,
    Boolean,
    String,
    __fetchPayload: { found: true, has_password: true },
    __persistedPasswordMap: {},
    __calls: {
      applyAuthenticationStatusPayload: [],
      schedulePasswordVerification: [],
      schedulePasswordAutofillSync: 0,
      persistPasswordForChave: [],
      clearTypedPasswordAuthentication: 0,
      applyAuthenticationLockedState: [],
    },
    __authState: {
      chave: '',
      found: false,
      hasPassword: false,
      authenticated: false,
      passwordVerified: false,
      statusResolved: false,
      statusLoading: false,
      statusErrored: false,
    },
    __passwordInput: { value: '' },
    sanitizeChave: (value) => String(value || '').trim().toUpperCase(),
    fetchAuthenticationStatus: async () => context.__fetchPayload,
    applyAuthenticationStatusPayload: (payload) => {
      context.__calls.applyAuthenticationStatusPayload.push(payload);
      context.__authState.hasPassword = Boolean(payload && payload.has_password);
    },
    schedulePasswordVerification: (options) => {
      context.__calls.schedulePasswordVerification.push(options);
    },
    schedulePasswordAutofillSync: () => {
      context.__calls.schedulePasswordAutofillSync += 1;
    },
    persistPasswordForChave: (chave, password) => {
      context.__calls.persistPasswordForChave.push({ chave, password });
    },
    clearTypedPasswordAuthentication: () => {
      context.__calls.clearTypedPasswordAuthentication += 1;
      context.__authState.authenticated = false;
      context.__authState.passwordVerified = false;
    },
    syncFormControlStates: () => {},
    clearProtectedClientState: () => {},
    setAuthenticationPrompt: () => {},
    applyAuthenticationLockedState: (options) => {
      context.__calls.applyAuthenticationLockedState.push(options);
    },
    clientState: {
      isPasswordLengthValid(password) {
        const rawPassword = String(password ?? '');
        return rawPassword.length >= 3 && rawPassword.length <= 10 && rawPassword.trim().length > 0;
      },
      resolvePersistedPassword(passwordMap, chave) {
        const normalizedChave = String(chave || '').trim().toUpperCase();
        return passwordMap[normalizedChave] || '';
      },
    },
    readPersistedUserPasswordMap: () => context.__persistedPasswordMap,
  };

  const moduleSource = [
    'let authStatusRequestToken = 0;',
    'let authStatusAbortController = null;',
    'const authState = globalThis.__authState;',
    'const passwordInput = globalThis.__passwordInput;',
    extractFunctionSource(checkScript, 'resolvePersistedPasswordForChave'),
    `async ${extractFunctionSource(checkScript, 'refreshAuthenticationStatus')}`,
    `globalThis.__authenticationStatusTestExports = {
      async refreshAuthenticationStatus(chave, options) {
        return refreshAuthenticationStatus(chave, options);
      },
      setPasswordValue(value) {
        passwordInput.value = value;
      },
      setPersistedPasswordMap(value) {
        globalThis.__persistedPasswordMap = value;
      },
      setFetchPayload(value) {
        globalThis.__fetchPayload = value;
      },
      resetCalls() {
        globalThis.__calls.applyAuthenticationStatusPayload = [];
        globalThis.__calls.schedulePasswordVerification = [];
        globalThis.__calls.schedulePasswordAutofillSync = 0;
        globalThis.__calls.persistPasswordForChave = [];
        globalThis.__calls.clearTypedPasswordAuthentication = 0;
        globalThis.__calls.applyAuthenticationLockedState = [];
      },
      getSnapshot() {
        return {
          schedulePasswordVerification: globalThis.__calls.schedulePasswordVerification.slice(),
          schedulePasswordAutofillSync: globalThis.__calls.schedulePasswordAutofillSync,
          clearTypedPasswordAuthentication: globalThis.__calls.clearTypedPasswordAuthentication,
          applyAuthenticationLockedState: globalThis.__calls.applyAuthenticationLockedState.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-authentication-status.vm.js' });
  return {
    helpers: context.__authenticationStatusTestExports,
    context,
  };
}

function createAuthenticationAssistanceAutoOpenHarness() {
  const context = {
    Boolean,
    String,
    __calls: [],
    __authState: {
      chave: '',
      found: false,
      hasPassword: false,
      statusResolved: false,
      statusErrored: false,
    },
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
    `globalThis.__authenticationAssistanceAutoOpenTestExports = {
      syncState(options) {
        return syncAuthenticationAssistanceAutoOpenState(options);
      },
      maybeAutoOpen() {
        return maybeAutoOpenAuthenticationAssistanceDialog();
      },
      dismissCurrent() {
        markCurrentAuthenticationAssistanceDialogAsManuallyDismissed();
      },
      reset() {
        resetAuthenticationAssistanceAutoOpenState();
        globalThis.__calls = [];
      },
      getSnapshot() {
        return {
          currentStateKey: currentAuthenticationAssistanceStateKey,
          lastAutoOpenedStateKey: lastAutoOpenedAuthenticationAssistanceStateKey,
          lastDismissedStateKey: lastDismissedAuthenticationAssistanceStateKey,
          calls: globalThis.__calls.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-authentication-assistance-auto-open.vm.js' });
  return {
    helpers: context.__authenticationAssistanceAutoOpenTestExports,
    context,
  };
}

function createAutomaticLocationDecisionHarness() {
  const context = {
    __calls: [],
    automaticActivities: {
      shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, settings) {
        context.__calls.push({ locationPayload, remoteState, settings });
        return true;
      },
    },
  };

  const moduleSource = [
    'let mixedZoneIntervalMinutes = 35;',
    extractFunctionSource(checkScript, 'shouldAttemptAutomaticLocationEvent'),
    `globalThis.__automaticLocationDecisionTestExports = {
      shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, options) {
        return shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, options);
      },
      getSnapshot() {
        return globalThis.__calls.slice();
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-automatic-location-decision.vm.js' });
  return {
    helpers: context.__automaticLocationDecisionTestExports,
    context,
  };
}

function createManualRefreshSequenceHarness(overrides = {}) {
  const context = {
    Boolean,
    Promise,
    __calls: {
      runWithLockedUserInteraction: 0,
      resolveCurrentLocation: [],
      runAutomaticActivitiesIfNeeded: [],
    },
    __locationPayload: null,
    isUserInteractionLocked: overrides.isUserInteractionLocked || (() => false),
    isApplicationUnlocked: overrides.isApplicationUnlocked || (() => true),
    runWithLockedUserInteraction: overrides.runWithLockedUserInteraction || (async (callback) => {
      context.__calls.runWithLockedUserInteraction += 1;
      return callback();
    }),
    resolveCurrentLocation: overrides.resolveCurrentLocation || (async (options) => {
      context.__calls.resolveCurrentLocation.push(options);
      return context.__locationPayload;
    }),
    runAutomaticActivitiesIfNeeded: overrides.runAutomaticActivitiesIfNeeded || (async (locationPayload, options) => {
      context.__calls.runAutomaticActivitiesIfNeeded.push({ locationPayload, options });
      return { performed: false, action: null, local: null };
    }),
  };

  const moduleSource = [
    `async ${extractFunctionSource(checkScript, 'runManualLocationRefreshSequence')}`,
    `globalThis.__manualRefreshSequenceTestExports = {
      async runManualLocationRefreshSequence() {
        return runManualLocationRefreshSequence();
      },
      setLocationPayload(value) {
        globalThis.__locationPayload = value;
      },
      getSnapshot() {
        return {
          runWithLockedUserInteraction: globalThis.__calls.runWithLockedUserInteraction,
          resolveCurrentLocation: globalThis.__calls.resolveCurrentLocation.slice(),
          runAutomaticActivitiesIfNeeded: globalThis.__calls.runAutomaticActivitiesIfNeeded.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-manual-refresh-sequence.vm.js' });
  return {
    helpers: context.__manualRefreshSequenceTestExports,
    context,
  };
}

function createManualRefreshAutomaticActivityHarness(overrides = {}) {
  const shouldAttemptAutomaticLocationEventImpl = overrides.shouldAttemptAutomaticLocationEvent
    || ((locationPayload, remoteState, settings) => (
      checkAutomaticActivities.shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, settings)
    ));
  const context = {
    Boolean,
    Promise,
    automaticCheckoutLocation: checkAutomaticActivities.AUTOMATIC_CHECKOUT_LOCATION,
    automaticActivities: checkAutomaticActivities,
    gpsLocationPermissionGranted: overrides.gpsLocationPermissionGranted !== undefined
      ? Boolean(overrides.gpsLocationPermissionGranted)
      : true,
    latestHistoryState: null,
    mixedZoneIntervalMinutes: overrides.mixedZoneIntervalMinutes !== undefined
      ? overrides.mixedZoneIntervalMinutes
      : 35,
    chaveInput: { value: overrides.chave || 'A123' },
    __calls: {
      runWithLockedUserInteraction: 0,
      resolveCurrentLocation: [],
      fetchWebState: [],
      applyHistoryState: [],
      shouldAttemptAutomaticLocationEvent: [],
      submitAutomaticActivity: [],
    },
    __locationPayload: null,
    __remoteState: overrides.remoteState || {
      current_action: 'checkout',
      current_local: 'Zona de CheckOut',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
    isUserInteractionLocked: overrides.isUserInteractionLocked || (() => false),
    isApplicationUnlocked: overrides.isApplicationUnlocked || (() => true),
    isAutomaticActivitiesEnabled: overrides.isAutomaticActivitiesEnabled || (() => true),
    sanitizeChave: overrides.sanitizeChave || ((value) => String(value || '').trim().toUpperCase()),
    runWithLockedUserInteraction: overrides.runWithLockedUserInteraction || (async (callback) => {
      context.__calls.runWithLockedUserInteraction += 1;
      return callback();
    }),
    resolveCurrentLocation: overrides.resolveCurrentLocation || (async (options) => {
      context.__calls.resolveCurrentLocation.push(options);
      return context.__locationPayload;
    }),
    fetchWebState: overrides.fetchWebState || (async (chave) => {
      context.__calls.fetchWebState.push(chave);
      return context.__remoteState;
    }),
    applyHistoryState: overrides.applyHistoryState || ((remoteState) => {
      context.__calls.applyHistoryState.push(remoteState);
    }),
    shouldAttemptAutomaticLocationEvent: (locationPayload, remoteState, settings) => {
      context.__calls.shouldAttemptAutomaticLocationEvent.push({ locationPayload, remoteState, settings });
      return shouldAttemptAutomaticLocationEventImpl(locationPayload, remoteState, settings);
    },
    shouldAttemptAutomaticOutOfRangeCheckout:
      overrides.shouldAttemptAutomaticOutOfRangeCheckout
      || ((locationPayload, remoteState) => (
        checkAutomaticActivities.shouldAttemptAutomaticOutOfRangeCheckout(locationPayload, remoteState)
      )),
    shouldAttemptAutomaticNearbyWorkplaceCheckIn:
      overrides.shouldAttemptAutomaticNearbyWorkplaceCheckIn
      || ((locationPayload, remoteState) => (
        checkAutomaticActivities.shouldAttemptAutomaticNearbyWorkplaceCheckIn(locationPayload, remoteState)
      )),
    resolveAutomaticCheckInLocation:
      overrides.resolveAutomaticCheckInLocation
      || ((locationPayload) => checkAutomaticActivities.resolveAutomaticCheckInLocation(locationPayload)),
    isOperationalAutomaticCheckInLocation:
      overrides.isOperationalAutomaticCheckInLocation
      || ((locationPayload, automaticLocal) => (
        checkAutomaticActivities.isOperationalAutomaticCheckInLocation(locationPayload, automaticLocal)
      )),
    isCheckoutZoneLocationName:
      overrides.isCheckoutZoneLocationName
      || ((value) => checkAutomaticActivities.isCheckoutZoneLocationName(value)),
    submitAutomaticActivity: overrides.submitAutomaticActivity || (async ({ action, local, suppressStatus }) => {
      context.__calls.submitAutomaticActivity.push({ action, local, suppressStatus });
      return {
        state: {
          current_action: action,
          current_local: local,
        },
      };
    }),
  };

  const moduleSource = [
    extractFunctionSource(checkScript, 'resolveAutomaticLocationAction'),
    `async ${extractFunctionSource(checkScript, 'runAutomaticActivitiesIfNeeded')}`,
    `async ${extractFunctionSource(checkScript, 'runManualLocationRefreshSequence')}`,
    `globalThis.__manualRefreshAutomaticActivityTestExports = {
      async runAutomaticActivitiesIfNeeded(locationPayload, options) {
        return runAutomaticActivitiesIfNeeded(locationPayload, options);
      },
      async runManualLocationRefreshSequence() {
        return runManualLocationRefreshSequence();
      },
      setLocationPayload(value) {
        globalThis.__locationPayload = value;
      },
      setRemoteState(value) {
        globalThis.__remoteState = value;
      },
      getSnapshot() {
        return {
          runWithLockedUserInteraction: globalThis.__calls.runWithLockedUserInteraction,
          resolveCurrentLocation: globalThis.__calls.resolveCurrentLocation.slice(),
          fetchWebState: globalThis.__calls.fetchWebState.slice(),
          applyHistoryState: globalThis.__calls.applyHistoryState.slice(),
          shouldAttemptAutomaticLocationEvent: globalThis.__calls.shouldAttemptAutomaticLocationEvent.slice(),
          submitAutomaticActivity: globalThis.__calls.submitAutomaticActivity.slice(),
          latestHistoryState: globalThis.latestHistoryState,
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-manual-refresh-automatic-activity.vm.js' });
  return {
    helpers: context.__manualRefreshAutomaticActivityTestExports,
    context,
  };
}

function createLifecycleAutomaticActivityHarness(overrides = {}) {
  const shouldAttemptAutomaticLocationEventImpl = overrides.shouldAttemptAutomaticLocationEvent
    || ((locationPayload, remoteState, settings) => (
      checkAutomaticActivities.shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, settings)
    ));
  const context = {
    Boolean,
    Promise,
    Date: overrides.Date || {
      now: () => 10_000,
    },
    automaticCheckoutLocation: checkAutomaticActivities.AUTOMATIC_CHECKOUT_LOCATION,
    gpsLocationPermissionGranted: overrides.gpsLocationPermissionGranted !== undefined
      ? Boolean(overrides.gpsLocationPermissionGranted)
      : true,
    latestHistoryState: null,
    mixedZoneIntervalMinutes: overrides.mixedZoneIntervalMinutes !== undefined
      ? overrides.mixedZoneIntervalMinutes
      : 35,
    chaveInput: { value: overrides.chave || 'A123' },
    lifecycleTriggerCooldownMs: overrides.lifecycleTriggerCooldownMs !== undefined
      ? overrides.lifecycleTriggerCooldownMs
      : 5000,
    lastLifecycleTriggerAt: overrides.lastLifecycleTriggerAt !== undefined
      ? overrides.lastLifecycleTriggerAt
      : 0,
    lifecycleRefreshInProgress: false,
    __locationPayload: null,
    __remoteState: overrides.remoteState || {
      current_action: 'checkout',
      current_local: 'Zona de CheckOut',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
    __calls: {
      refreshHistory: [],
      updateLocationForLifecycleSequence: [],
      fetchWebState: [],
      applyHistoryState: [],
      shouldAttemptAutomaticLocationEvent: [],
      setSequenceStatus: [],
      restorePersistedUserSettingsForChave: [],
      setNotificationMessage: [],
      setStatus: [],
      submitAutomaticActivity: [],
    },
    isUserInteractionLocked: overrides.isUserInteractionLocked || (() => false),
    sanitizeChave: overrides.sanitizeChave || ((value) => String(value || '').trim().toUpperCase()),
    isApplicationUnlocked: overrides.isApplicationUnlocked || (() => true),
    refreshHistory: overrides.refreshHistory || (async (chave, options) => {
      context.__calls.refreshHistory.push({ chave, options });
      return context.__remoteState;
    }),
    updateLocationForLifecycleSequence: overrides.updateLocationForLifecycleSequence || (async (options) => {
      context.__calls.updateLocationForLifecycleSequence.push(options);
      return context.__locationPayload;
    }),
    isAutomaticActivitiesEnabled: overrides.isAutomaticActivitiesEnabled || (() => true),
    fetchWebState: overrides.fetchWebState || (async (chave) => {
      context.__calls.fetchWebState.push(chave);
      return context.__remoteState;
    }),
    applyHistoryState: overrides.applyHistoryState || ((remoteState) => {
      context.__calls.applyHistoryState.push(remoteState);
    }),
    shouldAttemptAutomaticLocationEvent: (locationPayload, remoteState, settings) => {
      context.__calls.shouldAttemptAutomaticLocationEvent.push({ locationPayload, remoteState, settings });
      return shouldAttemptAutomaticLocationEventImpl(locationPayload, remoteState, settings);
    },
    shouldAttemptAutomaticOutOfRangeCheckout:
      overrides.shouldAttemptAutomaticOutOfRangeCheckout || (() => false),
    shouldAttemptAutomaticNearbyWorkplaceCheckIn:
      overrides.shouldAttemptAutomaticNearbyWorkplaceCheckIn || (() => false),
    resolveAutomaticCheckInLocation:
      overrides.resolveAutomaticCheckInLocation
      || ((locationPayload) => checkAutomaticActivities.resolveAutomaticCheckInLocation(locationPayload)),
    isOperationalAutomaticCheckInLocation:
      overrides.isOperationalAutomaticCheckInLocation
      || ((locationPayload, automaticLocal) => (
        checkAutomaticActivities.isOperationalAutomaticCheckInLocation(locationPayload, automaticLocal)
      )),
    isCheckoutZoneLocationName:
      overrides.isCheckoutZoneLocationName
      || ((value) => checkAutomaticActivities.isCheckoutZoneLocationName(value)),
    submitAutomaticActivity: overrides.submitAutomaticActivity || (async ({ action, local, suppressStatus }) => {
      context.__calls.submitAutomaticActivity.push({ action, local, suppressStatus });
      return {
        state: {
          current_action: action,
          current_local: local,
        },
      };
    }),
    setSequenceStatus: (message) => {
      context.__calls.setSequenceStatus.push(message);
    },
    restorePersistedUserSettingsForChave: (chave) => {
      context.__calls.restorePersistedUserSettingsForChave.push(chave);
    },
    setNotificationMessage: (channel, message, tone) => {
      context.__calls.setNotificationMessage.push({ channel, message, tone });
    },
    setStatus: (message, tone) => {
      context.__calls.setStatus.push({ message, tone });
    },
  };

  const moduleSource = [
    'const lifecycleDataReuseWindowMs = 5000;',
    extractFunctionSource(checkScript, 'resolveAutomaticLocationAction'),
    `async ${extractFunctionSource(checkScript, 'runAutomaticActivitiesIfNeeded')}`,
    `async ${extractFunctionSource(checkScript, 'runLifecycleUpdateSequence')}`,
    `globalThis.__lifecycleAutomaticActivityTestExports = {
      async runLifecycleUpdateSequence(options) {
        return runLifecycleUpdateSequence(options);
      },
      setLocationPayload(value) {
        globalThis.__locationPayload = value;
      },
      getSnapshot() {
        return {
          refreshHistory: globalThis.__calls.refreshHistory.slice(),
          updateLocationForLifecycleSequence: globalThis.__calls.updateLocationForLifecycleSequence.slice(),
          fetchWebState: globalThis.__calls.fetchWebState.slice(),
          applyHistoryState: globalThis.__calls.applyHistoryState.slice(),
          shouldAttemptAutomaticLocationEvent: globalThis.__calls.shouldAttemptAutomaticLocationEvent.slice(),
          setSequenceStatus: globalThis.__calls.setSequenceStatus.slice(),
          restorePersistedUserSettingsForChave: globalThis.__calls.restorePersistedUserSettingsForChave.slice(),
          setNotificationMessage: globalThis.__calls.setNotificationMessage.slice(),
          setStatus: globalThis.__calls.setStatus.slice(),
          submitAutomaticActivity: globalThis.__calls.submitAutomaticActivity.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-lifecycle-automatic-activity.vm.js' });
  return {
    helpers: context.__lifecycleAutomaticActivityTestExports,
    context,
  };
}

function createHistoryRefreshHarness(overrides = {}) {
  let currentNow = overrides.now !== undefined ? overrides.now : 10_000;
  const context = {
    AbortController,
    Promise,
    Boolean,
    Date: {
      now: () => currentNow,
    },
    __payload: overrides.payload || {
      found: true,
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
      projeto: 'BASE',
    },
    __calls: {
      fetch: [],
      setHistoryMessage: [],
      applyHistoryState: [],
      resetHistory: [],
    },
    sanitizeChave: overrides.sanitizeChave || ((value) => String(value || '').trim().toUpperCase()),
    isApplicationUnlocked: overrides.isApplicationUnlocked || (() => true),
    buildProtectedRequestError: overrides.buildProtectedRequestError || (() => new Error('request failed')),
    fetch: overrides.fetch || (async (url, options) => {
      context.__calls.fetch.push({ url, options });
      return {
        ok: true,
        json: async () => context.__payload,
      };
    }),
    setHistoryMessage: (message, tone) => {
      context.__calls.setHistoryMessage.push({ message, tone });
    },
  };

  const moduleSource = [
    'const stateEndpoint = "/api/web/check/state";',
    'let latestHistoryState = null;',
    'let historyRequestToken = 0;',
    'let historyAbortController = null;',
    'let historyRequestPromise = null;',
    'let historyRequestPromiseChave = "";',
    'let lastHistoryStateAppliedAt = 0;',
    'let lastHistoryStateAppliedChave = "";',
    'function getActiveChave() { return "A123"; }',
    `function applyHistoryState(state) {
      latestHistoryState = state;
      if (state) {
        lastHistoryStateAppliedAt = Date.now();
        lastHistoryStateAppliedChave = getActiveChave();
      } else {
        lastHistoryStateAppliedAt = 0;
        lastHistoryStateAppliedChave = '';
      }
      globalThis.__calls.applyHistoryState.push(state);
    }`,
    `function resetHistory(message) {
      applyHistoryState(null);
      globalThis.__calls.resetHistory.push(message || null);
      if (message) {
        setHistoryMessage(message);
      }
    }`,
    extractFunctionSource(checkScript, 'readRecentHistoryState'),
    `async ${extractFunctionSource(checkScript, 'refreshHistory')}`,
    `globalThis.__historyRefreshTestExports = {
      async refreshHistory(chave, options) {
        return refreshHistory(chave, options);
      },
      advanceTime(ms) {
        globalThis.__advanceTime(ms);
      },
      getSnapshot() {
        return {
          fetch: globalThis.__calls.fetch.slice(),
          setHistoryMessage: globalThis.__calls.setHistoryMessage.slice(),
          applyHistoryState: globalThis.__calls.applyHistoryState.slice(),
          resetHistory: globalThis.__calls.resetHistory.slice(),
        };
      },
    };`,
  ].join('\n\n');

  context.__advanceTime = (ms) => {
    currentNow += Number(ms) || 0;
  };

  vm.runInNewContext(moduleSource, context, { filename: 'check-history-refresh.vm.js' });
  return {
    helpers: context.__historyRefreshTestExports,
    context,
  };
}

function createSubmitGuardLocationHarness(overrides = {}) {
  let currentNow = overrides.now !== undefined ? overrides.now : 10_000;
  const context = {
    Promise,
    Boolean,
    Date: {
      now: () => currentNow,
    },
    __calls: {
      queryLocationPermissionState: 0,
      captureAndResolveLocation: [],
    },
    isApplicationUnlocked: overrides.isApplicationUnlocked || (() => true),
    getActiveChave: overrides.getActiveChave || (() => 'A123'),
    sanitizeChave: overrides.sanitizeChave || ((value) => String(value || '').trim().toUpperCase()),
    queryLocationPermissionState: overrides.queryLocationPermissionState || (async () => {
      context.__calls.queryLocationPermissionState += 1;
      return 'granted';
    }),
    readStorageFlag: overrides.readStorageFlag || (() => true),
    clientState: {
      shouldAttemptSilentLocationLookup: overrides.shouldAttemptSilentLocationLookup || (() => true),
    },
    captureAndResolveLocation: overrides.captureAndResolveLocation || (async (options) => {
      context.__calls.captureAndResolveLocation.push(options);
      return { status: 'matched', resolved_local: 'Portaria' };
    }),
  };

  const moduleSource = [
    'const lifecycleDataReuseWindowMs = 5000;',
    'const locationPermissionGrantedKey = "checking.web.user.location.permission-granted";',
    'let locationRequestPromise = null;',
    'let recentLocationResolutionPayload = null;',
    'let recentLocationResolutionAt = 0;',
    'let recentLocationResolutionChave = "";',
    extractFunctionSource(checkScript, 'readRecentLocationResolution'),
    `async ${extractFunctionSource(checkScript, 'ensureLocationReadyForSubmit')}`,
    `globalThis.__submitGuardLocationTestExports = {
      async ensureLocationReadyForSubmit() {
        return ensureLocationReadyForSubmit();
      },
      setRecentLocationResolution(payload, ageMs) {
        recentLocationResolutionPayload = payload;
        recentLocationResolutionAt = Date.now() - (Number(ageMs) || 0);
        recentLocationResolutionChave = 'A123';
      },
      clearRecentLocationResolution() {
        recentLocationResolutionPayload = null;
        recentLocationResolutionAt = 0;
        recentLocationResolutionChave = '';
      },
      getSnapshot() {
        return {
          queryLocationPermissionState: globalThis.__calls.queryLocationPermissionState,
          captureAndResolveLocation: globalThis.__calls.captureAndResolveLocation.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-submit-guard-location.vm.js' });
  return {
    helpers: context.__submitGuardLocationTestExports,
    context,
  };
}

function createSettingsLocationPermissionControlHarness() {
  function createElement() {
    return {
      disabled: false,
      attributes: {},
      setAttribute(name, value) {
        this.attributes[name] = String(value);
      },
      getAttribute(name) {
        return this.attributes[name];
      },
      querySelectorAll() {
        return [];
      },
      classList: {
        toggle() {},
      },
    };
  }

  const context = {
    Array,
    Boolean,
    Object,
    window: {
      HTMLButtonElement: function HTMLButtonElement() {},
    },
    __createElement: createElement,
    isUserInteractionLocked: () => false,
    syncAuthenticationFieldHighlights: () => {},
    isPasswordActionBusy: () => false,
    isAnyDialogOpen: () => false,
    isApplicationUnlocked: () => true,
    isAutomaticActivitiesEnabled: () => false,
    isAccuracyTooLowManualFallbackActive: () => false,
    resolveManualLocationOptions: () => ['Portaria'],
    shouldAllowManualLocationSelection: () => true,
    closeProjectMembershipPanel: () => {},
    resolveProjectMembershipStatusText: () => '',
    readSelectedProjectMembershipValues: () => ['Projeto A'],
    resolveCurrentUserProjectValues: () => ['Projeto A'],
    canOpenPasswordChangeFromSettings: () => false,
    canSubmitPasswordDialog: () => false,
    isPasswordRegistrationDialogMode: () => false,
    readStorageFlag(key) {
      return key === 'checking.web.user.location.permission-granted'
        ? context.__persistedGrant
        : false;
    },
    __persistedGrant: false,
  };

  const moduleSource = [
    'let gpsLocationPermissionGranted = false;',
    'let lastKnownLocationPermissionState = null;',
    'let transportStateLoading = false;',
    'let transportAddressSaveInProgress = false;',
    'let transportRequestInProgress = false;',
    'let transportCancelInProgress = false;',
    'let submitInProgress = false;',
    'let passwordRegisterInProgress = false;',
    'let passwordChangeInProgress = false;',
    'let userSelfRegistrationInProgress = false;',
    'let projectCatalogLoading = false;',
    'let userProjectsLoading = false;',
    'let projectUpdateInProgress = false;',
    'let locationRefreshLoading = false;',
    'let passwordLoginInProgress = false;',
    'const locationPermissionGrantedKey = "checking.web.user.location.permission-granted";',
    'const allowedProjectValues = ["Projeto A"];',
    'const actionInputs = [];',
    'const processControls = [];',
    'const authControls = [];',
    'const passwordDialogControls = [];',
    'const registrationDialogControls = [];',
    'const transportScreenControls = [];',
    'const highlightedAuthFields = [];',
    'const projectMembershipButton = globalThis.__createElement();',
    'const projectMembershipOptions = globalThis.__createElement();',
    'const projectMembershipStatus = globalThis.__createElement();',
    'const registrationProjectOptions = globalThis.__createElement();',
    'const settingsLocationPermissionButton = globalThis.__createElement();',
    'const settingsDialogControls = [settingsLocationPermissionButton];',
    'const settingsDialogBackButton = null;',
    'const settingsResetPasswordButton = null;',
    'const transportButton = null;',
    'const transportScreen = null;',
    'const passwordDialog = null;',
    'const registrationDialog = null;',
    'const form = globalThis.__createElement();',
    extractFunctionSource(checkScript, 'isLocationPermissionEffectivelySharedWithWebApp'),
    extractFunctionSource(checkScript, 'syncFormControlStates'),
    `globalThis.__settingsLocationPermissionControlTestExports = {
      syncFormControlStates,
      setGpsLocationPermissionGranted(value) {
        gpsLocationPermissionGranted = Boolean(value);
      },
      setPersistedGrant(value) {
        globalThis.__persistedGrant = Boolean(value);
      },
      setLastKnownLocationPermissionState(value) {
        lastKnownLocationPermissionState = value;
      },
      setLocationRefreshLoading(value) {
        locationRefreshLoading = Boolean(value);
      },
      getSnapshot() {
        return {
          disabled: settingsLocationPermissionButton.disabled,
          ariaDisabled: settingsLocationPermissionButton.getAttribute('aria-disabled'),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-settings-location-permission-control.vm.js' });
  return {
    helpers: context.__settingsLocationPermissionControlTestExports,
    context,
  };
}

function createSettingsDialogLifecycleHarness() {
  function createElement(options = {}) {
    const classes = new Set(options.classes || []);
    return {
      hidden: options.hidden !== undefined ? Boolean(options.hidden) : true,
      attributes: { ...(options.attributes || {}) },
      focusCalls: 0,
      setAttribute(name, value) {
        this.attributes[name] = String(value);
      },
      getAttribute(name) {
        return this.attributes[name];
      },
      focus() {
        this.focusCalls += 1;
      },
      classList: {
        add: (...tokens) => {
          tokens.forEach((token) => classes.add(token));
        },
        remove: (...tokens) => {
          tokens.forEach((token) => classes.delete(token));
        },
        contains: (token) => classes.has(token),
      },
      __classes: classes,
    };
  }

  const context = {
    Boolean,
    Promise,
    __calls: {
      dismissActiveKeyboard: 0,
      syncFormControlStates: 0,
      realignViewport: 0,
      closeProjectMembershipPanel: 0,
      queryLocationPermissionState: 0,
    },
    __blockingDialogs: {
      password: false,
      registration: false,
      transport: false,
    },
    __applicationUnlocked: false,
    __authState: {
      statusResolved: false,
      statusErrored: false,
      hasPassword: false,
    },
    __settingsDialog: createElement({ hidden: true, classes: ['is-hidden'] }),
    __settingsDialogBackdrop: createElement({ hidden: true, classes: ['is-hidden'] }),
    __settingsButton: createElement({ hidden: false, attributes: { 'aria-expanded': 'false' } }),
    __settingsLanguageSelect: createElement({ hidden: false }),
    __settingsDialogBackButton: createElement({ hidden: false }),
    dismissActiveKeyboard: () => {
      context.__calls.dismissActiveKeyboard += 1;
    },
    syncFormControlStates: () => {
      context.__calls.syncFormControlStates += 1;
    },
    realignViewport: () => {
      context.__calls.realignViewport += 1;
    },
    closeProjectMembershipPanel: () => {
      context.__calls.closeProjectMembershipPanel += 1;
    },
    queryLocationPermissionState: () => {
      context.__calls.queryLocationPermissionState += 1;
      return Promise.resolve('prompt');
    },
    isPasswordDialogOpen: () => Boolean(context.__blockingDialogs.password),
    isRegistrationDialogOpen: () => Boolean(context.__blockingDialogs.registration),
    isTransportScreenOpen: () => Boolean(context.__blockingDialogs.transport),
    isApplicationUnlocked: () => Boolean(context.__applicationUnlocked),
  };

  const moduleSource = [
    'const settingsDialog = globalThis.__settingsDialog;',
    'const settingsDialogBackdrop = globalThis.__settingsDialogBackdrop;',
    'const settingsButton = globalThis.__settingsButton;',
    'const settingsLanguageSelect = globalThis.__settingsLanguageSelect;',
    'const settingsDialogBackButton = globalThis.__settingsDialogBackButton;',
    'const authState = globalThis.__authState;',
    extractFunctionSource(checkScript, 'isSettingsDialogOpen'),
    extractFunctionSource(checkScript, 'closeSettingsDialog'),
    extractFunctionSource(checkScript, 'openSettingsDialog'),
    extractFunctionSource(checkScript, 'canOpenPasswordChangeFromSettings'),
    `globalThis.__settingsDialogLifecycleTestExports = {
      isSettingsDialogOpen,
      openSettingsDialog,
      closeSettingsDialog,
      canOpenPasswordChangeFromSettings,
      resetCalls() {
        globalThis.__calls.dismissActiveKeyboard = 0;
        globalThis.__calls.syncFormControlStates = 0;
        globalThis.__calls.realignViewport = 0;
        globalThis.__calls.closeProjectMembershipPanel = 0;
        globalThis.__calls.queryLocationPermissionState = 0;
        settingsButton.focusCalls = 0;
        settingsLanguageSelect.focusCalls = 0;
        settingsDialogBackButton.focusCalls = 0;
      },
      setBlockingDialogs(values) {
        Object.assign(globalThis.__blockingDialogs, values || {});
      },
      setApplicationUnlocked(value) {
        globalThis.__applicationUnlocked = Boolean(value);
      },
      assignAuthState(values) {
        Object.assign(authState, values || {});
      },
      getSnapshot() {
        return {
          dialogHidden: settingsDialog.hidden,
          backdropHidden: settingsDialogBackdrop.hidden,
          dialogClasses: Array.from(settingsDialog.__classes),
          backdropClasses: Array.from(settingsDialogBackdrop.__classes),
          ariaExpanded: settingsButton.getAttribute('aria-expanded'),
          dismissActiveKeyboard: globalThis.__calls.dismissActiveKeyboard,
          syncFormControlStates: globalThis.__calls.syncFormControlStates,
          realignViewport: globalThis.__calls.realignViewport,
          closeProjectMembershipPanel: globalThis.__calls.closeProjectMembershipPanel,
          queryLocationPermissionState: globalThis.__calls.queryLocationPermissionState,
          settingsButtonFocus: settingsButton.focusCalls,
          settingsLanguageSelectFocus: settingsLanguageSelect.focusCalls,
          settingsDialogBackButtonFocus: settingsDialogBackButton.focusCalls,
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-settings-dialog-lifecycle.vm.js' });
  return {
    helpers: context.__settingsDialogLifecycleTestExports,
    context,
  };
}

function createSettingsLocationPermissionRequestHarness(overrides = {}) {
  const context = {
    Promise,
    Boolean,
    window: {
      isSecureContext: overrides.isSecureContext !== undefined ? Boolean(overrides.isSecureContext) : true,
    },
    navigator: {
      geolocation: overrides.hasGeolocation === false ? null : {},
    },
    __calls: {
      syncFormControlStates: 0,
      queryLocationPermissionState: 0,
      setLocationWithoutPermission: 0,
      setStatus: [],
      runWithLockedUserInteraction: 0,
      resolveCurrentLocation: [],
    },
    isLocationPermissionEffectivelySharedWithWebApp: overrides.isLocationPermissionEffectivelySharedWithWebApp || (() => false),
    syncFormControlStates: () => {
      context.__calls.syncFormControlStates += 1;
    },
    queryLocationPermissionState: overrides.queryLocationPermissionState || (async () => {
      context.__calls.queryLocationPermissionState += 1;
      return 'prompt';
    }),
    setLocationWithoutPermission: () => {
      context.__calls.setLocationWithoutPermission += 1;
    },
    setStatus: (message, tone) => {
      context.__calls.setStatus.push({ message, tone });
    },
    runWithLockedUserInteraction: overrides.runWithLockedUserInteraction || (async (callback) => {
      context.__calls.runWithLockedUserInteraction += 1;
      return callback();
    }),
    resolveCurrentLocation: overrides.resolveCurrentLocation || (async (options) => {
      context.__calls.resolveCurrentLocation.push(options);
      return { status: 'matched', resolved_local: 'Portaria' };
    }),
  };

  const moduleSource = [
    `async ${extractFunctionSource(checkScript, 'requestPreciseLocationPermissionFromSettings')}`,
    `globalThis.__settingsLocationPermissionRequestTestExports = {
      async request() {
        return requestPreciseLocationPermissionFromSettings();
      },
      getSnapshot() {
        return {
          syncFormControlStates: globalThis.__calls.syncFormControlStates,
          queryLocationPermissionState: globalThis.__calls.queryLocationPermissionState,
          setLocationWithoutPermission: globalThis.__calls.setLocationWithoutPermission,
          setStatus: globalThis.__calls.setStatus.slice(),
          runWithLockedUserInteraction: globalThis.__calls.runWithLockedUserInteraction,
          resolveCurrentLocation: globalThis.__calls.resolveCurrentLocation.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-settings-location-permission-request.vm.js' });
  return {
    helpers: context.__settingsLocationPermissionRequestTestExports,
    context,
  };
}

function createSettingsSupportHarness(overrides = {}) {
  const context = {
    Boolean,
    String,
    Object,
    encodeURIComponent,
    __calls: {
      closeSettingsDialog: [],
      windowOpen: [],
      locationAssign: [],
    },
    authState: {
      authenticated: false,
      chave: '',
      ...overrides.authState,
    },
    chaveInput: {
      value: overrides.typedChave || '',
    },
    closeSettingsDialog: (options) => {
      context.__calls.closeSettingsDialog.push(options);
    },
    window: overrides.window || {
      open: (url, target, features) => {
        context.__calls.windowOpen.push([url, target, features]);
        return {};
      },
      location: {
        assign: (url) => {
          context.__calls.locationAssign.push(url);
        },
      },
    },
  };

  const moduleSource = [
    extractConstSource(checkScript, 'checkingWebSupportWhatsAppPhone'),
    extractConstSource(checkScript, 'checkingWebManualPath'),
    extractFunctionSource(checkScript, 'sanitizeChave'),
    extractFunctionSource(checkScript, 'getActiveChave'),
    extractFunctionSource(checkScript, 'resolveSupportRequestChave'),
    extractFunctionSource(checkScript, 'canOpenSupportFromSettings'),
    extractFunctionSource(checkScript, 'buildCheckingWebSupportMessage'),
    extractFunctionSource(checkScript, 'buildCheckingWebSupportWhatsAppUrl'),
    extractFunctionSource(checkScript, 'openSecondarySurface'),
    extractFunctionSource(checkScript, 'openCheckingWebSupport'),
    extractFunctionSource(checkScript, 'openCheckingWebManual'),
    `globalThis.__settingsSupportTestExports = {
      resolveSupportRequestChave,
      canOpenSupportFromSettings,
      buildCheckingWebSupportMessage,
      buildCheckingWebSupportWhatsAppUrl,
      openSupport() {
        return openCheckingWebSupport();
      },
      openManual() {
        return openCheckingWebManual();
      },
      setTypedChave(value) {
        chaveInput.value = value;
      },
      assignAuthState(values) {
        Object.assign(authState, values || {});
      },
      getSnapshot() {
        return {
          closeSettingsDialog: globalThis.__calls.closeSettingsDialog.slice(),
          windowOpen: globalThis.__calls.windowOpen.slice(),
          locationAssign: globalThis.__calls.locationAssign.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-settings-support.vm.js' });
  return {
    helpers: context.__settingsSupportTestExports,
    context,
  };
}

function toPlainValue(value) {
  return JSON.parse(JSON.stringify(value));
}

test('check controller source parses as valid JavaScript', () => {
  assert.doesNotThrow(() => {
    new vm.Script(checkScript);
  });
});

test('check page keeps Projetos, Local and Informe controls addressable for toggle-driven visibility', () => {
  assert.doesNotMatch(checkHtml, /<title>\s*Checking Mobile Web\s*<\/title>/);
  assert.match(checkHtml, /<span class="header-logo-text">\s*Checking Web\s*<\/span>/);
  assert.match(checkHtml, /id="automaticActivitiesToggle"/);
  assert.match(checkHtml, /id="projectField"/);
  assert.match(checkHtml, /id="projectMembershipButton"/);
  assert.match(checkHtml, /id="projectMembershipOptions"/);
  assert.doesNotMatch(checkHtml, /id="projectSelect"/);
  assert.match(checkHtml, /id="locationSelectField"/);
  assert.match(checkHtml, /id="informeField"/);
  assert.match(checkHtml, /id="submitButton"[\s\S]*>Registrar</);
});

test('check controller disables the Settings location action only when effective location sharing is already active or a refresh is in progress', () => {
  const { helpers } = createSettingsLocationPermissionControlHarness();

  helpers.syncFormControlStates();
  let snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.disabled, false);
  assert.equal(snapshot.ariaDisabled, 'false');

  helpers.setGpsLocationPermissionGranted(true);
  helpers.syncFormControlStates();
  snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.disabled, true);
  assert.equal(snapshot.ariaDisabled, 'true');

  helpers.setGpsLocationPermissionGranted(false);
  helpers.setPersistedGrant(true);
  helpers.syncFormControlStates();
  snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.disabled, true);

  helpers.setPersistedGrant(false);
  helpers.setLastKnownLocationPermissionState('granted');
  helpers.syncFormControlStates();
  snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.disabled, true);

  helpers.setLastKnownLocationPermissionState('prompt');
  helpers.setLocationRefreshLoading(true);
  helpers.syncFormControlStates();
  snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.disabled, true);
});

test('check controller opens and closes the Settings dialog with focus restoration and respects blocking dialogs', () => {
  const { helpers } = createSettingsDialogLifecycleHarness();

  assert.equal(helpers.isSettingsDialogOpen(), false);

  helpers.openSettingsDialog();
  let snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(helpers.isSettingsDialogOpen(), true);
  assert.equal(snapshot.dialogHidden, false);
  assert.equal(snapshot.backdropHidden, false);
  assert.equal(snapshot.dialogClasses.includes('is-hidden'), false);
  assert.equal(snapshot.backdropClasses.includes('is-hidden'), false);
  assert.equal(snapshot.ariaExpanded, 'true');
  assert.equal(snapshot.closeProjectMembershipPanel, 1);
  assert.equal(snapshot.queryLocationPermissionState, 1);
  assert.equal(snapshot.syncFormControlStates, 1);
  assert.equal(snapshot.realignViewport, 1);
  assert.equal(snapshot.settingsLanguageSelectFocus, 1);
  assert.equal(snapshot.settingsDialogBackButtonFocus, 0);

  helpers.closeSettingsDialog();
  snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(helpers.isSettingsDialogOpen(), false);
  assert.equal(snapshot.dialogHidden, true);
  assert.equal(snapshot.backdropHidden, true);
  assert.equal(snapshot.dialogClasses.includes('is-hidden'), true);
  assert.equal(snapshot.backdropClasses.includes('is-hidden'), true);
  assert.equal(snapshot.ariaExpanded, 'false');
  assert.equal(snapshot.dismissActiveKeyboard, 1);
  assert.equal(snapshot.syncFormControlStates, 2);
  assert.equal(snapshot.realignViewport, 2);
  assert.equal(snapshot.settingsButtonFocus, 1);

  helpers.resetCalls();
  helpers.setBlockingDialogs({ password: true });
  helpers.openSettingsDialog();
  snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(helpers.isSettingsDialogOpen(), false);
  assert.equal(snapshot.dialogHidden, true);
  assert.equal(snapshot.backdropHidden, true);
  assert.equal(snapshot.ariaExpanded, 'false');
  assert.equal(snapshot.closeProjectMembershipPanel, 0);
  assert.equal(snapshot.queryLocationPermissionState, 0);
  assert.equal(snapshot.syncFormControlStates, 0);
  assert.equal(snapshot.realignViewport, 0);
  assert.equal(snapshot.settingsLanguageSelectFocus, 0);
});

test('check controller only allows Settings > Reset Password for a fully unlocked authenticated session', () => {
  const { helpers } = createSettingsDialogLifecycleHarness();

  assert.equal(helpers.canOpenPasswordChangeFromSettings(), false);

  helpers.assignAuthState({
    statusResolved: true,
    statusErrored: false,
    hasPassword: true,
  });
  assert.equal(helpers.canOpenPasswordChangeFromSettings(), false);

  helpers.setApplicationUnlocked(true);
  assert.equal(helpers.canOpenPasswordChangeFromSettings(), true);

  helpers.assignAuthState({ hasPassword: false });
  assert.equal(helpers.canOpenPasswordChangeFromSettings(), false);

  helpers.assignAuthState({ hasPassword: true, statusErrored: true });
  assert.equal(helpers.canOpenPasswordChangeFromSettings(), false);
});

test('check controller reuses the shared geolocation pipeline for Settings > Allow Location', async () => {
  const { helpers } = createSettingsLocationPermissionRequestHarness();

  await helpers.request();
  const snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(snapshot.queryLocationPermissionState, 1);
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.resolveCurrentLocation, [{
    interactive: true,
    forceRefresh: true,
    measurementTrigger: 'settings_permission',
    showDetectingState: true,
    showCompletionStatus: true,
    suppressNotification: false,
  }]);
  assert.deepStrictEqual(snapshot.setStatus, []);
});

test('check controller keeps Settings > Allow Location safe for insecure, unsupported, and denied browser states', async () => {
  let harness = createSettingsLocationPermissionRequestHarness({
    isSecureContext: false,
  });
  await harness.helpers.request();
  let snapshot = toPlainValue(harness.helpers.getSnapshot());
  assert.equal(snapshot.queryLocationPermissionState, 0);
  assert.equal(snapshot.runWithLockedUserInteraction, 0);
  assert.deepStrictEqual(snapshot.resolveCurrentLocation, []);
  assert.deepStrictEqual(snapshot.setStatus, [{
    message: 'A localização precisa requer uma conexão segura (HTTPS).',
    tone: 'error',
  }]);

  harness = createSettingsLocationPermissionRequestHarness({
    hasGeolocation: false,
  });
  await harness.helpers.request();
  snapshot = toPlainValue(harness.helpers.getSnapshot());
  assert.equal(snapshot.queryLocationPermissionState, 0);
  assert.equal(snapshot.runWithLockedUserInteraction, 0);
  assert.deepStrictEqual(snapshot.resolveCurrentLocation, []);
  assert.deepStrictEqual(snapshot.setStatus, [{
    message: 'Este navegador não oferece suporte à localização precisa.',
    tone: 'error',
  }]);

  harness = createSettingsLocationPermissionRequestHarness({
    queryLocationPermissionState: async () => {
      harness.context.__calls.queryLocationPermissionState += 1;
      return 'denied';
    },
  });
  await harness.helpers.request();
  snapshot = toPlainValue(harness.helpers.getSnapshot());
  assert.equal(snapshot.queryLocationPermissionState, 1);
  assert.equal(snapshot.setLocationWithoutPermission, 1);
  assert.equal(snapshot.runWithLockedUserInteraction, 0);
  assert.deepStrictEqual(snapshot.resolveCurrentLocation, []);
  assert.deepStrictEqual(snapshot.setStatus, [{
    message: 'A permissão de localização está bloqueada no navegador. Libere o acesso ao site nas configurações do navegador.',
    tone: 'warning',
  }]);
});

test('check controller builds the WhatsApp support request from the authenticated key before any typed fallback', () => {
  const { helpers } = createSettingsSupportHarness({
    authState: {
      authenticated: true,
      chave: 'ab12',
    },
    typedChave: 'zz99',
  });

  const expectedMessage = 'Preciso de ajuda com a aplicacao Web. Minha chave e AB12.';
  const expectedUrl = `https://wa.me/5521992174446?text=${encodeURIComponent(expectedMessage)}`;

  assert.equal(helpers.resolveSupportRequestChave(), 'AB12');
  assert.equal(helpers.canOpenSupportFromSettings(), true);
  assert.equal(helpers.buildCheckingWebSupportMessage('ab12'), expectedMessage);
  assert.equal(helpers.buildCheckingWebSupportWhatsAppUrl('ab12'), expectedUrl);
  assert.equal(helpers.openSupport(), true);

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.closeSettingsDialog, [{ restoreFocus: false }]);
  assert.deepStrictEqual(snapshot.windowOpen, [[expectedUrl, '_blank', 'noopener']]);
  assert.deepStrictEqual(snapshot.locationAssign, []);
});

test('check controller falls back to the current typed key for Settings > Support when no authenticated key is available', () => {
  const { helpers } = createSettingsSupportHarness({
    authState: {
      authenticated: false,
      chave: '',
    },
    typedChave: 'cd34',
  });

  const expectedMessage = 'Preciso de ajuda com a aplicacao Web. Minha chave e CD34.';
  const expectedUrl = `https://wa.me/5521992174446?text=${encodeURIComponent(expectedMessage)}`;

  assert.equal(helpers.resolveSupportRequestChave(), 'CD34');
  assert.equal(helpers.canOpenSupportFromSettings(), true);
  assert.equal(helpers.openSupport(), true);

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.closeSettingsDialog, [{ restoreFocus: false }]);
  assert.deepStrictEqual(snapshot.windowOpen, [[expectedUrl, '_blank', 'noopener']]);
});

test('check controller keeps Settings > Support unavailable when it cannot resolve a valid 4-character key', () => {
  const { helpers } = createSettingsSupportHarness({
    authState: {
      authenticated: false,
      chave: '',
    },
    typedChave: 'a1',
  });

  assert.equal(helpers.resolveSupportRequestChave(), '');
  assert.equal(helpers.canOpenSupportFromSettings(), false);
  assert.equal(helpers.openSupport(), false);

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.closeSettingsDialog, []);
  assert.deepStrictEqual(snapshot.windowOpen, []);
  assert.deepStrictEqual(snapshot.locationAssign, []);
});

test('check controller opens the manual entry point in a new tab from Settings > About', () => {
  const { helpers } = createSettingsSupportHarness();

  assert.equal(helpers.openManual(), true);

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.closeSettingsDialog, [{ restoreFocus: false }]);
  assert.deepStrictEqual(snapshot.windowOpen, [['./manual.html', '_blank', 'noopener']]);
  assert.deepStrictEqual(snapshot.locationAssign, []);
});

test('check controller keeps automatic mode blocked outside the accuracy fallback override and reruns lifecycle updates when GPS is available', () => {
  const { helpers } = createManualOverrideUiHarness();

  helpers.setAutomaticActivitiesEnabled(true);
  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('matched');
  helpers.syncProjectVisibility();
  helpers.syncFormControlStates();

  const matchedSnapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(matchedSnapshot.projectHidden, true);
  assert.equal(matchedSnapshot.locationHidden, true);
  assert.equal(matchedSnapshot.informeHidden, true);
  assert.equal(matchedSnapshot.projectDisabled, true);
  assert.equal(matchedSnapshot.manualLocationDisabled, true);
  assert.deepStrictEqual(matchedSnapshot.actionDisabled, [true, true]);
  assert.equal(matchedSnapshot.submitDisabled, true);

  helpers.setGpsLocationPermissionGranted(false);
  helpers.setCurrentLocationResolutionStatus(null);
  helpers.syncProjectVisibility();
  helpers.syncFormControlStates();

  const noPermissionSnapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(noPermissionSnapshot.projectHidden, true);
  assert.equal(noPermissionSnapshot.locationHidden, true);
  assert.equal(noPermissionSnapshot.projectDisabled, true);
  assert.equal(noPermissionSnapshot.submitDisabled, true);

  assert.match(checkScript, /control === manualLocationSelect[\s\S]*!shouldAllowManualLocationSelection\(\)/);
  assert.match(checkScript, /if \(shouldAllowManualLocationSelection\(\) && !manualLocationSelect\.value\) \{/);
  assert.match(checkScript, /function resolveSubmittedLocationValue\(\) \{[\s\S]*shouldAllowManualLocationSelection\(\)[\s\S]*manualLocationSelect\.value \|\| null[\s\S]*resolveMatchedOperationalLocation\(currentLocationMatch\)/);
  assert.match(checkScript, /const submittedLocal = resolveFinalSubmittableLocationValue\(resolveSubmittedLocationValue\(\)\);/);
  assert.match(checkScript, /local: submittedLocal/);
  assert.match(checkScript, /setGpsLocationPermissionGranted\(value\) \{[\s\S]*syncProjectVisibility\(\);/);
  assert.match(checkScript, /automaticActivitiesToggle\.addEventListener\('change', \(\) => \{[\s\S]*syncProjectVisibility\(\);[\s\S]*syncManualLocationControl\(\);/);
  assert.match(checkScript, /if \(gpsLocationPermissionGranted && isApplicationUnlocked\(\)\) \{[\s\S]*runLifecycleUpdateSequence\(\{[\s\S]*ignoreCooldown: true,[\s\S]*triggerSource: 'automatic_activities_disable',[\s\S]*\}\);/);
  assert.match(checkScript, /if \(isAutomaticActivitiesEnabled\(\) && !isAccuracyTooLowManualFallbackActive\(\)\) \{[\s\S]*Desative Atividades Automáticas para registrar manualmente\./);
});

test('check controller preserves manual override across automatic toggle changes only while accuracy_too_low remains active', () => {
  const { helpers } = createManualOverrideUiHarness();

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('accuracy_too_low');
  helpers.setAvailableLocations(['Portaria']);

  helpers.setAutomaticActivitiesEnabled(false);
  helpers.syncProjectVisibility();
  helpers.syncFormControlStates();
  const manualModeSnapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(manualModeSnapshot.projectHidden, false);
  assert.equal(manualModeSnapshot.projectDisabled, false);
  assert.equal(manualModeSnapshot.manualLocationDisabled, false);

  helpers.setAutomaticActivitiesEnabled(true);
  helpers.syncProjectVisibility();
  helpers.syncFormControlStates();
  const automaticModeSnapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(automaticModeSnapshot.projectHidden, false);
  assert.equal(automaticModeSnapshot.projectDisabled, false);
  assert.equal(automaticModeSnapshot.manualLocationDisabled, false);

  helpers.setCurrentLocationResolutionStatus('matched');
  helpers.syncProjectVisibility();
  helpers.syncFormControlStates();
  const recoveredSnapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(recoveredSnapshot.projectHidden, true);
  assert.equal(recoveredSnapshot.projectDisabled, true);
  assert.equal(recoveredSnapshot.manualLocationDisabled, true);
});

test('check controller unlocks manual override controls during accuracy_too_low even with automatic mode enabled', () => {
  const { helpers } = createManualOverrideUiHarness();

  helpers.setAutomaticActivitiesEnabled(true);
  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('accuracy_too_low');
  helpers.setAvailableLocations(['Portaria']);
  helpers.syncProjectVisibility();
  helpers.syncFormControlStates();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.projectHidden, false);
  assert.equal(snapshot.locationHidden, false);
  assert.equal(snapshot.informeHidden, true);
  assert.equal(snapshot.projectDisabled, false);
  assert.equal(snapshot.manualLocationDisabled, false);
  assert.deepStrictEqual(snapshot.actionDisabled, [false, false]);
  assert.equal(snapshot.submitDisabled, false);

  helpers.setAvailableLocations([]);
  helpers.syncFormControlStates();
  const syntheticOnlySnapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(syntheticOnlySnapshot.manualLocationDisabled, false);
});

test('check controller prefers Escritório Principal and falls back to Precisao Insuficiente only during accuracy_too_low', () => {
  const { helpers } = createManualLocationSelectHarness();

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('accuracy_too_low');
  helpers.setAvailableLocations(['Portaria', 'Escritório Principal']);
  helpers.syncManualLocationControl();

  const preferredDefaultSnapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(preferredDefaultSnapshot.options, ['Portaria', 'Escritório Principal']);
  assert.equal(preferredDefaultSnapshot.selectedValue, 'Escritório Principal');
  assert.equal(preferredDefaultSnapshot.resolvedDefault, 'Escritório Principal');

  helpers.setAvailableLocations(['Portaria']);
  helpers.setManualLocationValue('');
  helpers.syncManualLocationControl();

  const syntheticFallbackSnapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(syntheticFallbackSnapshot.options, ['Precisao Insuficiente', 'Portaria']);
  assert.equal(syntheticFallbackSnapshot.selectedValue, 'Precisao Insuficiente');
  assert.equal(syntheticFallbackSnapshot.resolvedDefault, 'Precisao Insuficiente');
});

test('check controller keeps the no-permission manual flow limited to API-provided locations', () => {
  const { helpers } = createManualLocationSelectHarness();

  helpers.setGpsLocationPermissionGranted(false);
  helpers.setCurrentLocationResolutionStatus(null);
  helpers.setAvailableLocations(['Portaria']);
  helpers.syncManualLocationControl();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.options, ['Portaria']);
  assert.equal(snapshot.selectedValue, 'Portaria');
  assert.equal(snapshot.resolvedDefault, 'Portaria');
});

test('check controller recalculates manual location defaults when project options change during accuracy_too_low', () => {
  const { helpers } = createManualLocationSelectHarness();

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('accuracy_too_low');
  helpers.setAvailableLocations(['Portaria']);
  helpers.syncManualLocationControl();

  const firstProjectSnapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(firstProjectSnapshot.options, ['Precisao Insuficiente', 'Portaria']);
  assert.equal(firstProjectSnapshot.selectedValue, 'Precisao Insuficiente');

  helpers.setAvailableLocations(['Escritório Principal', 'Almoxarifado']);
  helpers.setManualLocationValue('Precisao Insuficiente');
  helpers.syncManualLocationControl();

  const secondProjectSnapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(secondProjectSnapshot.options, ['Escritório Principal', 'Almoxarifado']);
  assert.equal(secondProjectSnapshot.selectedValue, 'Escritório Principal');
  assert.equal(secondProjectSnapshot.resolvedDefault, 'Escritório Principal');
});

test('check controller removes the synthetic fallback option after leaving accuracy_too_low', () => {
  const { helpers } = createManualLocationSelectHarness();

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('accuracy_too_low');
  helpers.setAvailableLocations(['Portaria']);
  helpers.syncManualLocationControl();
  assert.deepStrictEqual(toPlainValue(helpers.getSnapshot()).options, ['Precisao Insuficiente', 'Portaria']);

  helpers.setCurrentLocationResolutionStatus('matched');
  helpers.syncManualLocationControl();

  const recoveredSnapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(recoveredSnapshot.options, ['Portaria']);
  assert.equal(recoveredSnapshot.selectedValue, 'Portaria');
  assert.equal(recoveredSnapshot.resolvedDefault, 'Portaria');
});

test('check controller resolves the submitted local from manual fallback and matched GPS states', () => {
  const { helpers } = createSubmittedLocationHarness();

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('accuracy_too_low');
  helpers.setManualLocationValue('Precisao Insuficiente');
  helpers.setCurrentLocationMatch(null);
  assert.equal(helpers.resolveSubmittedLocationValue(), 'Precisao Insuficiente');
  assert.equal(
    helpers.resolveFinalSubmittableLocationValue(helpers.resolveSubmittedLocationValue()),
    null
  );

  helpers.setGpsLocationPermissionGranted(false);
  helpers.setCurrentLocationResolutionStatus(null);
  helpers.setManualLocationValue('Portaria');
  assert.equal(helpers.resolveSubmittedLocationValue(), 'Portaria');
  assert.equal(
    helpers.resolveFinalSubmittableLocationValue(helpers.resolveSubmittedLocationValue()),
    'Portaria'
  );

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('not_in_known_location');
  helpers.setCurrentLocationMatch(null);
  helpers.setManualLocationValue('Localização não Cadastrada');
  assert.equal(helpers.resolveSubmittedLocationValue(), null);
  assert.equal(helpers.resolveFinalSubmittableLocationValue('Localização não Cadastrada'), null);

  helpers.setCurrentLocationResolutionStatus('outside_workplace');
  helpers.setManualLocationValue('Fora do Local de Trabalho');
  assert.equal(helpers.resolveSubmittedLocationValue(), null);
  assert.equal(
    helpers.resolveFinalSubmittableLocationValue('Fora do Local de Trabalho'),
    'Fora do Local de Trabalho'
  );

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('matched');
  helpers.setCurrentLocationMatch({ matched: true, resolved_local: 'Guarita' });
  helpers.setManualLocationValue('Ignorado');
  assert.equal(helpers.resolveSubmittedLocationValue(), 'Guarita');
  assert.equal(
    helpers.resolveFinalSubmittableLocationValue(helpers.resolveSubmittedLocationValue()),
    'Guarita'
  );
});

test('check controller blocks placeholder locals at final automatic submit assembly without calling fetch', async () => {
  const { helpers } = createAutomaticSubmitHarness();

  const result = await helpers.submitAutomaticActivity({
    action: 'checkin',
    local: 'Localização não Cadastrada',
    suppressStatus: true,
  });

  assert.equal(result, null);
  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.fetch, []);
  assert.deepStrictEqual(snapshot.applyHistoryState, []);
  assert.deepStrictEqual(snapshot.setStatus, []);
});

test('check controller keeps valid automatic submit locals eligible at final payload assembly', async () => {
  const { helpers } = createAutomaticSubmitHarness();

  const result = await helpers.submitAutomaticActivity({
    action: 'checkout',
    local: 'Fora do Local de Trabalho',
    suppressStatus: false,
  });

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.fetch, [{
    url: '/api/web/check',
    options: {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chave: 'A123',
        projeto: 'P80',
        action: 'checkout',
        local: 'Fora do Local de Trabalho',
        informe: 'normal',
        event_time: JSON.parse(snapshot.fetch[0].options.body).event_time,
        client_event_id: 'cid-123',
      }),
    },
  }]);
  assert.deepStrictEqual(snapshot.applyHistoryState, [{
    current_action: 'checkout',
    current_local: 'Fora do Local de Trabalho',
  }]);
  assert.deepStrictEqual(snapshot.setStatus, [{
    message: 'status.automaticCheckoutCompleted',
    tone: 'success',
  }]);
  assert.deepStrictEqual(result, {
    state: {
      current_action: 'checkout',
      current_local: 'Fora do Local de Trabalho',
    },
  });
});

test('check controller keeps failure labels in presentation without turning them into matched operational locations', () => {
  const cases = [
    {
      payload: {
        matched: false,
        status: 'not_in_known_location',
        label: 'Localização não Cadastrada',
        message: '',
        accuracy_meters: 8,
        accuracy_threshold_meters: 25,
      },
      expectedTone: 'muted',
    },
    {
      payload: {
        matched: false,
        status: 'accuracy_too_low',
        label: 'Precisão insuficiente',
        message: '',
        accuracy_meters: 44,
        accuracy_threshold_meters: 25,
      },
      expectedTone: 'warning',
    },
    {
      payload: {
        matched: false,
        status: 'outside_workplace',
        label: 'Fora do Local de Trabalho',
        message: '',
        accuracy_meters: 8,
        accuracy_threshold_meters: 25,
      },
      expectedTone: 'warning',
    },
  ];

  for (const { payload, expectedTone } of cases) {
    const { helpers } = createLocationMatchPresentationHarness();
    helpers.applyLocationMatch(payload, { suppressNotification: true });
    const snapshot = toPlainValue(helpers.getSnapshot());

    assert.deepStrictEqual(snapshot.presentationCalls, [[
      `UI:${payload.label}`,
      `MSG:${payload.message}`,
      expectedTone,
      `ACC:${payload.accuracy_meters}/${payload.accuracy_threshold_meters}`,
      { suppressNotification: true },
    ]]);
    assert.equal(snapshot.currentLocationMatch, null);
    assert.equal(snapshot.currentLocationResolutionStatus, payload.status);
  }
});

test('check controller reloads project locations during accuracy_too_low even when automatic mode is enabled', async () => {
  const { helpers } = createProjectSelectionHarness();

  helpers.setAutomaticActivitiesEnabled(true);
  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('matched');
  let result = await helpers.updateCurrentUserProjectSelection();
  let snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(result, false);
  assert.equal(snapshot.fetches.length, 0);
  assert.equal(snapshot.loadManualLocations, 0);

  helpers.setCurrentLocationResolutionStatus('accuracy_too_low');
  result = await helpers.updateCurrentUserProjectSelection();
  snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(result, true);
  assert.equal(snapshot.fetches.length, 1);
  assert.deepStrictEqual(snapshot.fetches[0].body, {
    projects: ['Projeto B'],
  });
  assert.equal(snapshot.loadManualLocations, 1);
  assert.equal(snapshot.lastCommittedProjectValue, 'Projeto B');
  assert.equal(snapshot.latestHistoryProject, 'Projeto B');
});

test('check controller submits plural projects in the registration dialog and syncs the main runtime state from the backend response', async () => {
  const { helpers } = createRegistrationSubmissionHarness();

  await helpers.submitRegistration();
  const snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(snapshot.preventDefault, 1);
  assert.deepStrictEqual(snapshot.loadProjectCatalog, [{ showError: true }]);
  assert.equal(snapshot.fetches.length, 1);
  assert.deepStrictEqual(snapshot.fetches[0], {
    url: '/api/web/auth/register-user',
    body: {
      chave: 'WU13',
      nome: 'ana multi projeto',
      projetos: ['P83', 'P80'],
      email: 'ana.multi@petrobras.com.br',
      senha: 'cad456',
      confirmar_senha: 'cad456',
    },
  });
  assert.deepStrictEqual(snapshot.currentUserProjectValues, ['P80', 'P83']);
  assert.deepStrictEqual(snapshot.lastCommittedUserProjectValues, ['P80', 'P83']);
  assert.equal(snapshot.lastCommittedProjectValue, 'P80');
  assert.equal(snapshot.persistCurrentUserSettings, 1);
  assert.deepStrictEqual(snapshot.writePersistedChave, ['WU13']);
  assert.deepStrictEqual(snapshot.persistPasswordForChave, [{ chave: 'WU13', password: 'cad456' }]);
  assert.equal(snapshot.closeRegistrationDialog, 1);
  assert.equal(snapshot.dismissActiveKeyboard, 1);
  assert.deepStrictEqual(snapshot.loadAuthenticatedApplication, [{
    chave: 'WU13',
    options: { showReadyMessage: false },
  }]);
  assert.equal(snapshot.chaveInputValue, 'WU13');
  assert.equal(snapshot.passwordInputValue, 'cad456');
  assert.equal(snapshot.authState.authenticated, true);
  assert.equal(snapshot.authState.statusErrored, false);
  assert.equal(snapshot.lastVerifiedPassword, 'cad456');
  assert.equal(snapshot.lastObservedPasswordFieldValue, 'cad456');
  assert.deepStrictEqual(snapshot.statuses.at(-1), {
    message: 'Cadastro concluído com sucesso.',
    tone: 'success',
  });
});

test('check controller stores mixed zone interval from the web locations catalog, falls back during partial rollout, and clears it on reset paths', async () => {
  const { helpers } = createLocationCatalogSettingsHarness();

  helpers.setPayload({
    items: ['Portaria', 'Portaria', 'Zona Mista'],
    location_accuracy_threshold_meters: 25,
    mixed_zone_interval_minutes: 35,
  });
  await helpers.loadManualLocations();

  let snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.availableLocations, ['Portaria', 'Zona Mista']);
  assert.equal(snapshot.locationAccuracyThresholdMeters, 25);
  assert.equal(snapshot.mixedZoneIntervalMinutes, 35);

  helpers.setPayload({
    items: ['Portaria'],
    location_accuracy_threshold_meters: 30,
  });
  await helpers.loadManualLocations();

  snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.locationAccuracyThresholdMeters, 30);
  assert.equal(snapshot.mixedZoneIntervalMinutes, 20);

  helpers.setApplicationUnlocked(false);
  await helpers.loadManualLocations();

  snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.availableLocations, []);
  assert.equal(snapshot.locationAccuracyThresholdMeters, null);
  assert.equal(snapshot.mixedZoneIntervalMinutes, null);
});

test('check controller keeps loading the locations catalog before the startup lifecycle refresh', async () => {
  const { helpers } = createAuthenticatedApplicationHarness();

  const result = await helpers.loadAuthenticatedApplication('ab12', { showReadyMessage: true });
  const snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(result, true);
  assert.deepStrictEqual(snapshot, [
    { step: 'loadProjectCatalog', options: { showError: false } },
    { step: 'restorePersistedUserSettingsForChave', chave: 'AB12' },
    { step: 'loadCurrentUserProjectMemberships', options: { showError: false } },
    { step: 'loadManualLocations' },
    { step: 'setStatus', message: 'Autenticação concluída. Atualizando a aplicação...', tone: 'info' },
    { step: 'runLifecycleUpdateSequence', options: { ignoreCooldown: true, triggerSource: 'startup' } },
  ]);
});

test('check controller does not auto-verify while the user is still typing the password', () => {
  const { helpers } = createPasswordInputAuthenticationHarness();

  helpers.setPasswordValue('abc');
  helpers.syncPasswordInputState({ showReadyMessage: true });

  let snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.schedulePasswordVerification, []);
  assert.equal(snapshot.clearPasswordVerificationTimer, 1);

  helpers.resetCalls();
  helpers.syncPasswordInputState({
    showReadyMessage: true,
    allowAutomaticVerification: true,
    requirePersistedPasswordMatch: false,
  });

  snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.schedulePasswordVerification, [{
    showReadyMessage: true,
    requirePersistedPasswordMatch: false,
  }]);
});

test('check controller only auto-verifies after auth status when the restored password matches the persisted value', async () => {
  const { helpers } = createAuthenticationStatusHarness();

  helpers.setPersistedPasswordMap({ AB12: 'segredo' });
  helpers.setPasswordValue('segredo');
  await helpers.refreshAuthenticationStatus('ab12', { schedulePasswordVerification: true });

  let snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.schedulePasswordVerification, [{ showReadyMessage: true }]);
  assert.equal(snapshot.schedulePasswordAutofillSync, 1);

  helpers.resetCalls();
  helpers.setPasswordValue('digitando');
  await helpers.refreshAuthenticationStatus('ab12', { schedulePasswordVerification: true });

  snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.schedulePasswordVerification, []);
  assert.equal(snapshot.schedulePasswordAutofillSync, 1);
});

test('check controller auto-opens the correct assistance dialog once per unresolved auth state and respects manual dismissal', () => {
  const { helpers } = createAuthenticationAssistanceAutoOpenHarness();

  helpers.syncState({
    chave: 'ab12',
    found: false,
    hasPassword: false,
    statusResolved: true,
    statusErrored: false,
  });
  helpers.maybeAutoOpen();

  let snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.calls, ['registration']);
  assert.equal(snapshot.currentStateKey, 'AB12:missing-user');
  assert.equal(snapshot.lastAutoOpenedStateKey, 'AB12:missing-user');

  helpers.dismissCurrent();
  helpers.maybeAutoOpen();

  snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.calls, ['registration']);
  assert.equal(snapshot.lastDismissedStateKey, 'AB12:missing-user');
});

test('check controller resets the assistance auto-open guard when the key or assistance state changes', () => {
  const { helpers } = createAuthenticationAssistanceAutoOpenHarness();

  helpers.syncState({
    chave: 'ab12',
    found: false,
    hasPassword: false,
    statusResolved: true,
    statusErrored: false,
  });
  helpers.maybeAutoOpen();
  helpers.dismissCurrent();

  helpers.syncState({
    chave: 'ab12',
    found: true,
    hasPassword: false,
    statusResolved: true,
    statusErrored: false,
  });
  helpers.maybeAutoOpen();

  let snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.calls, ['registration', 'password']);
  assert.equal(snapshot.currentStateKey, 'AB12:missing-password');
  assert.equal(snapshot.lastAutoOpenedStateKey, 'AB12:missing-password');
  assert.equal(snapshot.lastDismissedStateKey, '');

  helpers.dismissCurrent();
  helpers.syncState({
    chave: 'cd34',
    found: false,
    hasPassword: false,
    statusResolved: true,
    statusErrored: false,
  });
  helpers.maybeAutoOpen();

  snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.calls, ['registration', 'password', 'registration']);
  assert.equal(snapshot.currentStateKey, 'CD34:missing-user');
  assert.equal(snapshot.lastAutoOpenedStateKey, 'CD34:missing-user');
});

test('check controller does not replay the authenticated bootstrap for the same verified session', async () => {
  const { helpers } = createAuthenticatedApplicationHarness();

  const firstResult = await helpers.loadAuthenticatedApplication('ab12', { showReadyMessage: true });
  const secondResult = await helpers.loadAuthenticatedApplication('ab12', { showReadyMessage: true });
  const snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(firstResult, true);
  assert.equal(secondResult, true);
  assert.deepStrictEqual(snapshot, [
    { step: 'loadProjectCatalog', options: { showError: false } },
    { step: 'restorePersistedUserSettingsForChave', chave: 'AB12' },
    { step: 'loadCurrentUserProjectMemberships', options: { showError: false } },
    { step: 'loadManualLocations' },
    { step: 'setStatus', message: 'Autenticação concluída. Atualizando a aplicação...', tone: 'info' },
    { step: 'runLifecycleUpdateSequence', options: { ignoreCooldown: true, triggerSource: 'startup' } },
  ]);
});

test('check controller forwards the loaded mixed zone interval into the automatic location decision engine', () => {
  const { helpers } = createAutomaticLocationDecisionHarness();

  helpers.shouldAttemptAutomaticLocationEvent(
    { resolved_local: 'Zona Mista' },
    { current_action: 'checkout', current_local: 'Zona Mista' },
    { referenceTime: '2026-04-16T09:20:00' }
  );

  assert.deepStrictEqual(toPlainValue(helpers.getSnapshot()), [
    {
      locationPayload: { resolved_local: 'Zona Mista' },
      remoteState: { current_action: 'checkout', current_local: 'Zona Mista' },
      settings: {
        mixedZoneIntervalMinutes: 35,
        referenceTime: '2026-04-16T09:20:00',
      },
    },
  ]);
});

test('check controller injects the mixed zone interval into runtime automatic activity decisions', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    shouldAttemptAutomaticLocationEvent: () => false,
  });

  await helpers.runAutomaticActivitiesIfNeeded(
    { matched: true, resolved_local: 'Zona Mista', status: 'matched' },
    { suppressStatus: true }
  );

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.shouldAttemptAutomaticLocationEvent, [{
    locationPayload: { matched: true, resolved_local: 'Zona Mista', status: 'matched' },
    remoteState: {
      current_action: 'checkout',
      current_local: 'Zona de CheckOut',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
    settings: {
      mixedZoneIntervalMinutes: 35,
    },
  }]);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('check lifecycle sequence forwards the stored mixed zone interval into the automatic engine', async () => {
  const { helpers } = createLifecycleAutomaticActivityHarness({
    shouldAttemptAutomaticLocationEvent: () => false,
  });

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Zona Mista',
    status: 'matched',
  });

  const result = await helpers.runLifecycleUpdateSequence({ triggerSource: 'visibility' });
  const snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(result, true);
  assert.deepStrictEqual(snapshot.refreshHistory, [{
    chave: 'A123',
    options: {
      showLoadingMessage: false,
      silentSuccessMessage: true,
      suppressMessages: true,
      rethrowErrors: true,
      cacheWindowMs: 5000,
    },
  }]);
  assert.deepStrictEqual(snapshot.updateLocationForLifecycleSequence, [{
    triggerSource: 'visibility',
    cacheWindowMs: 5000,
  }]);
  assert.deepStrictEqual(snapshot.fetchWebState, []);
  assert.deepStrictEqual(snapshot.shouldAttemptAutomaticLocationEvent, [{
    locationPayload: {
      matched: true,
      resolved_local: 'Zona Mista',
      status: 'matched',
    },
    remoteState: {
      current_action: 'checkout',
      current_local: 'Zona de CheckOut',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
    settings: {
      mixedZoneIntervalMinutes: 35,
    },
  }]);
  assert.deepStrictEqual(snapshot.setSequenceStatus, [
    'Atualizando as atividades.....',
    'Atualizando a localização.....',
    'Realizando check-in ou check-out, se aplicável.....',
  ]);
  assert.deepStrictEqual(snapshot.restorePersistedUserSettingsForChave, ['A123']);
  assert.deepStrictEqual(snapshot.setStatus, [{
    message: 'Aplicação atualizada com sucesso.',
    tone: 'success',
  }]);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('check controller reuses recent history state during lifecycle refreshes inside the cache window', async () => {
  const { helpers } = createHistoryRefreshHarness();

  await helpers.refreshHistory('a123', {
    suppressMessages: true,
    cacheWindowMs: 5000,
  });
  await helpers.refreshHistory('a123', {
    suppressMessages: true,
    cacheWindowMs: 5000,
  });

  let snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.fetch.length, 1);
  assert.equal(snapshot.applyHistoryState.length, 1);

  helpers.advanceTime(6000);
  await helpers.refreshHistory('a123', {
    suppressMessages: true,
    cacheWindowMs: 5000,
  });

  snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.fetch.length, 2);
  assert.equal(snapshot.applyHistoryState.length, 2);
});

test('check controller reuses a recent lifecycle location for the submit guard instead of recapturing immediately', async () => {
  const { helpers } = createSubmitGuardLocationHarness();

  helpers.setRecentLocationResolution({
    matched: true,
    resolved_local: 'Portaria',
    status: 'matched',
  }, 1500);

  await helpers.ensureLocationReadyForSubmit();

  let snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.queryLocationPermissionState, 0);
  assert.deepStrictEqual(snapshot.captureAndResolveLocation, []);

  helpers.clearRecentLocationResolution();
  await helpers.ensureLocationReadyForSubmit();

  snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.queryLocationPermissionState, 1);
  assert.deepStrictEqual(snapshot.captureAndResolveLocation, [{
    interactive: false,
    forceRefresh: true,
    measurementTrigger: 'submit_guard',
  }]);
});

test('check controller submits automatic checkout when Zona Mista is reached after a remote check-in', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    remoteState: {
      current_action: 'checkin',
      current_local: 'Recepção',
      last_checkin_at: '2026-04-16T09:00:00',
      last_checkout_at: '2026-04-16T08:00:00',
    },
  });

  await helpers.runAutomaticActivitiesIfNeeded({
    matched: true,
    resolved_local: 'Zona Mista',
    status: 'matched',
  });

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, [{
    action: 'checkout',
    local: 'Zona Mista',
  }]);
});

test('check controller keeps checkout zone forcing automatic checkout after a mixed-zone check-in', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    remoteState: {
      current_action: 'checkin',
      current_local: 'Zona Mista',
      last_checkin_at: '2026-04-16T09:00:00',
      last_checkout_at: '2026-04-16T08:00:00',
    },
  });

  await helpers.runAutomaticActivitiesIfNeeded({
    matched: true,
    resolved_local: 'Zona de CheckOut',
    status: 'matched',
  }, {
    suppressStatus: true,
    referenceTime: '2026-04-16T09:10:00',
  });

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, [{
    action: 'checkout',
    local: 'Zona de CheckOut',
    suppressStatus: true,
  }]);
});

test('check controller keeps outside_workplace forcing automatic checkout after a mixed-zone check-in', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    remoteState: {
      current_action: 'checkin',
      current_local: 'Zona Mista',
      last_checkin_at: '2026-04-16T09:00:00',
      last_checkout_at: '2026-04-16T08:00:00',
    },
  });

  const result = await helpers.runAutomaticActivitiesIfNeeded({
    matched: false,
    status: 'outside_workplace',
    minimum_checkout_distance_meters: 2500,
  }, {
    suppressStatus: true,
    referenceTime: '2026-04-16T09:10:00',
  });

  assert.deepStrictEqual(toPlainValue(result), {
    performed: true,
    action: 'checkout',
    local: 'Fora do Local de Trabalho',
  });
  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, [{
    action: 'checkout',
    local: 'Fora do Local de Trabalho',
    suppressStatus: true,
  }]);
});

test('check controller keeps automatic check-in immediate when leaving mixed zone for a known location after checkout', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    remoteState: {
      current_action: 'checkout',
      current_local: 'Zona Mista',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
  });

  const result = await helpers.runAutomaticActivitiesIfNeeded({
    matched: true,
    resolved_local: 'Escritório Principal',
    status: 'matched',
  }, {
    suppressStatus: true,
    referenceTime: '2026-04-16T09:10:00',
  });

  assert.deepStrictEqual(toPlainValue(result), {
    performed: true,
    action: 'checkin',
    local: 'Escritório Principal',
  });
  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, [{
    action: 'checkin',
    local: 'Escritório Principal',
    suppressStatus: true,
  }]);
});

test('check controller does not submit automatic check-in for a nearby unregistered location after checkout', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    remoteState: {
      current_action: 'checkout',
      current_local: 'Zona Mista',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
  });

  const result = await helpers.runAutomaticActivitiesIfNeeded({
    matched: false,
    status: 'not_in_known_location',
    label: 'Localização não Cadastrada',
    nearest_workplace_distance_meters: 180,
  }, {
      suppressStatus: true,
      referenceTime: '2026-04-16T09:10:00',
    });

  assert.deepStrictEqual(toPlainValue(result), {
    performed: false,
    action: null,
    local: null,
  });
  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.fetchWebState, ['A123']);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('check controller does not submit automatic check-in when accuracy is too low after checkout', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    remoteState: {
      current_action: 'checkout',
      current_local: 'Zona Mista',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
  });

  const result = await helpers.runAutomaticActivitiesIfNeeded({
    matched: false,
    status: 'accuracy_too_low',
    label: 'Precisão insuficiente',
    resolved_local: null,
  }, {
    suppressStatus: true,
    referenceTime: '2026-04-16T09:10:00',
  });

  assert.deepStrictEqual(toPlainValue(result), {
    performed: false,
    action: null,
    local: null,
  });
  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.fetchWebState, ['A123']);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('check controller refuses placeholder automatic locals even if the nearby-workplace gate regresses open', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    remoteState: {
      current_action: 'checkout',
      current_local: 'Zona Mista',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
    shouldAttemptAutomaticNearbyWorkplaceCheckIn: () => true,
    resolveAutomaticCheckInLocation: () => 'Localização não Cadastrada',
  });

  const result = await helpers.runAutomaticActivitiesIfNeeded({
    matched: false,
    status: 'not_in_known_location',
    label: 'Localização não Cadastrada',
    nearest_workplace_distance_meters: 180,
  }, {
    suppressStatus: true,
    referenceTime: '2026-04-16T09:10:00',
  });

  assert.deepStrictEqual(toPlainValue(result), {
    performed: false,
    action: null,
    local: null,
  });
  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.fetchWebState, ['A123']);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('check controller re-enables manual local fallback when GPS ends below the required accuracy', () => {
  const { helpers } = createManualLocationFallbackHarness();

  assert.equal(helpers.isAccuracyTooLowManualFallbackActive(), false);
  assert.equal(helpers.shouldAllowManualLocationSelection(), true);

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setResolvedLocation({
    matched: true,
    status: 'matched',
    resolved_local: 'Portaria',
  });
  assert.equal(helpers.isAccuracyTooLowManualFallbackActive(), false);
  assert.equal(helpers.shouldAllowManualLocationSelection(), false);

  helpers.setResolvedLocation({
    matched: false,
    status: 'accuracy_too_low',
    label: 'Precisao insuficiente',
    resolved_local: null,
  });
  assert.equal(helpers.isAccuracyTooLowManualFallbackActive(), true);
  assert.equal(helpers.shouldAllowManualLocationSelection(), true);
  assert.deepStrictEqual(toPlainValue(helpers.getState()), {
    gpsLocationPermissionGranted: true,
    currentLocationMatch: null,
    currentLocationResolutionStatus: 'accuracy_too_low',
  });

  helpers.setResolvedLocation({
    matched: false,
    status: 'outside_workplace',
    resolved_local: null,
  });
  assert.equal(helpers.isAccuracyTooLowManualFallbackActive(), false);
  assert.equal(helpers.shouldAllowManualLocationSelection(), false);
});

test('check controller exposes opt-in local measurement support for baseline GPS sessions', () => {
  assert.match(checkScript, /const locationMeasurementStorageKey = 'checking\.web\.location\.measurement\.enabled';/);
  assert.match(checkScript, /window\.CheckingWebLocationMeasurement = Object\.freeze\(\{[\s\S]*enable\(\)[\s\S]*getSessions\(\)[\s\S]*getLatestSession\(\)[\s\S]*summarize\(\)[\s\S]*summarizeByTrigger\(\)[\s\S]*buildReport\(metadata\)[\s\S]*printReport\(metadata\)/);
  assert.match(checkScript, /measurementTrigger: 'manual_refresh'/);
  assert.match(checkScript, /measurementTrigger: 'settings_permission'/);
  assert.match(checkScript, /measurementTrigger: 'automatic_activities_enable'/);
});

test('check location helpers map lifecycle triggers to the 0s to 5s watch window and preserve enforced triggers elsewhere', () => {
  const { helpers } = createLocationHelperHarness();
  helpers.setLocationAccuracyThresholdMeters(30);

  assert.deepStrictEqual(toPlainValue(helpers.buildLocationCapturePlan({ measurementTrigger: 'startup' })), {
    trigger: 'startup',
    strategy: 'watch_window',
    minimumWindowMs: 0,
    maxWindowMs: 5000,
    targetAccuracyMeters: 30,
  });
  assert.deepStrictEqual(toPlainValue(helpers.buildLocationCapturePlan({ measurementTrigger: 'visibility' })), {
    trigger: 'visibility',
    strategy: 'watch_window',
    minimumWindowMs: 0,
    maxWindowMs: 5000,
    targetAccuracyMeters: 30,
  });
  assert.deepStrictEqual(toPlainValue(helpers.buildLocationCapturePlan({ measurementTrigger: 'pageshow' })), {
    trigger: 'pageshow',
    strategy: 'watch_window',
    minimumWindowMs: 0,
    maxWindowMs: 5000,
    targetAccuracyMeters: 30,
  });
  assert.deepStrictEqual(toPlainValue(helpers.buildLocationCapturePlan({ measurementTrigger: 'manual_refresh' })), {
    trigger: 'manual_refresh',
    strategy: 'watch_window',
    minimumWindowMs: 3000,
    maxWindowMs: 7000,
    targetAccuracyMeters: 30,
  });
  assert.deepStrictEqual(toPlainValue(helpers.buildLocationCapturePlan({ measurementTrigger: 'submit_guard' })), {
    trigger: 'submit_guard',
    strategy: 'watch_window',
    minimumWindowMs: 3000,
    maxWindowMs: 7000,
    targetAccuracyMeters: 30,
  });
  assert.deepStrictEqual(toPlainValue(helpers.buildLocationCapturePlan({ measurementTrigger: 'settings_permission' })), {
    trigger: 'settings_permission',
    strategy: 'watch_window',
    minimumWindowMs: 3000,
    maxWindowMs: 7000,
    targetAccuracyMeters: 30,
  });
  assert.deepStrictEqual(toPlainValue(helpers.buildLocationCapturePlan({ interactive: true })), {
    trigger: 'interactive',
    strategy: 'single_attempt',
    minimumWindowMs: 0,
    maxWindowMs: 0,
    targetAccuracyMeters: 30,
  });
});

test('check location helpers stop lifecycle watches immediately when the configured accuracy is met and keep the enforced minimum window elsewhere', () => {
  let nowMs = 5000;
  const { helpers } = createLocationHelperHarness({
    Date: {
      now: () => nowMs,
    },
  });
  const bestPosition = {
    coords: {
      accuracy: 18,
    },
  };

  assert.equal(helpers.shouldStopLocationWatch(bestPosition, {
    minimumWindowMs: 0,
    targetAccuracyMeters: 20,
  }, 5000), true);
  assert.equal(helpers.shouldStopLocationWatch(bestPosition, {
    minimumWindowMs: 3000,
    targetAccuracyMeters: 20,
  }, 5000), false);

  nowMs = 8000;
  assert.equal(helpers.shouldStopLocationWatch(bestPosition, {
    minimumWindowMs: 3000,
    targetAccuracyMeters: 20,
  }, 5000), true);
  assert.equal(helpers.shouldStopLocationWatch(bestPosition, {
    minimumWindowMs: 0,
    targetAccuracyMeters: null,
  }, 5000), false);
});

test('check location progress shows the current accuracy text and ignores invalid progress samples', () => {
  const presentationCalls = [];
  const { helpers } = createLocationHelperHarness({
    setLocationPresentation: (...args) => presentationCalls.push(args),
  });

  assert.equal(
    helpers.buildLocationCaptureProgressAccuracyText(18.2, { targetAccuracyMeters: 30 }),
    'Precisão atual 18 m / Limite 30 m'
  );
  assert.equal(
    helpers.buildLocationCaptureProgressAccuracyText(18.2, { targetAccuracyMeters: null }),
    'Precisão atual 18 m'
  );

  helpers.updateLocationCaptureProgress(
    {
      coords: {
        accuracy: 18.2,
      },
    },
    { targetAccuracyMeters: 30 },
    { showDetectingState: true }
  );

  assert.deepStrictEqual(toPlainValue(presentationCalls), [[
    'Buscando precisão suficiente...',
    '',
    'info',
    'Precisão atual 18 m / Limite 30 m',
    { suppressNotification: true },
  ]]);

  helpers.updateLocationCaptureProgress(
    {
      coords: {
        accuracy: null,
      },
    },
    { targetAccuracyMeters: 30 },
    { showDetectingState: true }
  );
  helpers.updateLocationCaptureProgress(
    {
      coords: {
        accuracy: 12,
      },
    },
    { targetAccuracyMeters: 30 },
    { showDetectingState: false }
  );

  assert.equal(presentationCalls.length, 1);
});

test('check watched GPS acquisition refreshes progress for each valid sample while keeping the best sample as the timeout fallback', async () => {
  let watchSuccess = null;
  let watchOptions = null;
  let clearedWatchId = null;
  let clearedTimeoutId = null;
  let timeoutCallback = null;
  const presentationCalls = [];
  const measurementEvents = [];
  const measurementSamples = [];
  const { helpers } = createLocationHelperHarness({
    navigator: {
      geolocation: {
        watchPosition(success, _error, options) {
          watchSuccess = success;
          watchOptions = options;
          return 77;
        },
        clearWatch(watchId) {
          clearedWatchId = watchId;
        },
      },
    },
    window: {
      setTimeout(callback, _delayMs) {
        timeoutCallback = callback;
        return 13;
      },
      clearTimeout(timeoutId) {
        clearedTimeoutId = timeoutId;
      },
    },
    setLocationPresentation: (...args) => presentationCalls.push(args),
    recordLocationMeasurementEvent: (_session, eventName, eventPayload) => {
      measurementEvents.push({ eventName, eventPayload });
    },
    recordLocationMeasurementSample: (_session, position) => {
      measurementSamples.push(position);
    },
  });

  const bestPosition = {
    coords: {
      latitude: -23.55,
      longitude: -46.63,
      accuracy: 18,
    },
    timestamp: 100,
  };
  const worsePosition = {
    coords: {
      latitude: -23.55,
      longitude: -46.63,
      accuracy: 42,
    },
    timestamp: 200,
  };
  const pendingPosition = helpers.requestWatchedCurrentPosition(
    {
      minimumWindowMs: 0,
      maxWindowMs: 5000,
      targetAccuracyMeters: 10,
    },
    { session_id: 'phase-3-watch-window' },
    { showDetectingState: true }
  );

  assert.equal(typeof watchSuccess, 'function');
  assert.equal(typeof timeoutCallback, 'function');
  assert.equal(watchOptions.timeout, 5000);

  watchSuccess(bestPosition);
  watchSuccess(worsePosition);

  assert.equal(measurementSamples.length, 2);
  assert.deepStrictEqual(presentationCalls.map((call) => call[3]), [
    'Precisão atual 18 m / Limite 10 m',
    'Precisão atual 42 m / Limite 10 m',
  ]);

  timeoutCallback();
  const resolvedPosition = await pendingPosition;

  assert.equal(resolvedPosition, bestPosition);
  assert.equal(clearedWatchId, 77);
  assert.equal(clearedTimeoutId, 13);
  assert.deepStrictEqual(measurementEvents.map((entry) => entry.eventName), [
    'watch_window_started',
    'watch_window_completed',
  ]);
  assert.deepStrictEqual(toPlainValue(measurementEvents[0].eventPayload), {
    max_window_ms: 5000,
    minimum_window_ms: 0,
    target_accuracy_meters: 10,
  });
  assert.deepStrictEqual(toPlainValue(measurementEvents[1].eventPayload), {
    termination_reason: 'acquisition_window_elapsed',
    best_accuracy_meters: 18,
  });
});

test('check controller keeps lifecycle GPS acquisition wired through the expected settings handoff', () => {
  assert.match(checkScript, /function requestCurrentPositionForPlan\(capturePlan, measurementSession, options\) \{[\s\S]*capturePlan\.strategy !== 'watch_window'[\s\S]*navigator\.geolocation\.watchPosition/);
  assert.match(checkScript, /async function updateLocationForLifecycleSequence\(options\) \{[\s\S]*showDetectingState: settings\.showDetectingState !== false,[\s\S]*\}/);
  assert.match(checkScript, /const locationPayload = await updateLocationForLifecycleSequence\(\{[\s\S]*cacheWindowMs: settings\.locationCacheWindowMs \?\? lifecycleDataReuseWindowMs,[\s\S]*\}\);/);
  assert.match(checkScript, /const position = await requestCurrentPositionForPlan\(capturePlan, measurementSession, \{[\s\S]*showDetectingState: settings\.showDetectingState,[\s\S]*\}\);/);
});

test('check controller keeps visibility, focus and pageshow routed through the shared lifecycle update sequence', () => {
  assert.match(checkScript, /function requestLifecycleUpdateFromUi\(triggerSource\) \{[\s\S]*window\.setTimeout\([\s\S]*runLifecycleUpdateSequence\(\{ triggerSource: nextTriggerSource \}\);/);
  assert.match(checkScript, /document\.addEventListener\('visibilitychange', \(\) => \{[\s\S]*requestLifecycleUpdateFromUi\('visibility'\);/);
  assert.match(checkScript, /window\.addEventListener\('focus', \(\) => \{[\s\S]*requestLifecycleUpdateFromUi\('focus'\);/);
  assert.match(checkScript, /window\.addEventListener\('pageshow', \(\) => \{[\s\S]*requestLifecycleUpdateFromUi\('pageshow'\);/);
});

test('manual refresh should evaluate automatic activities after a changed location during an active check-in', async () => {
  const { helpers } = createManualRefreshSequenceHarness();

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Almoxarifado',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.resolveCurrentLocation, [{
    interactive: true,
    forceRefresh: true,
    measurementTrigger: 'manual_refresh',
    showDetectingState: true,
    showCompletionStatus: true,
    suppressNotification: false,
  }]);
  assert.deepStrictEqual(snapshot.runAutomaticActivitiesIfNeeded, [{
    locationPayload: {
      matched: true,
      resolved_local: 'Almoxarifado',
      status: 'matched',
    },
  }]);
});

test('manual refresh forwards the stored mixed zone interval into the automatic engine', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    shouldAttemptAutomaticLocationEvent: () => false,
  });

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Zona Mista',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.resolveCurrentLocation, [{
    interactive: true,
    forceRefresh: true,
    measurementTrigger: 'manual_refresh',
    showDetectingState: true,
    showCompletionStatus: true,
    suppressNotification: false,
  }]);
  assert.deepStrictEqual(snapshot.fetchWebState, ['A123']);
  assert.deepStrictEqual(snapshot.shouldAttemptAutomaticLocationEvent, [{
    locationPayload: {
      matched: true,
      resolved_local: 'Zona Mista',
      status: 'matched',
    },
    remoteState: {
      current_action: 'checkout',
      current_local: 'Zona de CheckOut',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
    settings: {
      mixedZoneIntervalMinutes: 35,
    },
  }]);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('manual refresh should submit an automatic location update after an active check-in moves to another known location', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    remoteState: {
      current_action: 'checkin',
      current_local: 'Recepção',
      last_checkin_at: '2026-04-16T09:00:00',
      last_checkout_at: '2026-04-16T08:00:00',
    },
  });

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Almoxarifado',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.fetchWebState, ['A123']);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, [{
    action: 'checkin',
    local: 'Almoxarifado',
  }]);
});

test('manual refresh should submit automatic check-in after checkout when leaving checkout zone for a known location', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness();

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Escritório Principal',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.fetchWebState, ['A123']);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, [{
    action: 'checkin',
    local: 'Escritório Principal',
  }]);
});

test('manual refresh should not submit automatic check-in for a nearby unregistered location after checkout', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness();

  helpers.setLocationPayload({
    matched: false,
    status: 'not_in_known_location',
    label: 'Localização não Cadastrada',
    nearest_workplace_distance_meters: 180,
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.fetchWebState, ['A123']);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('manual refresh should not submit automatic activity after checkout when the location remains checkout zone', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness();

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Zona de CheckOut',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('manual refresh should not start a refresh sequence when the application is locked', async () => {
  const { helpers } = createManualRefreshSequenceHarness({
    isApplicationUnlocked: () => false,
  });

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Escritório Principal',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 0);
  assert.deepStrictEqual(snapshot.resolveCurrentLocation, []);
  assert.deepStrictEqual(snapshot.runAutomaticActivitiesIfNeeded, []);
});

test('manual refresh should not submit automatic activity when automatic activities are disabled', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    isAutomaticActivitiesEnabled: () => false,
  });

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Escritório Principal',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.equal(snapshot.resolveCurrentLocation.length, 1);
  assert.deepStrictEqual(snapshot.fetchWebState, []);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('manual refresh should not submit automatic activity when the key is invalid', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    chave: 'A1',
  });

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Escritório Principal',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.equal(snapshot.resolveCurrentLocation.length, 1);
  assert.deepStrictEqual(snapshot.fetchWebState, []);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('manual refresh should not submit automatic activity after checkout when backend reports outside workplace', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness();

  helpers.setLocationPayload({
    matched: false,
    status: 'outside_workplace',
    minimum_checkout_distance_meters: 2500,
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});
