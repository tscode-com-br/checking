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

function findMatchingBrace(sourceText, openBraceIndex) {
  let index = openBraceIndex + 1;
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

    if (char === '{') {
      depth += 1;
      continue;
    }

    if (char === '}') {
      depth -= 1;
      if (depth === 0) {
        return index;
      }
    }
  }

  throw new Error('Could not find the matching closing brace in app.js');
}

function extractFunctionSource(sourceText, functionName) {
  const functionToken = `function ${functionName}(`;
  const startIndex = sourceText.indexOf(functionToken);
  assert.notEqual(startIndex, -1, `Expected ${functionName} to be declared in app.js`);

  const openBraceIndex = sourceText.indexOf('{', startIndex);
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
    extractFunctionSource(checkScript, 'shouldAllowManualLocationSelection'),
    extractFunctionSource(checkScript, 'setResolvedLocation'),
    `globalThis.__manualLocationFallbackTestExports = {
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

function toPlainValue(value) {
  return JSON.parse(JSON.stringify(value));
}

test('check controller source parses as valid JavaScript', () => {
  assert.doesNotThrow(() => {
    new vm.Script(checkScript);
  });
});

test('check page keeps Projeto, Local and Informe controls addressable for toggle-driven visibility', () => {
  assert.doesNotMatch(checkHtml, /<title>\s*Checking Mobile Web\s*<\/title>/);
  assert.doesNotMatch(checkHtml, /<span class="header-logo-text">\s*Checking\s*<\/span>/);
  assert.match(checkHtml, /id="automaticActivitiesToggle"/);
  assert.match(checkHtml, /id="projectField"/);
  assert.match(checkHtml, /id="locationSelectField"/);
  assert.match(checkHtml, /id="informeField"/);
  assert.match(checkHtml, /id="submitButton"[\s\S]*>Registrar</);
});

test('check controller hides manual controls during automatic mode and reruns lifecycle updates when GPS is available', () => {
  assert.match(checkScript, /if \(actionInputs\.includes\(control\)\) \{[\s\S]*automaticActivitiesEnabled/);
  assert.match(checkScript, /control === submitButton[\s\S]*automaticActivitiesEnabled/);
  assert.match(checkScript, /const hideProjectField = isAutomaticActivitiesEnabled\(\);/);
  assert.match(checkScript, /const hideLocationField = isAutomaticActivitiesEnabled\(\) \|\| !shouldAllowManualLocationSelection\(\);/);
  assert.match(checkScript, /control === manualLocationSelect[\s\S]*!shouldAllowManualLocationSelection\(\)/);
  assert.match(checkScript, /if \(shouldAllowManualLocationSelection\(\) && !manualLocationSelect\.value\) \{/);
  assert.match(checkScript, /local: shouldAllowManualLocationSelection\(\)[\s\S]*manualLocationSelect\.value[\s\S]*currentLocationMatch \? currentLocationMatch\.resolved_local : null/);
  assert.match(checkScript, /setGpsLocationPermissionGranted\(value\) \{[\s\S]*syncProjectVisibility\(\);/);
  assert.match(checkScript, /if \(gpsLocationPermissionGranted && isApplicationUnlocked\(\)\) \{[\s\S]*runLifecycleUpdateSequence\(\{[\s\S]*ignoreCooldown: true,[\s\S]*triggerSource: 'automatic_activities_disable',[\s\S]*\}\);/);
  assert.match(checkScript, /if \(isAutomaticActivitiesEnabled\(\)\) \{[\s\S]*Desative Atividades Automáticas para registrar manualmente\./);
});

test('check controller re-enables manual local fallback when GPS ends below the required accuracy', () => {
  const { helpers } = createManualLocationFallbackHarness();

  assert.equal(helpers.shouldAllowManualLocationSelection(), true);

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setResolvedLocation({
    matched: true,
    status: 'matched',
    resolved_local: 'Portaria',
  });
  assert.equal(helpers.shouldAllowManualLocationSelection(), false);

  helpers.setResolvedLocation({
    matched: false,
    status: 'accuracy_too_low',
    label: 'Precisao insuficiente',
    resolved_local: null,
  });
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
  assert.equal(helpers.shouldAllowManualLocationSelection(), false);
});

test('check controller exposes opt-in local measurement support for baseline GPS sessions', () => {
  assert.match(checkScript, /const locationMeasurementStorageKey = 'checking\.web\.location\.measurement\.enabled';/);
  assert.match(checkScript, /window\.CheckingWebLocationMeasurement = Object\.freeze\(\{[\s\S]*enable\(\)[\s\S]*getSessions\(\)[\s\S]*getLatestSession\(\)[\s\S]*summarize\(\)[\s\S]*summarizeByTrigger\(\)[\s\S]*buildReport\(metadata\)[\s\S]*printReport\(metadata\)/);
  assert.match(checkScript, /measurementTrigger: 'manual_refresh'/);
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
  assert.match(checkScript, /const locationPayload = await updateLocationForLifecycleSequence\(settings\);/);
  assert.match(checkScript, /const position = await requestCurrentPositionForPlan\(capturePlan, measurementSession, \{[\s\S]*showDetectingState: settings\.showDetectingState,[\s\S]*\}\);/);
});