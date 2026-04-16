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

test('resolvePersistedUserSettings returns settings for the active key', () => {
  const settings = clientState.resolvePersistedUserSettings(
    {
      HR70: { project: 'P83', automaticActivitiesEnabled: true },
    },
    'hr70',
    {
      project: 'P80',
      automaticActivitiesEnabled: false,
      allowedProjects: ['P80', 'P82', 'P83'],
    }
  );

  assert.deepEqual(settings, {
    project: 'P83',
    automaticActivitiesEnabled: true,
  });
});

test('withPersistedUserSettings stores settings by sanitized chave', () => {
  const settingsMap = clientState.withPersistedUserSettings(
    {},
    'hr70',
    { project: 'p82', automaticActivitiesEnabled: true },
    {
      project: 'P80',
      allowedProjects: ['P80', 'P82', 'P83'],
    }
  );

  assert.deepEqual(settingsMap, {
    HR70: { project: 'P82', automaticActivitiesEnabled: true },
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