const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const transportScreen = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/transport-screen.js'),
  'utf8'
);

const checkApp = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/app.js'),
  'utf8'
);

const checkHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/index.html'),
  'utf8'
);

const checkCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/styles.css'),
  'utf8'
);

test('transport request state still persists local realized ids by chave for the fixed projection', () => {
  assert.match(checkApp, /checking\.web\.transport\.local-state\.by-chave/);
  assert.match(transportScreen, /realized_request_ids/);
  assert.match(transportScreen, /function persistTransportRequestLocalState\(chave\)/);
});

test('transport request state still normalizes API realized status back to confirmed for local handling', () => {
  assert.match(transportScreen, /function normalizeTransportRequestStatusValue\(value\)/);
  assert.match(transportScreen, /return normalizedStatus === 'realized' \? 'confirmed' : normalizedStatus;/);
});

test('transport request state still treats inactive requests as cancelled in the webapp UI', () => {
  assert.match(transportScreen, /if \(!isActive && normalizedStatus !== 'realized'\) \{[\s\S]*normalizedStatus = 'cancelled';[\s\S]*\}/);
});

test('transport screen renders only active requests in the main section', () => {
  assert.match(transportScreen, /function getActiveTransportRequests\(\)/);
  assert.match(transportScreen, /activeRequests = getActiveTransportRequests\(\)/);
  assert.match(transportScreen, /function renderTransportRequestSummaries\(\)/);
  assert.match(transportScreen, /translateTransport\('summary\.noActiveRequests'\)/);
});

test('transport screen includes a dedicated history panel with open\/close controls', () => {
  assert.match(checkHtml, /id="transportHistoryOpenButton"/);
  assert.match(checkHtml, /id="transportHistoryPanel"/);
  assert.match(checkHtml, /id="transportHistoryCloseButton"/);
  assert.match(checkHtml, /Solicitações ativas/);
  assert.match(transportScreen, /function renderTransportHistoryPanelList\(\)/);
  assert.match(transportScreen, /function createTransportHistoryCard\(requestItem\)/);
});

test('transport screen keeps action buttons in active request cards and keeps summary card styling', () => {
  assert.doesNotMatch(checkHtml, /id="transportRequestDetailWidget"/);
  assert.match(transportScreen, /realizedButton\.dataset\.transportRequestRealized = 'true'/);
  assert.match(transportScreen, /cancelButton\.dataset\.transportRequestCancel = 'true'/);
  assert.match(checkCss, /\.transport-request-summary-card/);
  assert.match(checkCss, /\.transport-request-summary-action\.is-realized/);
  assert.match(checkCss, /\.transport-request-summary-action\.is-cancel/);
});

test('transport webapp fetches transport state and actions with same-origin credentials', () => {
  assert.match(transportScreen, /fetch\(`\$\{transportStateEndpoint\}\?chave=\$\{encodeURIComponent\(chave\)\}`, \{[\s\S]*credentials: 'same-origin'/);
  assert.match(transportScreen, /async function postTransportPayload\(url, payload\) \{[\s\S]*credentials: 'same-origin'/);
});
