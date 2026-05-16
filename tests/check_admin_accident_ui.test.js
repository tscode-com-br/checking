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

test('test_accident_button_visible_after_login', () => {
  assert.match(adminHtml, /id="accidentToggleButton"/);
  assert.match(adminHtml, /class="accident-button-label"/);
  assert.match(adminJs, /accidentToggleButtonLogin\.classList\.remove\("hidden"\)/);
});

test('test_accident_button_label_changes_on_state', () => {
  assert.match(adminJs, /btn\.querySelector\("\.accident-button-label"\)\.textContent = state\.isActive \? "Acidente Reportado" : "Reportar Acidente"/);
  assert.match(adminJs, /btn\.setAttribute\("aria-pressed", state\.isActive \? "true" : "false"\)/);
});

test('test_wizard_advances_after_project_selection', () => {
  assert.match(adminJs, /function renderProjectRadios\(projects\)/);
  assert.match(adminJs, /accidentWizardData\.projectId = parseInt\(inp\.value, 10\)/);
  assert.match(adminJs, /document\.getElementById\("accidentWizardProjectAdvance"\)\.disabled = false/);
  assert.match(adminJs, /async function advanceWizardToLocations\(\)/);
  assert.match(adminJs, /\/api\/admin\/accidents\/wizard\/locations\?project_id=/);
});

test('test_wizard_advances_after_location_selection', () => {
  assert.match(adminJs, /function renderLocationRadios\(locations\)/);
  assert.match(adminJs, /accidentWizardData\.locationId = parseInt\(inp\.value, 10\)/);
  assert.match(adminJs, /accidentWizardData\.locationRegistered = true/);
  assert.match(adminJs, /function advanceWizardToConfirm\(\)/);
  assert.match(adminJs, /_hideAccidentModal\("accidentWizardLocationModal"\)/);
  assert.match(adminJs, /_showAccidentModal\("accidentWizardConfirmModal"\)/);
});

test('test_confirm_text_includes_project_and_location', () => {
  assert.match(adminJs, /accidentWizardConfirmText[\s\S]*\.textContent[\s\S]*projName[\s\S]*locName/);
  assert.match(adminJs, /async function submitAccidentOpen\(\)/);
  assert.match(adminJs, /\/api\/admin\/accidents\/open/);
  assert.match(adminJs, /method: "POST"/);
});

test('test_situacao_table_renders_rows_in_order', () => {
  assert.match(adminHtml, /id="situacaoPessoalBody"/);
  assert.match(adminJs, /function renderSituacaoPessoal\(rows\)/);
  assert.match(adminJs, /situacao-row-\$\{row\.row_color\}/);
  assert.match(adminJs, /rows\.forEach\(\(row\) =>/);
  assert.match(adminJs, /document\.getElementById\("accidentSectionCount"\)\.textContent = `\$\{rows\.length\} registros`/);
});

test('test_accidents_table_renders_history', () => {
  assert.match(adminHtml, /id="accidentsBody"/);
  assert.match(adminJs, /function renderAccidentsHistory\(rows\)/);
  assert.match(adminJs, /async function fetchAccidentsHistory\(\)/);
  assert.match(adminJs, /\/api\/admin\/accidents/);
  assert.match(adminJs, /download-pending/);
  assert.match(adminJs, /row\.download_ready/);
});

test('test_delete_button_only_for_perfil_9', () => {
  assert.match(adminJs, /row\.can_delete/);
  assert.match(adminJs, /secondary-button delete-button/);
  assert.match(adminJs, /\/api\/admin\/accidents\/\$\{row\.id\}/);
  assert.match(adminJs, /method: "DELETE"/);
});
