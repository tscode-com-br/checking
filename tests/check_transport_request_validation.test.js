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

test('transport module centralizes request eligibility and blocks missing address locally', () => {
  assert.match(transportScreen, /function canSubmitTransportRequest\(requestKind, options\)/);
  assert.match(transportScreen, /function getTransportAddressValidationMessage\(\)/);
  assert.match(transportScreen, /return translateTransport\('requestBuilder\.addressRequired'\);/);
  assert.match(transportScreen, /function getTransportRequestServiceDateConflictMessage\(requestKind, payload\)/);
  assert.match(transportScreen, /return translateTransport\('requestBuilder\.conflictByDate', \{ serviceDateLabel \}\);/);
  assert.match(transportScreen, /return \(dateValue\.getDay\(\) \+ 6\) % 7;/);
  assert.match(transportScreen, /if \(requestAvailability\.shouldOpenAddressEditor\) \{[\s\S]*openTransportAddressEditor\(\);[\s\S]*\}/);
  assert.match(transportScreen, /transportRequestBuilderSubmitButton\.dataset\.transportSubmitDisabled = submitBlocked \? 'true' : 'false';/);
});

test('transport shell respects module-provided disabled flags for options and submit', () => {
  assert.match(checkApp, /control === transportRegularButton \|\| control === transportWeekendButton \|\| control === transportExtraButton/);
  assert.match(checkApp, /control\.dataset\.transportOptionDisabled === 'true'/);
  assert.match(checkApp, /control\.dataset\.transportSubmitDisabled === 'true'/);
});