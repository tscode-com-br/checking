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

test('mixed zone drift from prior non-mixed states is suppressed within the interval and reopens after it', () => {
  // temp006 (Situação 8 revisada): ao detectar 'Zona Mista', a alternância automática só dispara quando a
  // ÚLTIMA atividade registrada (qualquer local/ação) está FORA do intervalo. Antes, disparava imediatamente
  // quando a última atividade não tinha sido na própria Zona Mista — o que gerava check-out/in espúrio por
  // drift de GPS entre a Zona Mista e localizações adjacentes (ex.: U4T4: check-in no 'Escritório Principal'
  // e, ~25 s depois, check-out espúrio na 'Zona Mista').
  const cases = [
    {
      name: 'regular checked-in location (drift → check-out espúrio)',
      remoteState: {
        current_action: 'checkin',
        current_local: 'Escritório Principal',
        last_checkin_at: '2026-04-16T09:00:00',
        last_checkout_at: '2026-04-16T08:00:00',
      },
    },
    {
      name: 'regular checked-out location (drift → check-in espúrio)',
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
    // última atividade às 09:00; referência 09:10 (10 min < 20) → suprime a alternância
    assert.equal(
      automation.shouldAttemptAutomaticLocationEvent(
        { resolved_local: 'Zona Mista' },
        remoteState,
        { mixedZoneIntervalMinutes: 20, referenceTime: '2026-04-16T09:10:00' }
      ),
      false,
      `${name} — dentro do intervalo`
    );
    // referência 09:30 (30 min >= 20) → a alternância automática volta a ser permitida
    assert.equal(
      automation.shouldAttemptAutomaticLocationEvent(
        { resolved_local: 'Zona Mista' },
        remoteState,
        { mixedZoneIntervalMinutes: 20, referenceTime: '2026-04-16T09:30:00' }
      ),
      true,
      `${name} — fora do intervalo`
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

test('mixed zone drift cooldown does not block immediate exits/entries on OTHER locations (Situação 8 exceptions preserved)', () => {
  // temp006: o gate de cooldown só afeta leituras que resolvem para 'Zona Mista'. Saídas/entradas genuínas
  // resolvem para OUTRO resolved_local e seguem pelos ramos não-Zona-Mista (inalterados), mesmo dentro do
  // intervalo. Isso preserva as exceções imediatas da Situação 8 (linhas 85–86).
  const afterRecentCheckinElsewhere = {
    current_action: 'checkin',
    current_local: 'Escritório Principal',
    last_checkin_at: '2026-04-16T09:00:00',
    last_checkout_at: '2026-04-16T08:00:00',
  };
  // saída por 'Zona de CheckOut' dentro do intervalo → check-out imediato (ramo da zona de check-out)
  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Zona de CheckOut' },
      afterRecentCheckinElsewhere,
      { mixedZoneIntervalMinutes: 20, referenceTime: '2026-04-16T09:10:00' }
    ),
    true
  );

  const afterRecentCheckoutElsewhere = {
    current_action: 'checkout',
    current_local: 'Zona de CheckOut',
    last_checkin_at: '2026-04-16T08:00:00',
    last_checkout_at: '2026-04-16T09:00:00',
  };
  // re-entrada por outra área cadastrada dentro do intervalo → check-in imediato (ramo de área cadastrada)
  assert.equal(
    automation.shouldAttemptAutomaticLocationEvent(
      { resolved_local: 'Escritório Principal' },
      afterRecentCheckoutElsewhere,
      { mixedZoneIntervalMinutes: 20, referenceTime: '2026-04-16T09:10:00' }
    ),
    true
  );
});

test('isMixedZoneCooldownActiveForLastActivity tracks the last recorded activity regardless of location', () => {
  const stateCheckinElsewhere = {
    current_action: 'checkin',
    current_local: 'Escritório Principal',
    last_checkin_at: '2026-04-16T09:00:00',
    last_checkout_at: '2026-04-16T08:00:00',
  };
  // última atividade 09:00; 09:10 (10 < 20) ativo; 09:20 (20 não < 20) inativo
  assert.equal(automation.isMixedZoneCooldownActiveForLastActivity(stateCheckinElsewhere, 20, '2026-04-16T09:10:00'), true);
  assert.equal(automation.isMixedZoneCooldownActiveForLastActivity(stateCheckinElsewhere, 20, '2026-04-16T09:20:00'), false);
  // intervalo inválido (< 1) → sem cooldown
  assert.equal(automation.isMixedZoneCooldownActiveForLastActivity(stateCheckinElsewhere, 0, '2026-04-16T09:05:00'), false);
  // sem atividade registrada → sem cooldown
  assert.equal(automation.isMixedZoneCooldownActiveForLastActivity({}, 20, '2026-04-16T09:05:00'), false);
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

test('Situação 3: automatic check-in runs after checkout even when the registered location is unchanged', () => {
  // Regressão: usuário em check-out cujo check-out foi registrado no mesmo local
  // cadastrado em que ele se encontra agora (ex.: check-out manual no Escritório
  // Principal). A Situação 3 exige o check-in independentemente de o local ter mudado.
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
    true
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

test('Situações 4 e 6: automatic check-in repeats for the same current location after a prior check-in', () => {
  // Descritivo atualizado: ao abrir/recarregar/foreground (Situação 4) ou pressionar
  // 'Atualizar' (Situação 6) com a última atividade = check-in, um NOVO check-in deve ser
  // realizado mesmo quando o usuário continua no MESMO local do último check-in.
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
    true
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
