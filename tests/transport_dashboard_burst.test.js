const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const transportScript = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/transport/app.js'),
  'utf8'
);

test('transport dashboard coalesces in-flight dashboard loads into one trailing refresh', () => {
  assert.match(
    transportScript,
    /dashboardLoadPromise:\s*null,[\s\S]*queuedDashboardLoad:\s*null,/
  );
  assert.match(
    transportScript,
    /function queueDashboardLoad\(selectedDate, options\) \{[\s\S]*state\.queuedDashboardLoad = \{[\s\S]*selectedDate: normalizedDate,[\s\S]*options: Object\.assign\(/ 
  );
  assert.match(
    transportScript,
    /function loadDashboard\(selectedDate, options\) \{[\s\S]*const normalizedDate = startOfLocalDay\(selectedDate \|\| dateStore\.getValue\(\)\);[\s\S]*if \(state\.dashboardLoadPromise\) \{[\s\S]*queueDashboardLoad\(normalizedDate, loadOptions\);[\s\S]*return state\.dashboardLoadPromise;[\s\S]*\}/
  );
  assert.match(
    transportScript,
    /state\.dashboardLoadPromise = requestJson\([\s\S]*\.finally\(function \(\) \{[\s\S]*const queuedLoad = state\.queuedDashboardLoad;[\s\S]*state\.dashboardLoadPromise = null;[\s\S]*if \(queuedLoad && state\.isAuthenticated\) \{[\s\S]*return loadDashboard\(queuedLoad\.selectedDate, queuedLoad\.options\);[\s\S]*\}[\s\S]*state\.isLoading = false;/
  );
});

test('transport auth verification now debounces longer and avoids clearing a valid session on partial input', () => {
  assert.match(transportScript, /const TRANSPORT_AUTH_VERIFY_DELAY_MS = 650;/);
  assert.match(
    transportScript,
    /authVerifySignature:\s*"",[\s\S]*lastVerifiedAuthSignature:\s*"",/
  );
  assert.match(
    transportScript,
    /if \(!signature\) \{[\s\S]*state\.authVerifySignature = "";[\s\S]*if \(!state\.isAuthenticated && !state\.sessionBootstrapPending\) \{[\s\S]*setAuthenticationState\(false, null, \{\}\);/
  );
  assert.match(
    transportScript,
    /if \(state\.isAuthenticated && signature === state\.lastVerifiedAuthSignature\) \{[\s\S]*state\.authVerifySignature = signature;[\s\S]*return;[\s\S]*\}[\s\S]*if \(verifySource === "input" && state\.isAuthenticated && !shouldVerifyImmediately\) \{[\s\S]*return;[\s\S]*\}[\s\S]*if \(signature === previousSignature && !shouldVerifyImmediately\) \{[\s\S]*return;/
  );
  assert.match(
    transportScript,
    /function verifyTransportCredentials\(requestToken, signature\) \{[\s\S]*const credentials = readTransportAuthCredentials\(\);[\s\S]*const currentSignature = signature \|\| credentials\.signature;[\s\S]*const authVerifyRequestController = typeof globalScope\.AbortController === "function"[\s\S]*if \(error && error\.name === "AbortError"\) \{[\s\S]*return null;/
  );
});

test('transport pauses background refreshes and reconnects realtime with explicit backoff', () => {
  assert.match(
    transportScript,
    /realtimeReconnectTimer:\s*null,[\s\S]*realtimeReconnectAttempt:\s*0,[\s\S]*realtimeReconnectPending:\s*false,[\s\S]*deferredDashboardLoad:\s*null,/
  );
  assert.match(
    transportScript,
    /function scheduleRealtimeReconnect\(\) \{[\s\S]*state\.realtimeReconnectPending = true;[\s\S]*if \(isTransportPageHidden\(\)\) \{[\s\S]*return;[\s\S]*\}[\s\S]*const delayMs = Math\.min\([\s\S]*TRANSPORT_REALTIME_RECONNECT_MAX_MS,[\s\S]*TRANSPORT_REALTIME_RECONNECT_BASE_MS \* Math\.pow\(2, Math\.max\(0, state\.realtimeReconnectAttempt\)\)/
  );
  assert.match(
    transportScript,
    /function handlePageVisibilityChange\(\) \{[\s\S]*if \(isTransportPageHidden\(\)\) \{[\s\S]*clearPendingAiRoutePolling\(\);[\s\S]*closeRealtimeEventStream\(\);[\s\S]*state\.realtimeReconnectPending = state\.isAuthenticated;[\s\S]*return;[\s\S]*\}[\s\S]*void flushDeferredDashboardLoad\(\);[\s\S]*queueAiRouteRunPoll\(state\.aiRouteRunKey, 0\);/
  );
});

test('transport bootstrap preserves typed auth drafts and defers verify until session bootstrap completes', () => {
  assert.match(transportScript, /sessionBootstrapPending:\s*true,/);
  assert.match(
    transportScript,
    /function bootstrapTransportSession\(\) \{[\s\S]*const initialAuthInputSnapshot = getTransportAuthInputSnapshot\(\);[\s\S]*state\.sessionBootstrapPending = true;[\s\S]*const authDraftChanged = getTransportAuthInputSnapshot\(\) !== initialAuthInputSnapshot;[\s\S]*fillKey: !authDraftChanged[\s\S]*resetInputs: !authDraftChanged[\s\S]*\.finally\(function \(\) \{[\s\S]*state\.sessionBootstrapPending = false;[\s\S]*scheduleTransportVerification\(\{ source: "bootstrap" \}\);/
  );
  assert.match(
    transportScript,
    /if \(state\.sessionBootstrapPending && verifySource !== "bootstrap"\) \{[\s\S]*return;[\s\S]*\}[\s\S]*if \(verifySource === "input" && state\.isAuthenticated && !shouldVerifyImmediately\) \{[\s\S]*return;/
  );
});

test('transport dashboard and AI polling pause while the tab is hidden', () => {
  assert.match(
    transportScript,
    /function isTransportPageHidden\(\) \{[\s\S]*globalScope\.document[\s\S]*visibilityState === "hidden"/
  );
  assert.match(
    transportScript,
    /function requestDashboardRefresh\(options\) \{[\s\S]*if \(isTransportPageHidden\(\)\) \{[\s\S]*queueDashboardLoad\(dateStore\.getValue\(\), Object\.assign\(\{ announce: false \}, refreshOptions\)\);[\s\S]*return;[\s\S]*\}/
  );
  assert.match(
    transportScript,
    /function queueAiRouteRunPoll\(runKey, delayMs\) \{[\s\S]*if \(isTransportPageHidden\(\)\) \{[\s\S]*syncAiAgentSettingsControls\(\{ preserveInputs: true \}\);[\s\S]*return;[\s\S]*\}/
  );
  assert.match(
    transportScript,
    /document\.addEventListener\("visibilitychange", function \(\) \{[\s\S]*if \(isTransportPageHidden\(\)\) \{[\s\S]*clearPendingRealtimeRefresh\(\);[\s\S]*clearPendingAiRoutePolling\(\);[\s\S]*return;[\s\S]*\}[\s\S]*requestDashboardRefresh\(\{ announce: false \}\);/
  );
});

test('transport AI polling backs off explicitly and resets on immediate re-entry or terminal states', () => {
  assert.match(
    transportScript,
    /const TRANSPORT_AI_ROUTE_POLL_INTERVAL_MS = 1200;[\s\S]*const TRANSPORT_AI_ROUTE_POLL_MAX_MS = 10000;/
  );
  assert.match(
    transportScript,
    /aiRoutePollingTimer:\s*null,[\s\S]*aiRoutePollingAttempt:\s*0,[\s\S]*aiRouteRequestPending:\s*false,/
  );
  assert.match(
    transportScript,
    /function getNextAiRoutePollDelay\(\) \{[\s\S]*const delayMs = Math\.min\([\s\S]*TRANSPORT_AI_ROUTE_POLL_MAX_MS,[\s\S]*TRANSPORT_AI_ROUTE_POLL_INTERVAL_MS \* Math\.pow\(2, Math\.max\(0, state\.aiRoutePollingAttempt\)\)[\s\S]*state\.aiRoutePollingAttempt \+= 1;[\s\S]*return delayMs;/
  );
  assert.match(
    transportScript,
    /function queueAiRouteRunPoll\(runKey, delayMs\) \{[\s\S]*const normalizedDelayMs = Math\.max\(0, Number\(delayMs\) \|\| 0\);[\s\S]*if \(normalizedDelayMs <= 0\) \{[\s\S]*resetAiRoutePollingBackoff\(\);[\s\S]*\}[\s\S]*state\.aiRoutePollingTimer = globalScope\.setTimeout/
  );
  assert.match(
    transportScript,
    /if \(hasRenderableTransportAiReview\(response\)\) \{[\s\S]*resetAiRoutePollingBackoff\(\);[\s\S]*requestDashboardRefresh\(\{ announce: false \}\);/
  );
  assert.match(
    transportScript,
    /if \(shouldContinuePollingAiRouteRun\(response\)\) \{[\s\S]*queueAiRouteRunPoll\(state\.aiRouteRunKey, getNextAiRoutePollDelay\(\)\);[\s\S]*\} else \{[\s\S]*resetAiRoutePollingBackoff\(\);[\s\S]*\}/
  );
});
