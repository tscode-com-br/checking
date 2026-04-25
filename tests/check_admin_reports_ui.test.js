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

test('admin reports tab is inserted between cadastro and eventos with the expected search and results structure', () => {
  assert.match(adminHtml, /data-tab="cadastro"[\s\S]*data-tab="relatorios"[\s\S]*data-tab="eventos"/);
  assert.match(adminHtml, /<section id="tab-relatorios" class="tab reports-tab">[\s\S]*<h2>Relatórios<\/h2>/);
  assert.match(adminHtml, /class="project-editor-panel reports-search-panel"/);
  assert.match(adminHtml, /class="presence-controls-grid reports-search-grid"/);
  assert.match(adminHtml, /class="locations-actions-bar reports-search-actions"/);
  assert.match(adminHtml, /class="project-editor-panel reports-results-panel"/);
  assert.match(adminHtml, /<select id="reportsSearchChave">[\s\S]*<option value="">Selecione uma chave<\/option>/);
  assert.match(adminHtml, /<select id="reportsSearchNome">[\s\S]*<option value="">Selecione um nome<\/option>/);
  assert.match(adminHtml, /id="reportsClearButton"[\s\S]*>Limpar</);
  assert.match(adminHtml, /id="reportsSearchButton"[\s\S]*>Buscar</);
  assert.match(adminHtml, /id="reportsExportButton"[\s\S]*>Exportar</);
  assert.match(adminHtml, /id="reportsResultsBody" class="reports-results-body"/);
  assert.match(adminHtml, /id="reportsPersonTitle">Nenhuma busca realizada</);
  assert.match(adminHtml, /id="reportsPersonMeta" class="section-header-copy">Selecione uma chave ou um nome para carregar o relatório\./);
});

test('admin reports controller keeps the tab full-admin only and wires the mutual search flow', () => {
  assert.match(adminJs, /relatorios:\s*"Relatórios"/);
  assert.match(adminJs, /const DEFAULT_ADMIN_ALLOWED_TABS = Object\.freeze\(\["checkin", "checkout", "forms", "inactive", "cadastro", "relatorios", "eventos", "banco-dados"\]\);/);
  assert.match(adminJs, /const LIMITED_ADMIN_ALLOWED_TABS = Object\.freeze\(\["checkin", "checkout"\]\);/);
  assert.match(adminJs, /async function loadRegisteredUsers\(\) \{[\s\S]*fetchJson\("\/api\/admin\/users"\);[\s\S]*populateReportsSearchOptions\(rows\);/);
  assert.match(adminJs, /function populateReportsSearchOptions\(rows\) \{[\s\S]*Selecione uma chave[\s\S]*Selecione um nome/);
  assert.match(adminJs, /const label = entry\.count > 1[\s\S]*usuários; use a chave/);
  assert.match(adminJs, /reportsSearchNomeInput\.disabled = hasChave;/);
  assert.match(adminJs, /reportsSearchChaveInput\.disabled = hasNome;/);
  assert.match(adminJs, /fetchJson\(`\/api\/admin\/reports\/events\?\$\{query\.toString\(\)\}`\)/);
  assert.match(adminJs, /fetchBlob\(`\/api\/admin\/reports\/events\/export\?\$\{reportsExportQueryString\}`,\s*"relatorio\.xlsx"\);/);
  assert.match(adminJs, /reportsClearButton\.addEventListener\("click", \(\) => \{\s*resetReportsView\(\{ focusPrimary: true \}\);\s*\}\);/);
  assert.match(adminJs, /reportsExportButton\.addEventListener\("click", \(\) => \{\s*downloadReportsExport\(\);\s*\}\);/);
  assert.match(adminJs, /row\.source_label \|\| row\.source \|\| "-"/);
  assert.match(adminJs, /class="responsive-table reports-results-table"/);
  assert.match(adminJs, /if \(focusPrimary && reportsSearchChaveInput\) \{\s*reportsSearchChaveInput\.focus\(\);\s*\}/);
  assert.match(adminJs, /if \(activeTab === "relatorios"\) \{\s*return;\s*\}/);
  assert.match(adminJs, /reportsSearchButton\.addEventListener\("click", \(\) => \{\s*submitReportsSearch\(\);\s*\}\);/);
  assert.match(adminJs, /input\.addEventListener\("change", \(\) => \{/);
});

test('admin reports styles keep tabs uniform and align the new report search layout', () => {
  assert.match(adminCss, /\.tabs \{[\s\S]*display:\s*grid;[\s\S]*grid-template-columns:\s*repeat\(auto-fit, minmax\(128px, 1fr\)\);/);
  assert.match(adminCss, /\.tabs button \{[\s\S]*width:\s*100%;[\s\S]*justify-content:\s*center;[\s\S]*white-space:\s*normal;/);
  assert.match(adminCss, /\.reports-search-grid \{[\s\S]*grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\);/);
  assert.match(adminCss, /\.reports-search-actions \{[\s\S]*gap:\s*10px;[\s\S]*justify-content:\s*flex-end;/);
  assert.match(adminCss, /\.reports-results-header \{[\s\S]*align-items:\s*flex-start;/);
  assert.match(adminCss, /\.reports-results-table \{[\s\S]*table-layout:\s*fixed;/);
  assert.match(adminCss, /\.reports-results-table col\.reports-col-timezone \{[\s\S]*width:\s*20%;/);
  assert.match(adminCss, /\.reports-results-body \{[\s\S]*display:\s*grid;[\s\S]*gap:\s*16px;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.tabs \{[\s\S]*grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\);[\s\S]*\.reports-search-grid \{[\s\S]*grid-template-columns:\s*1fr;[\s\S]*\.reports-results-header \{[\s\S]*flex-direction:\s*column;/);
});