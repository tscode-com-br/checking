const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const checkCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/styles.css'),
  'utf8'
);

test('check page keeps the request-registration trigger hidden and exposes the simplified signup widget', () => {
  const checkHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/check/index.html'),
    'utf8'
  );

  assert.match(checkHtml, /id="requestRegistrationButton"[^>]*hidden[^>]*aria-hidden="true"/);
  assert.match(checkHtml, />Solicitar cadastro</);
  assert.match(checkHtml, /id="passwordActionButton"[\s\S]*>Senha</);
  assert.match(checkHtml, /id="registrationDialogTitle">Solicitar Cadastro</);
  assert.match(checkHtml, /id="registrationProjectSelect"/);
  assert.match(checkHtml, /id="registrationEmailInput"[\s\S]*placeholder="Opcional"/);
  assert.match(checkHtml, /id="registrationDialogSubmitButton"[\s\S]*>Enviar</);
  assert.match(checkHtml, /id="passwordDialogOldPasswordField"/);
  assert.doesNotMatch(checkHtml, /id="registrationAddressInput"/);
  assert.doesNotMatch(checkHtml, /id="registrationZipInput"/);
});

test('check signup controller routes Chave? to self-registration and Senha? to the reduced password widget', () => {
  const checkScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/check/app.js'),
    'utf8'
  );

  assert.match(checkScript, /const requestRegistrationButton = document\.getElementById\('requestRegistrationButton'\);/);
  assert.match(checkScript, /requestRegistrationButton\.addEventListener\('click', \(\) => \{[\s\S]*openRegistrationDialog\(\);[\s\S]*\}\);/);
  assert.match(checkScript, /return 'Chave\?';/);
  assert.match(checkScript, /return 'Senha\?';/);
  assert.match(checkScript, /return 'Senha';/);
  assert.match(checkScript, /if \(userSelfRegistrationInProgress\) \{[\s\S]*return 'Aguarde';[\s\S]*\}/);
  assert.match(checkScript, /passwordDialogTitle\.textContent = isRegisterMode \? 'Cadastrar Senha' : 'Alterar Senha';/);
  assert.match(checkScript, /passwordDialogOldPasswordField\.classList\.toggle\('is-registration-placeholder', isRegisterMode\);/);
  assert.match(checkScript, /oldPasswordInput\.hidden = isRegisterMode;/);
  assert.match(checkCss, /#passwordDialogOldPasswordField\.is-registration-placeholder span\s*\{[\s\S]*text-decoration:\s*line-through;/);
  assert.match(checkScript, /if \(authState\.statusResolved && authState\.found && !authState\.hasPassword\) \{[\s\S]*openPasswordDialog\(\);[\s\S]*\}/);
  assert.match(checkScript, /registerPasswordMode[\s\S]*\?[\s\S]*projeto: projectSelect\.value,[\s\S]*senha: newPassword,[\s\S]*:[\s\S]*senha_antiga: oldPassword,[\s\S]*nova_senha: newPassword,/);
  assert.match(checkScript, /body: JSON\.stringify\(\{[\s\S]*chave: normalizedChave,[\s\S]*nome,[\s\S]*projeto,[\s\S]*email: email \|\| null,[\s\S]*senha: password,[\s\S]*confirmar_senha: confirmPassword,[\s\S]*\}\)/);
  assert.doesNotMatch(checkScript, /body: JSON\.stringify\(\{[\s\S]*end_rua:/);
  assert.doesNotMatch(checkScript, /body: JSON\.stringify\(\{[\s\S]*zip:/);
  assert.match(checkScript, /Cadastro concluído com sucesso\./);
});
