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

test('check-in and check-out tables share the same fixed-width class', () => {
  assert.match(adminHtml, /id="tab-checkin"[\s\S]*class="responsive-table presence-users-table"/);
  assert.match(adminHtml, /id="tab-checkout"[\s\S]*class="responsive-table presence-users-table"/);
  assert.match(adminCss, /\.presence-users-table \{[\s\S]*min-width:\s*1040px;[\s\S]*table-layout:\s*fixed;/);
  assert.match(adminCss, /\.presence-users-table th:nth-child\(2\),[\s\S]*\.presence-users-table td:nth-child\(2\) \{[\s\S]*width:\s*24%;/);
  assert.match(adminCss, /\.presence-users-table th:nth-child\(5\),[\s\S]*\.presence-users-table td:nth-child\(5\) \{[\s\S]*width:\s*17%;/);
});

test('forms table assigns explicit widths to every visible column including Hora', () => {
  assert.match(adminHtml, /class="responsive-table forms-table"/);
  assert.match(adminHtml, /id="refreshFormsButton"[\s\S]*id="clearFormsButton"/);
  assert.match(adminCss, /\.forms-table th:nth-child\(5\),[\s\S]*\.forms-table td:nth-child\(5\) \{[\s\S]*width:\s*136px;/);
  assert.match(adminCss, /\.forms-table th:nth-child\(9\),[\s\S]*\.forms-table td:nth-child\(9\) \{[\s\S]*width:\s*88px;/);
});

test('forms tab wires the clear button to delete only the Forms records and refresh the table state', () => {
  const adminJs = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/admin/app.js'),
    'utf8'
  );

  assert.match(adminJs, /async function clearForms\(\) \{/);
  assert.match(adminJs, /window\.confirm\("Deseja remover todos os registros da tabela Forms\?"\)/);
  assert.match(adminJs, /deleteJson\("\/api\/admin\/forms"\)/);
  assert.match(adminJs, /const clearFormsButton = document\.getElementById\("clearFormsButton"\);/);
  assert.match(adminJs, /runFormsClear\(clearFormsButton\)/);
  assert.match(adminJs, /updateFormsClearButtonState\(\);/);
});