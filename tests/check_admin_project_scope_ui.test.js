const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const adminHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/index.html'),
  'utf8'
);

const adminJs = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/app.js'),
  'utf8'
);

const adminCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/styles.css'),
  'utf8'
);

test('administrators table shows the Projetos column between Perfil and Acessos', () => {
  assert.match(adminHtml, /<tr><th>Chave<\/th><th>Nome<\/th><th>Perfil<\/th><th>Projetos<\/th><th>Acessos<\/th><th>Ações<\/th><\/tr>/);
});

test('administrator rows render project checkboxes while request rows stay readonly', () => {
  assert.match(adminJs, /function makeAdministratorProjectOptions\(row\) \{/);
  assert.match(adminJs, /class="admin-projects-panel"/);
  assert.match(adminJs, /data-admin-project-option="\$\{row\.id\}"/);
  assert.match(adminJs, /Defina os projetos apos aprovar o administrador\./);
  assert.match(adminCss, /\.admin-projects-panel \{[\s\S]*display: grid;[\s\S]*max-height: 220px;/);
  assert.match(adminCss, /\.admin-project-option \{[\s\S]*border-radius: 10px;[\s\S]*background: #f8fafc;/);
});

test('administrator profile save sends monitored_projects and blocks zero selected projects', () => {
  assert.match(adminJs, /function readAdministratorMonitoredProjects\(id\) \{/);
  assert.match(adminJs, /Selecione ao menos um projeto para o administrador\./);
  assert.match(adminJs, /const monitoredProjects = readAdministratorMonitoredProjects\(id\);/);
  assert.match(adminJs, /postJson\(`\/api\/admin\/administrators\/\$\{id\}\/profile`, \{[\s\S]*perfil: profile,[\s\S]*monitored_projects: monitoredProjects,[\s\S]*\}\)/);
  assert.match(adminJs, /resetProjectEditor\(\);[\s\S]*await loadProjects\(\);[\s\S]*await Promise\.all\(\[loadAdministrators\(\), loadPending\(\), loadRegisteredUsers\(\)\]\);/);
  assert.match(adminJs, /setStatus\("Projeto removido com sucesso", true\);[\s\S]*await loadProjects\(\);[\s\S]*await Promise\.all\(\[loadAdministrators\(\), loadPending\(\), loadRegisteredUsers\(\)\]\);/);
});