const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const checkApp = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/app.js'),
  'utf8'
);

const checkCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/styles.css'),
  'utf8'
);

const checkHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/index.html'),
  'utf8'
);

test('transport routine request builder uses the shortened Solicitar label', () => {
  assert.match(checkHtml, /id="transportRequestBuilderSubmitButton"[\s\S]*>Solicitar</);
  assert.match(checkApp, /transportRequestInProgress \? 'Solicitando\.{3}' : 'Solicitar'/);
});

test('transport weekday selector is compact enough for mobile viewport height constraints', () => {
  assert.match(
    checkCss,
    /\.transport-request-builder,\s*\.transport-request-builder-form,\s*\.transport-request-builder-group \{[\s\S]*gap:\s*8px;/
  );
  assert.match(
    checkCss,
    /\.transport-request-weekday-options \{[\s\S]*gap:\s*7px;/
  );
  assert.match(
    checkCss,
    /\.transport-request-day-chip \{[\s\S]*min-height:\s*42px;[\s\S]*padding:\s*9px 12px;/
  );
});

test('password register action shows Aguarde, uses a pending style, and locks other buttons', () => {
  assert.match(checkApp, /if \(passwordRegisterInProgress\) \{[\s\S]*return 'Aguarde';[\s\S]*\}/);
  assert.match(checkApp, /control\.classList\.toggle\('is-pending', passwordRegisterInProgress\);/);
  assert.match(checkApp, /const transportButtonLocked = dialogOpen \|\| lockActive \|\| submitInProgress \|\| authBusy \|\| passwordLoginInProgress;/);
  assert.match(checkCss, /\.auth-action-button\.is-pending \{[\s\S]*background:\s*#e2e8f0;[\s\S]*color:\s*#475569;/);
});

test('auth fields restore cleared chave and senha when the user leaves without typing', () => {
  assert.match(checkApp, /function restorePendingAuthFieldValuesIfNeeded\(\)/);
  assert.match(checkApp, /rememberPendingAuthFieldRestoreState\('chave'\);/);
  assert.match(checkApp, /rememberPendingAuthFieldRestoreState\('password'\);/);
  assert.match(checkApp, /document\.addEventListener\('pointerdown', restorePendingAuthFieldValuesOnExternalFocus, true\);/);
  assert.match(checkApp, /document\.addEventListener\('focusin', restorePendingAuthFieldValuesOnExternalFocus, true\);/);
});

test('transport widget subscribes to realtime updates while the transport screen is open', () => {
  assert.match(checkHtml, /data-transport-stream-endpoint="\/api\/web\/transport\/stream"/);
  assert.match(checkApp, /const transportStreamEndpoint = form\.dataset\.transportStreamEndpoint \|\| '\/api\/web\/transport\/stream';/);
  assert.match(checkApp, /function startTransportRealtimeUpdates\(\)/);
  assert.match(checkApp, /new window\.EventSource\(/);
  assert.match(checkApp, /function stopTransportRealtimeUpdates\(\)/);
  assert.match(checkApp, /startTransportRealtimeUpdates\(\);[\s\S]*void loadTransportState\(\);/);
  assert.match(checkApp, /stopTransportRealtimeUpdates\(\);[\s\S]*clearTransportAutoRefresh\(\);/);
});