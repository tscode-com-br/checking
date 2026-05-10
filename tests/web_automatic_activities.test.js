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

test('automatic check-in location resolves only from an operational resolved_local', () => {
  assert.equal(
    automation.resolveAutomaticCheckInLocation({
      resolved_local: 'Escritório Principal',
      label: 'Localização não Cadastrada',
    }),
    'Escritório Principal'
  );
  assert.equal(
    automation.resolveAutomaticCheckInLocation({
      matched: false,
      status: 'not_in_known_location',
      label: 'Localização não Cadastrada',
    }),
    null
  );
  assert.equal(
    automation.resolveAutomaticCheckInLocation({
      matched: false,
      status: 'accuracy_too_low',
      label: 'Precisão insuficiente',
    }),
    null
  );
  assert.equal(automation.resolveAutomaticCheckInLocation(null), null);
});

test('automatic check-in location guard rejects placeholder-only values', () => {
  assert.equal(
    automation.isOperationalAutomaticCheckInLocation(
      { resolved_local: 'Escritório Principal' },
      'Escritório Principal'
    ),
    true
  );
  assert.equal(
    automation.isOperationalAutomaticCheckInLocation(
      {
        matched: false,
        status: 'not_in_known_location',
        label: 'Localização não Cadastrada',
      },
      automation.AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION
    ),
    false
  );
  assert.equal(
    automation.isOperationalAutomaticCheckInLocation(
      {
        matched: false,
        status: 'accuracy_too_low',
        label: 'Precisão insuficiente',
      },
      'Precisão insuficiente'
    ),
    false
  );
});

test('mixed zone helper recognizes normalized mixed zone names', () => {
  assert.equal(automation.isMixedZoneLocationName('Zona Mista'), true);
  assert.equal(automation.isMixedZoneLocationName('  zona   mista '), true);
  assert.equal(automation.isMixedZoneLocationName('Zona de CheckOut'), false);
});

test('mixed zone helper resolves the latest relevant mixed zone activity from current state and timestamps', () => {
  const activity = automation.resolveLastRelevantMixedZoneActivity({
    current_action: 'checkout',
    current_local: 'Zona Mista',
    last_checkin_at: '2026-04-16T08:00:00',
    last_checkout_at: '2026-04-16T09:00:00',
  });

  assert.deepStrictEqual(activity, {
    action: 'checkout',
    local: 'Zona Mista',
    timestamp: new Date('2026-04-16T09:00:00'),
  });
  assert.equal(
    automation.resolveLastRelevantMixedZoneActivity({
      current_action: 'checkout',
      current_local: 'Escritório Principal',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    }),
    null
  );
});

test('mixed zone helper identifies when the latest relevant activity happened in Zona Mista', () => {
  assert.equal(
    automation.isLastRelevantActivityInMixedZone({
      current_action: 'checkin',
      current_local: 'Zona Mista',
      last_checkin_at: '2026-04-16T09:00:00',
      last_checkout_at: '2026-04-16T08:00:00',
    }),
    true
  );
  assert.equal(
    automation.isLastRelevantActivityInMixedZone({
      current_action: 'checkin',
      current_local: 'Escritório Principal',
      last_checkin_at: '2026-04-16T09:00:00',
      last_checkout_at: '2026-04-16T08:00:00',
    }),
    false
  );
});

test('mixed zone helper reports cooldown activity only while the configured interval is still open', () => {
  const state = {
    current_action: 'checkout',
    current_local: 'Zona Mista',
    last_checkin_at: '2026-04-16T08:00:00',
    last_checkout_at: '2026-04-16T09:00:00',
  };

  assert.equal(
    automation.isMixedZoneCooldownActive(state, 20, '2026-04-16T09:10:00'),
    true
  );
  assert.equal(
    automation.isMixedZoneCooldownActive(state, 20, '2026-04-16T09:20:00'),
    false
  );
  assert.equal(
    automation.isMixedZoneCooldownActive(
      {
        current_action: 'checkout',
        current_local: 'Escritório Principal',
        last_checkin_at: '2026-04-16T08:00:00',
        last_checkout_at: '2026-04-16T09:00:00',
      },
      20,
      '2026-04-16T09:10:00'
    ),
    false
  );
  assert.equal(automation.isMixedZoneCooldownActive(state, null, '2026-04-16T09:10:00'), false);
});

test('mixed zone repeated reads stay blocked while the cooldown is active and reopen when it expires', () => {
  const remoteState = {
    current_action: 'checkout',
    current_local: 'Zona Mista',
    last_checkin_at: '2026-04-16T08:00:00',
    last_checkout_at: '2026-04-16T09:00:00',
  };

  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Zona Mista' },
      remoteState,
      { mixedZoneIntervalMinutes: 20, referenceTime: '2026-04-16T09:10:00' }
    ),
    false
  );
  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Zona Mista' },
      remoteState,
      { mixedZoneIntervalMinutes: 20, referenceTime: '2026-04-16T09:20:00' }
    ),
    true
  );
});

test('mixed zone repeated reads also reopen for a prior mixed-zone check-in only after the interval expires', () => {
  const remoteState = {
    current_action: 'checkin',
    current_local: 'Zona Mista',
    last_checkin_at: '2026-04-16T09:00:00',
    last_checkout_at: '2026-04-16T08:00:00',
  };

  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Zona Mista' },
      remoteState,
      { mixedZoneIntervalMinutes: 20, referenceTime: '2026-04-16T09:10:00' }
    ),
    false
  );
  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Zona Mista' },
      remoteState,
      { mixedZoneIntervalMinutes: 20, referenceTime: '2026-04-16T09:20:00' }
    ),
    true
  );
});

test('mixed zone repeated reads stay blocked when the interval is unavailable, preserving the old same-location guard', () => {
  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Zona Mista' },
      {
        current_action: 'checkout',
        current_local: 'Zona Mista',
        last_checkin_at: '2026-04-16T08:00:00',
        last_checkout_at: '2026-04-16T09:00:00',
      },
      { referenceTime: '2026-04-16T09:20:00' }
    ),
    false
  );
});

test('mixed zone initial entry triggers automatic alternation from prior non-mixed states', () => {
  const cases = [
    {
      name: 'regular checked-in location',
      remoteState: {
        current_action: 'checkin',
        current_local: 'Escritório Principal',
        last_checkin_at: '2026-04-16T09:00:00',
        last_checkout_at: '2026-04-16T08:00:00',
      },
    },
    {
      name: 'regular checked-out location',
      remoteState: {
        current_action: 'checkout',
        current_local: 'Escritório Principal',
        last_checkin_at: '2026-04-16T08:00:00',
        last_checkout_at: '2026-04-16T09:00:00',
      },
    },
    {
      name: 'checkout zone',
      remoteState: {
        current_action: 'checkout',
        current_local: 'Zona de CheckOut',
        last_checkin_at: '2026-04-16T08:00:00',
        last_checkout_at: '2026-04-16T09:00:00',
      },
    },
    {
      name: 'outside workplace checkout',
      remoteState: {
        current_action: 'checkout',
        current_local: automation.AUTOMATIC_CHECKOUT_LOCATION,
        last_checkin_at: '2026-04-16T08:00:00',
        last_checkout_at: '2026-04-16T09:00:00',
      },
    },
  ];

  for (const { name, remoteState } of cases) {
    assert.equal(
      automation.shouldAttemptAutomaticLocationEvent(
        { resolved_local: 'Zona Mista' },
        remoteState,
        { mixedZoneIntervalMinutes: 20, referenceTime: '2026-04-16T09:10:00' }
      ),
      true,
      name
    );
  }
});

test('mixed zone exit exceptions keep automatic checkout immediate after a mixed-zone check-in', () => {
  const remoteState = {
    current_action: 'checkin',
    current_local: 'Zona Mista',
    last_checkin_at: '2026-04-16T09:00:00',
    last_checkout_at: '2026-04-16T08:00:00',
  };

  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Zona de CheckOut' },
      remoteState,
      { mixedZoneIntervalMinutes: 20, referenceTime: '2026-04-16T09:10:00' }
    ),
    true
  );
  assert.equal(
    automation.shouldAttemptAutomaticOutOfRangeCheckout(
      { status: 'outside_workplace', minimum_checkout_distance_meters: 2500 },
      remoteState
    ),
    true
  );
});

test('mixed zone exit exceptions keep automatic check-in immediate after a mixed-zone checkout only for known locations', () => {
  const remoteState = {
    current_action: 'checkout',
    current_local: 'Zona Mista',
    last_checkin_at: '2026-04-16T08:00:00',
    last_checkout_at: '2026-04-16T09:00:00',
  };

  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Escritório Principal' },
      remoteState,
      { mixedZoneIntervalMinutes: 20, referenceTime: '2026-04-16T09:10:00' }
    ),
    true
  );
  assert.equal(
    automation.shouldAttemptAutomaticNearbyWorkplaceCheckIn(
      {
        matched: false,
        label: 'Localização não Cadastrada',
        status: 'not_in_known_location',
        nearest_workplace_distance_meters: 180,
      },
      remoteState
    ),
    false
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

test('automatic check-in runs for a known location after checkout when leaving checkout zone', () => {
  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Escritório Principal' },
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

test('automatic nearby-workplace check-in does not run after checkout when leaving checkout zone without a matched location', () => {
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
    false
  );
});

test('automatic nearby-workplace check-in does not run when GPS accuracy is too low after checkout', () => {
  assert.equal(
    automation.shouldAttemptAutomaticNearbyWorkplaceCheckIn(
      {
        matched: false,
        label: 'Precisão insuficiente',
        status: 'accuracy_too_low',
      },
      {
        current_action: 'checkout',
        current_local: 'Zona Mista',
        last_checkin_at: '2026-04-16T08:00:00',
        last_checkout_at: '2026-04-16T09:00:00',
      }
    ),
    false
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

test('automatic check-in updates the recorded location after check-in when moving to another known location', () => {
  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Almoxarifado' },
      {
        current_action: 'checkin',
        current_local: 'Escritório Principal',
        last_checkin_at: '2026-04-16T09:00:00',
        last_checkout_at: '2026-04-16T08:00:00',
      }
    ),
    true
  );
});

test('automatic nearby-workplace check-in does not run while the user is already checked in near the workplace', () => {
  assert.equal(
    automation.shouldAttemptAutomaticNearbyWorkplaceCheckIn(
      {
        matched: false,
        label: 'Localização não Cadastrada',
        status: 'not_in_known_location',
        nearest_workplace_distance_meters: 180,
      },
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

test('automatic out-of-range checkout follows backend outside_workplace status after check-in', () => {
  assert.equal(
    automation.shouldAttemptAutomaticOutOfRangeCheckout(
      { status: 'outside_workplace', minimum_checkout_distance_meters: 1500 },
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
      { status: 'not_in_known_location', nearest_workplace_distance_meters: 2500 },
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
      { status: 'outside_workplace' },
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
