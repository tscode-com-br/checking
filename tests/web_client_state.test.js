const test = require('node:test');
const assert = require('node:assert/strict');

const clientState = require('../sistema/app/static/check/web-client-state.js');

test('splitNotificationMessage keeps short messages on one line', () => {
  assert.deepEqual(clientState.splitNotificationMessage('Aplicação atualizada com sucesso.'), {
    primary: 'Aplicação atualizada com sucesso.',
    secondary: '',
  });
});

test('splitNotificationMessage moves long messages to a second line', () => {
  const result = clientState.splitNotificationMessage(
    'Atividades automáticas ativadas. A automação será verificada ao abrir ou retornar ao site.',
    40
  );

  assert.equal(result.primary, 'Atividades automáticas ativadas. A');
  assert.equal(result.secondary, 'automação será verificada ao abrir ou retornar ao site.');
});

test('resolvePersistedUserSettings returns plural settings for the active key', () => {
  const settings = clientState.resolvePersistedUserSettings(
    {
      HR70: { projects: ['P83', 'P82'], activeProject: 'P83', automaticActivitiesEnabled: true },
    },
    'hr70',
    {
      projects: ['P80'],
      activeProject: 'P80',
      automaticActivitiesEnabled: false,
      allowedProjects: ['P80', 'P82', 'P83'],
    }
  );

  assert.deepEqual(settings, {
    projects: ['P83', 'P82'],
    activeProject: 'P83',
    automaticActivitiesEnabled: true,
  });
});

test('resolvePersistedUserSettings migrates legacy project and falls back to allowed memberships when needed', () => {
  const settings = clientState.resolvePersistedUserSettings(
    {
      HR71: { project: 'LEGACY', automaticActivitiesEnabled: false },
    },
    'hr71',
    {
      projects: ['P95', 'P97'],
      activeProject: '',
      automaticActivitiesEnabled: false,
      allowedProjects: ['P95', 'P97'],
    }
  );

  assert.deepEqual(settings, {
    projects: ['P95', 'P97'],
    activeProject: 'P95',
    automaticActivitiesEnabled: false,
  });
});

test('resolvePersistedUserSettings preserves legacy project when it is still allowed', () => {
  const settings = clientState.resolvePersistedUserSettings(
    {
      HR72: { project: 'p82', automaticActivitiesEnabled: true },
    },
    'hr72',
    {
      projects: ['P80', 'P82', 'P83'],
      activeProject: 'P80',
      automaticActivitiesEnabled: false,
      allowedProjects: ['P80', 'P82', 'P83'],
    }
  );

  assert.deepEqual(settings, {
    projects: ['P82'],
    activeProject: 'P82',
    automaticActivitiesEnabled: true,
  });
});

test('withPersistedUserSettings stores plural settings by sanitized chave', () => {
  const settingsMap = clientState.withPersistedUserSettings(
    {},
    'hr70',
    { projects: ['p82', 'P83'], activeProject: 'p83', automaticActivitiesEnabled: true },
    {
      projects: ['P80'],
      activeProject: 'P80',
      allowedProjects: ['P80', 'P82', 'P83'],
    }
  );

  assert.deepEqual(settingsMap, {
    HR70: { projects: ['P82', 'P83'], activeProject: 'P83', automaticActivitiesEnabled: true },
  });
});

test('withPersistedUserSettings migrates legacy project values without hardcoded fallbacks', () => {
  const settingsMap = clientState.withPersistedUserSettings(
    {},
    'hr73',
    { project: 'unknown', automaticActivitiesEnabled: false },
    {
      projects: ['P95', 'P97'],
      activeProject: '',
      allowedProjects: ['P95', 'P97'],
    }
  );

  assert.deepEqual(settingsMap, {
    HR73: { projects: ['P95', 'P97'], activeProject: 'P95', automaticActivitiesEnabled: false },
  });
});

test('shouldAttemptSilentLocationLookup only blocks explicit denial', () => {
  assert.equal(clientState.shouldAttemptSilentLocationLookup('granted', false), true);
  assert.equal(clientState.shouldAttemptSilentLocationLookup('prompt', true), true);
  assert.equal(clientState.shouldAttemptSilentLocationLookup(null, true), true);
  assert.equal(clientState.shouldAttemptSilentLocationLookup('prompt', false), true);
  assert.equal(clientState.shouldAttemptSilentLocationLookup(null, false), true);
  assert.equal(clientState.shouldAttemptSilentLocationLookup('denied', true), false);
});

test('resolveAuthenticationPromptMessage reflects password state', () => {
  assert.equal(
    clientState.resolveAuthenticationPromptMessage({ hasPassword: false, authenticated: false }),
    'Digite sua chave e crie uma senha.'
  );
  assert.equal(
    clientState.resolveAuthenticationPromptMessage({ hasPassword: true, authenticated: false }),
    'Digite sua senha para iniciar.'
  );
  assert.equal(
    clientState.resolveAuthenticationPromptMessage({ hasPassword: true, authenticated: true }),
    ''
  );
});

test('isPasswordLengthValid enforces the requested password length policy', () => {
  assert.equal(clientState.isPasswordLengthValid('12'), false);
  assert.equal(clientState.isPasswordLengthValid('123'), true);
  assert.equal(clientState.isPasswordLengthValid('abc@123'), true);
  assert.equal(clientState.isPasswordLengthValid('           '), false);
  assert.equal(clientState.isPasswordLengthValid('12345678901'), false);
});

test('isPasswordVerificationInputValid allows partial typed password attempts', () => {
  assert.equal(clientState.isPasswordVerificationInputValid(''), false);
  assert.equal(clientState.isPasswordVerificationInputValid('1'), true);
  assert.equal(clientState.isPasswordVerificationInputValid('12'), true);
  assert.equal(clientState.isPasswordVerificationInputValid('1234567890'), true);
  assert.equal(clientState.isPasswordVerificationInputValid('12345678901'), false);
});

test('autofillPetrobrasEmailDomain completes domain after @ is typed', () => {
  assert.equal(clientState.autofillPetrobrasEmailDomain('joao'), 'joao');
  assert.equal(clientState.autofillPetrobrasEmailDomain('joao@'), 'joao@petrobras.com.br');
  assert.equal(clientState.autofillPetrobrasEmailDomain('joao@petrobras.com.br'), 'joao@petrobras.com.br');
});

test('hasCurrentDayCheckIn prefers the backend same-day flag and falls back to Singapore calendar comparison', () => {
  assert.equal(
    clientState.hasCurrentDayCheckIn(
      { has_current_day_checkin: true, last_checkin_at: '2026-04-17T23:55:00+08:00' },
      '2026-04-18T00:10:00+08:00'
    ),
    true
  );
  assert.equal(
    clientState.hasCurrentDayCheckIn(
      { has_current_day_checkin: false, last_checkin_at: '2026-04-18T07:05:00+08:00' },
      '2026-04-18T19:30:00+08:00'
    ),
    false
  );
  assert.equal(
    clientState.hasCurrentDayCheckIn(
      { last_checkin_at: '2026-04-18T07:05:00+08:00' },
      '2026-04-18T19:30:00+08:00'
    ),
    true
  );
  assert.equal(
    clientState.hasCurrentDayCheckIn(
      { last_checkin_at: '2026-04-17T23:55:00+08:00' },
      '2026-04-18T00:10:00+08:00'
    ),
    false
  );
});

test('formatTransportVehicleType keeps labels in Portuguese for the transport confirmation view', () => {
  assert.equal(clientState.formatTransportVehicleType('carro'), 'carro');
  assert.equal(clientState.formatTransportVehicleType('onibus'), 'ônibus');
});

test('resolvePersistedPassword returns the saved password for the active key', () => {
  assert.equal(
    clientState.resolvePersistedPassword({ HR70: 'abc123' }, 'hr70'),
    'abc123'
  );
  assert.equal(
    clientState.resolvePersistedPassword({ HR70: '12' }, 'hr70'),
    ''
  );
});

test('withPersistedPassword stores and removes passwords by sanitized chave', () => {
  assert.deepEqual(
    clientState.withPersistedPassword({}, 'hr70', 'abc123'),
    { HR70: 'abc123' }
  );
  assert.deepEqual(
    clientState.withPersistedPassword({ HR70: 'abc123' }, 'hr70', ''),
    {}
  );
});