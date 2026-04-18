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

test('resolvePasswordActionLabel switches between register and change', () => {
  assert.equal(clientState.resolvePasswordActionLabel(false), 'Registrar');
  assert.equal(clientState.resolvePasswordActionLabel(true), 'Alterar');
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