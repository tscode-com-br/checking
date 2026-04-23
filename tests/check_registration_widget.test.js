const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('check page exposes the request-registration button and the simplified signup widget', () => {
  const checkHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/check/index.html'),
    'utf8'
  );

  assert.match(checkHtml, /id="requestRegistrationButton"/);
  assert.match(checkHtml, />Solicitar cadastro</);
  assert.match(checkHtml, /id="registrationDialogTitle">Solicitar Cadastro</);
  assert.match(checkHtml, /id="registrationProjectSelect"/);
  assert.match(checkHtml, /id="registrationEmailInput"[\s\S]*placeholder="Opcional"/);
  assert.match(checkHtml, /id="registrationDialogSubmitButton"[\s\S]*>Enviar</);
  assert.doesNotMatch(checkHtml, /id="registrationAddressInput"/);
  assert.doesNotMatch(checkHtml, /id="registrationZipInput"/);
});

test('check signup controller opens the widget from the key area and submits the reduced payload', () => {
  const checkScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/check/app.js'),
    'utf8'
  );

  assert.match(checkScript, /const requestRegistrationButton = document\.getElementById\('requestRegistrationButton'\);/);
  assert.match(checkScript, /requestRegistrationButton\.addEventListener\('click', \(\) => \{[\s\S]*openRegistrationDialog\(\);[\s\S]*\}\);/);
  assert.match(checkScript, /body: JSON\.stringify\(\{[\s\S]*chave: normalizedChave,[\s\S]*nome,[\s\S]*projeto,[\s\S]*email: email \|\| null,[\s\S]*senha: password,[\s\S]*confirmar_senha: confirmPassword,[\s\S]*\}\)/);
  assert.doesNotMatch(checkScript, /fetch\(authUserRegisterEndpoint,[\s\S]*body: JSON\.stringify\(\{[\s\S]*end_rua:/);
  assert.doesNotMatch(checkScript, /fetch\(authUserRegisterEndpoint,[\s\S]*body: JSON\.stringify\(\{[\s\S]*zip:/);
  assert.match(checkScript, /Cadastro enviado\. Aguarde aprovação para acessar o Transport\./);
});
