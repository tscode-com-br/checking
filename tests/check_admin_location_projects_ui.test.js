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

test('locations table shows the Projetos column before Local', () => {
  assert.match(adminHtml, /<tr><th>Projetos<\/th><th>Local<\/th><th>Coordenadas<\/th><th>Tolerância<\/th><th>Ações<\/th><\/tr>/);
});

test('locations rows render a project picker button and persist selected projects on save', () => {
  assert.match(adminJs, /class="secondary-button location-projects-button"[\s\S]*data-location-projects-toggle="\$\{row\.id\}"[\s\S]*>Projetos<\/button>/);
  assert.match(adminJs, /class="location-projects-panel"/);
  assert.match(adminJs, /data-location-project-option="\$\{row\.id\}"/);
  assert.match(adminJs, /const projects = normalizeProjectNames\(row\.projects\);/);
  assert.match(adminJs, /projects,/);
  assert.match(adminJs, /if \(target\.dataset\.locationProjectsToggle\) \{/);
  assert.match(adminJs, /if \(row\.projectPickerOpen\) \{[\s\S]*saveLocationRow\(row\.id\)\.catch/);
  assert.match(adminJs, /row\.projectPickerOpen = true;/);
});