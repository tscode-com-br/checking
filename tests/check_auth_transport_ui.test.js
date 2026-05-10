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
  assert.match(checkApp, /if \(control === transportRequestBuilderSubmitButton\) \{[\s\S]*transportRequestInProgress[\s\S]*transport\.requestBuilder\.submitButton/);
});

test('transport shell shows the new compact option labels with an instruction line above them', () => {
  assert.match(checkHtml, /id="transportOptionInstruction"[\s\S]*>Selecione o tipo de transporte para continuar\.</);
  assert.match(checkHtml, /id="transportRegularButton"[\s\S]*aria-label="Dias Úteis"[\s\S]*Dias\s*<br\s*\/?\s*>\s*Úteis/);
  assert.match(checkHtml, /id="transportWeekendButton"[\s\S]*aria-label="Fim de Semana"[\s\S]*Fim de\s*<br\s*\/?\s*>\s*Semana/);
  assert.match(checkHtml, /id="transportExtraButton"[\s\S]*aria-label="Data Específica"[\s\S]*Data\s*<br\s*\/?\s*>\s*Específica/);
  assert.match(checkApp, /function syncTranslatedRuntimeLabels\(\) \{[\s\S]*transport\.kinds\.regular[\s\S]*transport\.kinds\.weekend[\s\S]*transport\.kinds\.extra/);
});

test('main transport entry button advertises Em Teste in the primary shell', () => {
  assert.match(checkHtml, /id="transportButton"[\s\S]*>\s*<span>Em Teste<\/span>/);
  assert.doesNotMatch(checkHtml, /id="transportButton"[\s\S]*Em breve/);
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

test('password registration keeps the Aguarde state while Settings owns the password-change entry point', () => {
  assert.match(checkApp, /if \(control === settingsButton\) \{[\s\S]*passwordLoginInProgress[\s\S]*\}/);
  assert.match(checkApp, /if \(control === settingsResetPasswordButton\) \{[\s\S]*control\.disabled = !canOpenPasswordChangeFromSettings\(\);[\s\S]*\}/);
  assert.match(checkApp, /settingsResetPasswordButton\.addEventListener\('click', \(\) => \{[\s\S]*closeSettingsDialog\(\{ restoreFocus: false \}\);[\s\S]*openPasswordDialog\(\);[\s\S]*\}\);/);
  assert.match(checkApp, /function maybeAutoOpenAuthenticationAssistanceDialog\(\) \{[\s\S]*lastAutoOpenedAuthenticationAssistanceStateKey = stateKey;[\s\S]*openPasswordDialog\(\);/);
  assert.match(checkApp, /const transportButtonLocked = dialogOpen \|\| lockActive \|\| submitInProgress \|\| authBusy \|\| passwordLoginInProgress;/);
  assert.match(checkCss, /\.settings-trigger-button \{[\s\S]*min-height:\s*var\(--control-height\);/);
  assert.match(checkCss, /\.auth-field\.auth-field-pending input \{[\s\S]*border-color:\s*#f97316;/);
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

test('transport screen no longer renders or wires the old acknowledgement flow', () => {
  assert.doesNotMatch(checkHtml, /data-transport-ack-endpoint=/);
  assert.doesNotMatch(checkHtml, /transportAcknowledgementSection|Confirmo ciência das informações acima\.|CONFIRMAR CIÊNCIA/u);
  assert.doesNotMatch(checkApp, /transportAcknowledgeEndpoint|transportAcknowledgement|acknowledgementChecked|awarenessRequired|awarenessConfirmed/);
});
