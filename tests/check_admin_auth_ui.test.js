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
  assert.match(adminHtml, /Perfil 0 acessa apenas Check-In e Check-Out;/);
  assert.match(adminHtml, /A visualização dos horários das atividades é restrita ao perfil 9\./);
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
  assert.match(adminHtml, /<tr><th>Chave<\/th><th>Nome<\/th><th>Perfil<\/th><th>Projetos<\/th><th>Acessos<\/th><th>Ações<\/th><\/tr>/);
});

test('admin login utility buttons keep the requested black and white styling', () => {
  assert.match(adminCss, /\.auth-actions-secondary \{[\s\S]*margin-top:\s*10px;/);
  assert.match(adminCss, /\.auth-actions-secondary \.auth-utility-button \{[\s\S]*background:\s*#111827;[\s\S]*color:\s*#ffffff;/);
  assert.match(adminCss, /\.admin-status-badge\.is-pending \{[\s\S]*background:\s*#ffedd5;[\s\S]*color:\s*#c2410c;/);
});

test('admin change-password controller verifies the current password in real time and wires the new request-admin flow', () => {
  assert.match(adminHtml, /<nav class="tabs" aria-label="Seções do painel administrativo">/);
  assert.match(adminJs, /changePasswordButton\.addEventListener\("click", openChangePasswordModal\);/);
  assert.match(adminJs, /function setAdminAccessState\(admin\) \{/);
  assert.match(adminJs, /allowedAdminTabs = normalizeAllowedAdminTabs\(admin\?\.allowed_tabs, adminAccessScope\);/);
  assert.match(adminJs, /function applyAdminTabVisibility\(\) \{/);
  assert.match(adminJs, /function syncAdminResponsiveState\(options = \{\}\) \{/);
  assert.match(adminJs, /function scheduleAdminResponsiveSync\(options = \{\}\) \{/);
  assert.match(adminJs, /const MOBILE_FILTER_PANEL_KEYS = Object\.freeze\(\["checkin", "checkout", "inactive", "relatorios"\]\);/);
  assert.match(adminJs, /function syncAdminShellResponsiveState\(snapshot = buildAdminResponsiveStateSnapshot\(\)\) \{[\s\S]*syncAdminTabStrip\(snapshot\);[\s\S]*syncAdminMobileFilterPanels\(\);[\s\S]*\}/);
  assert.match(adminJs, /function syncAdminTabStrip\(snapshot = buildAdminResponsiveStateSnapshot\(\)\) \{[\s\S]*tabs\.dataset\.adminActiveTab = activeTab;[\s\S]*activeButton\.scrollIntoView\(\{ block: "nearest", inline: "center" \}\);[\s\S]*\}/);
  assert.match(adminJs, /function syncAdminMobileFilterPanel\(panelKey\) \{[\s\S]*panel\.hidden = !expanded;[\s\S]*button\.classList\.toggle\("hidden", !mobileViewport\);[\s\S]*button\.setAttribute\("aria-expanded", String\(expanded\)\);[\s\S]*\}/);
  assert.match(adminJs, /document\.querySelectorAll\("\[data-filter-toggle\]"\)\.forEach\(\(button\) => \{[\s\S]*toggleAdminMobileFilterPanel\(button\.dataset\.filterToggle\);[\s\S]*\}\);/);
  assert.match(adminJs, /if \(!isAdminTabAllowed\(tab\)\) \{\s*return;\s*\}/);
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
  assert.match(adminJs, /data-admin-project-option="\$\{row\.id\}"/);
  assert.match(adminJs, /data-admin-approve="\$\{row\.id\}"/);
  assert.match(adminJs, /data-admin-reject="\$\{row\.id\}"/);
  assert.match(adminJs, /data-admin-revoke="\$\{row\.id\}"/);
  assert.match(adminJs, /data-admin-profile-save="\$\{row\.id\}"/);
  assert.match(adminJs, /postJson\(`\/api\/admin\/administrators\/requests\/\$\{id\}\/approve`, \{ perfil: profile \}\);/);
  assert.match(adminJs, /function getAdministratorProjectNames\(row\) \{[\s\S]*normalizeUserProjectMemberships\(row\?\.projects\);[\s\S]*\}/);
  assert.match(adminJs, /function getAdministratorProjectsSummary\(row\) \{/);
  assert.match(adminJs, /Projetos reais/);
  assert.match(adminJs, /Esses vinculos definem o escopo real do administrador\./);
  assert.match(adminJs, /const projects = readAdministratorProjects\(id\);/);
  assert.match(adminJs, /postJson\(`\/api\/admin\/administrators\/\$\{id\}\/profile`, \{[\s\S]*perfil: profile,[\s\S]*projects,[\s\S]*\}\);/);
  assert.doesNotMatch(adminJs, /monitored_projects/);
});

test('pending and registered users tables use a checkbox project picker with plural membership payloads', () => {
  assert.match(adminHtml, /<tr><th>RFID<\/th><th>Nome<\/th><th>Chave<\/th><th>Projetos<\/th><th>Ações<\/th><\/tr>/);
  assert.match(adminHtml, /<tr><th>RFID<\/th><th>Nome<\/th><th>Chave<\/th><th>Perfil<\/th><th>Projetos<\/th><th>Endereço<\/th><th>ZIP Code<\/th><th>Cargo<\/th><th>Email<\/th><th>Ações<\/th><\/tr>/);
  assert.match(adminJs, /class="secondary-button membership-projects-button"[\s\S]*data-project-membership-toggle="\$\{escapeHtml\(projectMembershipKey\)\}"[\s\S]*>Select<\/button>/);
  assert.match(adminJs, /class="membership-projects-panel" hidden><\/div>/);
  assert.match(adminJs, /data-project-membership-back="\$\{escapeHtml\(editorKey\)\}">Back<\/button>/);
  assert.match(adminJs, /data-project-membership-apply="\$\{escapeHtml\(editorKey\)\}"[\s\S]*>Save<\/button>/);
  assert.match(adminJs, /const projetos = getProjectMembershipSelectionForSubmit\("pending", id\);/);
  assert.match(adminJs, /postJson\("\/api\/admin\/users", \{ rfid, nome, chave, projetos \}\)/);
  assert.match(adminJs, /const projetos = getProjectMembershipSelectionForSubmit\("user", normalizedUserId\);/);
  assert.match(adminJs, /postJson\("\/api\/admin\/users", \{[\s\S]*perfil: Number\(perfilValue\),[\s\S]*projetos,[\s\S]*end_rua: endRua \|\| null,[\s\S]*\}\);/);
  assert.match(adminJs, /if \(button\.dataset\.projectMembershipToggle\) \{[\s\S]*openProjectMembershipPanelByKey\(button\.dataset\.projectMembershipToggle\)\.catch/);
});
