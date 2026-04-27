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
  assert.match(adminHtml, /data-presence-primary-filter-label="checkin">Filtrar Horário</);
  assert.match(adminHtml, /data-presence-primary-filter-label="checkout">Filtrar Horário</);
  assert.match(adminHtml, /data-presence-primary-header-label="checkin">Horário</);
  assert.match(adminHtml, /data-presence-primary-header-label="checkout">Horário</);
  assert.match(adminCss, /\.presence-users-table \{[\s\S]*min-width:\s*1040px;[\s\S]*table-layout:\s*fixed;/);
  assert.match(adminCss, /\.presence-users-table th:nth-child\(2\),[\s\S]*\.presence-users-table td:nth-child\(2\) \{[\s\S]*width:\s*24%;/);
  assert.match(adminCss, /\.presence-users-table th:nth-child\(5\),[\s\S]*\.presence-users-table td:nth-child\(5\) \{[\s\S]*width:\s*17%;/);
});

test('presence tables use safe activity-time helpers and dynamic labels', () => {
  const adminJs = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/admin/app.js'),
    'utf8'
  );

  assert.match(adminJs, /let adminCanViewActivityTime = true;/);
  assert.match(adminJs, /function syncPresenceTimeLabels\(\) \{/);
  assert.match(adminJs, /function buildPresencePrimaryDisplayParts\(row, options = \{\}\) \{/);
  assert.match(adminJs, /function buildPresencePrimaryDisplay\(row, options = \{\}\) \{/);
  assert.match(adminJs, /function buildPresencePrimaryCell\(row, options = \{\}\) \{/);
  assert.match(adminJs, /activity_date_label/);
  assert.match(adminJs, /activity_time_label/);
  assert.match(adminJs, /activity_day_key/);
  assert.match(adminJs, /getPresencePrimaryColumnLabel\(\) \? "Horário" : "Data"|return canCurrentAdminViewActivityTime\(\) \? "Horário" : "Data";/);
  assert.match(adminJs, /return canCurrentAdminViewActivityTime\(\) \? "Filtrar Horário" : "Filtrar Data";/);
  assert.match(adminJs, /const filterLabel = document\.querySelector\(`\[data-presence-primary-filter-label="\$\{tableKey\}"\]`\);/);
  assert.match(adminJs, /filterLabel\.textContent = getPresencePrimaryFilterLabel\(\);/);
  assert.match(adminJs, /querySelector\("\.sortable-header span"\)\?\.textContent\?\.trim\(\)/);
  assert.match(adminJs, /makeEventDateTimeCellFromParts\(displayParts\.dateLabel, displayParts\.timeLabel\)/);
  assert.match(adminJs, /tr\.innerHTML = `<td>\$\{timeCell\.html\}<\/td><td>\$\{escapeHtml\(row\.nome\)\}<\/td>/);
  assert.match(adminJs, /const parsedDay = Date\.parse\(activityDayKey \? `\$\{activityDayKey\}T00:00:00Z` : ""\);/);
  assert.match(adminJs, /renderEmptyStateRow\(bodyId, 7, options\.emptyMessage \|\| "Nenhum registro encontrado\."\);/);
});

test('admin table variants stay limited to the slices that really lose a time column', () => {
  const adminJs = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/admin/app.js'),
    'utf8'
  );

  assert.match(adminCss, /\.forms-table--without-time \{/);
  assert.doesNotMatch(adminCss, /\.presence-users-table--without-time\b/);
  assert.doesNotMatch(adminCss, /\.events-table--without-time\b/);
  assert.match(adminJs, /function makeEventDateTimeCellFromParts\(dateLabel, timeLabel\) \{/);
  assert.match(adminJs, /<span class="event-cell event-datetime-cell">/);
  assert.match(adminJs, /normalizedTime \? `<span class="event-datetime-line">\$\{escapeHtml\(normalizedTime\)\}<\/span>` : ""/);
  assert.match(adminCss, /\.event-datetime-cell \{[\s\S]*display:\s*flex;[\s\S]*flex-direction:\s*column;[\s\S]*align-items:\s*center;/);
  assert.match(adminCss, /\.event-datetime-line \{[\s\S]*display:\s*block;[\s\S]*white-space:\s*nowrap;/);
});

test('admin shell centralizes the sensitive-time access state and resets it on auth transitions', () => {
  const adminJs = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/admin/app.js'),
    'utf8'
  );

  assert.match(adminJs, /let adminCanViewActivityTime = true;/);
  assert.match(adminJs, /function setAdminAccessState\(admin\) \{[\s\S]*adminAccessScope = admin\?\.access_scope === "limited" \? "limited" : "full";[\s\S]*allowedAdminTabs = normalizeAllowedAdminTabs\(admin\?\.allowed_tabs, adminAccessScope\);[\s\S]*adminCanViewActivityTime = Boolean\(admin\?\.can_view_activity_time\);[\s\S]*applyAdminTabVisibility\(\);[\s\S]*syncPresenceTimeLabels\(\);[\s\S]*\}/);
  assert.match(adminJs, /function resetAdminAccessState\(\) \{[\s\S]*adminAccessScope = "full";[\s\S]*allowedAdminTabs = getDefaultAllowedTabsForScope\(adminAccessScope\);[\s\S]*adminCanViewActivityTime = true;[\s\S]*applyAdminTabVisibility\(\);[\s\S]*syncPresenceTimeLabels\(\);[\s\S]*\}/);
  assert.match(adminJs, /function canCurrentAdminViewActivityTime\(\) \{[\s\S]*return adminCanViewActivityTime;[\s\S]*\}/);
  assert.match(adminJs, /function showAuthShell\(message = "", kind = "info"\) \{[\s\S]*resetAdminAccessState\(\);[\s\S]*\}/);
  assert.match(adminJs, /function showAdminShell\(admin\) \{[\s\S]*setAdminAccessState\(admin\);[\s\S]*\}/);
  assert.match(adminJs, /async function handleUnauthorized\(message\) \{[\s\S]*showAuthShell\(message \|\| "Sua sessão expirou\. Faça login novamente\.", "error"\);[\s\S]*\}/);
  assert.match(adminJs, /async function logout\(\) \{[\s\S]*showAuthShell\("Sessão encerrada com sucesso\.", "success"\);[\s\S]*\}/);
  assert.match(adminJs, /async function bootstrapAdmin\(\) \{[\s\S]*if \(!session\.authenticated \|\| !session\.admin\) \{[\s\S]*showAuthShell\("", "info"\);[\s\S]*return;[\s\S]*\}[\s\S]*showAdminShell\(session\.admin\);[\s\S]*\}/);
});

test('forms table assigns explicit widths to every visible column including Hora', () => {
  assert.match(adminHtml, /id="formsTable" class="responsive-table forms-table"/);
  assert.match(adminHtml, /id="refreshFormsButton"[\s\S]*id="clearFormsButton"/);
  assert.match(adminHtml, /<th data-forms-time-column-header>Hora<\/th>/);
  assert.match(adminCss, /\.forms-table th:nth-child\(5\),[\s\S]*\.forms-table td:nth-child\(5\) \{[\s\S]*width:\s*136px;/);
  assert.match(adminCss, /\.forms-table th:nth-child\(9\),[\s\S]*\.forms-table td:nth-child\(9\) \{[\s\S]*width:\s*88px;/);
  assert.match(adminCss, /\.forms-table--without-time \{[\s\S]*min-width:\s*892px;/);
  assert.match(adminCss, /\.forms-table--without-time th\[data-forms-time-column-header\],[\s\S]*\.forms-table--without-time td:nth-child\(9\) \{[\s\S]*display:\s*none;/);
});

test('forms table renders safe received-time fields separately from raw timestamps', () => {
  const adminJs = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/admin/app.js'),
    'utf8'
  );

  assert.match(adminJs, /function makeEventDateTimeCellFromParts\(dateLabel, timeLabel\) \{/);
  assert.match(adminJs, /function getFormsColumnCount\(includeTime = canCurrentAdminViewActivityTime\(\)\) \{/);
  assert.match(adminJs, /function syncFormsTimeColumnVisibility\(\) \{/);
  assert.match(adminJs, /formsTable\.classList\.toggle\("forms-table--without-time", !canViewTime\);/);
  assert.match(adminJs, /formsTimeHeader\.hidden = !canViewTime;/);
  assert.match(adminJs, /const canViewTime = syncFormsTimeColumnVisibility\(\);/);
  assert.match(adminJs, /makeEventDateTimeCellFromParts\(row\.recebimento_date_label, row\.recebimento_time_label\)/);
  assert.match(adminJs, /renderEmptyStateRow\("formsBody", getFormsColumnCount\(canViewTime\), "Nenhum evento do provider encontrado no historico sincronizado\."\);/);
  assert.match(adminJs, /if \(canViewTime\) \{[\s\S]*cells\.push\(`<td>\$\{makeEventCell\(row\.hora \?\? "-"\)\}<\/td>`\);[\s\S]*\}/);
  assert.match(adminJs, /makeEventCell\(row\.hora \?\? "-"\)/);
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