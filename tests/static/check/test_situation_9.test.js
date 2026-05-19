// Unit tests for the Situation 9 helper exported by web-client-state.js.
//
// Situation 9 (docs/descritivos/regras_checkin_checkout_webapp.txt): when
// "Atividades Automáticas" is disabled, the Local dropdown must always be
// available so the user can pick a location manually, regardless of GPS
// permission state or accuracy.
//
// Run: node --test tests/static/check/test_situation_9.test.js
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const helperModulePath = path.join(
  __dirname,
  '..',
  '..',
  '..',
  'sistema',
  'app',
  'static',
  'check',
  'web-client-state.js'
);

const helperModule = require(helperModulePath);
const { shouldOfferManualLocationSelection } = helperModule;

test('shouldOfferManualLocationSelection — auto OFF + GPS granted + accurate → true (Situation 9 core)', () => {
  assert.strictEqual(
    shouldOfferManualLocationSelection({
      automaticActivitiesEnabled: false,
      gpsLocationPermissionGranted: true,
      accuracyTooLowFallbackActive: false,
    }),
    true
  );
});

test('shouldOfferManualLocationSelection — auto OFF + GPS denied → true', () => {
  assert.strictEqual(
    shouldOfferManualLocationSelection({
      automaticActivitiesEnabled: false,
      gpsLocationPermissionGranted: false,
      accuracyTooLowFallbackActive: false,
    }),
    true
  );
});

test('shouldOfferManualLocationSelection — auto ON + GPS granted + accurate → false (legacy auto path)', () => {
  assert.strictEqual(
    shouldOfferManualLocationSelection({
      automaticActivitiesEnabled: true,
      gpsLocationPermissionGranted: true,
      accuracyTooLowFallbackActive: false,
    }),
    false
  );
});

test('shouldOfferManualLocationSelection — auto ON + GPS denied → true (legacy fallback preserved)', () => {
  assert.strictEqual(
    shouldOfferManualLocationSelection({
      automaticActivitiesEnabled: true,
      gpsLocationPermissionGranted: false,
      accuracyTooLowFallbackActive: false,
    }),
    true
  );
});

test('shouldOfferManualLocationSelection — auto ON + GPS granted + accuracy too low → true (legacy accuracy fallback preserved)', () => {
  assert.strictEqual(
    shouldOfferManualLocationSelection({
      automaticActivitiesEnabled: true,
      gpsLocationPermissionGranted: true,
      accuracyTooLowFallbackActive: true,
    }),
    true
  );
});
