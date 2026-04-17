const test = require('node:test');
const assert = require('node:assert/strict');

const automation = require('../sistema/app/static/check/automatic-activities.js');

test('resolveLastRecordedAction honors timestamps and current action fallback', () => {
  assert.equal(automation.resolveLastRecordedAction({ current_action: 'checkout' }), 'checkout');
  assert.equal(
    automation.resolveLastRecordedAction({
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
      current_action: 'checkin',
    }),
    'checkout'
  );
  assert.equal(
    automation.resolveLastRecordedAction({
      last_checkin_at: '2026-04-16T09:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
      current_action: 'checkin',
    }),
    'checkin'
  );
});

test('automatic check-in runs for a regular monitored location after checkout', () => {
  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Escritório Principal' },
      {
        current_action: 'checkout',
        current_local: null,
        last_checkin_at: '2026-04-16T08:00:00',
        last_checkout_at: '2026-04-16T09:00:00',
      }
    ),
    true
  );
});

test('automatic check-in after checkout requires a location change when current location is known', () => {
  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Escritório Principal' },
      {
        current_action: 'checkout',
        current_local: 'Escritório Principal',
        last_checkin_at: '2026-04-16T08:00:00',
        last_checkout_at: '2026-04-16T09:00:00',
      }
    ),
    false
  );
});

test('automatic nearby-workplace check-in runs after checkout when no location is registered', () => {
  assert.equal(
    automation.shouldAttemptAutomaticNearbyWorkplaceCheckIn(
      {
        matched: false,
        label: 'Localização não Cadastrada',
        status: 'not_in_known_location',
        nearest_workplace_distance_meters: 180,
      },
      {
        current_action: 'checkout',
        current_local: 'Zona de CheckOut',
        last_checkin_at: '2026-04-16T08:00:00',
        last_checkout_at: '2026-04-16T09:00:00',
      }
    ),
    true
  );
});

test('automatic nearby-workplace check-in does not run without location change', () => {
  assert.equal(
    automation.shouldAttemptAutomaticNearbyWorkplaceCheckIn(
      {
        matched: false,
        label: 'Localização não Cadastrada',
        status: 'not_in_known_location',
        nearest_workplace_distance_meters: 180,
      },
      {
        current_action: 'checkout',
        current_local: 'Localização não Cadastrada',
        last_checkin_at: '2026-04-16T08:00:00',
        last_checkout_at: '2026-04-16T09:00:00',
      }
    ),
    false
  );
});

test('automatic check-in does not repeat for the same current location', () => {
  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Escritório Principal' },
      {
        current_action: 'checkin',
        current_local: 'Escritório Principal',
        last_checkin_at: '2026-04-16T09:00:00',
        last_checkout_at: '2026-04-16T08:00:00',
      }
    ),
    false
  );
});

test('automatic checkout in checkout zone requires last action check-in', () => {
  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Zona de CheckOut' },
      {
        current_action: 'checkin',
        current_local: 'Escritório Principal',
        last_checkin_at: '2026-04-16T09:00:00',
        last_checkout_at: '2026-04-16T08:00:00',
      }
    ),
    true
  );
  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Zona de CheckOut' },
      {
        current_action: 'checkout',
        current_local: 'Escritório Principal',
        last_checkin_at: '2026-04-16T08:00:00',
        last_checkout_at: '2026-04-16T09:00:00',
      }
    ),
    false
  );
});

test('automatic out-of-range checkout only runs above 2 km after check-in', () => {
  assert.equal(
    automation.shouldAttemptAutomaticOutOfRangeCheckout(
      { nearest_workplace_distance_meters: 2001 },
      {
        current_action: 'checkin',
        current_local: 'P80',
        last_checkin_at: '2026-04-16T09:00:00',
        last_checkout_at: '2026-04-16T08:00:00',
      }
    ),
    true
  );
  assert.equal(
    automation.shouldAttemptAutomaticOutOfRangeCheckout(
      { nearest_workplace_distance_meters: 2000 },
      {
        current_action: 'checkin',
        current_local: 'P80',
        last_checkin_at: '2026-04-16T09:00:00',
        last_checkout_at: '2026-04-16T08:00:00',
      }
    ),
    false
  );
  assert.equal(
    automation.shouldAttemptAutomaticOutOfRangeCheckout(
      { nearest_workplace_distance_meters: 2500 },
      {
        current_action: 'checkout',
        current_local: 'P80',
        last_checkin_at: '2026-04-16T08:00:00',
        last_checkout_at: '2026-04-16T09:00:00',
      }
    ),
    false
  );
});