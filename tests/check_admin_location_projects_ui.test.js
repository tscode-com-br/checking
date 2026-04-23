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

test('locations table shows the Projetos column before Local', () => {
  assert.match(adminHtml, /<tr><th>Projetos<\/th><th>Local<\/th><th>Vértices do Polígono<\/th><th>Tolerância<\/th><th>Ações<\/th><\/tr>/);
});

test('locations rows render a project picker button and persist selected projects on save', () => {
  assert.match(adminJs, /class="secondary-button location-projects-button"[\s\S]*data-location-projects-toggle="\$\{row\.id\}"[\s\S]*\$\{row\.isEditing \? "" : 'disabled title="Clique em Editar antes de alterar os projetos desta localização\."'\}[\s\S]*>Projetos<\/button>/);
  assert.match(adminJs, /class="location-projects-panel"/);
  assert.match(adminJs, /data-location-project-option="\$\{row\.id\}"/);
  assert.match(adminJs, /const projects = normalizeProjectNames\(row\.projects\);/);
  assert.match(adminJs, /projects,/);
  assert.match(adminJs, /const button = target instanceof Element \? target\.closest\("button"\) : null;/);
  assert.match(adminJs, /if \(button\.dataset\.locationProjectsToggle\) \{/);
  assert.match(adminJs, /if \(!row\.isEditing\) \{[\s\S]*Clique em Editar antes de alterar os projetos da localização\.[\s\S]*return;/);
  assert.match(adminJs, /if \(row\.projectPickerOpen\) \{[\s\S]*saveLocationRow\(row\.id\)\.catch/);
  assert.match(adminCss, /\.location-projects-panel \{[\s\S]*box-sizing: border-box;[\s\S]*max-width: 100%;/);
  assert.match(adminCss, /\.location-actions \{[\s\S]*position: relative;[\s\S]*z-index: 1;/);
  assert.match(adminJs, /captureLocationRowDraft\(row\.id\);[\s\S]*row\.projectPickerOpen = true;/);
  assert.match(adminJs, /row\.projectPickerOpen = true;/);
});