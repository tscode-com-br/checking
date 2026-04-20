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

test('transport request history persists local realized and dismissed ids by chave', () => {
  assert.match(checkApp, /checking\.web\.transport\.local-state\.by-chave/);
  assert.match(checkApp, /dismissed_request_ids/);
  assert.match(checkApp, /realized_request_ids/);
  assert.match(checkApp, /function persistTransportRequestLocalState\(chave\)/);
});

test('transport request history normalizes API realized status back to confirmed for local handling', () => {
  assert.match(checkApp, /function normalizeTransportRequestStatusValue\(value\)/);
  assert.match(checkApp, /return normalizedStatus === 'realized' \? 'confirmed' : normalizedStatus;/);
});

test('transport request history only allows dismissing realized or cancelled cards', () => {
  assert.match(
    checkApp,
    /function canDismissTransportRequestItem\(requestItem\) \{[\s\S]*requestItem\.status === 'realized' \|\| requestItem\.status === 'cancelled'[\s\S]*\}/
  );
  assert.match(
    checkApp,
    /!canDismissTransportRequestItem\(findVisibleTransportRequestById\(requestId\) \|\| findTransportRequestById\(requestId\)\)/
  );
});

test('transport request history exposes a local Realizado action after departure', () => {
  assert.match(checkApp, /function canMarkTransportRequestAsRealized\(requestItem\)/);
  assert.match(checkApp, /function markTransportRequestAsRealized\(requestId\)/);
  assert.match(checkApp, /realizedButton\.dataset\.transportRequestRealized = 'true'/);
  assert.match(checkCss, /\.transport-request-card-realized-button/);
});