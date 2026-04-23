const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const adminHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/index.html'),
  'utf8'
);

const adminCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/styles.css'),
  'utf8'
);

const adminJs = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/app.js'),
  'utf8'
);

test('admin login page exposes the new utility buttons and change-password modal', () => {
  assert.match(adminHtml, /id="changePasswordButton"[\s\S]*>Alterar Senha</);
  assert.match(adminHtml, /id="requestAdminButton"[\s\S]*>Solicitar Administração</);
  assert.match(adminHtml, />Administradores</);
  assert.doesNotMatch(adminHtml, />Administradores \(admin\)</);
  assert.match(adminHtml, /id="changePasswordModal"/);
  assert.match(adminHtml, /id="requestAdminModal"/);
  assert.match(adminHtml, /id="requestAdminRegistrationModal"/);
  assert.match(adminHtml, /id="requestAdminRegistrationProjeto"/);
  assert.match(adminHtml, /id="changePasswordCurrent"/);
  assert.match(adminHtml, /id="changePasswordNew"[\s\S]*maxlength="10"/);
  assert.match(adminHtml, /id="changePasswordConfirm"[\s\S]*maxlength="10"/);
  assert.match(adminHtml, /id="requestAdminRegistrationSenha"[\s\S]*maxlength="10"/);
  assert.match(adminHtml, /id="requestAdminRegistrationConfirm"[\s\S]*maxlength="10"/);
  assert.match(adminHtml, /id="changePasswordSaveButton"[\s\S]*disabled[\s\S]*>Salvar</);
  assert.match(adminHtml, /<tr><th>Chave<\/th><th>Nome<\/th><th>Perfil<\/th><th>Acessos<\/th><th>Ações<\/th><\/tr>/);
});

test('admin login utility buttons keep the requested black and white styling', () => {
  assert.match(adminCss, /\.auth-actions-secondary \{[\s\S]*margin-top:\s*10px;/);
  assert.match(adminCss, /\.auth-actions-secondary \.auth-utility-button \{[\s\S]*background:\s*#111827;[\s\S]*color:\s*#ffffff;/);
  assert.match(adminCss, /\.admin-status-badge\.is-pending \{[\s\S]*background:\s*#ffedd5;[\s\S]*color:\s*#c2410c;/);
});

test('admin change-password controller verifies the current password in real time and wires the new request-admin flow', () => {
  assert.match(adminJs, /changePasswordButton\.addEventListener\("click", openChangePasswordModal\);/);
  assert.match(adminJs, /postJson\("\/api\/admin\/auth\/verify-current-password", \{[\s\S]*senha_atual: currentPassword,[\s\S]*\}\);/);
  assert.match(adminJs, /postJson\("\/api\/admin\/auth\/change-password", \{[\s\S]*confirmar_senha: confirmPassword,[\s\S]*\}\);/);
  assert.match(adminJs, /changePasswordSaveButton\.disabled = !canSave;/);
  assert.match(adminJs, /newPassword !== currentPassword/);
  assert.match(adminJs, /requestAdminButton\.addEventListener\("click", openRequestAdminModal\);/);
  assert.match(adminJs, /fetchJson\(`\/api\/admin\/auth\/request-access\/status\?chave=\$\{encodeURIComponent\(chave\)\}`\)/);
  assert.match(adminJs, /postJson\("\/api\/admin\/auth\/request-access\/self-service", \{ chave \}\);/);
  assert.match(adminJs, /postJson\("\/api\/admin\/auth\/request-access\/self-service", \{[\s\S]*confirmar_senha: confirmarSenha,[\s\S]*\}\);/);
});

test('administrators table renders editable profiles and request approval actions', () => {
  assert.match(adminJs, /data-admin-profile-input="\$\{row\.id\}"/);
  assert.match(adminJs, /data-admin-approve="\$\{row\.id\}"/);
  assert.match(adminJs, /data-admin-reject="\$\{row\.id\}"/);
  assert.match(adminJs, /data-admin-revoke="\$\{row\.id\}"/);
  assert.match(adminJs, /data-admin-profile-save="\$\{row\.id\}"/);
  assert.match(adminJs, /postJson\(`\/api\/admin\/administrators\/requests\/\$\{id\}\/approve`, \{ perfil: profile \}\);/);
  assert.match(adminJs, /postJson\(`\/api\/admin\/administrators\/\$\{id\}\/profile`, \{ perfil: profile \}\);/);
});